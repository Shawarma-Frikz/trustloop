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

## Test

```bat
cd scoring-service
python -m pytest -q
```

CI uses Python 3.12; any newer version with matching wheels works locally.
