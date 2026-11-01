import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.data_pipeline import (
    LeakageError,
    PipelineError,
    _assign_splits,
    _find_duplicate_components,
    assert_no_duplicate_leakage,
    build_splits,
    normalize_text,
)


FRACTIONS = {"train": 0.7, "dev": 0.1, "calibration": 0.1, "test": 0.1}
THRESHOLD = 0.92


def _fixture_repo(tmp_path: Path, *, tamper_after_manifest: bool = False) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    manifest_path = repo / "docs" / "dataset" / "dataset-manifest.json"
    raw_dir = repo / "data" / "raw" / "fixture-source"
    raw_dir.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    csv_path = raw_dir / "reviews.csv"
    texts = [
        "Copper lantern glows beside the balcony door while rain taps against the empty flowerpots.",
        "Basketball practice starts before sunrise because the neighborhood court becomes crowded later.",
        "A yellow recipe notebook contains handwritten soup measurements from several winter evenings.",
        "Mountain bicycles need replacement brake pads after dusty trails and steep downhill rides.",
        "The ceramic teapot pours slowly but keeps jasmine leaves warm through afternoon conversations.",
        "A wool scarf feels soft outdoors although its narrow fringe catches on the coat buttons.",
        "Portable speakers connect easily in the kitchen and remain audible beside the running faucet.",
        "Garden gloves protect both palms when pruning thorny roses near the wooden fence.",
    ]
    records = []
    for index in range(8):
        records.append({
            "record_id": f"r{index}",
            "text": texts[index],
            "label": "truthful" if index % 2 == 0 else "deceptive",
            "language": "en",
            "page_id": f"hotel-{index}",
            "product_id": "",
        })
    # Exact copy on a different page: it must be removed before any split is assigned.
    records.append({**records[0], "record_id": "duplicate-r0", "page_id": "hotel-copy"})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    raw_bytes = csv_path.read_bytes()

    manifest = {
        "manifestVersion": "test",
        "pipeline": {
            "seed": 17,
            "splitFractions": FRACTIONS,
            "normalization": "Unicode NFKC and whitespace collapse",
            "nearDuplicate": {"cosineThreshold": THRESHOLD},
            "inputColumns": {
                "recordId": "record_id",
                "text": "text",
                "label": "label",
                "language": "language",
                "pageId": "page_id",
                "productId": "product_id",
                "sourceGroup": None,
            },
        },
        "sources": [{
            "id": "fixture-source",
            "verification": "verified",
            "language": "en",
            "localPath": "data/raw/fixture-source/",
            "labelMapping": {"truthful": "organic", "deceptive": "manipulated"},
            "files": [{
                "path": "reviews.csv",
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "bytes": len(raw_bytes),
            }],
        }],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    if tamper_after_manifest:
        csv_path.write_text(csv_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return manifest_path, repo


def _read_split_rows(output_dir: Path) -> list[dict[str, str]]:
    rows = []
    for split in ("train", "dev", "calibration", "test"):
        with (output_dir / f"{split}.csv").open(encoding="utf-8", newline="") as handle:
            rows.extend({**row, "split": split} for row in csv.DictReader(handle))
    return rows


def test_normalization_is_nfkc_and_collapses_whitespace_without_stemming():
    assert normalize_text("  Ｈello\tworld\nwalking!  ") == "Hello world walking!"


def test_build_is_deterministic_hash_checked_and_reports_counts(tmp_path):
    manifest, repo = _fixture_repo(tmp_path)
    first = build_splits(manifest, repo / "data" / "processed" / "first")
    second = build_splits(manifest, repo / "data" / "processed" / "second")

    assert first.counts == second.counts
    assert first.dropped_duplicates == 1
    assert sum(split["total"] for split in first.counts.values()) == 8
    assert all(first.counts[name]["total"] > 0 for name in ("train", "dev", "calibration", "test"))
    first_rows = _read_split_rows(first.output_dir)
    second_rows = _read_split_rows(second.output_dir)
    assert [(r["record_id"], r["split"]) for r in first_rows] == [
        (r["record_id"], r["split"]) for r in second_rows
    ]
    assert "fixture-source/reviews.csv" in first.source_hashes
    assert_no_duplicate_leakage(first_rows, THRESHOLD)
    output_manifest = json.loads((first.output_dir / "split-manifest.json").read_text(encoding="utf-8"))
    assert output_manifest["seed"] == 17
    assert output_manifest["splitCounts"] == first.counts
    assert output_manifest["splitCountsBySource"]["train"]["fixture-source"] == first.counts["train"]["total"]
    assert not Path(output_manifest["datasetManifest"]).is_absolute()


def test_hash_mismatch_fails_closed(tmp_path):
    manifest, repo = _fixture_repo(tmp_path, tamper_after_manifest=True)
    with pytest.raises(PipelineError, match="hash or byte-count mismatch"):
        build_splits(manifest, repo / "data" / "processed" / "splits")


def test_near_duplicate_injected_across_train_and_test_fails_leakage_check():
    rows = [
        {"record_id": "train-copy", "normalized_text": "A comfortable hotel room with helpful staff and a quiet corner.", "split": "train"},
        {"record_id": "test-copy", "normalized_text": "A comfortable hotel room with helpful staff, in a quiet corner.", "split": "test"},
    ]
    assert _find_duplicate_components(rows, THRESHOLD)
    with pytest.raises(LeakageError, match="cross splits"):
        assert_no_duplicate_leakage(rows, THRESHOLD)


def test_rows_from_same_product_page_are_assigned_to_one_split():
    rows = [
        {"record_id": "p1-a", "source_id": "s", "source_group": "origin-a", "language": "en", "product_id": "p1", "page_id": "a"},
        {"record_id": "p1-b", "source_id": "s", "source_group": "origin-a", "language": "en", "product_id": "p1", "page_id": "b"},
        {"record_id": "p2", "source_id": "s", "source_group": "origin-a", "language": "en", "product_id": "p2", "page_id": "c"},
        {"record_id": "p3", "source_id": "s", "source_group": "origin-a", "language": "en", "product_id": "p3", "page_id": "d"},
        {"record_id": "p4", "source_id": "s", "source_group": "origin-a", "language": "en", "product_id": "p5", "page_id": "e"},
    ]

    _assign_splits(rows, 17, FRACTIONS)
    assert rows[0]["split"] == rows[1]["split"]


def test_conflicting_labels_in_near_duplicates_require_manual_resolution(tmp_path):
    manifest, repo = _fixture_repo(tmp_path)
    csv_path = repo / "data" / "raw" / "fixture-source" / "reviews.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    records[-1]["label"] = "deceptive"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    raw_bytes = csv_path.read_bytes()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["sources"][0]["files"][0]["sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    data["sources"][0]["files"][0]["bytes"] = len(raw_bytes)
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(PipelineError, match="conflicting labels"):
        build_splits(manifest, repo / "data" / "processed" / "splits")


def test_missing_acquired_files_do_not_create_fake_split_counts(tmp_path):
    manifest, repo = _fixture_repo(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["sources"][0]["files"] = []
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PipelineError, match="no hash-pinned"):
        build_splits(manifest, repo / "data" / "processed" / "splits")


def test_zip_source_filter_maps_only_approved_positive_polarity(tmp_path):
    manifest_path, repo = _fixture_repo(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = data["sources"][0]
    source["inputColumns"] = {
        "recordId": None,
        "text": "text",
        "label": "deceptive",
        "language": None,
        "pageId": "hotel",
        "productId": "hotel",
        "sourceGroup": "source",
    }
    source["rowIdFields"] = ["hotel", "source", "deceptive"]
    source["rowFilter"] = {"field": "polarity", "equals": "positive"}
    rows = []
    positive_texts = [
        "Copper lantern glows beside the balcony door while rain taps against empty flowerpots.",
        "Basketball practice starts before sunrise because the neighborhood court becomes crowded later.",
        "A yellow recipe notebook contains handwritten soup measurements from several winter evenings.",
        "Mountain bicycles need replacement brake pads after dusty trails and steep downhill rides.",
        "The ceramic teapot pours slowly but keeps jasmine leaves warm through afternoon conversations.",
        "A wool scarf feels soft outdoors although its narrow fringe catches on coat buttons.",
        "Portable speakers connect easily in the kitchen and remain audible beside the running faucet.",
        "Garden gloves protect both palms when pruning thorny roses near the wooden fence.",
    ]
    for index, hotel in enumerate([f"hotel-{n}" for n in range(8)]):
        rows.append({
            "deceptive": "truthful" if index % 2 == 0 else "deceptive",
            "hotel": hotel,
            "polarity": "positive",
            "source": "TripAdvisor",
            "text": positive_texts[index],
        })
    # The negative-polarity partition is present in the Kaggle archive but is not
    # part of the verified Ott 2011 positive-only source in the manifest.
    rows.append({
        "deceptive": "not-a-approved-label",
        "hotel": "hotel-negative",
        "polarity": "negative",
        "source": "TripAdvisor",
        "text": "This row must be filtered before labels are mapped.",
    })
    csv_stream = io.StringIO(newline="")
    writer = csv.DictWriter(csv_stream, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    archive_path = repo / "data" / "raw" / "fixture-source" / "fixture.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("deceptive-opinion.csv", csv_stream.getvalue().encode("utf-8"))
    archive_bytes = archive_path.read_bytes()
    source["files"] = [{
        "path": "fixture.zip",
        "format": "zip-member-csv",
        "member": "deceptive-opinion.csv",
        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "bytes": len(archive_bytes),
    }]
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    result = build_splits(manifest_path, repo / "data" / "processed" / "splits")

    assert sum(split["total"] for split in result.counts.values()) == 8
    assert "fixture-source/fixture.zip" in result.source_hashes
    build_manifest = json.loads((result.output_dir / "split-manifest.json").read_text(encoding="utf-8"))
    assert build_manifest["sourceRowCounts"]["fixture-source/fixture.zip"] == {
        "read": 9,
        "selected": 8,
        "filtered": 1,
    }
