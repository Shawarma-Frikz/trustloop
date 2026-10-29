from fastapi import FastAPI
from fastapi.responses import JSONResponse

SERVICE_VERSION = "0.0.1"
model_loaded = False  # replaced by the artifact loader in Phase 3

app = FastAPI(title="TrustLoop scoring service", version=SERVICE_VERSION)


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
