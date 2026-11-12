import json
import logging
import asyncio
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator

from app.main import create_app


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "v1"
VERSION = "tl-text-1.1.0"
SENTINEL = "private-review-sentinel-9f31"
REVIEW_KEY_SENTINEL = "private-review-key-sentinel-9f31"
URL_SENTINEL = "private-url-sentinel-9f31"
HOST_SENTINEL = "private-host-sentinel-9f31.example"


class WarmModel:
    def __init__(self):
        self.warm_inputs = []

    def predict_proba(self, texts):
        self.warm_inputs.extend(texts)
        return [[0.5, 0.5] for _ in texts]


def make_ready_client(monkeypatch, tmp_path, token="test-internal-secret"):
    model = WarmModel()
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()

    def fake_load(_path, expected_version):
        assert expected_version == VERSION
        return {
            "manifest": {
                "modelVersion": VERSION,
                "artifactStatus": "EXPERIMENTAL_NOT_FOR_SERVING",
                "productionDecision": "UNKNOWN",
                "servingEnabled": False,
            },
            "model": model,
        }

    monkeypatch.setattr("app.main.load_artifact_bundle", fake_load)
    application = create_app(
        artifact_dir=artifact_dir,
        expected_model_version=VERSION,
        scoring_token=token,
    )
    return application, model


def requests(application, calls):
    async def execute():
        async with application.router.lifespan_context(application):
            transport = httpx.ASGITransport(app=application)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return [
                    await client.request(method, path, **kwargs)
                    for method, path, kwargs in calls
                ]

    return asyncio.run(execute())


def schema(name):
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_warms_candidate_and_serves_contract_health_version_and_unknown_batch(monkeypatch, tmp_path):
    application, model = make_ready_client(monkeypatch, tmp_path)
    request = {
        "reviews": [
            {"reviewKey": "review-A", "text": "Short sample", "batchDuplicate": False},
            {
                "reviewKey": "review-B",
                "text": "This review has enough words to pass the minimum length but the model has not passed the in-domain approval gate.",
                "batchDuplicate": True,
            },
        ]
    }

    health, version, response = requests(application, [
        ("GET", "/health", {}),
        ("GET", "/version", {}),
        ("POST", "/score", {"json": request, "headers": {
            "X-Internal-Token": "test-internal-secret", "X-Request-Id": "req-42",
        }}),
    ])

    assert health.status_code == 200
    assert health.json() == {"status": "ready"}
    Draft202012Validator(schema("health-response.schema.json")).validate(health.json())
    assert version.status_code == 200
    Draft202012Validator(schema("version-response.schema.json")).validate(version.json())
    assert version.json()["expectedModelVersion"] == VERSION
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-42"
    assert response.json() == {
        "results": [
            {
                "reviewKey": "review-A",
                "status": "UNKNOWN",
                "reasonCode": "INSUFFICIENT_TEXT",
                "signals": [],
                "modelVersion": VERSION,
                "engine": "MODEL",
            },
            {
                "reviewKey": "review-B",
                "status": "UNKNOWN",
                "reasonCode": "SCORING_UNAVAILABLE",
                "signals": [],
                "modelVersion": VERSION,
                "engine": "MODEL",
            },
        ]
    }
    Draft202012Validator(schema("score-response.schema.json")).validate(response.json())
    assert len(model.warm_inputs) == 1
    assert "batchDuplicate" not in response.text


def test_token_is_required_and_compared_without_exposing_it(monkeypatch, tmp_path):
    application, _model = make_ready_client(monkeypatch, tmp_path)
    request = {"reviews": [{"reviewKey": "r1", "text": "A review with enough words to satisfy the minimum count even though its model is unavailable now.", "batchDuplicate": False}]}
    missing, wrong = requests(application, [
        ("POST", "/score", {"json": request}),
        ("POST", "/score", {"json": request, "headers": {"X-Internal-Token": "wrong-secret"}}),
    ])

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert "test-internal-secret" not in missing.text + wrong.text
    assert "wrong-secret" not in missing.text + wrong.text
    Draft202012Validator(schema("error-response.schema.json")).validate(wrong.json())


def test_invalid_request_and_oversized_payload_have_safe_error_envelopes(monkeypatch, tmp_path):
    application, _model = make_ready_client(monkeypatch, tmp_path)
    invalid, oversized = requests(application, [
        ("POST", "/score", {"json": {"reviews": []}, "headers": {"X-Internal-Token": "test-internal-secret"}}),
        ("POST", "/score", {"content": b" " * 131_073, "headers": {
            "X-Internal-Token": "test-internal-secret", "Content-Type": "application/json",
        }}),
    ])

    assert invalid.status_code == 400
    assert oversized.status_code == 413
    Draft202012Validator(schema("error-response.schema.json")).validate(invalid.json())
    Draft202012Validator(schema("error-response.schema.json")).validate(oversized.json())


def test_logs_and_responses_never_contain_review_text(monkeypatch, tmp_path, caplog):
    application, _model = make_ready_client(monkeypatch, tmp_path)
    caplog.set_level(logging.INFO, logger="trustloop.scoring")
    request = {"reviews": [{"reviewKey": REVIEW_KEY_SENTINEL, "text": f"{SENTINEL} this is enough words in a longer review text to pass the service minimum word check.", "batchDuplicate": False}]}
    (response,) = requests(application, [
        ("POST", "/score", {"json": request, "headers": {
            "X-Internal-Token": "test-internal-secret",
            "X-Page-Url": f"https://{URL_SENTINEL}.example/private/path?query=hidden",
            "X-Page-Hostname": HOST_SENTINEL,
        }}),
    ])

    assert response.status_code == 200
    assert SENTINEL not in response.text
    for private_value in (SENTINEL, REVIEW_KEY_SENTINEL, URL_SENTINEL, HOST_SENTINEL):
        assert private_value not in caplog.text
    assert "test-internal-secret" not in caplog.text


def test_service_is_not_ready_without_artifact(tmp_path):
    absent_artifact_app = create_app(
        artifact_dir=tmp_path / "missing",
        expected_model_version=VERSION,
        scoring_token="configured",
    )
    (response,) = requests(absent_artifact_app, [("GET", "/health", {})])
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_service_is_not_ready_without_internal_token(monkeypatch, tmp_path):
    monkeypatch.delenv("TRUSTLOOP_SCORING_TOKEN", raising=False)
    application, _model = make_ready_client(monkeypatch, tmp_path, token=None)
    (response,) = requests(application, [("GET", "/health", {})])
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

