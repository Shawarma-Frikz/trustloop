# TrustLoop MVP requirements

## Goal

Demonstrate that TrustLoop can identify supported reviews on one e-commerce site, analyze them, and explain the resulting estimate in the browser. A reviewer should be able to follow the entire path without creating an account.

## Included in the MVP

Requirement IDs are used by the [traceability table](#traceability) and the delivery plan.

### R1 — One supported page type

The Amazon product-review page adapter described in [product decisions](product-decisions.md#first-supported-site-and-scope-boundary). Include fixtures for representative supported and unsupported page markup. The Phase 0 feasibility spike must pass before this adapter is treated as dependable.

### R2 — Review extraction

Extract only eligible review text and the minimum optional context needed by the model (adapter ID and optional language hint). An eligible review is rendered and not hidden inside the adapter's container, with extractable text; viewport intersection only schedules scanning. Mark each review with a session-scoped, salted deduplication key so rescans do not submit it repeatedly while scrolling or after DOM mutation. Send at most 10 reviews per request. The backend derives a transient `batchDuplicate` flag within the request; the extension does not compute or store it.

### R3 — Analysis

Send normalized review input through the Spring Boot API to the Python scoring service. Return a calibrated organic-likelihood score, one of the six verdict bands, evidence quality, engine/model version, and up to five model-contributing signals. The model must pass the published acceptance gate for its language in the [model plan](model-plan.md#9-evaluation-and-acceptance-gate), or that language uses `SIGNALS_ONLY`/`UNKNOWN`; an unvalidated score is never presented as `MODEL`.

### R4 — In-page result

Show a badge beside each recognized review. The score and verdict label must both be understandable without relying on colour alone. Unknown results have no numeric score. A `LOW` evidence result keeps its score and band but carries the "Indicative — limited text" qualifier.

### R5 — Explanation

Clicking a badge opens the factors that contributed to the output. Phrase them as model signals, preserve positive/negative contribution direction where supported, and avoid claims that the model proved the review false or identified its author. Do not quote review text in the panel. When the engine is `SIGNALS_ONLY`, the panel says "Descriptive signals only — no score."

### R6 — Local scan history

Optionally show the user's recent scans in the extension, stored only in that browser and off by default. When enabled, store timestamp, site hostname, adapter ID, status, score/verdict when scored, evidence quality when present, engine, model version when present, and reason code when unknown. Do not store review text, review keys, full page URLs, or a persistent text fingerprint. Cap history at 100 entries or 30 days and provide a clear-history action. Full policy: [product decisions](product-decisions.md#local-history).

### R7 — Failure and partial states

Show clear states for unsupported page, no eligible reviews, insufficient text, unsupported language, scoring timeout, scoring unavailable, and successful analysis. On model failure show unknown with a retry action; never substitute an unvalidated heuristic score. Request-level validation and rate-limit errors use the documented error envelope. Reason codes are enumerated in [architecture and data](architecture-and-data.md#unknown-reason-codes).

### R8 — Accessibility and language

Keyboard-operable badge/panel, visible focus, non-colour verdict cues, readable text at 200% zoom, screen-reader labels that include score, verdict, evidence quality, and engine, and French/English UI copy from the normative [copy deck](product-decisions.md#copy-deck). The model must report unsupported language rather than silently implying equal coverage. UI translation does not imply model language support.

### N1 — Privacy baseline

Process review text transiently; do not persist it or log request/response bodies. Logs are content-free and contain only the fields allowed by [architecture and data](architecture-and-data.md#observability). No external hosted AI provider receives live review text. Local history follows R6.

### N2 — Frozen contract

The three components share `contracts/v1/` request/response examples and fixtures. Endpoints, limits, reason codes, status and engine labels, and model-version format are frozen before integration; a change is a contract version change.

### N3 — Security baseline

Input validation, request-size limits, rate limits, timeouts, extension-origin restrictions, safe error responses, secrets management, and HTTPS in a hosted environment. The backend never trusts an extension-supplied score or verdict. The scoring service is internal-only and requires its internal token.

### N4 — Performance

Warm scoring p95 is at most 1.5 seconds for a 10-review batch on the reference environment (4 vCPU, 8 GB RAM, CPU-only). Timeout hierarchy: scoring service 3 seconds, backend 4 seconds, extension 6 seconds. Cold start is warmed before `/health` reports ready.

### N5 — Admin isolation

When admin or adapter-inspection surfaces exist (Phase 2), they exist only in the `dev-admin` profile, bind to loopback, and are absent (404) in the default profile. They are local-only until authentication exists. See [architecture and data](architecture-and-data.md#profiles-and-admin-isolation).

### N6 — Model reproducibility

Each release ships a versioned artifact bundle, metrics, and a model card; the evaluation script reproduces the reported metrics. See [model plan](model-plan.md#14-reproducibility-and-model-card).

### N7 — Design source of truth

The graphic charter and Figma prompt are stored in `docs/design/` and linked from the baseline. The copy deck is normative. Trust badges and trust-scale fills are solid, with non-colour verdict cues.

## Explicitly deferred

The following are deferred from the MVP. Items marked Phase 2 are planned before authentication but only in the local `dev-admin` profile; they are not part of the first demonstrable release.

- Registration, login, password reset, JWT, user roles, admin accounts, and guest quotas.
- Server-side accounts or history, cross-device history, and user profiles.
- A full admin dashboard, adapter-management UI, model-confidence dashboard, and live retraining. **Deferred from the MVP; Phase 2 provides local-only inspection and enablement, not a full dashboard or runtime authoring.**
- Runtime adapter authoring or editing. **Deferred until a persistence decision; bundled adapter files only in Phase 2.**
- Multiple production site adapters, a general-purpose generic fallback, mobile app, and broad multilingual claims.
- Star-rating, verified-purchase, reviewer-identity, or image inputs. Model v1 is text-only; adding any of these is a new decision.
- A transformer model, unless it passes the model gate and explanation-stability checks.
- Product/page aggregate trust scores. Do not average individual scores into a page badge; that can hide mixed evidence and imply a meaning the score does not have.
- Persistent cross-session deduplication fingerprints.
- A hosted public API without authentication, quotas, and edge rate limiting.
- Production deployment as a release requirement. A hosted demo is optional after the local end-to-end flow is stable.

## Acceptance criteria

- On a supported fixture/page, the extension identifies each eligible review once, requests analysis, and displays the returned result next to the matching review.
- The explanation displayed in the extension corresponds to the exact result returned by the API, including the engine and model version when present.
- Unsupported pages, no eligible reviews, insufficient text, and unsupported language produce an explicit no-estimate state with the correct reason code. Never a fabricated 0%, a silent 50, or a generic page scrape.
- If the scoring service is down or exceeds its timeout, the extension reports that the result is unavailable and allows retry; it does not present a fallback estimate as model output.
- The same visible review is not repeatedly submitted as the user scrolls or the page mutates.
- No account is required to scan or read an explanation. Local history is opt-in, contains no raw review text, full URL, review key, or fingerprint, and can be cleared.
- UI copy describes score estimates and contributing signals, not truth, reviewer identity, or proof of fraud. The copy deck is used in both languages.
- The model meets its published gate for each supported language, or that language visibly uses `SIGNALS_ONLY`/`UNKNOWN` with no score.
- Contract fixtures pass across all three components: endpoints, limits, reason codes, status and engine labels, and model-version format.
- The backend follows the professor-required package layout and includes tests under the matching `src/test/java` package tree. Tests are added in the phase that introduces the behaviour, not postponed.
- When the Phase 2 admin surface is present, the default backend profile exposes none; `dev-admin` binds to loopback and is documented as local-only.
- Accessibility checks pass: keyboard operation, visible focus, non-colour cues, 200% zoom, and screen-reader labels.

## Output contract (conceptual)

The analysis response has stable, documented fields equivalent to the batch envelope below. This is a planning contract, not code.

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

Rules:

- `status` is `SCORED`, `SIGNALS_ONLY`, or `UNKNOWN`; `engine` is `MODEL` or `SIGNALS_ONLY`.
- `UNKNOWN` omits `trustScore` and `verdict`; it never sends `0` or `null` as a score. It carries `reasonCode`.
- When present, `evidenceQuality` is `LOW` or `ADEQUATE`; it is not a percentage. It is omitted when the scoring service did not assess the input (timeout, unavailable, or version mismatch).
- `signals` contains at most five entries and never includes raw review text, names, or URLs.
- `contribution` is optional and appears only when the explainer can produce a stable, validated value; otherwise omit it.
- `SIGNALS_ONLY` results carry status and engine `SIGNALS_ONLY`, validated signals, no `trustScore`, no `verdict`, no numeric contribution, and no `modelVersion`.
- A batch uses one engine and one model version; per-review status may vary. If the backend detects a scoring-service version mismatch, all results in that batch are `UNKNOWN` with `SCORING_UNAVAILABLE`.
- Request-level errors (invalid request, too large, rate limited) use a separate error envelope documented in [architecture and data](architecture-and-data.md#request-and-response-rules).

## Traceability

Phases refer to the [delivery plan](delivery-plan.md). Every row must have its verification evidence before its phase exits.

| ID | Design / model reference | Verification evidence | Phase |
|---|---|---|---|
| R1 | Architecture §Eligibility and deduplication; delivery plan Phase 0 spike | Adapter fixture tests; manual spike report | 0, 1 |
| R2 | Architecture §Eligibility and deduplication | JS unit tests: eligibility, extraction, dedup, batch cap | 1 |
| R3 | Model plan §9, §11; architecture §API surface | Offline evaluation report; API contract tests; scoring-client tests | 1 |
| R4 | Product decisions §Copy deck; MVP R4 | UI state tests; visual check; low-evidence label test | 1, 3 |
| R5 | Model plan §10 | Explanation stability test; UI-to-result mapping test | 1, 3 |
| R6 | Product decisions §Local history | Local-storage tests; inspection that no text/URL/key is stored; clear-history test | 1 |
| R7 | Architecture §Unknown reason codes | MockMvc validation tests; stubbed timeout/unavailable tests; UI state tests | 1 |
| R8 | Product decisions §Copy deck | Manual accessibility checklist; keyboard/focus/zoom/screen-reader checks; string test | 3 |
| N1 | Architecture §Privacy and retention baseline | Log-capture test; storage inspection; no-body assertion | 1 |
| N2 | Architecture §API surface, §Contract constants | Shared JSON schema/fixture tests across components | 0, 1 |
| N3 | Architecture §Security and resilience without accounts | Validation, size, rate-limit, CORS, internal-token tests | 1 |
| N4 | Model plan §9; architecture §Contract constants | Performance test on reference environment | 1, 3 |
| N5 | Architecture §Profiles and admin isolation | Default-profile 404 test; `dev-admin` loopback binding test | 2 |
| N6 | Model plan §14 | Evaluation rerun reproduces metrics; model card review | 3 |
| N7 | Product decisions §Design consistency, §Copy deck | Design review; copy-deck string test | 0, 3 |
