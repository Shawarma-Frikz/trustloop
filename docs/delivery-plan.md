# TrustLoop delivery plan

## Sequencing principle

Build and demonstrate the useful review-analysis functions before adding authentication, as the professor advised. Accounts are an access and persistence feature, not a prerequisite for scoring. This order also keeps the first end-to-end demonstration small enough to debug.

Two rules apply to every phase:

- **Tests are part of the phase that introduces the behaviour.** A phase is not complete with failing or missing tests. The evidence is listed in the [MVP traceability table](mvp-requirements.md#traceability).
- **The decision register and risk register are reviewed at every phase gate.** Decisions that change are updated in [product decisions](product-decisions.md#decision-register), not left implicit.

## Phase 0 — Agree, freeze the contract, prove feasibility

Current gate status: **open**. See the [Phase 0 closeout checklist](evidence/phase-0-closeout.md) for item-by-item evidence and pending human sign-offs.

- Keep this document set as the initial product baseline and add/confirm the decision register.
- Create one `trustloop` monorepo with `backend/`, `scoring-service/`, `extension/`, `docs/`, and `contracts/v1/`.
- Create the Spring Boot project using the course-approved Java/Spring versions and the package names in [architecture and data](architecture-and-data.md#professor-required-spring-boot-package-layout).
- Attach the graphic charter and Figma prompt in `docs/design/`, or record a professor-approved waiver. Link them from [product decisions](product-decisions.md#design-consistency).
- Freeze contract v1: public and internal endpoints, contract constants, unknown reason codes, status and engine labels, model-version format, and shared JSON fixtures in `contracts/v1/`.
- Confirm dataset access and licenses, the annotation codebook, the evaluation sample plan, and the model acceptance gate. Record decisions D22–D24 or their defaults.
- Run and record the Amazon feasibility spike using the explicit criteria in [spike evidence](evidence/spike-amazon.md): three pre-chosen page variants, at least five eligible reviews per page, at least 90% precision against a manual count, stable selectors across two consecutive loads, and hidden-card handling. The 2026-10-30 anonymous-session run failed because all three review sections required sign-in; the recorded demo fallback is synthetic saved fixtures while retaining the adapter boundary. Re-run the live spike before treating Amazon extraction as dependable. An alternate site still requires the professor's approval.
- Create the test harness skeleton in all three components and confirm the shared contract fixtures load.
- Review the risk register and assign a phase owner for each high-impact risk.

**Exit condition:** the repository builds its empty component skeletons, the professor-required backend layout is present, the contract fixtures are agreed, dataset access is confirmed, the spike result and fallback choice are recorded, the charter is attached or waived, the test harness runs, and the team can explain the data flow and score meaning.

## Phase 1 — Analysis core, no accounts

- Implement the baseline scoring model and calibration from the [model plan](model-plan.md); document training/evaluation data, language coverage, limitations, and the per-language gate result. Ship `MODEL` only for a language that passes; otherwise record `SIGNALS_ONLY` or `UNKNOWN` for that language.
- Build the versioned artifact bundle and a draft model card. Pin the expected model version in the backend.
- Implement the public analyze endpoint, health/version endpoints, `ScoringClient`, response validation, reason codes, timeout handling, and safe errors.
- Implement one page adapter with manifest, selectors, supported-page description, extraction fixtures, eligibility rules, session-scoped deduplication, and batching up to 10.
- Connect badge and explanation panel to the real API result, including low-evidence qualification, unknown states, retry, keyboard operation, and visible focus.
- Add the optional local history with metadata-only storage, cap, and clear action.
- Add content-free error/latency logging, `X-Request-Id` propagation, request-size checks, rate limiting, origin restrictions, and the privacy defaults.
- Add tests with each behaviour: controller validation, scoring-client failure paths, adapter fixtures, eligibility/dedup, store privacy, contract fixtures, and no-body logging.

**Exit condition:** a supported page or fixture can be scanned end to end; score, label, evidence quality, and explanation match the API result; each supported language meets its gate or visibly uses `SIGNALS_ONLY`/`UNKNOWN`; unsupported input and service failure display honest unknown states; local history stores no content; tests are green; latency is within the target.

## Phase 2 — Finish non-auth product functions, local-only

- Add any agreed additional adapters, each with a manifest, fixtures, and explicit unsupported states. Do not add a generic fallback scraper.
- Package adapter configuration as versioned files. Do not add runtime adapter authoring.
- Build the local-only admin inspection surface under the `dev-admin` profile: list bundled adapters, inspect fixtures/supported pages, local enable/disable toggles, and in-memory metrics. No persistence.
- Enforce the profile boundary: default profile returns 404 for `/api/v1/admin/**`; `dev-admin` binds to loopback and triggers the boot guard if the bind address is not loopback.
- Keep account creation, account management, and role enforcement out of this phase; those require authentication and are the explicit exception to "features before auth."
- Avoid building server-side personal history as a workaround. Local history from Phase 1 remains browser-local.
- Add tests: adapter fixtures and unsupported states, default-profile 404, `dev-admin` loopback/boot guard, and admin inspection without writes.

**Exit condition:** all agreed non-auth user and admin flows work locally and are demonstrable; the default profile has no admin surface; the unauthenticated development surface is documented as local-only; adapter files are versioned; no database was introduced without a persistence decision; tests are green.

## Phase 3 — Quality, academic evidence, accessibility

- Evaluate the model on the held-out manual in-domain sample: AUROC, AUPRC, F1, ECE, Brier, reliability curves, per-language results, confidence intervals, and the per-language gate decision. Report cross-dataset transfer separately.
- Test explanation stability and determinism, then finalize the model card with limitations and the confirmed language go/no-go.
- Test request validation, scoring behaviour, adapter fixtures, deduplication, batching, and API failure paths across the whole system.
- Verify keyboard use, visible focus, non-colour labels, 200% zoom, screen-reader labels, and French/English strings from the [copy deck](product-decisions.md#copy-deck).
- Run the performance test on the reference environment and confirm the timeout hierarchy. Run the privacy/log-capture and security checks again.
- Prepare the architecture, API, persistence decision, model-evaluation, and risk evidence required by the course. Fix defects found by the evaluation rather than hiding them in the report.

**Exit condition:** the team can reproduce the demo and explain a supported result, an uncertain/unknown result, a service failure, and the access rules; the evaluation report and model card are complete; accessibility checks pass; tests are green with no known regressions; the report evidence is ready.

## Phase 4 — Authentication and ownership

- Before implementation, define exactly what history stores, retention/deletion, account ownership rules, and which endpoints require which roles. Do not retrofit raw review-text storage as a shortcut.
- Add registration/login (and password reset only if required), password hashing, JWT, roles, and account-owned server-side history as separate, testable increments.
- Introduce PostgreSQL only for the scheduled account/history/audit features, with migrations and retention rules defined first. Keep DTOs distinct from entities.
- Require authentication for admin functions before any shared or hosted use. Decide whether any explanation should become member-only only if that requirement is retained; the MVP made explanations public.
- Add tests for the access matrix, token handling, ownership isolation, history retention/deletion, migrations, and admin protection.

**Exit condition:** the access matrix is verified by tests; admin functions require authentication; history ownership and retention are enforced; no raw review text is stored; migrations reproduce from an empty database; tests are green.

## Phase 5 — Deployment and expansion

- A hosted deployment is optional, not an MVP requirement. If attempted, require authentication, quotas, edge rate limiting, HTTPS, secret management, monitoring, and a documented retention policy.
- Add account-management functions, further sites, or richer language support only in response to course priorities and remaining time.
- Each new adapter needs fixtures, a supported-page description, and a clear unsupported state.
- No new language or site reuses the MVP model silently; it needs its own gate evaluation and model version.

**Exit condition:** a hosted demo, if produced, has the security controls above and reproduces the local behavior; expansion items each have fixtures, tests, and an honest unsupported state.

## Scope control

If time becomes tight, preserve this order:

1. Working one-site scan.
2. Honest score/explanation contract.
3. Error and unknown states.
4. Model gate/evaluation and tests.
5. Local history.
6. Any agreed non-auth admin/adapter functions in local-only mode.
7. Authentication.
8. Deployment polish.

Cut breadth before weakening the meaning of a score or hiding model failures. If a language fails its model gate, ship `SIGNALS_ONLY` or narrow that language to `UNKNOWN`; never substitute an unvalidated score. Do not cut tests to buy time; cut adapters, admin polish, or deployment first.

## Risk register

Likelihood and impact are high/medium/low. Review at every phase gate; add a row when a new risk appears. Model-specific detail is in the [model plan](model-plan.md#16-model-specific-risks).

| ID | Risk | Likelihood | Impact | Mitigation | Early trigger |
|---|---|---|---|---|---|
| R-01 | Amazon DOM or Terms of Service changes break extraction | High | High | Narrow adapter, fixtures, Phase 0 spike, explicit unsupported state, saved-page demo fallback | Spike fails or selectors break on a chosen page |
| R-02 | Public dataset or license unavailable | Medium | High | Confirm licenses in Phase 0; approved alternatives; never scrape unlicensed data | No licensed corpus by Phase 0 exit |
| R-03 | Hotel/Yelp-to-Amazon domain shift or label noise | High | Medium | Manual in-domain evaluation, gate, model card limitations, `SIGNALS_ONLY` fallback | EN gate fails |
| R-04 | French data gap | High | Medium | FR conditional on its own gate; return `UNKNOWN` if not met | FR gate fails or sample too small |
| R-05 | Calibration misread as real-world prevalence | Medium | High | State calibration scope; ECE gate; copy review; avoid prevalence claims | Report or UI implies a real-world probability |
| R-06 | Explanation instability or overclaim | Medium | Medium | Linear baseline, stability gate, qualitative fallback, copy rules | Top-5 Jaccard below 0.80 or copy says "proof" |
| R-07 | Admin surface exposed | Medium | High | `dev-admin` only, loopback bind, boot guard, 404 by default, no tunnels, auth before hosting | Any non-loopback bind or admin route in default profile |
| R-08 | Privacy leak in logs, history, or telemetry | Medium | High | No-body logging, metadata-only opt-in history, log-capture and storage tests | Any review text, URL, or key in logs/storage |
| R-09 | Scope and time overrun | High | High | Narrow MVP, one adapter, cut order, per-phase tests | A phase exit slips; cut breadth, not tests or honesty |
| R-10 | Cold start or latency exceeds timeouts | Medium | Medium | Warm-up at boot, CPU baseline, batch cap, timeout hierarchy | p95 above 1.5 s or a timeout in the demo |
| R-11 | Public API abuse if hosted | Medium | Medium | Local default, auth, quotas, edge rate limits, explicit risk decision | Any hosted unauthenticated exposure |
| R-12 | Contract drift across components | Medium | High | `contracts/v1/` fixtures, contract tests, versioned changes, reason-code list | One component accepts a field or code the others do not |
| R-13 | Accessibility found too late | Medium | Medium | Semantic markup and keyboard support in Phase 1; full audit in Phase 3 | Keyboard/focus/zoom failures at Phase 1 exit |
| R-14 | UI copy drifts between languages or overclaims | Medium | High | Normative copy deck, string test, bilingual review | One language claims truth, identity, or fraud |
