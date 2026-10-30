# Held-out manual evaluation sample · plan v1.0

**Status:** frozen with the acceptance gate, 2026-10-30. The gate
([gate-v1.json](../../scoring-service/evaluation/gate-v1.json)) is evaluated on this
sample only. Changing the sample method after seeing results invalidates the gate;
any change here is a new version of this document plus a decision-register entry.

## 1. Purpose and rule

This sample is the **primary held-out evaluation** for the per-language acceptance
gate ([model plan](../model-plan.md) §9). It is labelled by hand under the
[codebook](codebook.md). Live TrustLoop review text is never used for training;
this sample is evaluation-only and doubly so — no part of it may feed training,
feature selection, threshold tuning, or calibration. If adaptation is ever needed,
a separate adaptation split is carved out **before** labelling and the gate is
computed only on the untouched remainder (both results are then reported).

## 2. Size and language

| Language | Target size | Hard range | Rationale |
|---|---|---|---|
| English | 250 | 200–300 | Enough for AUROC CI width ≈ ±0.05 at worst-case variance; matches the model plan. |
| French | 175 | 150–200 | Matches the model plan; FR gate targets are relaxed accordingly. |

`uncertain` items count toward the sample size but are excluded from primary
metrics; the plan therefore over-samples by ~15% so that the labelled
organic/manipulated pools still meet the range after exclusions.

## 3. Sampling frame and method

**Frame.** Amazon product review pages across at least four product categories
(for example: home goods, electronics accessories, books, beauty). At least three
distinct product pages per category, chosen by hand before any review is read —
the page list is fixed in advance and archived with the sample.

**Method (documented, reproducible):**

1. From each chosen page, take all reviews rendered on first load, in page order.
2. **Eligibility:** visible review text of at least 20 whitespace-delimited words,
   in the target language. The 20-word floor mirrors the product's evidence gate so
   the evaluation set matches production inputs.
3. **Selection:** deterministic systematic sample — every *k*-th eligible review,
   where *k* is chosen per page so the page contributes proportionally to the
   frame, seed recorded. No cherry-picking: the person collecting cannot read the
   full text before selection, only confirm eligibility.
4. **Stratification:** the final sample is checked so that neither label class
   (after annotation) dominates beyond 70/30. The *check* is reported; if violated,
   the sampling is rerun with a different seed — never by hand-picking individual
   reviews.
5. **Cap per page:** at most 25% of the final sample from any single page, to
   bound page-level correlation.

**Why systematic rather than "interesting" sampling:** the gate must measure the
model on the population it will see — ordinary rendered reviews — not on examples
chosen because they look manipulated. Convenience sampling is the main way a gate
like this lies.

## 4. Collection hygiene

- Reviews are collected into an offline sheet with an opaque ID (page index +
  sequence number). **No reviewer names, avatars, profile links, or star ratings
  are recorded.**
- The sheet and any exports live outside version control (same rule as all
  reviewer-adjacent data). Only counts and aggregates enter the repository.
- Collection date, page list (ASINs or URLs), seed, and the eligibility counts per
  page are recorded in the sample's provenance note — URLs are a sampling document,
  not product history, and are stored with the sheet, not committed.

## 5. Annotation protocol

Exactly as defined in [codebook](codebook.md) §5–§6:

- Two annotators, independent, blind to each other and to any model output.
- Cohen's kappa ≥ 0.60 on the three-label set or the codebook is revised before
  the sample is usable.
- Third-pass adjudication of every disagreement; adjudicated label is the
  evaluation label.
- Calibration batch first: ≥ 30 items (invented or public-corpus text), labelled
  before the real sample, to sign off the codebook.

## 6. Deliverables of the annotation effort

| Artifact | Where | Committed? |
|---|---|---|
| Annotated sheet (IDs, labels, rationales, difficulty) | offline storage | No — contains review text |
| Kappa report (per-label confusion, overall) | `scoring-service/evaluation/` summary | Yes — counts only |
| Adjudication log (disagreement → rule applied) | with the sheet; rules appended to codebook addenda | Rules yes, text no |
| Sample provenance (page list, seed, eligibility counts, dates) | with the sheet | Counts yes, URLs no |
| Final per-language evaluation sets | rebuilt by the Phase 1 pipeline from the sheet + manifest | Hashes and counts only |

## 7. Timeline

| Step | Owner | When |
|---|---|---|
| Codebook calibration batch + sign-off | both annotators | before collection |
| EN collection (250 target) | collector + recorder | week 1 |
| FR collection (175 target) | collector + recorder | week 1 |
| Independent double annotation | annotators A and B | weeks 2–3 |
| Kappa report; codebook addenda if needed | adjudicator | week 3 |
| Adjudication pass | adjudicator | week 4 |
| Hand-off to Phase 1 evaluation pipeline | ML owner | Phase 1 start |

## 8. Failure handling

- **Kappa < 0.60:** stop; rewrite codebook; fresh calibration batch; re-annotate.
  Do not "average" labels.
- **Frame too small** (page yields fewer eligible reviews than needed): add pages
  from the pre-agreed reserve list (same categories), document the addition.
- **Label class imbalance beyond 70/30 after annotation:** rerun sampling with a
  new recorded seed; never relabel by hand to force balance.
