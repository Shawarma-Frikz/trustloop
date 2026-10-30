# Held-out manual evaluation sample · plan v1.1

**Status:** pre-registered before collection, 2026-10-30. This v1.1 resolves
label-dependent resampling and adaptation ambiguities in v1.0. The gate
([gate-v1.json](../../scoring-service/evaluation/gate-v1.json)) is evaluated on this
sample only. Later changes require a decision-register entry and a new gate version
before evaluation results are seen.

## 1. Purpose and rule

This sample is the **primary held-out evaluation** for the per-language acceptance
gate ([model plan](../model-plan.md) §9). It is labelled by hand under the
[codebook](codebook.md). Live TrustLoop review text is never used for training;
this sample is evaluation-only and doubly so — no part of it may feed training,
feature selection, threshold tuning, or calibration. There is no adaptation split
within this sample. Any future adaptation data must be separately sourced and
documented before use; this sample and gate remain untouched.

## 2. Size and language

| Language | Target size | Hard range | Rationale |
|---|---|---|---|
| English | 250 | 200–300 | Matches the predeclared EN plan and gate. |
| French | 175 | 150–200 | Matches the predeclared FR plan and gate. |

The target and range refer to all selected, eligible items, including items later
labelled `uncertain`. `uncertain` is excluded from binary gate metrics. Report the
uncertain count and rate and the resulting binary metric denominators. Do not add
items, change the seed, or resample based on labels or model results. If fewer than
200 EN or 150 FR items receive an adjudicated binary label, that language's gate is
inconclusive and the model does not ship for that language.

## 3. Sampling frame and method

**Frame.** Amazon product review pages across at least four product categories
(for example: home goods, electronics accessories, books, beauty). At least three
distinct product pages per category, chosen by hand before any review is read —
the page list is fixed in advance and archived with the sample.

**Method (documented, reproducible):**

1. From each chosen page, enumerate reviews rendered on first load, in page order.
2. **Eligibility:** visible review text of at least 20 whitespace-delimited words,
   in the target language. The 20-word floor mirrors the product's evidence gate so
   the evaluation set matches production inputs.
3. **Selection:** use one recorded random seed to select eligible review positions
   systematically within each page, with the random start in `1..k`. Fix page
   allocation, *k*, and seed before reading selected review text. The collector
   may inspect text only to apply the eligibility rule.
4. **Class balance:** report adjudicated class counts and proportions. Do not
   stratify, rerun, or change the seed based on labels. Retain natural imbalance
   and report it with AUPRC.
5. **Cap per page:** at most 25% of the final sample from any single page, to
   bound page-level correlation.

**Scope of inference:** pages are a predeclared, purposively selected frame, not a
probability sample of all Amazon reviews. The gate supports claims only about this
documented frame and language-specific sample. Do not describe results as
representative of all Amazon reviews. Confidence intervals must account for page
clustering by resampling pages, then reviews within pages.

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
- Calibration batches first: ≥ 30 items per evaluated language (invented or
  licensed text), labelled before the real sample; calculate kappa separately by
  language.

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
- **Label class imbalance:** keep the sample, report its balance, and interpret
  AUPRC against that balance. Never redraw to change class proportions.
- **Too few adjudicated binary labels:** report the gate as inconclusive and keep
  the language unsupported; do not supplement based on observed labels.
