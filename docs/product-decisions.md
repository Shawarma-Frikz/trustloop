# TrustLoop product decisions

**Status:** Baseline for the new project, starting from zero. Last reviewed 2026-10-27.

This document resolves the product questions that affect requirements, UI, model outputs, and architecture. If later evidence or course guidance changes a decision, add or update the row in the [decision register](#decision-register) and update the affected documents. The decision register is the change log; it is not a second specification.

Companion documents: [model plan](model-plan.md), [MVP requirements](mvp-requirements.md), [architecture and data](architecture-and-data.md), [delivery plan](delivery-plan.md).

## Product definition

TrustLoop is a browser extension with a Spring Boot API and a Python scoring service. It analyzes review text visible on a supported product-review page and presents a review-level estimate with an explanation of the model signals that contributed to it.

TrustLoop assesses text patterns. In model v1 it uses review text only; star rating, verified-purchase flags, reviewer identity, profile data, and images are not model inputs. It does not verify a purchase, identify a reviewer, prove that a review is true, or determine whether a product is good. User-facing copy must not claim otherwise. It does not average reviews into a page or product score.

## Score and verdict

- **Trust score:** an integer from 0 to 100 representing the model's calibrated estimate that the review text is organic rather than manipulated, based only on the text and the inputs listed in the [model plan](model-plan.md). It is an estimate, not a guarantee or a measure of product quality.
- **Score mapping:** `trustScore` is `100 × p_organic` rounded half up, then clipped to 0–100. There is no separate mapping layer and no post-hoc band adjustment.
- **Calibration scope:** `p_organic` is calibrated to the evaluation distribution, not to the prevalence of manipulation on Amazon. Public datasets are often class-balanced by construction, so the score is not a real-world probability. The report and UI must not imply otherwise.
- **Verdict:** a plain-language band derived only from the score. Six bands preserve the graphic charter's scale: 0–19 *strong manipulation signals*; 20–39 *likely manipulated*; 40–54 *inconclusive*; 55–69 *mixed signals*; 70–84 *likely organic*; 85–100 *strong organic signals*. Band names describe the model output, not a fact about the reviewer.
- **Band rationale:** 50 sits inside the inconclusive band rather than on a boundary, so the interface never treats 50 as a decision line. The outer bands are wider because a strong claim needs a clear margin; the inner bands are narrower around the uncertain centre. Boundaries are fixed by the graphic charter's six stops and require a decision-register change.
- **Unknown:** use when no score can be responsibly produced, including unsupported pages, no eligible reviews, insufficient text, unsupported language, or a scoring-service failure. Unknown has no number and must never be encoded as 0. The reason codes are enumerated in [architecture and data](architecture-and-data.md#unknown-reason-codes).
- **Evidence quality:** `LOW` or `ADEQUATE`, determined by input sufficiency, not by model confidence. The review language must be supported with detector confidence of at least 0.80; otherwise the result is `UNKNOWN` with `UNSUPPORTED_LANGUAGE`, regardless of length. A supported review needs at least 20 words to be scored; fewer returns `UNKNOWN` with `INSUFFICIENT_TEXT`. A 20–49 word supported review is `LOW`; at least 50 words is `ADEQUATE`. Low evidence is not a second probability and must not be shown as a percentage or called confidence.
- **Low-evidence display:** a `LOW` result keeps its score and band but must be visibly qualified as "Indicative — limited text" in the panel and badge label. Do not hide the score and do not convert it to a confident result.
- **Signals:** descriptive evidence such as repeated phrases, unusually generic wording, or duplicated text. Say that a signal influenced the model output; do not say it proves deception or causation. At most five signals are returned. A numeric contribution is shown only when the selected explainer can produce a stable, validated value; otherwise the signal is qualitative. Signal summaries never quote the review text.
- **Engine and status:** `status` is `SCORED`, `SIGNALS_ONLY`, or `UNKNOWN`. `engine` is `MODEL` or `SIGNALS_ONLY`. A `MODEL` result is scored. A `SIGNALS_ONLY` result carries validated descriptive patterns, no score, no verdict, and no numeric contribution. `UNKNOWN` has no score. A distinct engine/status label must be visible whenever the result is not a `MODEL` score.

The model should expose a calibrated probability for the organic class and an evidence-quality state. Do not infer exact categories such as "bot" or "spam" from a score band. "Bot-like" or "spam-like" may be used for a named text pattern only when the explanation identifies the observable pattern and its limits.

## Copy deck

The English and French strings below are normative. They describe model output, not truth. In French, *authentique* means "text patterns consistent with a spontaneous review"; it does not mean verified or true.

### Verdict bands

| Score | Code | English | French |
|---|---|---|---|
| 0–19 | `STRONG_MANIPULATION_SIGNALS` | Strong manipulation signals | Signaux forts de manipulation |
| 20–39 | `LIKELY_MANIPULATED` | Likely manipulated | Probablement manipulé |
| 40–54 | `INCONCLUSIVE` | Inconclusive | Non concluant |
| 55–69 | `MIXED_SIGNALS` | Mixed signals | Signaux mitigés |
| 70–84 | `LIKELY_ORGANIC` | Likely organic | Probablement authentique |
| 85–100 | `STRONG_ORGANIC_SIGNALS` | Strong organic signals | Signaux forts d'authenticité |

### Interface strings

| Key | English | French |
|---|---|---|
| Estimate disclaimer | Estimated from text patterns. Does not verify purchase, identity, or truth. | Estimation fondée sur des motifs textuels. Ne vérifie ni l'achat, ni l'identité, ni la véracité. |
| Low evidence | Indicative — limited text | Indicatif — texte limité |
| Unknown heading | No estimate | Aucune estimation |
| Unsupported page | This page is not supported yet. | Cette page n'est pas encore prise en charge. |
| No reviews found | No reviews found to analyze. | Aucun avis à analyser. |
| Insufficient text | Not enough text to estimate. | Texte insuffisant pour une estimation. |
| Unsupported language | This language is not supported yet. | Cette langue n'est pas encore prise en charge. |
| Timeout | Analysis timed out. Try again. | L'analyse a expiré. Réessayez. |
| Unavailable | Analysis is unavailable right now. Try again. | L'analyse est indisponible. Réessayez. |
| Signal-only mode | Descriptive signals only — no score | Signaux descriptifs seulement — aucun score |
| Details action | Details | Détails |
| Retry action | Retry | Réessayer |
| History label | History | Historique |
| Clear history action | Clear history | Effacer l'historique |

Both languages use the same score meaning, bands, and engine labels. Do not introduce a stronger claim in one language than the other.

## Local history

Local history is optional and off by default. When the user enables it, the extension may store only:

- timestamp;
- site hostname, not the full URL;
- adapter ID;
- status (`SCORED`, `SIGNALS_ONLY`, or `UNKNOWN`);
- score and verdict when scored;
- evidence quality when present, engine, and model version when present;
- reason code when unknown.

It must not store review text, review keys, reviewer identifiers, page URLs, or a persistent text fingerprint. The page-session deduplication key is salted per page session, held in memory, and discarded on navigation; it is never written to history.

History is capped at 100 entries or 30 days, whichever comes first, and has a clear-history action. It stays in browser storage and is never synchronized. If later evidence shows that persistent deduplication requires a stored fingerprint, that is a new decision and a privacy review, not an implementation detail.

## Authentication and access

Authentication is postponed until the public analysis flow is complete, following the professor's sequencing advice. The first release has no accounts, roles, login screen, guest quota, or server-side user history. Scoring and its explanation are available without signing in.

Later, accounts may add synchronized history, saved preferences, and role-gated administration. Authentication will not be required to make the core scanner work. Admin inspection and local adapter-enablement functions may be built and exercised in a local development environment before authentication; they must be protected before any shared or hosted deployment and are absent from the default backend profile. Managing user accounts itself depends on account functionality and therefore belongs with authentication.

Postponing authentication does not mean postponing basic security: validate inputs, restrict browser origins, protect secrets, use HTTPS for hosted communication, and avoid logging review text. The local MVP backend binds to loopback by default; exposing an unauthenticated scoring API on a shared network requires an explicit risk decision plus quotas and edge rate limiting.

## First supported site and scope boundary

The first adapter targets Amazon product review pages, because Amazon is already a named target in the project brief and provides a concrete page type for the first end-to-end demonstration. The adapter is intentionally narrow: supported product-review pages only, with selectors validated against a small set of manually chosen pages and fixtures. It does not promise compatibility with every Amazon locale, layout, or page state.

Phase 0 runs a feasibility spike with pass criteria: on three pre-chosen page variants it must extract at least five eligible reviews per page, match a manual count with at least 90% precision, and keep stable selectors across two consecutive loads. If the spike fails, the team records why and either uses saved-page fixtures for the demo while keeping the adapter architecture, or chooses an alternate site with the professor's approval. A late pivot without a recorded trigger is not acceptable.

If the adapter cannot reliably identify a review, return an explicit unsupported/unknown state. Do not apply a generic page-wide text scraper and present its output as a review.

## Repository and component decision

Start with one GitHub monorepo named `trustloop`, containing three independently runnable components: `backend/`, `scoring-service/`, and `extension/`, plus `docs/`, and a shared `contracts/v1/` directory for the frozen request/response examples and fixtures. This resolves the earlier two-repository versus three-codebase mismatch and keeps contracts and the academic submission together. The components remain separate processes with explicit API contracts; the monorepo does not mean one deployable application.

## Delivery principle

Complete a narrow, working path from a supported page to a score and explanation before adding authentication. Prefer one coherent and testable flow over implementing every later requirement shallowly. The architecture must leave room for additional adapters and account features without making them prerequisites for the MVP.

If a supported language does not meet its published acceptance gate, preserve honest behaviour before breadth: ship `SIGNALS_ONLY` or narrow that language to `UNKNOWN`. Never replace a failed model with an unvalidated score.

## Design consistency

The graphic charter is the visual source of truth. It must be exported into `docs/design/` and linked from this document before Phase 0 exits; a Figma file alone is not a versioned baseline. See [design source of truth](design/README.md).

Keep the charter's six solid trust-scale stops and non-colour verdict cues, but use the revised band labels in the [copy deck](#copy-deck) instead of labels that claim a review is a bot or spam. The Figma prompt should permit only gradients the charter explicitly assigns to a surface; trust badges and trust-scale fills are always solid. Explanations describe contributing model signals, never proof or causation. French and English strings use the same score meaning and verdict bands.

## Decision register

Status values: **Accepted** (baseline), **Provisional** (valid until the stated gate), **Open** (not yet decided).

| ID | Decision | Authoritative section | Status | Revisit trigger |
|---|---|---|---|---|
| D01 | The product estimates text patterns only; no identity, purchase, truth, or product-quality claim. | §Product definition | Accepted | Any proposal to add non-text inputs or a page aggregate |
| D02 | `trustScore` is `100 × p_organic` rounded half up, clipped to 0–100; six fixed bands; no post-hoc adjustment. | §Score and verdict | Accepted | Model or charter change that alters band meaning |
| D03 | `UNKNOWN` is never numeric and carries an enumerated reason code; no score or verdict field. | §Score and verdict; architecture §Unknown reason codes | Accepted | New failure mode or reason code |
| D04 | Evidence quality is `LOW`/`ADEQUATE` from input sufficiency, not confidence; `LOW` is shown with an indicative qualifier. | §Score and verdict; model plan §11 | Accepted | Evidence thresholds fail validation |
| D05 | Authentication is postponed; security baseline is not. | §Authentication and access | Accepted | Any shared or hosted deployment |
| D06 | Amazon is the first adapter; narrow scope, fixtures, explicit unsupported state, spike pass criteria. | §First supported site | Accepted | Phase 0 spike failure |
| D07 | One monorepo with three runnable components, `docs/`, and `contracts/v1/`. | §Repository and component decision | Accepted | A component needs independent release cadence |
| D08 | Build the non-auth analysis path first; cut breadth before weakening score meaning. | §Delivery principle; delivery plan §Scope control | Accepted | Course deadline or scope change |
| D09 | Local history is opt-in, metadata-only, capped, and never stores text, URL, review key, or persistent fingerprint. | §Local history | Accepted | A requirement for cross-session history |
| D10 | Live review text never goes to an external hosted AI provider; the scoring service is local/private. | Architecture §Privacy and retention baseline | Accepted | A hosted model proposal |
| D11 | Explanations describe contributing signals, never proof or causation; numeric contributions only when validated. | §Score and verdict; model plan §10 | Accepted | A new explainer method |
| D12 | Model v1 supports English; French is conditional on passing the FR gate. | Model plan §5, §9 | Provisional | Phase 1 FR evaluation |
| D13 | Gate is per language: a passing language serves `MODEL`; a failing language returns `UNKNOWN` or `SIGNALS_ONLY`, never an unvalidated score. | Model plan §9, §12 | Accepted | Gate failure in any language |
| D14 | Freeze contract v1 endpoints, constants, reason codes, and shared JSON fixtures before integration. | Architecture §API surface, §Contract constants | Accepted | Any contract change |
| D15 | Admin surfaces exist only in the `dev-admin` profile, bind to loopback, and are absent by default. | Architecture §Profiles and admin isolation | Accepted | Any need to expose admin remotely |
| D16 | Adapter configuration lives in versioned files; PostgreSQL arrives only for a defined later feature. | Architecture §Persistence trigger | Accepted | Runtime adapter authoring, accounts, or durable aggregates |
| D17 | An eligible review is rendered and not hidden; viewport intersection only schedules scanning. | Architecture §Eligibility and deduplication | Accepted | A page type where this definition is insufficient |
| D18 | Every request carries `X-Request-Id`; logs are content-free. | Architecture §Observability | Accepted | Hosted monitoring requirement |
| D19 | Model artifacts are versioned bundles with a model card; the backend checks the expected version. | Model plan §2, §14 | Accepted | Artifact distribution change |
| D20 | The graphic charter and Figma prompt are stored in `docs/design/`; the copy deck above is normative. | §Design consistency; §Copy deck | Accepted | Charter revision |
| D21 | Tests are part of every phase exit, not a final phase. | Delivery plan exit conditions; MVP §Traceability | Accepted | None |
| D22 | Final training dataset selection and licensing: fixed in `docs/dataset/dataset-manifest.json` — Ott 2011 (CC BY-NC-SA 4.0, verified), Ott 2013 and YelpChi (research-use terms to be recorded at download; YelpChi evaluation-only, never training), GraphConsis Amazon (pending verification, unused until verified). Raw data stays outside version control; hashes recorded at download. | Model plan §4; manifest | Accepted | A source fails its stated verification |
| D23 | French go/no-go criterion frozen: FR ships `MODEL` only if the frozen FR gate in `scoring-service/evaluation/gate-v1.json` passes on the manual FR sample; otherwise `SIGNALS_ONLY` or `UNKNOWN` per the ladder. The criterion leaves no discretion at Phase 1; only its mechanical application remains. | Model plan §5, §9, §12; gate-v1.json | Accepted | FR gate evaluation (outcome applies automatically) |
| D24 | One model per supported language; no single multilingual model at MVP. EN trains on the verified Ott corpora. FR training data, if pursued, comes only through documented translation augmentation and the FR model is still gated on the manual FR labels; if either fails, French returns `UNKNOWN` per D23. Translation augmentation never expands the language claim. | Model plan §6, §7 | Accepted | FR data sufficiency at Phase 1 training |

## Glossary

| Term | Meaning |
|---|---|
| Organic | Review text whose patterns are consistent with a spontaneous review. Not a claim that the review is true or verified. |
| Manipulated | Review text whose patterns are consistent with manipulation. Not proof of intent or reviewer identity. |
| `p_organic` | Calibrated probability that the text is organic, on the evaluation distribution. |
| Trust score | Integer 0–100 equal to `100 × p_organic` rounded half up; a text-pattern estimate. |
| Verdict band | One of the six fixed score ranges in §Score and verdict. |
| Evidence quality | `LOW` or `ADEQUATE` input sufficiency, not model confidence. |
| Signal | A named text pattern that contributed to the model output, with direction and optional validated contribution. |
| Contribution | Signed, normalized attribution for a signal; shown only when the explainer is stable and validated. |
| Engine | `MODEL` or `SIGNALS_ONLY`; identifies what produced the result. |
| Status | `SCORED`, `SIGNALS_ONLY`, or `UNKNOWN`. |
| Unknown | No estimate can be produced; carries a reason code and never a numeric score. |
| Reason code | Enumerated cause of an unknown result or request error. |
| Adapter | Page-specific extraction module with a manifest, selectors, supported-page description, and fixtures. |
| Eligible review | A review card rendered and not hidden inside the adapter's container, with extractable text. |
| Batch | Up to 10 reviews sent in one analyze request. |
| Model version | `tl-text-<major>.<minor>.<patch>`; carried by `MODEL` results and by `UNKNOWN` results produced by the scoring service. |
| Calibration | Mapping from raw model output to `p_organic`; evaluated with ECE and reliability curves. |
| Session-scoped dedup key | Salted page-session identifier used to avoid resubmission; never persisted. |
| Signal-only mode | Descriptive, validated text patterns without a score or probability. |
