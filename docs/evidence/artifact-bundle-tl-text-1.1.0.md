# Phase 1.4 artifact bundle evidence

**Artifact:** `tl-text-1.1.0`  
**Status:** experimental, local-only, not for serving  
**Production decision:** English `UNKNOWN`; French `UNKNOWN`  
**Built and verified:** 2026-11-02

The local bundle at `scoring-service/artifacts/tl-text-1.1.0/` contains the
trained pipeline, calibration parameters, transfer metrics with clustered 95%
intervals, model card, dataset manifest, exact runtime lock, and source training
and calibration reports. The builder verified all 8 files against
the artifact manifest and loaded the pipeline offline. The manifest checksum is:

```text
c7ec55715148a0829ffdf4bef52100f754d37a04312bfbd395ac50d77de32f0a
```

The confidence intervals use only **4** independent
source/page clusters in the 80-row public test set; they are therefore unstable
and indicative. ECE's interval is 0.0414–0.1777 and Brier's is 0.0634–0.1132. This is not the manually labeled Amazon gate. No artifact serving is enabled.

The backend pins expected model version `tl-text-1.1.0`. If the local bundle is
present, scoring-service startup verifies its version, manifest hash, file
hashes, runtime lock, and pipeline shape. A mismatch aborts startup. A valid
candidate bundle still leaves `/health` not-ready while the product gate is
`UNKNOWN`.

The binary bundle is ignored by Git to avoid distributing a model derived from
the non-commercial CC BY-NC-SA training corpus. Recreate it locally with
`python -m app.build_artifact` after rebuilding and evaluating the candidate.
