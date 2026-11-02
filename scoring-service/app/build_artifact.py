"""Build an ignored, versioned experimental bundle from verified candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from joblib import load

from app.artifact_loader import ArtifactError, load_artifact_bundle
from app.calibrate_explain import (
    _organic_scores,
    apply_calibrator,
    calibration_metrics,
)
from app.data_pipeline import PipelineError
from app.train_baseline import REPO_ROOT, TrainingError, _load_json, _read_split


TRAINING_DIR = REPO_ROOT / "scoring-service/artifacts/candidates/baseline-v1"
CALIBRATION_DIR = REPO_ROOT / "scoring-service/artifacts/candidates/calibration-v1"
SPLIT_DIR = REPO_ROOT / "data/processed/splits"
DATASET_MANIFEST = REPO_ROOT / "docs/dataset/dataset-manifest.json"
GATE_CONFIG = REPO_ROOT / "scoring-service/evaluation/gate-v1.json"
DEFAULT_OUTPUT = REPO_ROOT / "scoring-service/artifacts/tl-text-1.1.0"
BOOTSTRAP_RUNS = 1000
BOOTSTRAP_SEED = 20261104
METRIC_NAMES = ("aurocManipulated", "auprcManipulated", "f1ManipulatedAtPOrganic050", "ece", "brier")
METRIC_LABELS = {
    "aurocManipulated": "AUROC (manipulated)",
    "auprcManipulated": "AUPRC (manipulated)",
    "f1ManipulatedAtPOrganic050": "F1 (manipulated, pOrganic=0.50)",
    "ece": "ECE",
    "brier": "Brier score",
}
REQUIRED_FILES = (
    "model.joblib",
    "calibration.json",
    "metrics.json",
    "model-card.md",
    "dataset-manifest.json",
    "requirements.lock",
    "training-report.json",
    "calibration-explanation-report.json",
)


class ArtifactBuildError(ValueError):
    """Raised when source artifacts cannot safely form a bundle."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cluster_bootstrap_intervals(rows: list[dict[str, str]], labels: list[str], probabilities: np.ndarray) -> dict:
    clusters: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        group_key = (row["source_id"], row["source_group"], row["page_id"] or row["product_id"])
        clusters[group_key].append(index)
    cluster_keys = sorted(clusters)
    if len(cluster_keys) < 2:
        raise ArtifactBuildError("confidence intervals require at least two test page clusters")

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples: dict[str, list[float]] = {metric: [] for metric in METRIC_NAMES}
    for _ in range(BOOTSTRAP_RUNS):
        selected = rng.choice(len(cluster_keys), size=len(cluster_keys), replace=True)
        indices = [index for picked in selected for index in clusters[cluster_keys[int(picked)]]]
        resampled_labels = [labels[index] for index in indices]
        if len({label for label in resampled_labels}) < 2:
            continue
        metrics = calibration_metrics(resampled_labels, probabilities[indices])
        for metric in METRIC_NAMES:
            value = metrics.get(metric)
            if value is not None and np.isfinite(value):
                samples[metric].append(float(value))

    intervals = {}
    for metric, values in samples.items():
        if not values:
            intervals[metric] = {"lower95": None, "upper95": None, "validReplicates": 0}
            continue
        lower, upper = np.percentile(np.asarray(values), [2.5, 97.5])
        intervals[metric] = {
            "lower95": float(lower),
            "upper95": float(upper),
            "validReplicates": len(values),
        }
    return {
        "method": "percentile bootstrap resampling source-group/page clusters with replacement",
        "confidenceLevel": 0.95,
        "replicatesRequested": BOOTSTRAP_RUNS,
        "seed": BOOTSTRAP_SEED,
        "clusterCount": len(cluster_keys),
        "metrics": intervals,
    }


def _model_card(version: str, calibration: dict, training: dict, metrics: dict) -> str:
    calibrated = metrics["calibrated"]
    intervals = metrics["confidenceIntervals"]["calibrated"]["metrics"]
    interval_lines = "\n".join(
        f"| {METRIC_LABELS[name]} | {calibrated[name]:.4f} | {intervals[name]['lower95']:.4f}–{intervals[name]['upper95']:.4f} |"
        for name in METRIC_NAMES
        if calibrated.get(name) is not None and intervals[name]["lower95"] is not None
    )
    counts = training.get("languages", {}).get("en", {})
    train_counts = counts.get("trainCounts", {})
    dev_counts = counts.get("devCounts", {})
    test_counts = calibrated.get("classCounts", {})
    return f"""# Model card — {version}

**Status:** experimental artifact; not for serving. **Production decision:** `UNKNOWN` until the frozen manual in-domain Amazon gate passes.

## Intended use

Reproducible coursework and offline evaluation of a text-only linear baseline. It is not intended to assess individual reviewers, determine whether a review is true, moderate content, or support purchase, safety, employment, or other consequential decisions. It is not connected to the extension or public API.

## Model and version

- Version: `{version}`; family: word 1–2 gram and character 3–5 gram TF-IDF with balanced logistic regression.
- Selected regularization: `C={counts.get('selectedC', 'unknown')}`; tuned on dev only.
- Calibration: `{calibration.get('method')}` on the dedicated calibration split; method selected on dev by ECE then Brier.
- Explanation: signed linear feature contributions are aggregated to named signal families and normalized over the complete active feature set. Numeric contributions are kept only after the 3-run stability and determinism checks. Cross-review duplication remains qualitative because it was not a trained feature.

## Data

- Training source: Ott et al. 2011 positive-polarity English hotel reviews (public Kaggle mirror; CC BY-NC-SA 4.0, non-commercial). No raw examples are included in this bundle.
- Label mapping: crowdsourced deceptive → `manipulated`; truthful → `organic`. These are noisy proxy labels, not ground truth.
- Rows: train {sum(train_counts.values())} ({train_counts}); dev {sum(dev_counts.values())} ({dev_counts}); public test {sum(test_counts.values())} ({test_counts}).
- Calibration and test samples are from the same public hotel corpus. The test metrics below are transfer evidence, not an Amazon in-domain evaluation.
- French has no candidate or evaluation sample.

## Evaluation — public-corpus transfer only

The 95% intervals are percentile intervals from {metrics['confidenceIntervals']['calibrated']['method']}, {BOOTSTRAP_RUNS} replicates, seed {BOOTSTRAP_SEED}. The test data has only {metrics['confidenceIntervals']['calibrated']['clusterCount']} source/page clusters, so these intervals are unstable and indicative. They do not become the frozen gate's confidence intervals because the evaluation sample is not the manual in-domain sample.

| Metric | Point estimate | 95% cluster-bootstrap interval |
|---|---:|---:|
{interval_lines}

The frozen manual gate result is **NOT EVALUATED**. English and French production decisions remain `UNKNOWN`. Do not interpret calibrated probabilities as Amazon prevalence or real-world likelihood.

## Limitations and risks

- Strong domain shift: hotel reviews are not Amazon product reviews; no Amazon gate sample has been evaluated.
- Small, balanced public test set; confidence intervals are wide and reliability bins are sparse.
- Labels are crowdsourced proxies and may encode dataset collection artifacts.
- English only; unsupported and French-language production use is not validated.
- Signal families use English lexicons; summaries describe text patterns and do not establish deception, intent, identity, or causation.
- Model integrity checks detect accidental or unmanifested changes; the unsigned SHA-256 manifest is not a cryptographic publisher signature.

## Provenance and decisions

Dataset-manifest SHA-256: `{_sha256(DATASET_MANIFEST.read_bytes())}`. Training report and calibration report hashes are recorded in `artifact-manifest.json`. Relevant decisions: D22 (source/licence), D28 (baseline), D29 (calibration and explanation protocol).

Artifact built for local offline use on 2026-11-02. Raw dataset and model bundle are not committed; regenerate from the hash-pinned local corpus using the documented pipeline.
"""


def build_artifact(
    training_dir: Path = TRAINING_DIR,
    calibration_dir: Path = CALIBRATION_DIR,
    split_dir: Path = SPLIT_DIR,
    dataset_manifest_path: Path = DATASET_MANIFEST,
    gate_config_path: Path = GATE_CONFIG,
    output_dir: Path = DEFAULT_OUTPUT,
) -> dict:
    training_report_path = training_dir / "training-report.json"
    calibration_report_path = calibration_dir / "calibration-explanation-report.json"
    calibration_path = calibration_dir / "calibration.json"
    candidate_report = _load_json(training_report_path)
    evaluation_report = _load_json(calibration_report_path)
    calibration = _load_json(calibration_path)
    dataset_manifest = _load_json(dataset_manifest_path)
    gate_config = _load_json(gate_config_path)

    model_version = evaluation_report.get("modelVersionCandidate")
    if not isinstance(model_version, str) or not re.fullmatch(r"tl-text-\d+\.\d+\.\d+", model_version):
        raise ArtifactBuildError("candidate report has an invalid model version")
    if candidate_report.get("status") != "EXPERIMENTAL_CANDIDATE_NOT_FOR_SERVING":
        raise ArtifactBuildError("baseline report is not marked experimental")
    if evaluation_report.get("status") != "TRANSFER_EVALUATION_ONLY_NOT_FOR_SERVING":
        raise ArtifactBuildError("calibration report is not marked transfer-only")
    if evaluation_report.get("productionDecision", "").split()[0] != "UNKNOWN":
        raise ArtifactBuildError("production decision must remain UNKNOWN")
    if calibration.get("productionDecision", "").split()[0] != "UNKNOWN":
        raise ArtifactBuildError("calibrator must remain unapproved for production")
    if calibration.get("modelVersionCandidate") != model_version:
        raise ArtifactBuildError("model and calibration versions do not match")
    if evaluation_report.get("candidateSha256") != candidate_report.get("languages", {}).get("en", {}).get("candidateSha256"):
        raise ArtifactBuildError("calibration report references a different trained candidate")

    split_manifest_path = split_dir / "split-manifest.json"
    split_manifest_bytes = split_manifest_path.read_bytes()
    if _sha256(split_manifest_bytes) != evaluation_report.get("splitManifestSha256"):
        raise ArtifactBuildError("calibration report references a different split manifest")
    split_manifest = _load_json(split_manifest_path)
    test_rows = _read_split(split_dir, "test", split_manifest["splitHashes"]["test"])
    test_rows = [row for row in test_rows if row["language"] == "en" and row["label"] in {"organic", "manipulated"}]
    candidate_info = candidate_report["languages"]["en"]
    model_source = training_dir / candidate_info["candidateFile"]
    model_raw = model_source.read_bytes()
    if _sha256(model_raw) != candidate_info.get("candidateSha256"):
        raise ArtifactBuildError("baseline candidate checksum mismatch")
    model = load(model_source)
    if calibration.get("trainingCandidateSha256") != _sha256(model_raw):
        raise ArtifactBuildError("calibration parameters are for a different model binary")

    test_texts = [row["normalized_text"] for row in test_rows]
    test_labels = [row["label"] for row in test_rows]
    raw_scores = _organic_scores(model, test_texts)
    probabilities = apply_calibrator(calibration, raw_scores)
    confidence_intervals = _cluster_bootstrap_intervals(test_rows, test_labels, probabilities)

    metrics = {
        "modelVersion": model_version,
        "artifactStatus": "EXPERIMENTAL_NOT_FOR_SERVING",
        "evaluationStatus": "PUBLIC_CORPUS_TRANSFER_ONLY",
        "productionGate": {
            "status": "NOT_EVALUATED",
            "perLanguageDecision": {"en": "UNKNOWN", "fr": "UNKNOWN"},
            "evaluatedOn": gate_config["evaluatedOn"],
            "frozenThresholds": gate_config["languages"],
            "reason": "No manually labeled in-domain gate sample has been collected and evaluated.",
            "confidenceIntervals": None,
        },
        "sourceDomain": evaluation_report["sourceDomain"],
        "rowCount": len(test_rows),
        "classCounts": {
            "organic": sum(label == "organic" for label in test_labels),
            "manipulated": sum(label == "manipulated" for label in test_labels),
        },
        "calibratorSelection": evaluation_report["selection"],
        "raw": evaluation_report["metrics"]["raw"],
        "calibrated": evaluation_report["metrics"]["calibrated"],
        "confidenceIntervals": {
            "raw": None,
            "calibrated": confidence_intervals,
        },
        "explanation": evaluation_report["explanation"],
        "limitations": [
            "Public hotel-review performance is transfer evidence, not the Amazon gate.",
            "Balanced labels do not represent real-world prevalence.",
            "French is not evaluated and remains UNKNOWN.",
        ],
    }
    # Add matching raw-score cluster intervals without changing model selection.
    raw_probabilities = 1.0 / (1.0 + np.exp(-np.clip(raw_scores, -709, 709)))
    metrics["confidenceIntervals"]["raw"] = _cluster_bootstrap_intervals(test_rows, test_labels, raw_probabilities)

    files_to_copy = {
        "model.joblib": model_source,
        "calibration.json": calibration_path,
        "requirements.lock": training_dir / "requirements.lock",
        "training-report.json": training_report_path,
        "calibration-explanation-report.json": calibration_report_path,
    }
    dataset_bytes = dataset_manifest_path.read_bytes()
    output_dir = Path(output_dir)
    artifacts_root = (REPO_ROOT / "scoring-service/artifacts").resolve()
    output_resolved = output_dir.resolve()
    if output_resolved != artifacts_root and artifacts_root not in output_resolved.parents:
        raise ArtifactBuildError("artifact output must stay inside scoring-service/artifacts")
    if output_dir.is_symlink():
        raise ArtifactBuildError("artifact output directory cannot be a symlink")
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, source in files_to_copy.items():
        shutil.copyfile(source, output_dir / name)
    (output_dir / "dataset-manifest.json").write_bytes(dataset_bytes)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    model_card = _model_card(model_version, calibration, candidate_report, metrics)
    (output_dir / "model-card.md").write_text(model_card, encoding="utf-8")
    model_card_evidence = REPO_ROOT / "docs" / "evidence" / f"model-card-{model_version}.md"
    model_card_evidence.write_text(model_card, encoding="utf-8")

    missing = [name for name in REQUIRED_FILES if not (output_dir / name).is_file()]
    if missing:
        raise ArtifactBuildError(f"artifact output missing files: {', '.join(missing)}")
    file_table = {}
    for name in sorted(REQUIRED_FILES + ("training-report.json", "calibration-explanation-report.json")):
        raw = (output_dir / name).read_bytes()
        file_table[name] = {"sha256": _sha256(raw), "bytes": len(raw)}
    manifest = {
        "formatVersion": "1",
        "modelVersion": model_version,
        "artifactStatus": "EXPERIMENTAL_NOT_FOR_SERVING",
        "productionDecision": "UNKNOWN",
        "servingEnabled": False,
        "sourceStatus": evaluation_report["status"],
        "datasetManifestSha256": _sha256(dataset_bytes),
        "trainingReportSha256": _sha256(training_report_path.read_bytes()),
        "calibrationReportSha256": _sha256(calibration_report_path.read_bytes()),
        "files": file_table,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    (output_dir / "artifact-manifest.json").write_bytes(manifest_bytes)
    artifact_digest = _sha256(manifest_bytes)
    (output_dir / "artifact.sha256").write_text(f"{artifact_digest}  artifact-manifest.json\n", encoding="ascii")

    loaded = load_artifact_bundle(output_dir, model_version)
    evidence_path = REPO_ROOT / "docs" / "evidence" / f"artifact-bundle-{model_version}.md"
    interval_summary = confidence_intervals["metrics"]
    evidence_text = f"""# Phase 1.4 artifact bundle evidence

**Artifact:** `{model_version}`  
**Status:** experimental, local-only, not for serving  
**Production decision:** English `UNKNOWN`; French `UNKNOWN`  
**Built and verified:** 2026-11-02

The local bundle at `scoring-service/artifacts/{model_version}/` contains the
trained pipeline, calibration parameters, transfer metrics with clustered 95%
intervals, model card, dataset manifest, exact runtime lock, and source training
and calibration reports. The builder verified all {len(file_table)} files against
the artifact manifest and loaded the pipeline offline. The manifest checksum is:

```text
{artifact_digest}
```

The confidence intervals use only **{confidence_intervals['clusterCount']}** independent
source/page clusters in the 80-row public test set; they are therefore unstable
and indicative. ECE's interval is {interval_summary['ece']['lower95']:.4f}–{interval_summary['ece']['upper95']:.4f} and Brier's is {interval_summary['brier']['lower95']:.4f}–{interval_summary['brier']['upper95']:.4f}. This is not the manually labeled Amazon gate. No artifact serving is enabled.

The backend pins expected model version `{model_version}`. If the local bundle is
present, scoring-service startup verifies its version, manifest hash, file
hashes, runtime lock, and pipeline shape. A mismatch aborts startup. A valid
candidate bundle still leaves `/health` not-ready while the product gate is
`UNKNOWN`.

The binary bundle is ignored by Git to avoid distributing a model derived from
the non-commercial CC BY-NC-SA training corpus. Recreate it locally with
`python -m app.build_artifact` after rebuilding and evaluating the candidate.
"""
    evidence_path.write_text(evidence_text, encoding="utf-8")
    return {
        "output": str(output_dir),
        "modelVersion": model_version,
        "artifactStatus": manifest["artifactStatus"],
        "productionDecision": manifest["productionDecision"],
        "artifactSha256": artifact_digest,
        "fileCount": len(file_table),
        "modelCardEvidence": str(model_card_evidence),
        "artifactEvidence": str(evidence_path),
        "loadedAndVerified": isinstance(loaded.get("model"), type(model)),
        "confidenceIntervals": confidence_intervals,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-dir", type=Path, default=TRAINING_DIR)
    parser.add_argument("--calibration-dir", type=Path, default=CALIBRATION_DIR)
    parser.add_argument("--splits", type=Path, default=SPLIT_DIR)
    parser.add_argument("--dataset-manifest", type=Path, default=DATASET_MANIFEST)
    parser.add_argument("--gate-config", type=Path, default=GATE_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = build_artifact(
            args.training_dir,
            args.calibration_dir,
            args.splits,
            args.dataset_manifest,
            args.gate_config,
            args.output,
        )
    except (ArtifactBuildError, ArtifactError, PipelineError, TrainingError, OSError, KeyError, ValueError) as exc:
        print(f"artifact build error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
