"""Calibrate and explain the experimental linear baseline on frozen splits.

The held-out test split is opened only by this evaluation step. Its results are
public-corpus transfer evidence, never the in-domain production gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from joblib import load
from sklearn.isotonic import IsotonicRegression
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score

from app.data_pipeline import PipelineError
from app.train_baseline import (
    REPO_ROOT,
    TRAINING_CONFIG,
    TrainingError,
    _load_json,
    _make_pipeline,
    _read_split,
)


SPLIT_DIR = REPO_ROOT / "data/processed/splits"
TRAINING_OUTPUT = REPO_ROOT / "scoring-service/artifacts/candidates/baseline-v1"
OUTPUT_DIR = REPO_ROOT / "scoring-service/artifacts/candidates/calibration-v1"
CONSTANTS_PATH = REPO_ROOT / "contracts/v1/constants.json"
BIN_COUNT = 10
CALIBRATION_CONFIG = Path(__file__).resolve().parents[1] / "evaluation" / "calibration-explanation-v1.json"

SIGNAL_SUMMARIES = {
    "REPEATED_PHRASING": "Repeats the same phrasing",
    "CROSS_REVIEW_DUPLICATE": "Shares wording with other visible reviews",
    "GENERIC_WORDING": "Uses generic wording with few concrete details",
    "PROMOTIONAL_TONE": "Reads like promotional copy",
    "EXTREME_CLAIMS": "Makes extreme or unverifiable claims",
    "CONCRETE_DETAIL": "Includes a concrete usage detail",
    "LEXICAL_VARIETY": "Shows varied, natural wording",
}

# These small, explicit English lexicons identify observable feature families;
# they do not label intent and are not a standalone score.
SIGNAL_LEXICONS = {
    "PROMOTIONAL_TONE": (
        "buy now", "order now", "must have", "must-have", "limited time",
        "highly recommend", "best seller", "get yours", "do not miss",
        "don't miss", "perfect gift",
    ),
    "EXTREME_CLAIMS": (
        "best ever", "the best", "never fails", "always works", "guaranteed",
        "unbeatable", "perfect", "flawless", "life changing", "life-changing",
        "100 percent", "number one", "#1",
    ),
    "GENERIC_WORDING": (
        "great product", "good product", "nice product", "very good",
        "works great", "really good", "excellent product", "high quality",
        "easy to use", "love this product", "great quality",
    ),
    "CONCRETE_DETAIL": (
        "after", "before", "week", "weeks", "month", "months", "day", "days",
        "hour", "hours", "minute", "minutes", "mile", "miles", "kilometer",
        "kilometers", "km", "inch", "inches", "cm", "while using", "compared with",
        "compared to",
    ),
}

WORD_RE = re.compile(r"[\w]+(?:['’][\w]+)?", re.UNICODE)


class CalibrationExplanationError(ValueError):
    """Raised for incomplete or inconsistent calibration inputs."""


def _organic_scores(model, texts: list[str]) -> np.ndarray:
    classes = list(model.named_steps["clf"].classes_)
    if "organic" not in classes or "manipulated" not in classes:
        raise CalibrationExplanationError("candidate must contain both expected labels")
    scores = np.asarray(model.decision_function(texts), dtype=float)
    if classes.index("organic") == 0:
        scores = -scores
    return scores


def _fit_calibrator(method: str, raw_scores: np.ndarray, labels: list[str]) -> dict:
    targets = np.asarray([label == "organic" for label in labels], dtype=int)
    if len(np.unique(targets)) != 2:
        raise CalibrationExplanationError("calibration fit requires both labels")
    if method == "sigmoid":
        estimator = LogisticRegression(C=1_000_000, solver="lbfgs", max_iter=2000)
        estimator.fit(np.asarray(raw_scores).reshape(-1, 1), targets)
        positive_index = list(estimator.classes_).index(1)
        coefficient_row = 0 if estimator.coef_.shape[0] == 1 else positive_index
        coefficient = float(estimator.coef_[coefficient_row, 0])
        intercept = float(estimator.intercept_[coefficient_row])
        if coefficient < 0:
            prior = float(np.mean(targets))
            coefficient = 0.0
            intercept = math.log(prior / (1.0 - prior))
        return {
            "method": "sigmoid",
            "coefficient": coefficient,
            "intercept": intercept,
        }
    if method == "isotonic":
        estimator = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
        estimator.fit(raw_scores, targets)
        return {
            "method": "isotonic",
            "xThresholds": [float(value) for value in estimator.X_thresholds_],
            "yThresholds": [float(value) for value in estimator.y_thresholds_],
        }
    raise CalibrationExplanationError(f"unsupported calibration method: {method}")


def apply_calibrator(calibrator: dict, raw_scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(raw_scores, dtype=float)
    if calibrator["method"] == "sigmoid":
        logits = np.clip(
            float(calibrator["coefficient"]) * scores + float(calibrator["intercept"]),
            -709,
            709,
        )
        return 1.0 / (1.0 + np.exp(-logits))
    if calibrator["method"] == "isotonic":
        return np.interp(
            scores,
            np.asarray(calibrator["xThresholds"], dtype=float),
            np.asarray(calibrator["yThresholds"], dtype=float),
            left=float(calibrator["yThresholds"][0]),
            right=float(calibrator["yThresholds"][-1]),
        )
    raise CalibrationExplanationError("unknown calibration method in saved parameters")


def calibration_metrics(labels: list[str], probabilities: np.ndarray, bin_count: int = BIN_COUNT) -> dict:
    targets = np.asarray([label == "organic" for label in labels], dtype=float)
    probs = np.clip(np.asarray(probabilities, dtype=float), 0.0, 1.0)
    if len(targets) == 0 or len(targets) != len(probs):
        raise CalibrationExplanationError("metrics need equally sized non-empty labels and probabilities")
    bins = []
    ece = 0.0
    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        mask = (probs >= lower) & ((probs <= upper) if index == bin_count - 1 else (probs < upper))
        count = int(mask.sum())
        mean_probability = float(probs[mask].mean()) if count else None
        organic_fraction = float(targets[mask].mean()) if count else None
        if count:
            ece += (count / len(targets)) * abs(mean_probability - organic_fraction)
        bins.append({
            "lowerBound": lower,
            "upperBound": upper,
            "count": count,
            "meanPredictedPOrganic": mean_probability,
            "observedOrganicFraction": organic_fraction,
        })
    manipulated_truth = 1 - targets.astype(int)
    manipulated_prediction = (probs < 0.5).astype(int)
    return {
        "rowCount": len(targets),
        "classCounts": {
            "organic": int(targets.sum()),
            "manipulated": int(len(targets) - targets.sum()),
        },
        "aurocManipulated": float(roc_auc_score(manipulated_truth, 1 - probs)) if len(np.unique(manipulated_truth)) == 2 else None,
        "auprcManipulated": float(average_precision_score(manipulated_truth, 1 - probs)) if len(np.unique(manipulated_truth)) == 2 else None,
        "f1ManipulatedAtPOrganic050": float(f1_score(manipulated_truth, manipulated_prediction, zero_division=0)),
        "ece": float(ece),
        "brier": float(np.mean((probs - targets) ** 2)),
        "reliabilityCurve": bins,
    }


def trust_score_and_verdict(p_organic: float, bands: list[dict]) -> tuple[int, str]:
    score = min(100, max(0, int(math.floor(100 * min(1.0, max(0.0, p_organic)) + 0.5))))
    for band in bands:
        if int(band["min"]) <= score <= int(band["max"]):
            return score, str(band["name"])
    raise CalibrationExplanationError(f"no contract verdict band for score {score}")


def _repeated_bigrams(text: str) -> set[str]:
    words = [word.lower() for word in WORD_RE.findall(text)]
    bigrams = [" ".join(words[index:index + 2]) for index in range(max(0, len(words) - 1))]
    return {phrase for phrase, count in Counter(bigrams).items() if count > 1}


def _group_for_feature(feature: str, text: str, repeated: set[str], unigram_counts: Counter) -> str | None:
    prefix, _, raw_feature = feature.partition("__")
    feature_text = raw_feature.lower().replace("’", "'").strip()
    normalized_text = text.lower().replace("’", "'")
    if prefix == "word" and feature_text in repeated:
        return "REPEATED_PHRASING"
    # Specific observed phrases activate a family. Character fragments are only
    # assigned when they overlap a matching lexicon phrase of at least four chars.
    for kind in ("EXTREME_CLAIMS", "PROMOTIONAL_TONE", "GENERIC_WORDING", "CONCRETE_DETAIL"):
        for phrase in SIGNAL_LEXICONS[kind]:
            phrase_norm = phrase.lower().replace("’", "'")
            if phrase_norm not in normalized_text:
                continue
            if prefix == "word":
                feature_tokens = set(WORD_RE.findall(feature_text))
                phrase_tokens = set(WORD_RE.findall(phrase_norm))
                if feature_text == phrase_norm or (feature_tokens and feature_tokens.issubset(phrase_tokens)):
                    return kind
            elif prefix == "char" and len(feature_text) >= 4 and feature_text in phrase_norm:
                return kind
    if prefix == "word" and " " not in feature_text and unigram_counts[feature_text] == 1 and len(feature_text) > 2:
        return "LEXICAL_VARIETY"
    return None


def explain_linear(model, text: str, batch_duplicate: bool = False, numeric: bool = False) -> list[dict]:
    feature_union = model.named_steps["features"]
    classifier = model.named_steps["clf"]
    classes = list(classifier.classes_)
    organic_index = classes.index("organic")
    feature_names = feature_union.get_feature_names_out()
    vector = feature_union.transform([text]).tocsr()
    coefficients = classifier.coef_[0]
    if organic_index == 0:
        coefficients = -coefficients
    all_signed = vector.data * coefficients[vector.indices]
    denominator = float(np.abs(all_signed).sum())
    grouped: dict[str, float] = Counter()
    repeated = _repeated_bigrams(text)
    unigram_counts = Counter(
        word.lower() for word in WORD_RE.findall(text)
        if len(word) > 2 and word.lower() not in ENGLISH_STOP_WORDS
    )
    for feature_index, contribution in zip(vector.indices, all_signed):
        group = _group_for_feature(str(feature_names[feature_index]), text, repeated, unigram_counts)
        if group:
            grouped[group] += float(contribution)

    candidates = []
    for kind, contribution in grouped.items():
        normalized = float(contribution / denominator) if denominator else 0.0
        if abs(normalized) > 1e-12:
            candidates.append((abs(normalized), kind, normalized))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    signals = []
    for _, kind, contribution in candidates[:5]:
        signal = {"kind": kind, "summary": SIGNAL_SUMMARIES[kind]}
        if numeric:
            signal["contribution"] = round(contribution, 8)
        signals.append(signal)

    # Duplicate status is observable batch context but was not part of the
    # fitted text-only classifier, so it deliberately carries no attribution.
    if batch_duplicate:
        signals.append({"kind": "CROSS_REVIEW_DUPLICATE", "summary": SIGNAL_SUMMARIES["CROSS_REVIEW_DUPLICATE"]})
    return signals[:5]


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _canonical_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _bootstrap_rows(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["source_id"], row["source_group"], row["page_id"] or row["product_id"])
        groups.setdefault(key, []).append(row)
    keys = sorted(groups)
    if len(keys) < 2:
        raise CalibrationExplanationError("explanation stability needs at least two training groups")
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(keys), size=len(keys), replace=True)
    sample = [row for index in selected for row in groups[keys[int(index)]]]
    if {row["label"] for row in sample} != {"organic", "manipulated"}:
        raise CalibrationExplanationError("bootstrap sample did not include both labels")
    return sample


def _verify_inputs(split_dir: Path, training_dir: Path, language: str) -> tuple[dict, dict, dict, dict, dict, dict]:
    split_manifest_path = split_dir / "split-manifest.json"
    split_manifest_bytes = split_manifest_path.read_bytes()
    split_manifest = _load_json(split_manifest_path)
    training_report = _load_json(training_dir / "training-report.json")
    if training_report.get("status") != "EXPERIMENTAL_CANDIDATE_NOT_FOR_SERVING":
        raise CalibrationExplanationError("baseline report is not an experimental candidate")
    if training_report.get("splitManifestSha256") != hashlib.sha256(split_manifest_bytes).hexdigest():
        raise CalibrationExplanationError("baseline was trained against a different split manifest; retrain first")
    hashes = split_manifest.get("splitHashes", {})
    if training_report.get("splitHashes", {}) != {name: hashes.get(name) for name in ("train", "dev")}:
        raise CalibrationExplanationError("training report train/dev hashes do not match current splits")
    if not all(name in hashes for name in ("train", "dev", "calibration", "test")):
        raise CalibrationExplanationError("split manifest is missing a required split hash")
    rows = {
        name: _read_split(split_dir, name, hashes[name])
        for name in ("train", "dev", "calibration", "test")
    }
    config = training_report["configuration"]
    chosen = training_report.get("languages", {}).get(language, {})
    if chosen.get("trainingDecision") != "CANDIDATE_TRAINED":
        raise CalibrationExplanationError("English baseline candidate is not trained")
    candidate_path = training_dir / chosen["candidateFile"]
    candidate_bytes = candidate_path.read_bytes()
    if hashlib.sha256(candidate_bytes).hexdigest() != chosen.get("candidateSha256"):
        raise CalibrationExplanationError("English candidate hash does not match training report")
    candidate = load(candidate_path)
    return split_manifest, training_report, rows, config, chosen, candidate


def calibrate_and_evaluate(
    split_dir: Path = SPLIT_DIR,
    training_dir: Path = TRAINING_OUTPUT,
    output_dir: Path = OUTPUT_DIR,
    calibration_config_path: Path = CALIBRATION_CONFIG,
) -> dict:
    calibration_config = _load_json(calibration_config_path)
    language = calibration_config["language"]
    split_manifest, training_report, rows, config, chosen, final_model = _verify_inputs(split_dir, training_dir, language)
    train = [row for row in rows["train"] if row["language"] == language and row["label"] in {"organic", "manipulated"}]
    dev = [row for row in rows["dev"] if row["language"] == language and row["label"] in {"organic", "manipulated"}]
    calibration = [row for row in rows["calibration"] if row["language"] == language and row["label"] in {"organic", "manipulated"}]
    test = [row for row in rows["test"] if row["language"] == language and row["label"] in {"organic", "manipulated"}]
    for name, split_rows in (("train", train), ("dev", dev), ("calibration", calibration), ("test", test)):
        if not split_rows or {row["label"] for row in split_rows} != {"organic", "manipulated"}:
            raise CalibrationExplanationError(f"English {name} split is empty or missing a class")

    selected_c = float(chosen["selectedC"])
    selection_model = _make_pipeline(config, selected_c)
    selection_model.fit([row["normalized_text"] for row in train], [row["label"] for row in train])
    calibration_for_selection = _organic_scores(selection_model, [row["normalized_text"] for row in calibration])
    dev_scores = _organic_scores(selection_model, [row["normalized_text"] for row in dev])
    selection_labels = [row["label"] for row in calibration]
    dev_labels = [row["label"] for row in dev]

    selection_results = {}
    for method in calibration_config["methods"]:
        calibrator = _fit_calibrator(method, calibration_for_selection, selection_labels)
        probabilities = apply_calibrator(calibrator, dev_scores)
        metrics = calibration_metrics(dev_labels, probabilities, calibration_config["reliabilityBins"])
        selection_results[method] = {
            "devECE": metrics["ece"],
            "devBrier": metrics["brier"],
        }
    selected_method = min(calibration_config["methods"], key=lambda method: (
        selection_results[method]["devECE"], selection_results[method]["devBrier"], method
    ))

    calibration_scores = _organic_scores(final_model, [row["normalized_text"] for row in calibration])
    final_calibrator = _fit_calibrator(selected_method, calibration_scores, [row["label"] for row in calibration])
    test_texts = [row["normalized_text"] for row in test]
    test_labels = [row["label"] for row in test]
    test_raw_scores = _organic_scores(final_model, test_texts)
    calibrated_test = apply_calibrator(final_calibrator, test_raw_scores)
    raw_test_probabilities = 1.0 / (1.0 + np.exp(-np.clip(test_raw_scores, -709, 709)))
    test_metrics = {
        "raw": calibration_metrics(test_labels, raw_test_probabilities, calibration_config["reliabilityBins"]),
        "calibrated": calibration_metrics(test_labels, calibrated_test, calibration_config["reliabilityBins"]),
    }

    contract_constants = _load_json(CONSTANTS_PATH)
    model_version = "tl-text-1.1.0"
    def make_scoring_result(index: int, text: str, probability: float, include_numeric: bool) -> dict:
        review_key = f"calib-test-{index:03d}"
        word_count = len(text.split())
        if word_count < 20:
            return {
                "reviewKey": review_key,
                "status": "UNKNOWN",
                "signals": [],
                "engine": "MODEL",
                "reasonCode": "INSUFFICIENT_TEXT",
            }
        score, verdict = trust_score_and_verdict(probability, contract_constants["bands"])
        signals = explain_linear(final_model, text, numeric=include_numeric)
        return {
            "reviewKey": review_key,
            "status": "SCORED",
            "engine": "MODEL",
            "evidenceQuality": "LOW" if word_count < 50 else "ADEQUATE",
            "trustScore": score,
            "pOrganic": float(probability),
            "verdict": verdict,
            "signals": signals,
            "modelVersion": model_version,
        }

    train_dev = train + dev
    stability_models = []
    bootstrap_seeds = calibration_config["explanation"]["bootstrapSeeds"]
    bootstrap_runs = int(calibration_config["explanation"]["bootstrapRuns"])
    stability_threshold = float(calibration_config["explanation"]["minimumMeanPairwiseTop5JaccardForNumericContributions"])
    stability_seeds = [int(seed) for seed in bootstrap_seeds]
    if len(stability_seeds) != bootstrap_runs:
        raise CalibrationExplanationError("bootstrap seed count must match configured run count")
    for seed in stability_seeds:
        bootstrap = _bootstrap_rows(train_dev, seed)
        model = _make_pipeline(config, selected_c)
        model.fit([row["normalized_text"] for row in bootstrap], [row["label"] for row in bootstrap])
        stability_models.append(model)

    per_input_scores = []
    eligible_inputs = 0
    for text in test_texts:
        signal_sets = []
        for model in stability_models:
            explanations = explain_linear(model, text, numeric=False)
            signal_sets.append({signal["kind"] for signal in explanations if signal["kind"] not in {"CROSS_REVIEW_DUPLICATE", "LEXICAL_VARIETY"}})
        if any(signal_sets):
            eligible_inputs += 1
            pairs = [_jaccard(signal_sets[i], signal_sets[j]) for i in range(bootstrap_runs) for j in range(i + 1, bootstrap_runs)]
            per_input_scores.append(float(np.mean(pairs)))
    stability = float(np.mean(per_input_scores)) if per_input_scores else None
    stable_enough = bool(stability is not None and stability >= stability_threshold)
    result_once = [make_scoring_result(index, text, float(probability), stable_enough) for index, (text, probability) in enumerate(zip(test_texts, calibrated_test))]
    result_twice = [make_scoring_result(index, text, float(probability), stable_enough) for index, (text, probability) in enumerate(zip(test_texts, calibrated_test))]
    digest_once = _canonical_hash(result_once)
    digest_twice = _canonical_hash(result_twice)
    deterministic = digest_once == digest_twice
    if not deterministic:
        raise CalibrationExplanationError("identical input/model version produced different full results")
    numeric_enabled = bool(stable_enough and deterministic)
    explanation_samples = [explain_linear(final_model, text, numeric=numeric_enabled) for text in test_texts]
    signal_counts = Counter(signal["kind"] for signals in explanation_samples for signal in signals)

    report = {
        "status": "TRANSFER_EVALUATION_ONLY_NOT_FOR_SERVING",
        "modelVersionCandidate": model_version,
        "language": language,
        "productionDecision": "UNKNOWN pending frozen manual in-domain gate evaluation",
        "sourceDomain": "Ott 2011 positive-polarity hotel reviews; public-corpus transfer evidence only",
        "candidateSha256": chosen["candidateSha256"],
        "splitManifestSha256": hashlib.sha256((split_dir / "split-manifest.json").read_bytes()).hexdigest(),
        "splitHashes": {name: split_manifest["splitHashes"][name] for name in ("calibration", "test")},
        "selection": {
            "selectedC": selected_c,
            "calibratorFitSplit": "calibration",
            "calibratorSelectionSplit": "dev",
            "selectionRule": "lowest dev ECE; tie-break by dev Brier then method name",
            "candidateResults": selection_results,
            "selectedMethod": selected_method,
            "finalCalibratorRefitOn": "calibration predictions from the train+dev candidate",
        },
        "configuration": calibration_config,
        "metrics": {
            "evaluationSplit": "test",
            "testOpenedOnceForTransferEvaluation": True,
            "raw": test_metrics["raw"],
            "calibrated": test_metrics["calibrated"],
        },
        "explanation": {
            "method": "linear word/character coefficient times normalized TF-IDF value; aggregate mapped feature contributions; normalize by total absolute contribution across the complete active feature set",
            "returnedMaximum": int(contract_constants["constants"]["MAX_SIGNALS"]),
            "topFiveSubsetRenormalized": False,
            "bootstrapRuns": bootstrap_runs,
            "bootstrapSeeds": stability_seeds,
            "bootstrapUnit": "source-group and page clusters sampled with replacement from train+dev",
            "fixedInputTestRows": len(test_texts),
            "inputsWithAtLeastOneMappedSignal": eligible_inputs,
            "meanPairwiseTop5Jaccard": stability,
            "minimumForNumericContributions": stability_threshold,
            "deterministicFullResultHash": digest_once,
            "determinismPassed": deterministic,
            "numericContributionsEnabledForCandidate": numeric_enabled,
            "qualitativeOnlyKinds": ["CROSS_REVIEW_DUPLICATE"],
            "signalOccurrenceCountsOnTest": dict(sorted(signal_counts.items())),
        },
        "languages": {
            "en": "TRANSFER_EVALUATION_ONLY_NOT_FOR_SERVING",
            "fr": "NOT_EVALUATED_NO_FRENCH_DATA",
        },
        "caveat": "Public hotel-review metrics do not evaluate or satisfy the manual Amazon acceptance gate; no live scores may be claimed from this report.",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    calibration_parameters = {
        **final_calibrator,
        "calibrationVersion": "v1",
        "modelVersionCandidate": model_version,
        "language": language,
        "targetClass": "organic",
        "fitSplit": "calibration",
        "selectionSplit": "dev",
        "selectedBy": report["selection"]["selectionRule"],
        "trainingCandidateSha256": chosen["candidateSha256"],
        "productionDecision": report["productionDecision"],
    }
    (output_dir / "calibration.json").write_text(json.dumps(calibration_parameters, indent=2) + "\n", encoding="utf-8")
    (output_dir / "calibration-explanation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--splits", type=Path, default=SPLIT_DIR)
    parser.add_argument("--training-output", type=Path, default=TRAINING_OUTPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--config", type=Path, default=CALIBRATION_CONFIG)
    args = parser.parse_args(argv)
    try:
        report = calibrate_and_evaluate(args.splits, args.training_output, args.output, args.config)
    except (CalibrationExplanationError, TrainingError, PipelineError, OSError, KeyError, ValueError) as exc:
        print(f"calibration/explanation error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": str(args.output),
        "status": report["status"],
        "method": report["selection"]["selectedMethod"],
        "metrics": report["metrics"]["calibrated"],
        "explanation": report["explanation"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
