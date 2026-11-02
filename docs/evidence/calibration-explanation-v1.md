# Phase 1.3 calibration and explanation evidence

**Status:** implemented for the experimental English candidate; transfer
evaluation only, not approved for serving. The source is the public Ott 2011
positive-polarity hotel-review corpus, not Amazon reviews.

## Frozen method and split use

The protocol is `scoring-service/evaluation/calibration-explanation-v1.json`.
Sigmoid and isotonic calibrators were fitted using calibration predictions. The
selected-C model trained on train only was used to compare the two calibrators
on dev by ECE, with Brier score and method name as tie-breakers. Isotonic was
selected (dev ECE 0.0681, Brier 0.1051; sigmoid ECE 0.1053, Brier 0.1074). The
selected method was then refitted using calibration predictions from the
train+dev candidate. The test split was read once for the final transfer
evaluation and was not used for fitting or selection.

The final public test set has 80 rows: 40 organic and 40 manipulated. It is a
held-out public-corpus split, not the separately planned manual in-domain
Amazon sample. These numbers do not satisfy or replace the frozen acceptance
gate.

## Test metrics

| Metric | Raw model | Calibrated isotonic |
|---|---:|---:|
| AUROC, manipulated | 0.9544 | 0.9419 |
| AUPRC, manipulated | 0.9530 | 0.9224 |
| F1 manipulated at `p_organic = 0.50` | 0.9048 | 0.8941 |
| ECE (10 equal-width bins) | 0.3952 | 0.0778 |
| Brier score | 0.2457 | 0.0890 |

Calibrated reliability curve:

| `p_organic` bin | Rows | Mean predicted | Observed organic fraction |
|---|---:|---:|---:|
| 0.0–0.1 | 9 | 0.0048 | 0.0000 |
| 0.1–0.2 | 12 | 0.1546 | 0.0833 |
| 0.2–0.3 | 1 | 0.2500 | 0.0000 |
| 0.3–0.4 | 18 | 0.3224 | 0.1667 |
| 0.4–0.5 | 5 | 0.4300 | 0.6000 |
| 0.5–0.6 | 3 | 0.5000 | 0.6667 |
| 0.6–0.7 | 0 | — | — |
| 0.7–0.8 | 0 | — | — |
| 0.8–0.9 | 0 | — | — |
| 0.9–1.0 | 32 | 0.9977 | 0.9688 |

The small sample and empty middle bins make this calibration estimate coarse.
It describes this balanced hotel-review split only, not Amazon prevalence or
real-world probability.

## Explanation and determinism

Signed linear feature contributions are grouped into the frozen signal kinds,
then divided by the total absolute contribution over the full active feature
set. The top-five subset is not renormalized. Repeated word bigrams, English
promotional/extreme/generic/concrete lexicons, and unique non-stopword unigrams
map to their corresponding signal kinds. Character n-grams are grouped only
when they match a configured lexicon phrase. `CROSS_REVIEW_DUPLICATE` remains
qualitative because the trained text-only candidate did not use that feature.

Three source-group/page-cluster bootstrap refits were compared on the same 80
test inputs. Mean pairwise top-five signal-set Jaccard was 1.00 across the 73
inputs with at least one mapped model signal. Canonical hashes of repeated full
candidate outputs matched (`25acb56b7ca68852e469d12abb3a9159e2fc9d7c3a5893371ef61174db6cd062`). Numeric contributions are therefore enabled in this
experimental candidate's explanation output; this is not a serving approval.

## Per-language decision

- **EN:** `UNKNOWN` for production pending the frozen manual in-domain Amazon gate.
- **FR:** not evaluated; no French split or candidate exists, so production is
  `UNKNOWN`.

Reproduce after rebuilding splits and training the baseline:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.calibrate_explain
Pop-Location
```

Generated parameters and the complete aggregate report are kept under the
ignored `scoring-service/artifacts/candidates/calibration-v1/`; no review text
is written to the report.
