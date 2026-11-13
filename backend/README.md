# Backend

Spring Boot public API. It is the only public application surface and binds to
`127.0.0.1:8080` by default. The browser extension calls this API; only this
backend calls the internal scoring service.

## Run locally (PowerShell)

Start the scoring service first, then configure the same internal token here:

```powershell
$env:TRUSTLOOP_SCORING_URL = "http://127.0.0.1:8000"
$env:TRUSTLOOP_SCORING_TOKEN = "your-local-scoring-token"
$env:TRUSTLOOP_EXPECTED_MODEL_VERSION = "tl-text-1.1.0"
$env:TRUSTLOOP_ALLOWED_ORIGINS = "chrome-extension://your-extension-id"
Push-Location backend
mvn spring-boot:run
Pop-Location
```

Set `TRUSTLOOP_ALLOWED_ORIGINS` to the exact installed extension origin. Keep
it empty if only command-line or local test clients will call the API. Never use
a wildcard origin with credentials or expose the API beyond loopback.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| `POST` | `/api/v1/analyze` | Validates and forwards a batch of 1–10 reviews; public results omit `pOrganic`. |
| `GET` | `/api/v1/health` | Reports `503` with `not_ready` until the scoring service is ready. |
| `GET` | `/api/v1/version` | Returns API, contract, expected model, and engine versions. |

The API validates review keys and lengths, the optional `en`/`fr` hint, request
IDs, total body size, rate limits, and the scoring response. If scoring times
out, is unavailable, or returns inconsistent data, the affected batch returns
honest `UNKNOWN` results with a safe reason. Request-level errors use the
contract v1 `{requestId, error}` envelope. Logs contain request IDs and error
types only; never log review text or request bodies.

The in-memory rate limit defaults to the contract value of 60 analyze requests
per minute per remote address. CORS accepts only the explicitly configured
origins. Both controls are local development safeguards, not production edge
controls.

## Local inspection surface

The optional inspection page is a development-only tool. It is absent (404)
unless the `dev-admin` Spring profile is active, and that profile refuses to
start unless `server.address` is `127.0.0.1` or `::1`. It lists bundled adapter
metadata, previews only bundled synthetic fixtures, offers a volatile
inspection-catalog toggle, and reports in-memory counts/status/latency buckets
for analyze requests. The toggle resets on restart and does not change
extension scanning. No account, database, or file persistence is used.

Run it locally with:

```powershell
$env:SPRING_PROFILES_ACTIVE = "dev-admin"
Push-Location backend
mvn spring-boot:run
Pop-Location
```

Then open `http://127.0.0.1:8080/api/v1/admin`. Do not activate this profile in
a hosted or shared environment.

## Test

```powershell
Push-Location backend
mvn test
Pop-Location
```

Controller tests use an in-memory scoring stub and require no running Python
service or network connection. Contract constants are copied into the packaged
application from `contracts/v1/constants.json` during the Maven build.
