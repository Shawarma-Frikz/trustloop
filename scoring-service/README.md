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

## Test

```bat
cd scoring-service
python -m pytest -q
```

CI uses Python 3.12; any newer version with matching wheels works locally.
