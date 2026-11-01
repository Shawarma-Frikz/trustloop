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
| [data pipeline](../../scoring-service/app/data_pipeline.py) | Hash-checks canonical CSV or manifest-declared ZIP-member CSV inputs, normalizes text, removes near-duplicates, groups by source/product-or-page, and deterministically writes train/dev/calibration/test splits plus an aggregate build manifest. |

## Closeout status

- [x] Codebook v1.1 and calibration procedure written.
- [x] Invented English and French calibration batches prepared; no labels or answer key included.
- [ ] Independent calibration by two annotators (at least 30 items), kappa ≥ 0.60, and adjudication records.
- [x] Sample plan v1.1 pre-registered; label-dependent redraw and adaptation use removed.
- [x] Manifest records the verified Ott 2011 candidate and blocks sources with unresolved terms.
- [x] EN/FR gate frozen and pinned to model plan §9 by `test_gate_and_manifest.py`.
- [x] Reproducible split pipeline and injected-duplicate leakage test implemented; the approved Ott 2011 archive has been acquired and hash-pinned. Run the pipeline to generate the actual split counts.
- [x] D22–D24 outcomes recorded; D25 records the sample-plan correction.
- [x] Acquire only the approved Ott 2011 corpus and record its real archive SHA-256 and byte count; the source filter excludes the later negative-polarity corpus.

## What is deliberately not here yet

- **Dataset hashes** — the local Ott archive is ignored by Git; its real SHA-256
  and byte count are recorded in `dataset-manifest.json`. Other sources remain
  unacquired until their terms are verified.
- **The annotated sample itself** — collection and double annotation are scheduled
  in [sample-plan.md](sample-plan.md) §7; review text never enters this repository.
- **Kappa numbers** — require two independent human annotations; report aggregate
  counts only after the calibration is performed.

## Hard rule

No live TrustLoop review text is ever used for training. Inference text is
processed transiently and never retained.

## Rebuild training-development splits

Raw data must remain under `data/raw/<source-id>/`, outside version control.
Inputs can be canonical CSV files or a manifest-declared CSV member inside a ZIP
archive. The Ott archive is read without extraction; its manifest entry filters
`polarity=positive`, maps truthful/deceptive to organic/manipulated, and groups by
hotel. The negative-polarity rows from the later Ott collection are excluded.
The pipeline verifies the archive hash and byte count before reading it. Future
sources need an explicit schema, license verification, label mapping, and filter
where required. Held-out manual samples must not be included in these splits.

From the repository root, run:

```powershell
Push-Location scoring-service
.\.venv\Scripts\python.exe -m app.data_pipeline
Pop-Location
```

Outputs are written under the ignored `data/processed/splits/` directory. Its
`split-manifest.json` records source and generated split-file hashes, seed, split
fractions, per-split and per-source counts, and removed near-duplicates. Split groups stay within one
source, language, and product (or page when product is absent). The calibration
split is separate from held-out manual evaluation and is not for hyperparameter
tuning. The command fails if the manifest lists no acquired files or if any
recorded hash/byte count differs; it never invents counts or hashes.
