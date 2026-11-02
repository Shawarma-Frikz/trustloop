# Scoring service

Internal FastAPI service. Binds to loopback; the extension never calls it directly.

## Run (cmd.exe)

```bat
cd scoring-service
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In Git Bash the activation line is `source .venv/Scripts/activate`.

`GET /health` returns `503` until a model artifact is loaded. That is the expected state in Phase 0.

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
version mismatch. It still returns not-ready and exposes no scoring endpoint:
the model is experimental until the manual in-domain gate passes.

## Test

```bat
cd scoring-service
python -m pytest -q
```

CI uses Python 3.12; any newer version with matching wheels works locally.
