# Contract v1 — frozen

Every message exchanged between the extension, the Spring Boot API, and the scoring
service is defined here and nowhere else. A change to any file in this directory is a
**contract change**: it requires a version bump, not a silent edit.

## Layout

| File | Scope |
|---|---|
| `constants.json` | Single source of truth: 17 constants, statuses, engines, reason codes (with scope), bands, signals |
| `analyze-request.schema.json` | `POST /api/v1/analyze` request (public) |
| `analyze-response.schema.json` | `POST /api/v1/analyze` response (public) |
| `error-response.schema.json` | Request-level error envelope: 400, 413, 429, 500 (public) |
| `health-response.schema.json` | `GET /api/v1/health` and internal `GET /health` body (200/503) |
| `version-response.schema.json` | `GET /api/v1/version` body (public) |
| `score-request.schema.json` | `POST /score` request (internal, `X-Internal-Token`) |
| `score-response.schema.json` | `POST /score` response (internal; adds `pOrganic`, never public) |
| `fixtures/*.json` | Valid and invalid examples; each must pass or fail validation as its name says |

JSON Schema draft 2020-12. Status-dependent field rules (e.g. `UNKNOWN` never carries
`trustScore` or `verdict`) are expressed with `if`/`then` inside the schemas.

## Rules

- `constants.json` holds every named value. Schema enums and bounds are cross-checked
  against it in the test suites of all three components, so a value cannot drift between
  the schema and the single source.
- No schema may contain review text, reviewer names, or URLs. Fixtures use invented text.
- The internal `score-*` schemas add `pOrganic`; that field must never appear on the
  public surface.

## Validation

The standalone contract suite validates every example against its matching schema:

```bat
cd contracts
python -m pip install -r requirements.txt
python -m pytest -q
```

The backend and extension also run contract assertions in their own test suites:

- Backend: `ContractValidationTest` (Maven `verify`)
- Scoring service: `tests/test_contract.py` (pytest)
- Extension: `tests/contract.test.ts` (vitest)
