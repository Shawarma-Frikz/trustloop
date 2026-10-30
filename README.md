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

## Status

Phase 0.4 artifacts are drafted. The live Phase 0.5 Amazon spike failed in the unsigned session; synthetic page fixtures are the recorded demo fallback. See [spike evidence](docs/evidence/spike-amazon.md), [dataset closeout](docs/dataset/README.md), and the [delivery plan](docs/delivery-plan.md).

## Documentation

Start at `docs/README.md`.
The build roadmap is `docs/playbook/TrustLoop-Complete-Build-Playbook-v1.0.pdf`.
Phase gates are in `docs/delivery-plan.md`.
The visual system is `docs/design/TrustLoop-Graphic-Charter-v1.0.pdf`.
