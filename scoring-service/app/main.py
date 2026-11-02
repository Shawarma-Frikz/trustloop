"""Loopback-only, token-gated scoring boundary for the internal API."""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.artifact_loader import ArtifactError, load_artifact_bundle
from app.contract_constants import MAX_REQUEST_BYTES, MIN_REVIEW_WORDS
from app.schemas import (
    ErrorResponse,
    HealthResponse,
    ScoreRequest,
    ScoreResponse,
    VersionResponse,
)

SERVICE_VERSION = "0.0.2"
DEFAULT_MODEL_VERSION = "tl-text-1.1.0"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / DEFAULT_MODEL_VERSION
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
logger = logging.getLogger("trustloop.scoring")


def _read_request_id(scope: dict) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == b"x-request-id":
            try:
                candidate = value.decode("ascii")
            except UnicodeDecodeError:
                break
            if REQUEST_ID_PATTERN.fullmatch(candidate):
                return candidate
            break
    return str(uuid.uuid4())


def initialize_candidate_artifact(application: FastAPI, artifact_dir: Path, expected_version: str) -> None:
    application.state.candidate_artifact = None
    application.state.artifact_bundle_verified = False
    application.state.artifact_warmed = False
    application.state.model_loaded = False
    application.state.model_serving_enabled = False
    if artifact_dir.exists():
        bundle = load_artifact_bundle(artifact_dir, expected_version)
        # Warm locally before declaring the service ready. The candidate may
        # still be forbidden to score until the frozen in-domain gate passes.
        bundle["model"].predict_proba(["TrustLoop startup warm-up review text."])
        application.state.candidate_artifact = bundle
        application.state.artifact_bundle_verified = True
        application.state.artifact_warmed = True
        application.state.model_loaded = True
        application.state.model_serving_enabled = bool(
            bundle["manifest"].get("servingEnabled") is True
            and bundle["manifest"].get("artifactStatus") == "APPROVED_FOR_SERVING"
            and bundle["manifest"].get("productionDecision") == "PASS"
        )


def _error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(
        requestId=request.state.request_id,
        error={"code": code, "message": message},
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _word_count(text: str) -> int:
    return len(text.split())


def _unavailable_result(review_key: str, reason_code: str, model_version: str) -> dict:
    return {
        "reviewKey": review_key,
        "status": "UNKNOWN",
        "reasonCode": reason_code,
        "signals": [],
        "modelVersion": model_version,
        "engine": "MODEL",
    }


def create_app(
    *,
    artifact_dir: Path | None = None,
    expected_model_version: str | None = None,
    scoring_token: str | None = None,
) -> FastAPI:
    configured_artifact_dir = artifact_dir
    configured_model_version = expected_model_version
    configured_token = scoring_token

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        selected_artifact_dir = Path(
            configured_artifact_dir
            or os.environ.get("TRUSTLOOP_ARTIFACT_DIR")
            or DEFAULT_ARTIFACT_DIR
        )
        selected_model_version = (
            configured_model_version
            or os.environ.get("TRUSTLOOP_EXPECTED_MODEL_VERSION")
            or DEFAULT_MODEL_VERSION
        )
        selected_token = configured_token if configured_token is not None else os.environ.get("TRUSTLOOP_SCORING_TOKEN")
        application.state.expected_model_version = selected_model_version
        application.state.scoring_token = selected_token
        application.state.ready = False
        if configured_artifact_dir is None and os.environ.get("TRUSTLOOP_ARTIFACT_DIR") and not selected_artifact_dir.exists():
            raise ArtifactError("configured model artifact directory is missing")
        initialize_candidate_artifact(application, selected_artifact_dir, selected_model_version)
        # Readiness means this process can safely receive internal batches and
        # answer with scores or explicit unknowns. It does not approve serving.
        application.state.ready = bool(
            application.state.artifact_bundle_verified
            and application.state.artifact_warmed
            and selected_token
        )
        yield
        application.state.candidate_artifact = None
        application.state.artifact_bundle_verified = False
        application.state.artifact_warmed = False
        application.state.model_loaded = False
        application.state.model_serving_enabled = False
        application.state.ready = False

    application = FastAPI(title="TrustLoop scoring service", version=SERVICE_VERSION, lifespan=lifespan)

    @application.middleware("http")
    async def request_boundary(request: Request, call_next):
        request_id = _read_request_id(request.scope)
        request.state.request_id = request_id
        try:
            declared_size = int(request.headers.get("content-length", "0"))
        except ValueError:
            declared_size = 0
        if declared_size > MAX_REQUEST_BYTES:
            response = _error(request, 413, "PAYLOAD_TOO_LARGE", "Request body exceeds the allowed size.")
        else:
            response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        logger.info(
            "request completed request_id=%s method=%s path=%s status=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _exc: RequestValidationError):
        return _error(request, 400, "INVALID_REQUEST", "Request does not match the scoring contract.")

    @application.get("/health", response_model=HealthResponse)
    def health(request: Request):
        if not request.app.state.ready:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return {"status": "ready"}

    @application.get("/version", response_model=VersionResponse)
    def version_info(request: Request):
        return {
            "service": "trustloop-api",
            "version": SERVICE_VERSION,
            "contractVersion": "v1",
            "expectedModelVersion": getattr(request.app.state, "expected_model_version", configured_model_version or DEFAULT_MODEL_VERSION),
            "engine": "MODEL",
        }

    @application.post("/score", response_model=ScoreResponse, response_model_exclude_none=True)
    def score(
        payload: ScoreRequest,
        request: Request,
        x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    ):
        expected_token = request.app.state.scoring_token
        if not expected_token:
            return _error(request, 503, "INTERNAL_ERROR", "Scoring service token is not configured.")
        if x_internal_token is None or not hmac.compare_digest(x_internal_token, expected_token):
            return _error(request, 401, "INVALID_REQUEST", "Internal token is missing or invalid.")
        if not request.app.state.ready:
            return _error(request, 503, "INTERNAL_ERROR", "Scoring service is not ready.")

        model_version = request.app.state.expected_model_version
        serving_approved = request.app.state.model_serving_enabled
        results = []
        for review in payload.reviews:
            if _word_count(review.text) < MIN_REVIEW_WORDS:
                results.append(_unavailable_result(review.reviewKey, "INSUFFICIENT_TEXT", model_version))
            elif not serving_approved:
                results.append(_unavailable_result(review.reviewKey, "SCORING_UNAVAILABLE", model_version))
            else:
                # Approval requires an in-domain gate and language routing. The
                # current experimental bundle cannot enter this branch.
                results.append(_unavailable_result(review.reviewKey, "SCORING_UNAVAILABLE", model_version))
        return {"results": results}

    @application.exception_handler(Exception)
    async def internal_error(request: Request, _exc: Exception):
        logger.error(
            "request failed request_id=%s exception_type=%s",
            getattr(request.state, "request_id", "unknown"),
            type(_exc).__name__,
        )
        return _error(request, 500, "INTERNAL_ERROR", "Scoring service could not process the request.")

    return application


app = create_app()


def main() -> None:
    bind_host = os.environ.get("TRUSTLOOP_BIND_HOST", "127.0.0.1")
    try:
        is_loopback = ipaddress.ip_address(bind_host).is_loopback
    except ValueError:
        is_loopback = bind_host.lower() == "localhost"
    if not is_loopback:
        raise SystemExit("TRUSTLOOP_BIND_HOST must be a loopback address (127.0.0.1 or ::1).")
    port = int(os.environ.get("TRUSTLOOP_PORT", "8000"))
    uvicorn.run(app, host=bind_host, port=port, access_log=False)


if __name__ == "__main__":
    main()
