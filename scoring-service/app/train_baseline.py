"""Train candidate per-language linear baselines using train/dev only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

from app.data_pipeline import PipelineError


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_CONFIG = Path(__file__).resolve().parents[1] / "evaluation" / "training-v1.json"
FIELDS = {
    "record_id", "text", "normalized_text", "label", "language",
    "source_id", "source_group", "page_id", "product_id",
}
TRAINABLE_LABELS = {"organic", "manipulated"}


class TrainingError(ValueError):
    """Raised when candidate training inputs are incomplete or inconsistent."""


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingError(f"cannot read {path}: {exc}") from exc


def _read_split(split_dir: Path, name: str, expected_hash: dict) -> list[dict[str, str]]:
    split_path = split_dir / f"{name}.csv"
    if not split_path.is_file():
        raise TrainingError(f"required {name}.csv split is missing")
    raw = split_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_hash.get("sha256") or len(raw) != expected_hash.get("bytes"):
        raise TrainingError(f"{name}.csv does not match split-manifest.json")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        if reader.fieldnames is None or not FIELDS.issubset(reader.fieldnames):
            raise TrainingError(f"{name}.csv is missing required canonical columns")
        rows = list(reader)
    except UnicodeDecodeError as exc:
        raise TrainingError(f"{name}.csv must be UTF-8") from exc
    if any(row["label"] not in TRAINABLE_LABELS | {"uncertain"} for row in rows):
        raise TrainingError(f"{name}.csv has an unknown label")
    return rows


def _usable(rows: list[dict[str, str]], language: str) -> list[dict[str, str]]:
    return [row for row in rows if row["language"] == language and row["label"] in TRAINABLE_LABELS]


def _class_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(row["label"] for row in rows).items()))


def _make_pipeline(config: dict, c_value: float) -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word",
            ngram_range=tuple(config["wordNgramRange"]),
            sublinear_tf=config["sublinearTf"],
            min_df=config["minimumDocumentFrequency"],
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=tuple(config["charNgramRange"]),
            sublinear_tf=config["sublinearTf"],
            min_df=config["minimumDocumentFrequency"],
        )),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(
            class_weight=config["classWeight"],
            solver=config["solver"],
            max_iter=config["maxIterations"],
            random_state=config["randomSeed"],
            C=c_value,
        )),
    ])


def _dev_f1(model: Pipeline, rows: list[dict[str, str]]) -> float:
    texts = [row["normalized_text"] for row in rows]
    truth = [row["label"] for row in rows]
    classes = list(model.named_steps["clf"].classes_)
    organic_index = classes.index("organic")
    raw_p_organic = model.predict_proba(texts)[:, organic_index]
    predicted = ["organic" if probability >= 0.5 else "manipulated" for probability in raw_p_organic]
    return float(f1_score(truth, predicted, pos_label="manipulated", zero_division=0))


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not-installed"


def _runtime_lock() -> tuple[dict[str, str], str]:
    packages = ("scikit-learn", "joblib", "numpy", "scipy", "threadpoolctl")
    versions = {package: _package_version(package) for package in packages}
    lines = [f"{package}=={package_version}" for package, package_version in versions.items()]
    lines.insert(0, f"# Python {platform.python_version()}")
    return versions, "\n".join(lines) + "\n"


def train_candidates(split_dir: Path, output_dir: Path, config_path: Path = TRAINING_CONFIG) -> dict:
    config = _load_json(config_path)
    split_manifest = _load_json(split_dir / "split-manifest.json")
    split_hashes = split_manifest.get("splitHashes", {})
    # Only train and dev bytes are opened. Calibration and test remain untouched.
    train_rows = _read_split(split_dir, "train", split_hashes.get("train", {}))
    dev_rows = _read_split(split_dir, "dev", split_hashes.get("dev", {}))
    languages = config.get("languages", [])
    if not languages:
        raise TrainingError("training config has no languages")

    language_results = {}
    for language in languages:
        train = _usable(train_rows, language)
        dev = _usable(dev_rows, language)
        if {row["label"] for row in train} != TRAINABLE_LABELS:
            language_results[language] = {
                "trainingDecision": "NOT_TRAINED",
                "reason": "train split does not contain both organic and manipulated labels",
                "productionDecision": "UNKNOWN",
            }
            continue
        if {row["label"] for row in dev} != TRAINABLE_LABELS:
            language_results[language] = {
                "trainingDecision": "NOT_TRAINED",
                "reason": "dev split does not contain both organic and manipulated labels",
                "productionDecision": "UNKNOWN",
            }
            continue

        train_text = [row["normalized_text"] for row in train]
        train_labels = [row["label"] for row in train]
        tuning = []
        for c_value in config["regularizationCGrid"]:
            model = _make_pipeline(config, float(c_value))
            model.fit(train_text, train_labels)
            tuning.append({"C": float(c_value), "devF1ManipulatedAtRawOrganicProbability050": _dev_f1(model, dev)})
        chosen = min(
            tuning,
            key=lambda item: (-item["devF1ManipulatedAtRawOrganicProbability050"], item["C"]),
        )

        final_rows = train + dev
        final_model = _make_pipeline(config, chosen["C"])
        final_model.fit(
            [row["normalized_text"] for row in final_rows],
            [row["label"] for row in final_rows],
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{language}.joblib"
        dump(final_model, model_path)
        model_bytes = model_path.read_bytes()
        language_results[language] = {
            "trainingDecision": "CANDIDATE_TRAINED",
            "selectedC": chosen["C"],
            "tuningSplit": "dev",
            "selectionMetric": config["selectionMetric"],
            "devScores": tuning,
            "trainCounts": _class_counts(train),
            "devCounts": _class_counts(dev),
            "finalFitRows": len(final_rows),
            "finalFitSplits": ["train", "dev"],
            "candidateFile": model_path.name,
            "candidateSha256": hashlib.sha256(model_bytes).hexdigest(),
            "productionDecision": "UNKNOWN pending frozen held-out manual in-domain gate evaluation",
        }

    if not any(item.get("trainingDecision") == "CANDIDATE_TRAINED" for item in language_results.values()):
        raise TrainingError("no language has sufficient labeled train and dev rows to fit a candidate")

    split_manifest_bytes = (split_dir / "split-manifest.json").read_bytes()
    package_versions, requirements_lock = _runtime_lock()
    report = {
        "status": "EXPERIMENTAL_CANDIDATE_NOT_FOR_SERVING",
        "trainingVersion": config["trainingVersion"],
        "splitManifestFile": "data/processed/splits/split-manifest.json",
        "datasetManifest": split_manifest.get("datasetManifest", "docs/dataset/dataset-manifest.json"),
        "splitManifestSha256": hashlib.sha256(split_manifest_bytes).hexdigest(),
        "splitHashes": {name: split_hashes[name] for name in ("train", "dev")},
        "configuration": config,
        "libraries": {
            **package_versions,
            "python": platform.python_version(),
        },
        "calibrationSplitLoaded": False,
        "testSplitLoaded": False,
        "languages": language_results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "training-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "requirements.lock").write_text(requirements_lock, encoding="utf-8")
    (output_dir / "model-decision.md").write_text(
        "# Per-language model decision\n\n" + "\n".join(
            f"- **{language.upper()}:** `UNKNOWN` until a candidate is evaluated on the frozen manual in-domain gate; "
            f"current training state: {result['trainingDecision']}."
            for language, result in language_results.items()
        ) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", type=Path, default=REPO_ROOT / "data/processed/splits")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "scoring-service/artifacts/candidates/baseline-v1")
    parser.add_argument("--config", type=Path, default=TRAINING_CONFIG)
    args = parser.parse_args(argv)
    try:
        report = train_candidates(args.splits, args.output, args.config)
    except (TrainingError, PipelineError) as exc:
        print(f"baseline training error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": str(args.output), "status": report["status"], "languages": report["languages"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
