import json
from pathlib import Path

import numpy as np
import pytest

from app.calibrate_explain import (
    _fit_calibrator,
    _jaccard,
    apply_calibrator,
    calibration_metrics,
    explain_linear,
    trust_score_and_verdict,
)
from app.train_baseline import TRAINING_CONFIG, _make_pipeline


def test_sigmoid_and_isotonic_calibrators_return_bounded_probabilities():
    raw = np.asarray([-2.0, -1.0, -0.25, 0.25, 1.0, 2.0])
    labels = ["manipulated", "manipulated", "manipulated", "organic", "organic", "organic"]

    for method in ("sigmoid", "isotonic"):
        calibrator = _fit_calibrator(method, raw, labels)
        probabilities = apply_calibrator(calibrator, np.asarray([-3.0, 0.0, 3.0]))
        assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))
        assert np.all(np.diff(probabilities) >= 0.0)

    reversed_labels = ["organic", "organic", "organic", "manipulated", "manipulated", "manipulated"]
    bounded_sigmoid = _fit_calibrator("sigmoid", raw, reversed_labels)
    assert bounded_sigmoid["coefficient"] >= 0.0
    assert np.all(np.diff(apply_calibrator(bounded_sigmoid, np.asarray([-1.0, 0.0, 1.0]))) >= 0.0)


def test_calibration_metrics_include_bins_ece_and_brier():
    metrics = calibration_metrics(["organic", "manipulated"], np.asarray([0.9, 0.1]))

    assert metrics["rowCount"] == 2
    assert metrics["ece"] == pytest.approx(0.1)
    assert metrics["brier"] == pytest.approx(0.01)
    assert len(metrics["reliabilityCurve"]) == 10
    assert sum(row["count"] for row in metrics["reliabilityCurve"]) == 2


def test_score_mapping_uses_half_up_rounding_and_frozen_bands():
    bands = [
        {"name": "INCONCLUSIVE", "min": 40, "max": 54},
        {"name": "MIXED_SIGNALS", "min": 55, "max": 69},
        {"name": "LIKELY_ORGANIC", "min": 70, "max": 84},
    ]

    assert trust_score_and_verdict(0.695, bands) == (70, "LIKELY_ORGANIC")


def test_linear_explanation_is_bounded_static_and_keeps_duplicate_qualitative():
    config = json.loads(TRAINING_CONFIG.read_text(encoding="utf-8"))
    model = _make_pipeline(config, 0.1)
    organic = [
        "After two weeks this kettle heats water evenly and the handle stays comfortable",
        "I used the lamp every evening for a month beside my reading chair",
        "The case survived a short fall and still closes without a gap",
    ] * 2
    manipulated = [
        "Perfect amazing product buy now for the best ever experience",
        "Must have item guaranteed flawless and always works perfectly",
        "Great product excellent product very good and highly recommend",
    ] * 2
    model.fit(organic + manipulated, ["organic"] * len(organic) + ["manipulated"] * len(manipulated))
    input_text = "This perfect product is a great product; I used it after two weeks."

    signals = explain_linear(model, input_text, batch_duplicate=True, numeric=True)
    repeated_signals = explain_linear(model, input_text, batch_duplicate=True, numeric=True)
    qualitative_signals = explain_linear(model, input_text, batch_duplicate=True)

    assert len(signals) <= 5
    assert signals == repeated_signals
    assert any(signal["kind"] == "CROSS_REVIEW_DUPLICATE" for signal in signals)
    duplicate = next(signal for signal in signals if signal["kind"] == "CROSS_REVIEW_DUPLICATE")
    assert "contribution" not in duplicate
    assert all(input_text not in signal["summary"] for signal in signals)
    assert all(abs(signal["contribution"]) <= 1 for signal in signals if "contribution" in signal)
    assert sum(abs(signal.get("contribution", 0)) for signal in signals) <= 1.0000001
    assert all("contribution" not in signal for signal in qualitative_signals)


def test_signal_set_jaccard_handles_overlap_and_empty_sets():
    assert _jaccard({"GENERIC_WORDING", "CONCRETE_DETAIL"}, {"GENERIC_WORDING"}) == 0.5
    assert _jaccard(set(), set()) == 1.0
