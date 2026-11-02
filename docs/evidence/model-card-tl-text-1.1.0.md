# Model card — tl-text-1.1.0

**Status:** experimental artifact; not for serving. **Production decision:** `UNKNOWN` until the frozen manual in-domain Amazon gate passes.

## Intended use

Reproducible coursework and offline evaluation of a text-only linear baseline. It is not intended to assess individual reviewers, determine whether a review is true, moderate content, or support purchase, safety, employment, or other consequential decisions. It is not connected to the extension or public API.

## Model and version

- Version: `tl-text-1.1.0`; family: word 1–2 gram and character 3–5 gram TF-IDF with balanced logistic regression.
- Selected regularization: `C=0.01`; tuned on dev only.
- Calibration: `isotonic` on the dedicated calibration split; method selected on dev by ECE then Brier.
- Explanation: signed linear feature contributions are aggregated to named signal families and normalized over the complete active feature set. Numeric contributions are kept only after the 3-run stability and determinism checks. Cross-review duplication remains qualitative because it was not a trained feature.

## Data

- Training source: Ott et al. 2011 positive-polarity English hotel reviews (public Kaggle mirror; CC BY-NC-SA 4.0, non-commercial). No raw examples are included in this bundle.
- Label mapping: crowdsourced deceptive → `manipulated`; truthful → `organic`. These are noisy proxy labels, not ground truth.
- Rows: train 560 ({'manipulated': 280, 'organic': 280}); dev 80 ({'manipulated': 40, 'organic': 40}); public test 80 ({'organic': 40, 'manipulated': 40}).
- Calibration and test samples are from the same public hotel corpus. The test metrics below are transfer evidence, not an Amazon in-domain evaluation.
- French has no candidate or evaluation sample.

## Evaluation — public-corpus transfer only

The 95% intervals are percentile intervals from percentile bootstrap resampling source-group/page clusters with replacement, 1000 replicates, seed 20261104. The test data has only 4 source/page clusters, so these intervals are unstable and indicative. They do not become the frozen gate's confidence intervals because the evaluation sample is not the manual in-domain sample.

| Metric | Point estimate | 95% cluster-bootstrap interval |
|---|---:|---:|
| AUROC (manipulated) | 0.9419 | 0.8887–1.0000 |
| AUPRC (manipulated) | 0.9224 | 0.7304–1.0000 |
| F1 (manipulated, pOrganic=0.50) | 0.8941 | 0.7347–0.9703 |
| ECE | 0.0778 | 0.0414–0.1777 |
| Brier score | 0.0890 | 0.0634–0.1132 |

The frozen manual gate result is **NOT EVALUATED**. English and French production decisions remain `UNKNOWN`. Do not interpret calibrated probabilities as Amazon prevalence or real-world likelihood.

## Limitations and risks

- Strong domain shift: hotel reviews are not Amazon product reviews; no Amazon gate sample has been evaluated.
- Small, balanced public test set; confidence intervals are wide and reliability bins are sparse.
- Labels are crowdsourced proxies and may encode dataset collection artifacts.
- English only; unsupported and French-language production use is not validated.
- Signal families use English lexicons; summaries describe text patterns and do not establish deception, intent, identity, or causation.
- Model integrity checks detect accidental or unmanifested changes; the unsigned SHA-256 manifest is not a cryptographic publisher signature.

## Provenance and decisions

Dataset-manifest SHA-256: `8b1ee73cec12329261ee25e24626ec983310f3dcdeb4a3d53d3c3bd0bcb0d60c`. Training report and calibration report hashes are recorded in `artifact-manifest.json`. Relevant decisions: D22 (source/licence), D28 (baseline), D29 (calibration and explanation protocol).

Artifact built for local offline use on 2026-11-02. Raw dataset and model bundle are not committed; regenerate from the hash-pinned local corpus using the documented pipeline.
