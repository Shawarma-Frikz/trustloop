# TrustLoop model plan

**Status:** Baseline for the MVP. Last reviewed 2026-10-27. This plan is subordinate to [product decisions](product-decisions.md). Changes to score meaning, label definition, or acceptance thresholds require a decision-register entry (see D02, D04, D12, D13).

## 1. What the model estimates

The model estimates `p_organic`: the probability that a review's text is organic rather than manipulated, based only on the review text and the inputs listed above. It does not verify a purchase, identify a reviewer, prove intent, or judge product quality. Labels are noisy proxies for a text pattern, not ground truth.

The MVP produces one estimate per review. It does not average reviews into a page or product score.

**MVP model inputs**

- Normalized review text (maximum 2,000 Unicode code points; see architecture contract constants).
- Server-derived `batchDuplicate` flag: whether the review shares normalized wording with another review in the same request batch. Computed transiently; never stored.
- Language detection result (internal); the extension's language hint is advisory only.

**Excluded from model v1:** star rating, verified-purchase flags, reviewer names, profile data, images, page context, and any metadata that would imply identity or purchase verification. Rating-based signals are a later, separately versioned decision.

**MVP outputs:** `SCORED` with `p_organic`, `trustScore`, `verdict`, `evidenceQuality`, up to five `signals`, `modelVersion`, and `engine = MODEL`; `SIGNALS_ONLY` with validated signals and no score; or `UNKNOWN` with a reason code. `evidenceQuality` is present when input sufficiency was assessed.

## 2. Model versioning and artifacts

`modelVersion` uses `tl-text-<major>.<minor>.<patch>`.

| Change | Version bump | Example |
|---|---|---|
| Label definition, score meaning, or band mapping | MAJOR | `tl-text-2.0.0` |
| Training data, features, calibration, or retraining | MINOR | `tl-text-1.1.0` |
| Explanation copy, performance work, no score change | PATCH | `tl-text-1.0.1` |

Each release is a self-contained artifact directory:

```text
scoring-service/artifacts/<modelVersion>/
  model.joblib              # trained pipeline
  calibration.json          # calibration method and parameters
  metrics.json              # evaluation results and confidence intervals
  model-card.md             # §14 template, filled in
  dataset-manifest.json     # sources, licenses, hashes, split counts
  requirements.lock         # pinned runtime dependencies
  artifact.sha256           # hash of the bundle
```

The backend is configured with an expected `modelVersion`. A mismatch, a malformed response, or an artifact that fails its hash check is treated as `SCORING_UNAVAILABLE`, not as a valid result. Scored results carry `engine` and `modelVersion`; `SIGNALS_ONLY` carries its engine/status and no `modelVersion`, so the UI can identify what produced every result.

The scoring service warms the model at startup and only reports ready on `/health` after the artifact is loaded. This avoids a cold first request in a demo.

## 3. Label definition

Two labels are used for training and evaluation:

- **Organic:** the text shows no manipulation pattern under the codebook and reads as a spontaneous review. This is not a claim that the review is true or verified.
- **Manipulated:** the text exhibits at least one defined manipulation pattern with enough context to support the label. Patterns include templated or duplicated wording, generic promotional phrasing, repeated superlatives, coordinated boilerplate, and content that reads as marketing copy rather than a customer account.

**Explicitly excluded from the manipulated label**

- Negative opinions, poor grammar, typos, or short reviews.
- Incentivized but honestly disclosed reviews, unless the text itself is deceptive.
- Disagreement with other reviewers, sarcasm, or unusual style.
- Reviews that are too short or ambiguous to label. These are marked `uncertain` and excluded from training and from the primary metric, not coerced into a class.

**Annotation protocol**

- Two annotators apply the same written codebook to the in-domain evaluation sample.
- Report Cohen's kappa. The sample is usable only if kappa is at least 0.60; disagreements are adjudicated by a third pass and the adjudicated label is used.
- Public dataset labels may encode a different definition (platform filter, reviewer-level flag, crowdsourced deception). Map them explicitly, report the mapping, and never merge labels silently.

## 4. Data sources

| Source | Role | Language | Label basis | Main risk / action |
|---|---|---|---|---|
| Ott et al. (2011), Deceptive Opinion Spam Corpus | Training/dev | EN | Crowdsourced deceptive vs truthful hotel reviews | Hotel domain, not Amazon; confirm research license |
| Ott et al. (2013), Negative Deceptive Opinion Spam | Training/dev | EN | Negative deceptive vs truthful hotel reviews | Same domain shift; confirm license |
| YelpChi (Rayana & Akoglu, 2015) | Optional cross-domain evaluation | EN | Yelp's review filter | Filter label is a platform signal, not ground truth; metadata leakage; text-only evaluation only |
| Amazon review dataset distributed with GraphConsis (Dou et al., 2020) | Optional adaptation/evaluation | EN | Platform-derived fake labels | Verify whether labels are review-level or reviewer-level; do not treat reviewer-level labels as review labels; confirm license |
| In-domain manual sample: 200–300 EN reviews; 150–200 FR reviews | Primary held-out evaluation | EN/FR | Manual codebook (§3) | Small sample; report confidence intervals and sampling method |
| EN→FR translation augmentation of training data | Training augmentation only | FR | Inherited | Translation artifacts; FR evaluation must use manual labels only |

**Data rules**

- Use public or explicitly licensed research data. No scraped reviewer names, profiles, or account data.
- Store datasets outside version control when their license forbids redistribution; commit a download script and `dataset-manifest.json` with hashes instead.
- Do not use live TrustLoop review text for training in the MVP. Inference text is processed transiently and never retained.
- If translation is used for training augmentation, use a local or licensed tool. The "no external AI provider" rule applies to live review text at inference; public training text still needs a documented processing note.
- Final dataset selection and licensing are open until Phase 0 exit (D22).

If part of the manual sample is used for adaptation or threshold tuning, the gate in §9 is computed only on the untouched held-out portion; report both the adaptation and held-out results.

## 5. Language coverage

- **English:** primary MVP language; must pass the EN gate in §9.
- **French:** supported only if the manual FR evaluation set passes the FR gate. Until then, French review text returns `UNKNOWN` with `UNSUPPORTED_LANGUAGE`. There is no silent translation of live reviews at inference.
- Language identification uses a lightweight detector (for example fastText `lid.176` or CLD3). A supported language requires confidence of at least 0.80. Low-confidence, mixed, or unsupported language returns `UNKNOWN`.
- UI copy is English and French regardless of model language support. The normative copy deck is in [product decisions](product-decisions.md#copy-deck).
- French go/no-go is a Phase 1 gate decision (D23). Do not claim French model coverage because the UI is translated.

## 6. Model family and baseline

**MVP model:** TF-IDF (word 1–2 grams plus character 3–5 grams) with logistic regression, class weights balanced, regularisation tuned on the dev split.

Why this baseline:

- It works on small labelled datasets and CPU-only student hardware.
- It is deterministic and fast, which keeps the scoring timeout honest.
- Linear coefficients give an exact, stable attribution for the explanation, avoiding unstable post-hoc explainers.
- Platt or isotonic calibration is direct and auditable.

**Optional Phase 3 candidate:** a multilingual transformer (for example DistilBERT or XLM-R). It may replace the baseline only if it beats it on the manual in-domain evaluation, passes calibration and explanation-stability gates, and ships with a new MINOR/MAJOR model version. A transformer is not required for the MVP.

No off-the-shelf "fake review detector" is trusted without in-domain validation. A model trained on hotel reviews is not assumed to work on Amazon reviews.

## 7. Splits and training protocol

- Split by product/page and by source, not by individual review, to prevent near-duplicate leakage.
- Remove near-duplicates across splits (MinHash or cosine similarity on normalized text) before training.
- Use train / dev / calibration / test splits. The calibration split is never used for hyperparameter tuning.
- Fix random seeds. Record library versions, split manifests, and dataset hashes.
- Tune hyperparameters on dev only. Touch the test split once per candidate model and report the result even if it is disappointing.
- Report class balance and sampling method. Public datasets are often class-balanced by construction; do not read their base rate as real-world prevalence.
- Decide single multilingual vs per-language models in Phase 1 (D24). Default preference is one model per supported language when each has enough labelled data; otherwise one multilingual model with language as a reported subgroup.

## 8. Calibration

- Fit Platt scaling or isotonic regression on the dedicated calibration split; choose the method by reliability on dev, then report on test.
- Report expected calibration error (ECE), Brier score, and a reliability curve, per language and overall.
- **Calibration scope:** `p_organic` is calibrated to the evaluation distribution, not to the prevalence of manipulation on Amazon. Because public corpora are balanced by construction, the score is a text-pattern estimate, not a real-world probability. The report and UI must state this limitation; do not present `73` as "73% of Amazon reviews like this are fake/organic."
- If calibration does not reach the gate in §9, the numeric score is not shipped as a calibrated probability. Use the fallback ladder in §12.

## 9. Evaluation and acceptance gate

The gate is evaluated on the held-out manual in-domain sample, not on the training distribution. Public-dataset results are reported separately as transfer evidence, not as the gate.

| Metric | EN target | FR target | Notes |
|---|---|---|---|
| AUROC (manipulated vs organic) | ≥ 0.75 | ≥ 0.70 | Report 95% confidence intervals |
| AUPRC (manipulated class) | ≥ 0.70 | ≥ 0.65 | State the class balance of the evaluation set |
| F1 manipulated at `p_organic = 0.50` | ≥ 0.70 | ≥ 0.65 | Operating point, not a deployed threshold |
| ECE | ≤ 0.10 | ≤ 0.15 | Reliability curve shown in the report |
| Brier score | ≤ 0.20 | ≤ 0.25 | Lower is better |
| Explanation stability: top-5 signal-set Jaccard | ≥ 0.80 across 3 runs | ≥ 0.80 | Bootstrap or seed variation; fixed input |
| Determinism | Identical output for identical input and version | Same | Hash the full result |
| Latency p95, 10-review batch, 4 vCPU / 8 GB RAM, CPU-only | ≤ 1.5 s warm | Same | Cold start is warmed at boot; report separately |

The gate is a point-estimate check with confidence intervals reported and is evaluated per language. English may pass while French does not; a failing language returns `UNKNOWN` (or `SIGNALS_ONLY` if validated descriptive signals exist) and does not force a passing language into fallback. If the gate fails for a language:

1. Improve data, labels, or features and re-evaluate.
2. If it still fails, ship `SIGNALS_ONLY` (descriptive text patterns, no score, no probability) and label the engine visibly.
3. If even the descriptive signals are not validated, return `UNKNOWN`. Never present an unvalidated heuristic as `MODEL`.

## 10. Explanation method and signals

For the linear baseline, the contribution of a feature is its signed coefficient multiplied by its normalized value. Token features are aggregated into named, human-readable signal groups. Signed contributions are normalized across the full feature set so that the total absolute contribution is 1. Only the top five signals are returned, with their original normalized values; do not renormalize the returned subset. Direction is preserved. A numeric contribution is shown only when the explanation passes the stability and determinism checks; otherwise the signal is qualitative.

| Code | EN summary template | Direction | Definition | Limits |
|---|---|---|---|---|
| `REPEATED_PHRASING` | "Repeats the same phrasing" | manipulative | Repeated n-grams or sentence templates within the review | Repetition also occurs in authentic reviews |
| `CROSS_REVIEW_DUPLICATE` | "Shares wording with other visible reviews" | manipulative | Batch duplicate flag from §1 | Only within the request batch (max 10), not the whole page; shared wording can be a template or translation |
| `GENERIC_WORDING` | "Uses generic wording with few concrete details" | manipulative | Low specificity and high generic-lexicon density | Domain-dependent; not proof of intent |
| `PROMOTIONAL_TONE` | "Reads like promotional copy" | manipulative | Promotional lexicon and call-to-action patterns | Spam and advertising are not the same as deception |
| `EXTREME_CLAIMS` | "Makes extreme or unverifiable claims" | manipulative | Superlatives and absolute assertions | Stylistic signal; many genuine reviews do this |
| `CONCRETE_DETAIL` | "Includes a concrete usage detail" | organic | Specificity features such as use case, duration, comparison | Detail can be fabricated |
| `LEXICAL_VARIETY` | "Shows varied, natural wording" | organic | Type-token ratio and related diversity features | Unstable on short texts |

Rules:

- Summaries are generic templates. Never quote raw review text, names, URLs, or personal details in a signal summary.
- Say that a signal contributed to the model output. Never say it proves deception, causation, or reviewer identity.
- Do not infer "bot" or "spam account" from a score band. A named text pattern may be described only with its observable definition and limits.
- For a transformer, use a validated attribution method only if top-5 stability and determinism pass. Otherwise return qualitative signals or keep the linear model.

## 11. Evidence quality, unknown, and score mapping

- Language: the text must be a supported language with detector confidence of at least 0.80; otherwise return `UNKNOWN` with `UNSUPPORTED_LANGUAGE`.
- Hard minimum: fewer than 20 whitespace-delimited words after normalization returns `UNKNOWN` with `INSUFFICIENT_TEXT`.
- Low evidence: 20–49 words in a supported language returns a score with `evidenceQuality = LOW`.
- Adequate evidence: at least 50 words in a supported language returns `ADEQUATE`.
- Low evidence remains visible: the score and band are shown with an "Indicative — limited text" qualifier, never hidden and never silently converted to a confident result. Explanation copy states the limitation.
- `trustScore` is `100 × p_organic` rounded half up, then clipped to 0–100. The verdict is derived only from the fixed bands in [product decisions](product-decisions.md#score-and-verdict). No post-hoc band adjustment.
- `UNKNOWN` has no `trustScore` and no `verdict`; it carries a reason code and may carry `evidenceQuality`.

## 12. Fallback ladder

The fallback is chosen per language and per adapter; one language's decision does not change another language's engine. `SIGNALS_ONLY` requires the same language support and minimum text length as a scored result; otherwise the result is `UNKNOWN`. Signal-only mode is limited to patterns validated as observable facts (for example cross-review duplication and repeated phrasing); model-dependent signals such as lexical variety are not used without a validated model.

1. **`MODEL`** — the baseline meets the §9 gate. Scores and bands are served with model/version provenance.
2. **`SIGNALS_ONLY`** — a validated model score is not available, but descriptive patterns (for example cross-review duplication or repeated phrasing) are validated as observable facts. Return signals, no score, no probability, status and engine visibly `SIGNALS_ONLY`, and copy that says "descriptive only."
3. **`UNKNOWN`** — neither a validated score nor validated signals are available. Return a reason code. Never fabricate a 0, a 50, or a heuristic score.

The fallback choice is recorded in the model card and the Phase 1 gate report. It is not a silent runtime guess.

## 13. Privacy and data handling

- Live review text is processed transiently for inference. Do not persist it, log it, or send it to an external hosted AI provider.
- Training and evaluation data are public or licensed research data, kept with license notes and hashes. No reviewer identifiers.
- Model artifacts contain derived features, not raw training text. Do not publish artifacts or vocabularies that would redistribute restricted data.
- Evaluation quotes in the report must come from public datasets and must not include reviewer identifiers. Live reviews are never quoted.
- The scoring service is internal-only: loopback in local development, private network when hosted, with an internal token. It never receives browser traffic directly.

## 14. Reproducibility and model card

Every MINOR or MAJOR release includes a model card with:

- Intended use and out-of-scope uses.
- Training and evaluation data, licenses, hashes, and split method.
- Supported languages and language-specific caveats.
- Metrics with confidence intervals, calibration plots, and the acceptance-gate result.
- Explanation method, signal taxonomy, and stability result.
- Known limitations: domain shift, label noise, class-balanced calibration data, short text, sarcasm, translation artifacts, adversarial and LLM-generated text.
- Version, date, and the decision-register entries that authorised the release.

The evaluation script writes `metrics.json` from the pinned artifact and split manifest. A rerun on the same environment must reproduce the reported metrics; report any non-determinism rather than hiding it.

## 15. Phase deliverables

| Phase | Model deliverables |
|---|---|
| 0 | Confirm dataset access and licenses; define the annotation codebook and sample; freeze the §9 gate; record open decisions D22–D24 |
| 1 | Baseline training and calibration; manual evaluation sample; per-language gate result; model card draft; artifact bundle; `MODEL`, `SIGNALS_ONLY`, or `UNKNOWN` decision per language |
| 2 | No model changes unless a new adapter exposes a validated input gap; any change is a new MINOR version |
| 3 | Full held-out evaluation, calibration and stability report, confirmation of the per-language go/no-go, final model card, report evidence |
| 4 | Authentication work does not change the model; any model change follows §2 and is re-evaluated |
| 5 | Expansion only after a new gate evaluation; no silent reuse of the MVP model for a new site or language |

## 16. Model-specific risks

These are mirrored in the [delivery plan](delivery-plan.md#risk-register) risk register.

| Risk | Trigger | Mitigation |
|---|---|---|
| Public data or license unavailable | Phase 0 check fails | Switch to an approved alternative corpus; narrow claims; do not scrape |
| Domain shift from hotel/Yelp data to Amazon | Manual in-domain gate fails | Collect in-domain labels; adapt features; `SIGNALS_ONLY` fallback |
| Label noise or reviewer-level labels | Kappa below 0.60 or label granularity unclear | Rewrite codebook; drop uncertain items; exclude dataset |
| Class-balanced calibration misread as real-world probability | Report or UI implies prevalence | State calibration scope; avoid prevalence claims; copy review |
| French data gap | Manual FR set below gate | French returns `UNKNOWN`; do not claim FR model support |
| Explanation instability | Top-5 Jaccard below 0.80 | Keep linear model; qualitative signals only; version bump |
| Adversarial or LLM-generated reviews | Evaluation shows weakness | Document limitation; do not claim general detection; widen scope only with evidence |
| Cold start or latency | p95 above 1.5 s or timeout | Warm up at boot; reduce batch size; local CPU baseline |
| Overclaiming in the defense or UI | Copy says "fake" or "proven" | Copy deck review; signal language rules; model card limitations |

## 17. Open decisions

| ID | Decision | Needed by | Default if unresolved |
|---|---|---|---|
| D22 | Final dataset selection and licensing | Phase 0 exit | Do not start training on an unlicensed corpus |
| D23 | French model support go/no-go | Phase 1 gate | French returns `UNKNOWN` |
| D24 | Single multilingual model vs per-language models | Phase 1 training | Per-language if each has enough data; otherwise a single model with language subgroup reporting |
