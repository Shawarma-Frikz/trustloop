# Dataset, codebook, and acceptance gate (roadmap step 0.4)

This directory freezes the evaluation contract before any training happens.
Roadmap rule: *deciding the pass mark after seeing the result is how projects
become unfalsifiable.* Everything here is versioned; changing it requires a
decision-register entry and a new version.

## Contents

| File | Role |
|---|---|
| [codebook.md](codebook.md) | Annotation codebook v1.0: `organic` / `manipulated` / `uncertain`, manipulation-pattern checklist, explicit exclusions, worked invented examples, kappa + adjudication protocol. |
| [sample-plan.md](sample-plan.md) | Held-out manual evaluation sample plan: 250 EN (range 200–300) and 175 FR (range 150–200), systematic sampling over pre-chosen Amazon pages, eligibility floor, stratification check, collection hygiene, timeline. |
| [dataset-manifest.json](dataset-manifest.json) | Sources, roles, languages, licence terms, verification status, hash policy. Raw data stays outside version control; hashes are recorded at download and enforced by the Phase 1 pipeline. |
| `../../scoring-service/evaluation/gate-v1.json` | The frozen EN/FR acceptance gate transcribed from model plan §9, with its anti-tamper test. |

## Sign-off checklist

- [x] Codebook written (v1.0) — awaits annotator calibration-batch sign-off (§9).
- [x] Sample plan frozen (v1.0) — sizes, frame, method, hygiene.
- [x] Dataset manifest written; Ott 2011 licence verified (CC BY-NC-SA 4.0), Ott 2013 / YelpChi on-request terms flagged, GraphConsis pending.
- [x] Gate table frozen with tests pinning it to model plan §9 (`test_gate_and_manifest.py`).
- [x] D22, D23, D24 recorded in the decision register (all Accepted).

## What is deliberately not here yet

- **Hashes of raw files** — recorded at download time (Phase 1, step 1.1); the
  manifest's `files[]` entries are empty until then and the test suite enforces
  the policy that listed files must match their recorded hashes.
- **The annotated sample itself** — collection and double annotation are scheduled
  in [sample-plan.md](sample-plan.md) §7; review text never enters this repository.
- **Kappa numbers** — computed during annotation; reported as counts only.

## Hard rule

No live TrustLoop review text is ever used for training. Inference text is
processed transiently and never retained.
