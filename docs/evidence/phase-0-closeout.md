# Phase 0 closeout checklist

**Status: OPEN.** This checklist distinguishes repository evidence from human
sign-off and environment-dependent checks. A fallback or a planned action is not
recorded as a passed gate.

| Exit item | Status | Evidence / remaining work |
|---|---|---|
| Monorepo and three component skeletons | Present; builds passed | `backend/`, `scoring-service/`, `extension/`, `contracts/v1/`; backend Maven verify and extension build passed. |
| Course backend package layout | Present | Spring sources use `com.trustloop.api`; compare with the course specification if it names a different package. |
| Contract v1 and shared fixtures | Present; tests passed | Backend and extension contract tests passed; standalone `contracts/tests/test_contract.py` passed. |
| Dataset licenses, codebook, sample plan, and frozen gates | Written; human calibration pending | See [dataset closeout](../dataset/README.md). Two independent annotators must label the calibration batch, achieve Cohen's kappa ≥0.60, and record adjudication. |
| Dataset acquisition hashes | Pending before Phase 1 data use | Acquire only approved data; record real hashes in the manifest. Do not fabricate hashes or check raw data into the repository. |
| Amazon feasibility decision | Failed; fallback recorded | See [Amazon spike evidence](spike-amazon.md). This satisfies the documented fallback branch. Synthetic fixtures are for development only; if the course requires live-site scanning, professor approval for an alternate site and a new passing spike are still needed. |
| Graphic charter and Figma prompt | Repository artifacts present | See [`docs/design/`](../design/README.md) and decision D20. Record a waiver only if a required artifact is not accepted for the course. |
| Test harness and pull-request CI | Local suites green; CI configured | Backend 5 tests, scoring 27 tests, extension typecheck/build plus 30 tests, and standalone contracts 1 test passed. CI is configured in `.github/workflows/phase-0-harness.yml`; confirm a green PR run. |
| Risk review and high-impact owners | Pending | Risk register is in `docs/delivery-plan.md`; the team must assign named owners to high-impact risks and review them at the Phase 0 gate. |
| Data flow and score meaning explained by team | Human check pending | Confirm at the phase review; see [architecture and data](../architecture-and-data.md) and [product decisions](../product-decisions.md). |

## Local harness results (2026-10-30)

| Command | Result |
|---|---|
| Extension `npm run typecheck` | Passed |
| Extension `npm test` | Passed: 30 tests across 3 files |
| Extension `npm run build` | Passed |
| Backend `mvn -B verify` | Passed: 5 tests, no failures |
| Scoring service `python -m pytest -q` | Passed: 27 tests (one upstream deprecation warning) |
| Contract `python -m pytest -q` | Passed: 1 test, using the existing scoring-service virtualenv's Python and installed `jsonschema` dependency |

CI is configured to run these four suites on pull requests and pushes to `main`.
Confirm the workflow passes on a pull request before treating hosted CI as verified.
