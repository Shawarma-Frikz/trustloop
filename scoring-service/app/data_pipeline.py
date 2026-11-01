"""Rebuild deterministic, source-aware review splits from hash-pinned CSV inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SPLIT_NAMES = ("train", "dev", "calibration", "test")
OUTPUT_FIELDS = (
    "record_id",
    "text",
    "normalized_text",
    "label",
    "language",
    "source_id",
    "page_id",
    "product_id",
)
LABELS = {"organic", "manipulated", "uncertain"}
WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


class PipelineError(ValueError):
    """Raised when source data cannot be safely split."""


class LeakageError(PipelineError):
    """Raised when near-duplicate text crosses split boundaries."""


@dataclass(frozen=True)
class BuildResult:
    output_dir: Path
    counts: dict[str, dict[str, int]]
    dropped_duplicates: int
    source_hashes: dict[str, dict[str, str | int]]


def normalize_text(text: str) -> str:
    """Apply NFKC and whitespace collapse without stemming or case-folding."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _char_ngrams(text: str) -> Counter[str]:
    normalized = normalize_text(text).casefold()
    features: Counter[str] = Counter()
    for token in WORD_RE.findall(normalized):
        padded = f"^{token}$"
        for size in (3, 4, 5):
            features.update(padded[i : i + size] for i in range(max(0, len(padded) - size + 1)))
    return features


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(feature, 0) for feature, count in left.items())
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return dot / (left_norm * right_norm)


def _find_duplicate_components(rows: list[dict[str, str]], threshold: float) -> list[list[int]]:
    """Return connected near-duplicate components using sparse cosine candidates."""
    vectors = [_char_ngrams(row["normalized_text"]) for row in rows]
    feature_rows: dict[str, list[int]] = defaultdict(list)
    for index, vector in enumerate(vectors):
        for feature in vector:
            feature_rows[feature].append(index)

    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    candidate_pairs: set[tuple[int, int]] = set()
    for indices in feature_rows.values():
        for offset, left in enumerate(indices):
            for right in indices[offset + 1 :]:
                candidate_pairs.add((left, right))
    for left, right in sorted(candidate_pairs):
        if _cosine(vectors[left], vectors[right]) >= threshold:
            union(left, right)

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(rows)):
        components[find(index)].append(index)
    return [component for component in components.values() if len(component) > 1]


def assert_no_duplicate_leakage(rows: list[dict[str, str]], threshold: float) -> None:
    """Fail if a cosine-near-duplicate component occurs in multiple splits."""
    for component in _find_duplicate_components(rows, threshold):
        splits = {rows[index]["split"] for index in component}
        if len(splits) > 1:
            ids = sorted(rows[index]["record_id"] for index in component)
            raise LeakageError(f"near-duplicate records cross splits {sorted(splits)}: {ids}")


def _read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"cannot read dataset manifest: {exc}") from exc


def _resolve_input(raw_root: Path, relative_path: str) -> Path:
    candidate = (raw_root / relative_path).resolve()
    root = raw_root.resolve()
    if candidate != root and root not in candidate.parents:
        raise PipelineError(f"input path escapes the raw-data directory: {relative_path}")
    return candidate


def _load_rows(manifest: dict, manifest_path: Path) -> tuple[list[dict[str, str]], dict]:
    repo_root = manifest_path.resolve().parents[2]
    schema = manifest.get("pipeline", {}).get("inputColumns", {})
    required = {"recordId", "text", "label", "pageId", "language"}
    if not required.issubset(schema):
        raise PipelineError(f"pipeline.inputColumns must define {sorted(required)}")

    raw_root = repo_root / "data" / "raw"
    rows: list[dict[str, str]] = []
    hashes: dict[str, dict[str, str | int]] = {}
    seen_ids: set[str] = set()
    loaded_sources = 0

    for source in manifest.get("sources", []):
        listed_files = source.get("files", [])
        if not listed_files:
            continue
        if source.get("verification") != "verified":
            raise PipelineError(f"source {source['id']} has files but is not verified")
        loaded_sources += 1
        label_mapping = source.get("labelMapping")
        if not isinstance(label_mapping, dict):
            raise PipelineError(f"source {source['id']} needs a machine-readable labelMapping")
        local_path = Path(source.get("localPath", ""))
        if local_path.is_absolute() or ".." in local_path.parts or local_path.parts[:2] != ("data", "raw"):
            raise PipelineError(f"source {source['id']} has an unsafe localPath")
        source_raw_dir = (repo_root / local_path).resolve()
        if raw_root.resolve() not in source_raw_dir.parents:
            raise PipelineError(f"source {source['id']} localPath escapes data/raw")
        for entry in listed_files:
            relative = entry.get("path", "")
            file_path = _resolve_input(source_raw_dir, relative)
            if not file_path.is_file():
                raise PipelineError(f"manifest input is missing: {source['localPath']}{relative}")
            raw_bytes = file_path.read_bytes()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            if digest != entry.get("sha256") or len(raw_bytes) != entry.get("bytes"):
                raise PipelineError(f"hash or byte-count mismatch: {source['id']}/{relative}")
            hashes[f"{source['id']}/{relative}"] = {"sha256": digest, "bytes": len(raw_bytes)}
            try:
                decoded = raw_bytes.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(decoded, newline=""))
                if reader.fieldnames is None:
                    raise PipelineError(f"CSV has no header: {source['id']}/{relative}")
                missing = {schema[key] for key in required} - set(reader.fieldnames)
                if missing:
                    raise PipelineError(f"CSV missing columns {sorted(missing)}: {source['id']}/{relative}")
                for line_number, record in enumerate(reader, start=2):
                    raw_id = (record.get(schema["recordId"]) or "").strip()
                    text = record.get(schema["text"]) or ""
                    raw_label = (record.get(schema["label"]) or "").strip().casefold()
                    label = label_mapping.get(raw_label)
                    language_column = schema.get("language")
                    language = (record.get(language_column) if language_column else source["language"]) or source["language"]
                    page_id = (record.get(schema["pageId"]) or "").strip()
                    product_column = schema.get("productId")
                    product_id = (record.get(product_column) if product_column else "") or ""
                    normalized = normalize_text(text)
                    if not raw_id or not normalized or not page_id:
                        raise PipelineError(f"empty ID, text, or page at {source['id']}/{relative}:{line_number}")
                    if label not in LABELS:
                        raise PipelineError(f"unmapped label {raw_label!r} at {source['id']}/{relative}:{line_number}")
                    if language not in {"en", "fr"}:
                        raise PipelineError(f"unsupported language {language!r} at {source['id']}/{relative}:{line_number}")
                    record_id = f"{source['id']}:{raw_id}"
                    if record_id in seen_ids:
                        raise PipelineError(f"duplicate record ID: {record_id}")
                    seen_ids.add(record_id)
                    rows.append({
                        "record_id": record_id,
                        "text": text,
                        "normalized_text": normalized,
                        "label": label,
                        "language": language,
                        "source_id": source["id"],
                        "page_id": page_id,
                        "product_id": product_id.strip(),
                    })
            except UnicodeDecodeError as exc:
                raise PipelineError(f"input is not UTF-8: {source['id']}/{relative}") from exc

    if not loaded_sources or not rows:
        raise PipelineError("no hash-pinned, verified CSV inputs are listed in dataset-manifest.json")
    return rows, hashes


def _deduplicate(rows: list[dict[str, str]], threshold: float) -> tuple[list[dict[str, str]], int]:
    duplicates = _find_duplicate_components(rows, threshold)
    dropped: set[int] = set()
    for component in duplicates:
        labels = {rows[index]["label"] for index in component}
        if len(labels) > 1:
            ids = sorted(rows[index]["record_id"] for index in component)
            raise PipelineError(f"near-duplicates have conflicting labels; review manually: {ids}")
        keep = min(component, key=lambda index: (rows[index]["source_id"], rows[index]["record_id"]))
        dropped.update(index for index in component if index != keep)
    return [row for index, row in enumerate(rows) if index not in dropped], len(dropped)


def _assign_splits(rows: list[dict[str, str]], seed: int, fractions: dict[str, float]) -> None:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        page_group = row["product_id"] or row["page_id"]
        groups[(row["source_id"], row["language"], page_group)].append(row)

    by_source_language: dict[tuple[str, str], list[tuple[str, list[dict[str, str]]]]] = defaultdict(list)
    for (source_id, language, group_id), group_rows in groups.items():
        by_source_language[(source_id, language)].append((group_id, group_rows))

    for (source_id, language), source_groups in by_source_language.items():
        if len(source_groups) < len(SPLIT_NAMES):
            raise PipelineError(
                f"{source_id}/{language} has {len(source_groups)} independent product/page groups; "
                f"at least {len(SPLIT_NAMES)} are required for the four frozen splits"
            )
        ordered = sorted(
            source_groups,
            key=lambda pair: hashlib.sha256(f"{seed}:{source_id}:{language}:{pair[0]}".encode()).hexdigest(),
        )
        source_row_count = sum(len(group_rows) for _, group_rows in ordered)
        target_rows = {name: source_row_count * fractions[name] for name in SPLIT_NAMES}
        assigned_counts = {name: 0 for name in SPLIT_NAMES}
        for position, (group_id, group_rows) in enumerate(ordered):
            empty = [name for name in SPLIT_NAMES if assigned_counts[name] == 0]
            remaining_groups = len(ordered) - position
            candidates = empty if remaining_groups <= len(empty) else list(SPLIT_NAMES)
            split = min(
                candidates,
                key=lambda name: (
                    assigned_counts[name] / target_rows[name] if target_rows[name] else float("inf"),
                    SPLIT_NAMES.index(name),
                ),
            )
            for row in group_rows:
                row["split"] = split
            assigned_counts[split] += len(group_rows)


def _validate_pipeline_config(config: dict) -> tuple[int, dict[str, float], float]:
    seed = config.get("seed")
    fractions = config.get("splitFractions")
    duplicate = config.get("nearDuplicate", {})
    threshold = duplicate.get("cosineThreshold")
    if not isinstance(seed, int) or not isinstance(fractions, dict) or set(fractions) != set(SPLIT_NAMES):
        raise PipelineError("pipeline must freeze integer seed and train/dev/calibration/test splitFractions")
    if any(not isinstance(value, (int, float)) or value <= 0 for value in fractions.values()):
        raise PipelineError("split fractions must all be positive numbers")
    if not math.isclose(sum(fractions.values()), 1.0, abs_tol=1e-9):
        raise PipelineError("split fractions must sum to 1")
    if not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        raise PipelineError("nearDuplicate.cosineThreshold must be in (0, 1]")
    return seed, fractions, float(threshold)


def build_splits(manifest_path: Path, output_dir: Path) -> BuildResult:
    manifest = _read_manifest(manifest_path)
    config = manifest.get("pipeline", {})
    seed, fractions, threshold = _validate_pipeline_config(config)
    rows, source_hashes = _load_rows(manifest, manifest_path)
    rows, dropped_duplicates = _deduplicate(rows, threshold)
    _assign_splits(rows, seed, fractions)
    assert_no_duplicate_leakage(rows, threshold)

    output_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"total": 0, "en": 0, "fr": 0} for name in SPLIT_NAMES}
    source_counts = {name: {} for name in SPLIT_NAMES}
    for split in SPLIT_NAMES:
        split_rows = sorted(
            (row for row in rows if row["split"] == split),
            key=lambda row: (row["source_id"], row["language"], row["record_id"]),
        )
        with (output_dir / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows({field: row[field] for field in OUTPUT_FIELDS if field != "split"} for row in split_rows)
        counts[split]["total"] = len(split_rows)
        for row in split_rows:
            counts[split][row["language"]] += 1
            source_counts[split].setdefault(row["source_id"], 0)
            source_counts[split][row["source_id"]] += 1

    repo_root = manifest_path.resolve().parents[2]
    try:
        manifest_reference = manifest_path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        manifest_reference = manifest_path.name
    build_manifest = {
        "manifestVersion": "1",
        "datasetManifest": manifest_reference,
        "seed": seed,
        "splitFractions": fractions,
        "normalization": config["normalization"],
        "nearDuplicate": {"method": "cosine-character-3-5-grams", "threshold": threshold},
        "grouping": "source + language + product_id (or page_id when product_id is empty)",
        "sourceHashes": source_hashes,
        "inputRows": sum(counts[name]["total"] for name in SPLIT_NAMES) + dropped_duplicates,
        "deduplicatedRows": sum(counts[name]["total"] for name in SPLIT_NAMES),
        "droppedNearDuplicates": dropped_duplicates,
        "splitCounts": counts,
        "splitCountsBySource": source_counts,
    }
    (output_dir / "split-manifest.json").write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return BuildResult(output_dir, counts, dropped_duplicates, source_hashes)


def _main(argv: Iterable[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=repo_root / "docs/dataset/dataset-manifest.json")
    parser.add_argument("--output", type=Path, default=repo_root / "data/processed/splits")
    args = parser.parse_args(argv)
    try:
        result = build_splits(args.manifest, args.output)
    except PipelineError as exc:
        print(f"data pipeline error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": str(result.output_dir),
        "splitCounts": result.counts,
        "droppedNearDuplicates": result.dropped_duplicates,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
