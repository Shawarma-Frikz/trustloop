# TrustLoop project documents

This folder contains TrustLoop's product baseline and delivery plan. Phase 0.4's plans and gate are versioned; annotator sign-off and dataset acquisition remain explicit pre-Phase-1 work in [dataset closeout](dataset/README.md).

## Read in this order

1. [Product decisions](product-decisions.md) — resolved definitions, score and evidence contract, copy deck, local-history policy, decision register, and glossary.
2. [Model plan](model-plan.md) — data, labels, calibration, acceptance gate, explanation method, versioning, and model limitations.
3. [MVP requirements](mvp-requirements.md) — what the first demonstrable release includes and excludes, failure states, the output contract, and traceability.
4. [Architecture and data](architecture-and-data.md) — component responsibilities, API surface, frozen constants, reason codes, privacy, profiles, and security.
5. [Delivery plan](delivery-plan.md) — phases 0–5 with per-phase tests, feasibility criteria, scope control, and the risk register.

These are planning documents, not implementation instructions to create every listed feature at once. The MVP is the delivery target; later phases are intentionally deferred.

## Change control

- Decisions have IDs in the [decision register](product-decisions.md#decision-register). A changed decision updates its row and every document that depends on it; a change is not recorded only in conversation.
- Contract v1 (endpoints, constants, reason codes, status and engine labels, model-version format) is frozen in Phase 0 and shared as JSON fixtures in `contracts/v1/`. A contract change is a version change.
- Tests belong to the phase that introduces the behaviour. The [traceability table](mvp-requirements.md#traceability) is the evidence map.
- The [risk register](delivery-plan.md#risk-register) is reviewed at every phase gate.

## Required source assets

The graphic charter and Figma prompt are not implementation code, but they are part of the baseline. They must be exported into [`docs/design/`](design/README.md) and linked from the product decisions before Phase 0 exits. The [copy deck](product-decisions.md#copy-deck) is normative and must not be duplicated inside a Figma file only.

`contracts/v1/` is also created in Phase 0; until then it is a planned path, not a code artifact.
