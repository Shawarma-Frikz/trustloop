# Dataset, codebook, and acceptance gate (roadmap step 0.4)

This directory freezes the evaluation contract before any training happens.
Roadmap rule: *deciding the pass mark after seeing the result is how projects
become unfalsifiable.* Everything here is versioned; changing it requires a
decision-register entry and a new version.

## Contents

| File | Role |
|---|---|
| [codebook.md](codebook.md) | Annotation codebook v1.1: `organic` / `manipulated` / `uncertain`, manipulation-pattern checklist, explicit exclusions, kappa + adjudication protocol. |
| [calibration-batch-v1.md](calibration-batch-v1.md) | Thirty original invented texts in each language for blind, independent codebook calibration. |
| [sample-plan.md](sample-plan.md) | Held-out manual evaluation plan v1.1: 250 EN and 175 FR targets, deterministic selection, eligibility floor, page-cluster confidence intervals, collection hygiene. |
| [dataset-manifest.json](dataset-manifest.json) | Sources, roles, languages, licence terms, verification status, and acquisition-time hash policy. Raw data stays outside version control. |
| `../../scoring-service/evaluation/gate-v1.json` | The frozen EN/FR acceptance gate transcribed from model plan §9, with its anti-tamper test. |

## Closeout status

- [x] Codebook v1.1 and calibration procedure written.
- [x] Invented English and French calibration batches prepared; no labels or answer key included.
- [ ] Independent calibration by two annotators (at least 30 items), kappa ≥ 0.60, and adjudication records.
- [x] Sample plan v1.1 pre-registered; label-dependent redraw and adaptation use removed.
- [x] Manifest records the verified Ott 2011 candidate and blocks sources with unresolved terms.
- [x] EN/FR gate frozen and pinned to model plan §9 by `test_gate_and_manifest.py`.
- [x] D22–D24 outcomes recorded; D25 records the sample-plan correction.
- [ ] Acquire only approved data and add real file hashes before the dataset is used in Phase 1.

## What is deliberately not here yet

- **Dataset hashes** — no dataset files are present in the workspace. Hashes are
  recorded at acquisition in Phase 1; empty `files[]` means not acquired, never a
  fabricated hash.
- **The annotated sample itself** — collection and double annotation are scheduled
  in [sample-plan.md](sample-plan.md) §7; review text never enters this repository.
- **Kappa numbers** — require two independent human annotations; report aggregate
  counts only after the calibration is performed.

## Hard rule

No live TrustLoop review text is ever used for training. Inference text is
processed transiently and never retained.
