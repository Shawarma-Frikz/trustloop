import csv
import hashlib
import json
from pathlib import Path

from app.train_baseline import train_candidates


def _write_split(path: Path, records: list[dict[str, str]]) -> dict[str, str | int]:
    fields = [
        "record_id", "text", "normalized_text", "label", "language",
        "source_id", "source_group", "page_id", "product_id",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _records(split: str, count_per_label: int) -> list[dict[str, str]]:
    rows = []
    for label, template in (
        ("organic", "I used this lamp for several evenings, and the switch feels stiff beside my desk"),
        ("manipulated", "This perfect amazing lamp is the ultimate must have, buy now for the best experience"),
    ):
        for index in range(count_per_label):
            text = f"{template} during {split} example number {index}."
            rows.append({
                "record_id": f"{split}-{label}-{index}",
                "text": text,
                "normalized_text": text,
                "label": label,
                "language": "en",
                "source_id": "synthetic-test-only",
                "source_group": "synthetic-origin",
                "page_id": f"page-{split}-{label}-{index}",
                "product_id": "",
            })
    return rows


def test_baseline_tunes_on_dev_and_does_not_open_calibration_or_test(tmp_path):
    split_dir = tmp_path / "splits"
    split_dir.mkdir()
    hashes = {
        "train": _write_split(split_dir / "train.csv", _records("train", 8)),
        "dev": _write_split(split_dir / "dev.csv", _records("dev", 4)),
    }
    # Calibration and test files are intentionally absent. This command must not load them.
    (split_dir / "split-manifest.json").write_text(json.dumps({
        "datasetManifest": "docs/dataset/dataset-manifest.json",
        "splitHashes": hashes,
    }), encoding="utf-8")
    config_path = Path(__file__).resolve().parents[1] / "evaluation" / "training-v1.json"
    output_dir = tmp_path / "candidate"

    report = train_candidates(split_dir, output_dir, config_path)

    en = report["languages"]["en"]
    assert report["status"] == "EXPERIMENTAL_CANDIDATE_NOT_FOR_SERVING"
    assert report["calibrationSplitLoaded"] is False
    assert report["testSplitLoaded"] is False
    assert en["trainingDecision"] == "CANDIDATE_TRAINED"
    assert en["tuningSplit"] == "dev"
    assert en["selectedC"] in {0.01, 0.1, 1.0, 10.0}
    assert len(en["devScores"]) == 4
    assert en["productionDecision"].startswith("UNKNOWN")
    assert (output_dir / "en.joblib").is_file()
    assert (output_dir / "training-report.json").is_file()
    assert (output_dir / "requirements.lock").is_file()
    decisions = (output_dir / "model-decision.md").read_text(encoding="utf-8")
    assert "**EN:** `UNKNOWN`" in decisions
    assert "**FR:** `UNKNOWN`" in decisions
