# Phase 1.2 baseline model decision

**Status:** an experimental English candidate was trained on the verified
Ott 2011 positive-polarity hotel-review corpus. It is a public-corpus baseline,
not an in-domain Amazon model, and is not enabled for serving.

- **EN — `UNKNOWN`:** candidate trained with selected `C=0.01`; dev-only tuning
  F1 for manipulated was 0.8736 on 80 rows. This is a tuning score on an out-of-
  domain public hotel corpus, not a gate result. The frozen manual Amazon gate has
  not been evaluated.
- **FR — `UNKNOWN`:** no verified French training source or independently labeled
  French manual sample is available; D23 requires both a separate French model
  and a passing frozen French gate before support.

The archive contained 1,600 rows. The manifest filters to 800 positive-polarity
Ott 2011 rows and excludes 800 negative-polarity rows from the later collection.
The deterministic split is 560 train, 80 dev, 80 calibration, and 80 test rows;
all splits are English, with 280/40/40/40 from each of the MTurk and TripAdvisor
source groups. Near-duplicate removal dropped zero rows. The trainer read only
train/dev and refit on their 640 combined rows; it did not open calibration or test.

The binary candidate and exact `requirements.lock` remain in ignored
`scoring-service/artifacts/candidates/baseline-v1/`; they are regenerated with
`python -m app.train_baseline` after rebuilding splits. These are product
decisions, not model predictions. The candidate remains unserved until held-out
manual evaluation, calibration, and the per-language acceptance gate are complete.
