import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.artifact_loader import ArtifactError, load_artifact_bundle

SERVICE_VERSION = "0.0.1"
model_loaded = False  # serving remains disabled until the frozen language gate passes
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "tl-text-1.1.0"


def initialize_candidate_artifact(application: FastAPI, artifact_dir: Path, expected_version: str) -> None:
    application.state.candidate_artifact = None
    application.state.artifact_bundle_verified = False
    application.state.model_loaded = False
    if artifact_dir.exists():
        application.state.candidate_artifact = load_artifact_bundle(artifact_dir, expected_version)
        application.state.artifact_bundle_verified = True


@asynccontextmanager
async def lifespan(application: FastAPI):
    configured_path = os.environ.get("TRUSTLOOP_ARTIFACT_DIR")
    artifact_dir = Path(configured_path or DEFAULT_ARTIFACT_DIR)
    expected_version = os.environ.get("TRUSTLOOP_EXPECTED_MODEL_VERSION", "tl-text-1.1.0")
    if configured_path and not artifact_dir.exists():
        raise ArtifactError("configured model artifact directory is missing")
    # A present but corrupt or mismatched bundle is a startup failure. A valid
    # experimental bundle loads for inspection, but does not mark the service ready.
    initialize_candidate_artifact(application, artifact_dir, expected_version)
    yield
    application.state.candidate_artifact = None
    application.state.artifact_bundle_verified = False


app = FastAPI(title="TrustLoop scoring service", version=SERVICE_VERSION, lifespan=lifespan)


@app.get("/health")
def health() -> JSONResponse:
    if not model_loaded:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "modelLoaded": False},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "modelLoaded": True},
    )
