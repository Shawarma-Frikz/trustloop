import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import pytest
from joblib import dump

from app.artifact_loader import ArtifactError, load_artifact_bundle, verify_artifact_bundle
from app.main import app, initialize_candidate_artifact
from app.train_baseline import TRAINING_CONFIG, _make_pipeline


VERSION = "tl-text-1.1.0"
REQUIRED_FILES = (
    "model.joblib",
    "calibration.json",
    "metrics.json",
    "model-card.md",
    "dataset-manifest.json",
    "requirements.lock",
    "training-report.json",
    "calibration-explanation-report.json",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _make_test_bundle(path: Path) -> Path:
    path.mkdir()
    config = json.loads(TRAINING_CONFIG.read_text(encoding="utf-8"))
    model = _make_pipeline(config, 0.1)
    model.fit(
        [
            "I used this lamp every evening and it works beside my chair",
            "The lamp stays bright during my reading time each evening",
            "Perfect amazing lamp buy now for the best ever experience",
            "Guaranteed perfect product buy now and order today for best results",
        ],
        ["organic", "organic", "manipulated", "manipulated"],
    )
    dump(model, path / "model.joblib")
    file_content = {
        "calibration.json": {"method": "sigmoid", "modelVersionCandidate": VERSION},
        "metrics.json": {"modelVersion": VERSION, "productionDecision": "UNKNOWN"},
        "model-card.md": "# Test model card\n",
        "dataset-manifest.json": {"manifestVersion": "test"},
        "requirements.lock": (
            f"# Python {platform.python_version()}\n"
            f"scikit-learn=={importlib.metadata.version('scikit-learn')}\n"
            f"joblib=={importlib.metadata.version('joblib')}\n"
        ),
        "training-report.json": {"status": "test"},
        "calibration-explanation-report.json": {"status": "test"},
    }
    for name, value in file_content.items():
        payload = value if isinstance(value, str) else json.dumps(value)
        (path / name).write_text(payload, encoding="utf-8")
    files = {
        name: {"sha256": _sha((path / name).read_bytes()), "bytes": (path / name).stat().st_size}
        for name in REQUIRED_FILES
    }
    artifact_manifest = {
        "formatVersion": "1",
        "modelVersion": VERSION,
        "artifactStatus": "EXPERIMENTAL_NOT_FOR_SERVING",
        "productionDecision": "UNKNOWN",
        "files": files,
    }
    manifest_bytes = (json.dumps(artifact_manifest, indent=2) + "\n").encode("utf-8")
    (path / "artifact-manifest.json").write_bytes(manifest_bytes)
    (path / "artifact.sha256").write_text(f"{_sha(manifest_bytes)}  artifact-manifest.json\n", encoding="ascii")
    return path


def test_versioned_bundle_verifies_and_loads_offline(tmp_path):
    bundle = _make_test_bundle(tmp_path / "bundle")

    manifest = verify_artifact_bundle(bundle, VERSION)
    loaded = load_artifact_bundle(bundle, VERSION)

    assert manifest["productionDecision"] == "UNKNOWN"
    assert set(loaded["model"].named_steps) == {"features", "clf"}
    assert loaded["calibration"]["modelVersionCandidate"] == VERSION


def test_bundle_rejects_corruption_and_version_mismatch(tmp_path):
    bundle = _make_test_bundle(tmp_path / "bundle")
    (bundle / "metrics.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactError, match="checksum mismatch: metrics.json"):
        verify_artifact_bundle(bundle, VERSION)

    with pytest.raises(ArtifactError, match="expected version"):
        verify_artifact_bundle(bundle, "tl-text-9.9.9")


def test_startup_artifact_initialization_loads_candidate_without_marking_ready(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    sentinel = {"manifest": {"servingEnabled": False}}
    calls = []

    def fake_loader(path, expected_version):
        calls.append((Path(path), expected_version))
        return sentinel

    monkeypatch.setattr("app.main.load_artifact_bundle", fake_loader)
    monkeypatch.setenv("TRUSTLOOP_ARTIFACT_DIR", str(bundle))
    monkeypatch.setenv("TRUSTLOOP_EXPECTED_MODEL_VERSION", VERSION)

    initialize_candidate_artifact(app, bundle, VERSION)
    assert app.state.artifact_bundle_verified is True
    assert app.state.candidate_artifact is sentinel
    assert app.state.model_loaded is False
    assert calls == [(bundle, VERSION)]
