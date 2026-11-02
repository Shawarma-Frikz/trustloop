# TrustLoop

Browser-extension analysis of review text on a supported product-review page.

## What it is — and is not

Estimates whether review text looks organic or manipulated, one review at a time.
It does not verify purchases, identify reviewers, prove fraud, or rate products.

## Components

| Path | Role |
|---|---|
| `extension/` | Manifest V3 browser extension and page adapters |
| `backend/` | Spring Boot public API |
| `scoring-service/` | Python model service, internal only |
| `contracts/v1/` | Frozen request/response schemas and fixtures |
| `docs/` | Product, model, architecture, delivery baseline, design |

## Local run

1. Scoring service — see `scoring-service/README.md`
2. Backend — see `backend/README.md`
3. Extension — load `extension/dist` unpacked in Chrome

## Test harness

Run the complete checks for the current project state from the repository root in PowerShell (Python 3.12+, JDK 21+, Maven 3.9+, and Node 24+):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-project.ps1
```

This rebuilds the dataset splits, baseline candidate, calibration/evaluation
report, and local experimental artifact bundle, then runs all four component suites. The
binary bundle is ignored by Git because of the source corpus licence. The original Phase 0-only harness remains at
`scripts/test-phase0.ps1`. CI runs the component suites on every pull request and
on pushes to `main` via
`.github/workflows/phase-0-harness.yml`. The runner stops at the first failing
command.

## Status

Phase 0 is still open. All four local harness suites pass and pull-request CI is configured. Remaining closeout work includes independent annotator calibration, named risk owners, a green hosted CI run, and the team's phase review. The live Phase 0.5 Amazon spike failed; synthetic fixtures are the documented development fallback. See the [Phase 0 checklist](docs/evidence/phase-0-closeout.md), [dataset closeout](docs/dataset/README.md), and [spike evidence](docs/evidence/spike-amazon.md).

## Documentation

Start at `docs/README.md`.
The build roadmap is `docs/playbook/TrustLoop-Complete-Build-Playbook-v1.0.pdf`.
Phase gates are in `docs/delivery-plan.md`.
The visual system is `docs/design/TrustLoop-Graphic-Charter-v1.0.pdf`.
