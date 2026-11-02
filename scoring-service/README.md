# Scoring service

Internal FastAPI service. Binds to loopback; the extension never calls it directly.

## Install (cmd.exe)

```bat
cd scoring-service
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

In Git Bash the activation line is `source .venv/Scripts/activate`.

`GET /health` returns `not_ready` until the version-pinned artifact is verified,
warmed, and an internal token is configured. Readiness means the process can
handle internal calls; it does not mean the model has passed its product gate.

## Internal scoring API (Phase 1.5)

From the repository root, run in PowerShell with a per-session token. The service launcher rejects a
non-loopback bind address, and Uvicorn access logging is disabled so request
content cannot leak through access logs:

```powershell
$env:TRUSTLOOP_SCORING_TOKEN = [guid]::NewGuid().ToString("N")
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.main
Pop-Location
```

The service exposes `POST /score`, `GET /health`, and `GET /version`. `/score`
requires `X-Internal-Token`, accepts 1–10 reviews (at most 2,000 characters
each), propagates or creates `X-Request-Id`, and returns results in input order.
Request errors use the shared safe error envelope. Logs contain only request ID,
method, path, status, and exception type; they never include bodies or tokens.

The bundled `tl-text-1.1.0` artifact is still `UNKNOWN` and explicitly
not-for-serving. Accordingly, the service returns `UNKNOWN` with
`SCORING_UNAVAILABLE` for adequate-length reviews, and `INSUFFICIENT_TEXT` for
short reviews. It will not turn public hotel-review transfer metrics into
Amazon scores. `/health` can report ready when the local artifact is warmed and
the service token is set; that indicates the internal process is responsive,
not that a model score is approved.

Run the service boundary tests with:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m pytest -q tests/test_scoring_service.py tests/test_artifact_loader.py
Pop-Location
```

## Dataset preparation (Phase 1.1)

After approved raw CSV files are placed under `data/raw/<source-id>/` and their
real hashes/byte counts are recorded in `docs/dataset/dataset-manifest.json`,
rebuild the splits from the repository root:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.data_pipeline
Pop-Location
```

The command refuses absent or mismatched inputs. It writes normalized,
deduplicated train/dev/calibration/test files and a hash/count manifest under
ignored `data/processed/splits/`. See `docs/dataset/README.md` for the canonical
CSV schema and leakage policy.

## Baseline candidate (Phase 1.2)

After rebuilding the splits, fit an experimental candidate with train/dev only:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.train_baseline
Pop-Location
```

The frozen `evaluation/training-v1.json` controls TF-IDF ranges, `min_df`, the
dev-only regularization search, and language-detector decision. The script checks
the split hashes, tunes on dev, refits on train+dev, and does not load the
calibration or test CSVs. Candidate artifacts are ignored by Git and are not
loaded for serving. The per-language `UNKNOWN` decisions remain until the frozen
manual in-domain gates pass.

## Calibration and explanation (Phase 1.3)

After training the baseline candidate, run the frozen calibration/evaluation
protocol:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.calibrate_explain
Pop-Location
```

This fits sigmoid and isotonic candidates on calibration predictions, selects by
dev reliability (ECE, then Brier), refits the selected calibrator on the final
candidate, and reports once on the public-corpus test split. It also evaluates
coefficient-to-signal aggregation, source/page-cluster bootstrap stability, and
full-result determinism. Outputs go to ignored
`artifacts/candidates/calibration-v1/`. Public hotel-review results are transfer
evidence only; they do not pass the manual Amazon gate or enable serving.

## Versioned experimental artifact (Phase 1.4)

Build and verify the local, ignored bundle after the baseline and calibration
steps:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.build_artifact
Pop-Location
```

The builder pins `tl-text-1.1.0`, packages the model, calibration, metrics with
public-transfer confidence intervals, model card, dataset manifest, and exact
runtime lock, then verifies every file hash. The bundle is local and ignored by
Git because the source corpus is non-commercial and the project does not
redistribute derived model artifacts. The model card and aggregate evidence are
committed separately. The scoring service verifies a present bundle against
`TRUSTLOOP_EXPECTED_MODEL_VERSION` at startup and fails startup on corruption or
version mismatch. The internal `/score` route returns contract-shaped `UNKNOWN`
results while the model is experimental and the manual in-domain gate remains
pending.

## Test

```bat
cd scoring-service
python -m pytest -q
```

CI uses Python 3.12; any newer version with matching wheels works locally.
