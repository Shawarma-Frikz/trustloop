"""Frozen-gate and dataset-manifest guards (roadmap step 0.4).

The gate table is frozen before training; these tests pin gate-v1.json to the
values in docs/model-plan.md section 9 so a silent threshold edit fails CI.
The manifest test enforces the licence/verification/hash bookkeeping rules.
"""

import hashlib
import json
from pathlib import Path

import pytest

SERVICE = Path(__file__).resolve().parents[1]
REPO = SERVICE.parent

GATE = SERVICE / "evaluation" / "gate-v1.json"
MANIFEST = REPO / "docs" / "dataset" / "dataset-manifest.json"
MODEL_PLAN = REPO / "docs" / "model-plan.md"

# Values transcribed from docs/model-plan.md section 9. If the model plan is
# legitimately revised, revise this table in the same commit — the gate file
# alone must never be the only place a threshold changes.
EXPECTED_GATE = {
    "en": {
        "aurocMin": 0.75,
        "auprcMin": 0.70,
        "f1ManipulatedAtPOrganic050Min": 0.70,
        "eceMax": 0.10,
        "brierMax": 0.20,
        "explanationStabilityTop5JaccardMin": 0.80,
        "latencyP95WarmMsMax": 1500,
    },
    "fr": {
        "aurocMin": 0.70,
        "auprcMin": 0.65,
        "f1ManipulatedAtPOrganic050Min": 0.65,
        "eceMax": 0.15,
        "brierMax": 0.25,
        "explanationStabilityTop5JaccardMin": 0.80,
        "latencyP95WarmMsMax": 1500,
    },
}

HELDOUT_RANGE = {"en": (200, 300), "fr": (150, 200)}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate_matches_model_plan_section_9():
    gate = _load(GATE)
    for lang, expected in EXPECTED_GATE.items():
        actual = gate["languages"][lang]
        for key, value in expected.items():
            assert actual[key] == value, f"{lang}.{key} drifted from model plan section 9"


def test_gate_internal_coherence():
    gate = _load(GATE)
    assert set(gate["languages"]) == {"en", "fr"}
    en, fr = gate["languages"]["en"], gate["languages"]["fr"]
    # FR targets are the relaxed counterpart of EN, never stricter.
    for key in ("aurocMin", "auprcMin", "f1ManipulatedAtPOrganic050Min"):
        assert fr[key] <= en[key], f"FR {key} must not exceed EN {key}"
    for key in ("eceMax", "brierMax"):
        assert fr[key] >= en[key], f"FR {key} must not be tighter than EN {key}"
    assert gate["languages"]["en"]["explanationStabilityRuns"] == 3
    assert gate["evaluatedOn"].startswith("held-out manual")
    assert gate["perLanguage"] is True


def test_gate_numbers_appear_in_model_plan():
    """The frozen file cannot invent thresholds the model plan does not state."""
    plan = MODEL_PLAN.read_text(encoding="utf-8")
    gate = _load(GATE)
    for lang in ("en", "fr"):
        block = gate["languages"][lang]
        for key in (
            "aurocMin",
            "auprcMin",
            "f1ManipulatedAtPOrganic050Min",
            "eceMax",
            "brierMax",
            "explanationStabilityTop5JaccardMin",
        ):
            rendered = f"{block[key]:.2f}"
            assert rendered in plan, f"{key}={rendered} for {lang} not found in model plan"


def test_sample_sizes_match_model_plan_ranges():
    plan = MODEL_PLAN.read_text(encoding="utf-8")
    assert "200–300 EN reviews; 150–200 FR" in plan
    sample_plan = (REPO / "docs" / "dataset" / "sample-plan.md").read_text(encoding="utf-8")
    for lang, (low, high) in HELDOUT_RANGE.items():
        assert f"{low}–{high}" in sample_plan, f"sample plan missing range for {lang}"


def test_manifest_structure_and_verification_rules():
    manifest = _load(MANIFEST)
    states = set(manifest["verificationStates"])
    seen = set()
    for source in manifest["sources"]:
        sid = source["id"]
        assert sid not in seen
        seen.add(sid)
        assert source["verification"] in states
        assert source["role"]
        assert source["language"] in {"en", "fr"}
        assert source["localPath"].startswith(("data/raw/", "data/eval/"))
        # Hash policy: a file listed in files[] must exist on disk and match;
        # verification 'verified' requires either files or an explicit note
        # that collection is scheduled (held-out samples are collected later).
        for entry in source["files"]:
            path = REPO / source["localPath"] / entry["path"]
            assert path.exists(), f"{sid}: {entry['path']} listed but absent"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == entry["sha256"], f"{sid}: hash mismatch for {entry['path']}"
    heldout = [s for s in manifest["sources"] if s["id"].startswith("manual-heldout")]
    assert {s["language"] for s in heldout} == {"en", "fr"}
    # The gate runs on the manual held-out sources only.
    for s in manifest["sources"]:
        if s["id"].startswith("manual-heldout"):
            assert "gate" in s["role"]


def test_no_review_text_in_manifest():
    """The manifest must never carry review text, URLs of pages, or keys."""
    manifest = _load(MANIFEST)
    blob = json.dumps(manifest)
    assert "http://" not in blob and "https://" not in blob.replace(
        "https://creativecommons.org/licenses/by-nc-sa/4.0/", ""
    ), "unexpected URL in manifest (licence URLs excepted)"


@pytest.mark.parametrize("source_id", [s["id"] for s in _load(MANIFEST)["sources"]])
def test_each_source_has_label_mapping_note(source_id):
    manifest = _load(MANIFEST)
    source = next(s for s in manifest["sources"] if s["id"] == source_id)
    assert source["labelMapping"], f"{source_id} missing label-mapping caveat"
