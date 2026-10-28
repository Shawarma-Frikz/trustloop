# TrustLoop architecture and data rules

## Component flow

```text
Supported review page
    -> browser extension adapter and visible-review scanner
    -> Spring Boot Review Analysis API  (public boundary, X-Request-Id)
    -> Python scoring service           (internal HTTP, X-Internal-Token)
    <- p_organic, score, verdict, evidence quality, signals, engine/model version
    <- extension badge and explanation panel
```

The Spring Boot backend is the public API boundary. The extension does not call the Python service directly. PostgreSQL is not required for the unauthenticated MVP analysis path; add persistence only when a defined later feature needs it. Browser-local scan history is separate from server persistence.

## Responsibility boundaries

- **Extension:** detect supported review cards, extract minimum text, deduplicate visible reviews within the page session, batch up to 10, render badge/panel, keep optional local history, and handle unknown/failure states. It never computes or sends a score or verdict.
- **Site adapter:** own selectors and page-specific extraction rules. Each adapter has an ID, a supported-page description, a manifest, and fixtures. An adapter miss is explicit; it is not permission to submit arbitrary page text.
- **Spring Boot API:** validate requests, apply request-size/rate/time limits, call the scoring service, validate and normalize the service response, apply the frozen score/band consistency checks, and return the documented response. It does not claim to prove authenticity.
- **Python scoring service:** perform the versioned model inference and explanation calculation; return `p_organic`, score, verdict, evidence quality, supported signals, model version, and engine. It must not retain request bodies. It is internal-only.
- **PostgreSQL (later):** introduce only for a feature that requires durable ownership or audit. See [persistence trigger](#persistence-trigger).

## API surface

### Public Spring Boot endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/analyze` | Analyze a batch of 1–10 reviews from one adapter |
| `GET` | `/api/v1/health` | Liveness/readiness for local use; `503` when scoring is not ready |
| `GET` | `/api/v1/version` | Backend, contract, expected model, and engine information |

Admin paths are reserved under `/api/v1/admin/**` and exist only in the `dev-admin` profile (Phase 2). They return `404` in the default profile. See [profiles and admin isolation](#profiles-and-admin-isolation).

### Internal Python endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/score` | Batch inference; requires `X-Internal-Token` |
| `GET` | `/health` | Ready only after the model artifact is loaded and warmed |
| `GET` | `/version` | Scoring service, model artifact, and engine version |

The internal service binds to loopback in local development and to a private network when hosted. It never accepts browser traffic.

## Request and response rules

### Public analyze request

The extension sends only the review text needed for analysis and small non-identifying metadata.

```json
{
  "adapterId": "amazon.reviews.v1",
  "languageHint": "en",
  "reviews": [
    {
      "reviewKey": "r-3f9c",
      "text": "…"
    }
  ]
}
```

Rules:

- `X-Request-Id` is required on the wire; the extension generates a UUIDv4, and the backend generates one if the header is absent or malformed. The response echoes it.
- `reviewKey` is an opaque page-session key. The backend echoes it and never persists it.
- Do not send reviewer names, profile links, avatars, full product pages, unrelated page text, full URLs, star ratings, or verified-purchase flags.
- The extension truncates text to `MAX_REVIEW_CHARS`. An empty batch, more than `MAX_REVIEWS_PER_REQUEST`, or a body over `MAX_REQUEST_BYTES` is a request-level error.
- `languageHint` is advisory. The scoring service's language detection is authoritative.
- The extension sends only free-text review bodies that the adapter has identified as eligible; it never sends a generic page-wide scrape.

### Public analyze response

```json
{
  "requestId": "b1f4c2e8-3a6d-4f2b-9c1e-7d5a0b3c8e21",
  "results": [
    {
      "reviewKey": "r-3f9c",
      "status": "SCORED",
      "trustScore": 73,
      "verdict": "LIKELY_ORGANIC",
      "evidenceQuality": "ADEQUATE",
      "signals": [
        {
          "kind": "CONCRETE_DETAIL",
          "summary": "Includes a concrete usage detail",
          "contribution": 0.18
        }
      ],
      "modelVersion": "tl-text-1.0.0",
      "engine": "MODEL"
    },
    {
      "reviewKey": "r-4a2d",
      "status": "UNKNOWN",
      "reasonCode": "INSUFFICIENT_TEXT",
      "evidenceQuality": "LOW",
      "signals": [],
      "modelVersion": "tl-text-1.0.0",
      "engine": "MODEL"
    }
  ]
}
```

Response rules:

- `status` is `SCORED`, `SIGNALS_ONLY`, or `UNKNOWN`; `engine` is `MODEL` or `SIGNALS_ONLY`.
- Every result carries `reviewKey`, `status`, `signals`, and `engine`. `evidenceQuality` is present when the scoring service assessed input sufficiency (`SCORED`, `SIGNALS_ONLY`, and service-produced `UNKNOWN`); it is omitted for `UNKNOWN` caused by timeout, unavailability, or version mismatch.
- `SCORED` carries `trustScore`, `verdict`, `modelVersion`, and `engine = MODEL`. Score and band are checked for consistency before returning.
- `UNKNOWN` omits `trustScore` and `verdict`; it never sends `0`, `50`, or `null` as a score. It carries `reasonCode`.
- `modelVersion` is present for `MODEL` results and for `UNKNOWN` results produced by the scoring service. It is omitted for `SIGNALS_ONLY`, for transport failure, and for a version mismatch, because no valid model output exists.
- `SIGNALS_ONLY` carries `status = SIGNALS_ONLY`, `engine = SIGNALS_ONLY`, validated signals, no score, no verdict, and no numeric contribution. It omits `modelVersion`. It is used only when language support and minimum text length are met; otherwise the result is `UNKNOWN`.
- At most five signals are returned. Summaries are generic templates; they never quote the review text, names, or URLs.
- `contribution` is optional and appears only when the explainer can produce a stable, validated value; otherwise omit it.
- A scoring call is atomic for the batch: timeout or unavailability marks every result in the batch as `UNKNOWN`. A batch uses one engine and one model version; per-review status may vary within that engine (for `MODEL`, scored or unknown; for `SIGNALS_ONLY`, signal-only or unknown).
- A result from a different engine or model version must be visibly identifiable. The backend does not silently mix engines or versions within a batch.
- Do not return raw review text unless the UI genuinely needs it to match a review already on the page; the MVP does not need it.

### Request-level errors

Invalid, oversized, or rate-limited requests use a separate error envelope with a safe message. They do not expose stack traces or internal details.

```json
{
  "requestId": "b1f4c2e8-3a6d-4f2b-9c1e-7d5a0b3c8e21",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request rejected"
  }
}
```

Scoring timeout or unavailability is reported per result at HTTP `200` with `UNKNOWN`, so every review keeps its matching key. Health checks may return `503`.

## Contract constants

These are MVP defaults, frozen with contract v1 in Phase 0. Changing a value is a contract change. Model thresholds are normative in the [model plan](model-plan.md#11-evidence-quality-unknown-and-score-mapping); the values are repeated here for the transport contract.

| Constant | Value | Notes |
|---|---|---|
| `MAX_REVIEW_CHARS` | 2,000 | Unicode code points after normalization; extension truncates |
| `MAX_REVIEWS_PER_REQUEST` | 10 | One adapter per request |
| `MAX_REQUEST_BYTES` | 131,072 | Accommodates 10 × 2,000 four-byte characters plus JSON |
| `MIN_REVIEW_WORDS` | 20 | Below this: `UNKNOWN` / `INSUFFICIENT_TEXT` |
| `ADEQUATE_REVIEW_WORDS` | 50 | 20–49 words: `LOW`; ≥ 50: `ADEQUATE` |
| `LANGUAGE_CONFIDENCE_MIN` | 0.80 | Below this: `UNKNOWN` / `UNSUPPORTED_LANGUAGE` |
| `MAX_SIGNALS` | 5 | Per result |
| `SCORING_TIMEOUT_MS` | 3,000 | Backend → scoring service; one attempt, no retry |
| `BACKEND_TIMEOUT_MS` | 4,000 | Extension → backend |
| `EXTENSION_TIMEOUT_MS` | 6,000 | Must exceed the backend timeout |
| `SCAN_DEBOUNCE_MS` | 750 | After DOM mutations |
| `MIN_RESCAN_INTERVAL_MS` | 2,000 | Avoid scan loops |
| `LOCAL_HISTORY_MAX_ENTRIES` | 100 | History cap |
| `LOCAL_HISTORY_MAX_AGE_DAYS` | 30 | Whichever limit is reached first |
| `RATE_LIMIT_PER_MINUTE` | 60 | Local/dev, per client IP; hosted limits are an edge concern |
| `REQUEST_ID_HEADER` | `X-Request-Id` | 1–64 characters, `[A-Za-z0-9-]` |
| `MODEL_VERSION_FORMAT` | `^tl-text-\d+\.\d+\.\d+$` | Backend validates the expected version |

## Unknown reason codes

| Code | Scope | Meaning |
|---|---|---|
| `UNSUPPORTED_PAGE` | Extension state | The adapter does not claim this page or layout |
| `NO_REVIEWS_FOUND` | Extension state | The adapter found no eligible review card |
| `INSUFFICIENT_TEXT` | Result | Fewer than 20 normalized words |
| `UNSUPPORTED_LANGUAGE` | Result | Unsupported language or detection confidence below 0.80 |
| `SCORING_TIMEOUT` | Result | The scoring call exceeded 3,000 ms |
| `SCORING_UNAVAILABLE` | Result | Connection failure, malformed response, version mismatch, internal error, or invalid service output |
| `INVALID_REQUEST` | Request error (`400`) | Malformed JSON, empty batch, more than 10 reviews, or invalid fields |
| `PAYLOAD_TOO_LARGE` | Request error (`413`) | Body exceeds `MAX_REQUEST_BYTES` |
| `RATE_LIMITED` | Request error (`429`) | Client exceeded the local rate limit |
| `INTERNAL_ERROR` | Request error (`500`) | Unexpected backend failure; safe message only |

Internal exception text, stack traces, and scoring-service details never cross the public boundary. An internal failure maps to `SCORING_UNAVAILABLE` per result or `INTERNAL_ERROR` for a request-level failure.

## Scoring service seam

- The backend calls `POST http://127.0.0.1:8000/score` in local development; hosted deployments use a private network address.
- Every internal call carries `X-Internal-Token` from the environment (`TRUSTLOOP_SCORING_TOKEN`) and forwards `X-Request-Id`. The token is never committed to the repository.
- The backend sends `reviewKey`, normalized `text`, and the server-derived `batchDuplicate` flag per review. The scoring service returns `p_organic`, `trustScore`, `verdict`, `evidenceQuality`, `signals`, `modelVersion`, and `engine` for scored results; validated signals and engine/status for `SIGNALS_ONLY`; or `UNKNOWN` with a reason code.
- The backend validates the service response: status/field consistency, score range, band range, evidence values, signal count, engine values, and model-version format. Any inconsistency maps to `UNKNOWN` / `SCORING_UNAVAILABLE`.
- One attempt, no automatic retry. The call is atomic for the batch: a timeout, connection error, non-2xx response, malformed body, or model-version mismatch produces `UNKNOWN` for every review in the batch with `SCORING_TIMEOUT` or `SCORING_UNAVAILABLE`; the extension offers a manual retry.
- The scoring service warms the model at startup; `/health` is not ready until the artifact is loaded. A cold start must not be presented as a model failure.
- The scoring service does not persist request bodies or log review text. It is not exposed to the browser.

## Eligibility and deduplication

- An **eligible review** is a review card inside the adapter's container that is rendered and not hidden: not `display: none`, not `visibility: hidden`, non-zero layout box, not `aria-hidden`, and with extractable text.
- Viewport intersection only schedules scanning. Scrolling does not change which reviews are eligible, so two users scanning the same DOM state see the same review set.
- The adapter's supported-page description and fixtures define valid containers. A selector miss produces `UNSUPPORTED_PAGE` or `NO_REVIEWS_FOUND`; it never triggers a generic page scrape.
- The session deduplication key uses the adapter-provided stable card ID when one exists; otherwise it is a salted hash of normalized text. The DOM ordinal is only a tie-breaker. It is generated per page session, held in memory, discarded on navigation, and never written to local history or a server.
- A DOM mutation triggers a scan after `SCAN_DEBOUNCE_MS`; rescans are rate-limited to `MIN_RESCAN_INTERVAL_MS`. Already-submitted keys are skipped, so scrolling does not repeatedly submit the same visible review.
- The extension batches up to 10 unscored eligible reviews. The backend computes `batchDuplicate` transiently within the request; it does not retain the batch.

## Professor-required Spring Boot package layout

Use the package names and layered organization from the supplied professor reference. Use a project-owned base package such as `com.trustloop.api`; do not leave `com.example` in the real project. Keep the screenshot's plural package names (`controllers`, `services`) consistently. Do not create empty packages or add layers only for appearance.

```text
backend/
  src/main/java/com/trustloop/api/
    common/       shared errors and response utilities when needed
    config/       application, HTTP client, profile, and rate-limit configuration
    context/      request-scoped caller context only when needed
    controllers/  REST endpoints
    interceptor/  request/security interception when introduced
    listener/     application events when introduced
    model/        domain types and DTOs as the course structure permits
    repository/   persistence interfaces when persistence is introduced
    services/     application and domain logic, including ScoringClient
    TrustLoopApiApplication.java
  src/main/resources/
    application.properties
    application-dev-admin.properties
    logback.xml
  src/test/java/com/trustloop/api/
    controllers/
    services/
```

For the MVP, `repository/`, `listener/`, and `context/` may be absent until there is a real requirement for them. Keep request/response DTOs distinct from persistence entities if entities are later added. Extension templates, if any, live in `extension/`, not in the backend's `resources/templates/`, because the browser extension is a separate component.

## Profiles and admin isolation

- **`default`:** public analysis endpoints only. No admin beans, no admin routes; `/api/v1/admin/**` returns `404`.
- **`dev-admin`:** local-only inspection of bundled adapters, local enable/disable toggles, and in-memory metrics. Toggles are local UI state, not adapter-file writes. It binds to `127.0.0.1`, logs a warning at startup, and has no authentication. Never expose it through a tunnel, shared network, or hosted deployment.
- **`test`:** deterministic tests with a stubbed scoring client; no external calls.
- Boot guard: if `dev-admin` is active and the bind address is not loopback, the application refuses to start. "Local-only" is enforced, not a verbal promise.
- Phase 2 admin scope is inspection and local toggles, not runtime adapter authoring. Runtime authoring is deferred until a persistence decision.

## Persistence trigger

PostgreSQL is introduced only when one of these is scheduled and its retention rules are defined:

- accounts or account-owned history;
- runtime adapter authoring with audit requirements;
- durable aggregate statistics that must survive restarts.

Until then, adapter configuration lives in versioned files under `extension/adapters/<adapterId>/` with a manifest, selectors, supported-page description, and fixtures. Admin inspection reads those files; it does not write them. Local enable/disable toggles are UI state, not file writes. If persistence is added, define ownership, retention, deletion, and access before creating the schema, and keep request/response DTOs distinct from entities.

## Privacy and retention baseline

- Process review text transiently for inference; do not persist it in the MVP.
- Do not log request or response bodies. Logs may contain request IDs, status, elapsed time, reason code, engine, model version, and adapter ID, but no review text, review keys, URLs, or personal identifiers.
- Do not send review text to an external hosted AI provider. The planned Python model runs as the project's scoring service.
- Keep optional history in browser storage only. Do not save raw text, review keys, full URLs, or a persistent fingerprint. Provide clear-history controls and enforce the 100-entry/30-day cap.
- Local history is off by default and follows [product decisions](product-decisions.md#local-history).
- Do not add product analytics or telemetry containing page/review content. Operational counters are aggregate and content-free.
- If account-based or server-side history is added later, define consent, purpose, retention, deletion, and access controls before enabling it.

## Observability

- The extension generates `X-Request-Id`; the backend validates it, regenerates it if malformed, and forwards it to the scoring service. The response echoes it.
- Structured log events: `api.request.received`, `api.scoring.completed`, `api.scoring.failed`, `api.response.sent`.
- Allowed fields: timestamp, level, event, requestId, adapterId, reviewCount, status, reasonCode, engine, modelVersion, latencyMs, httpStatus.
- Forbidden fields: review text, review key, URL, hostname, reviewer name, request/response body, exception stack trace in public logs.
- Content-free counters: requests by status, results by status/reason, scoring latency, model version. No per-review content.
- A single scan must be traceable across extension → backend → scoring service by its request ID during the demo.

## Security and resilience without accounts

Authentication is postponed, but the API still needs:

- input validation, safe error responses, request-size limits, timeouts, and one-attempt calls;
- rate limiting (local default 60 requests/minute per client IP; hosted deployments need edge limits);
- extension-origin restrictions in CORS; origin checks are not authentication and do not stop non-browser clients;
- secret management for `TRUSTLOOP_SCORING_TOKEN`; no secrets in the repository;
- HTTPS for any hosted communication;
- loopback binding for the local backend and the scoring service by default;
- no trust in extension-supplied scores or verdicts; the backend never accepts a score from the client;
- no silent fallback to a heuristic until it has a separately validated score definition and a distinct visible engine label. `SIGNALS_ONLY` is the only approved fallback and has no score.

On a scoring timeout or failure, return an unavailable/unknown response and let the extension offer retry. Do not silently fall back to a heuristic.

Exposing an unauthenticated public scoring API requires an explicit risk decision plus quotas and edge rate limiting. Until then, the supported deployment is local.

## Test locations and shared fixtures

- Backend: `backend/src/test/java/com/trustloop/api/controllers/` and `services/`.
- Scoring service: `scoring-service/tests/` for unit, calibration, evaluation, and artifact checks.
- Extension: `extension/tests/` for adapter fixtures, eligibility, deduplication, UI states, and storage privacy.
- Contract: `contracts/v1/` holds the request/response examples and JSON schema shared by all three components. A contract change is a version change, not a local edit.
- Tests are introduced with the behaviour in the same phase. The [MVP traceability table](mvp-requirements.md#traceability) maps each requirement to its evidence.
