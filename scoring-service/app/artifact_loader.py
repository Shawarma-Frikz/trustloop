"""Verify and load a versioned TrustLoop model artifact bundle."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

from joblib import load
from sklearn.pipeline import Pipeline


REQUIRED_FILES = {
    "model.joblib",
    "calibration.json",
    "metrics.json",
    "model-card.md",
    "dataset-manifest.json",
    "requirements.lock",
}


class ArtifactError(RuntimeError):
    """Raised when an artifact bundle is incomplete, corrupt, or mismatched."""


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot read artifact metadata {path.name}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"artifact metadata {path.name} must be a JSON object")
    return value


def _verify_runtime_lock(path: Path) -> None:
    expected_python = None
    packages = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# Python "):
            expected_python = line.removeprefix("# Python ").strip()
            continue
        if line.startswith("#") or "==" not in line:
            raise ArtifactError("runtime lock contains an invalid line")
        name, package_version = line.split("==", 1)
        packages[name.strip()] = package_version.strip()
    if expected_python and platform.python_version() != expected_python:
        raise ArtifactError("running Python version does not match the artifact runtime lock")
    for name, expected in packages.items():
        try:
            installed = version(name)
        except PackageNotFoundError as exc:
            raise ArtifactError(f"runtime dependency is missing: {name}") from exc
        if installed != expected:
            raise ArtifactError(f"runtime dependency version mismatch: {name}")


def verify_artifact_bundle(bundle_dir: Path, expected_model_version: str) -> dict:
    bundle_dir = Path(bundle_dir)
    if not bundle_dir.is_dir():
        raise ArtifactError("model artifact directory is missing")
    root = bundle_dir.resolve()
    manifest_path = root / "artifact-manifest.json"
    checksum_path = root / "artifact.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise ArtifactError("artifact manifest or artifact.sha256 is missing")

    manifest_bytes = manifest_path.read_bytes()
    checksum_fields = checksum_path.read_text(encoding="ascii").strip().split()
    if not checksum_fields:
        raise ArtifactError("artifact checksum file is empty")
    expected_digest = checksum_fields[0].lower()
    actual_digest = hashlib.sha256(manifest_bytes).hexdigest()
    if actual_digest != expected_digest:
        raise ArtifactError("artifact manifest checksum mismatch")
    manifest = _read_json(manifest_path)
    if manifest.get("modelVersion") != expected_model_version:
        raise ArtifactError("artifact model version does not match the configured expected version")
    if manifest.get("artifactStatus") != "EXPERIMENTAL_NOT_FOR_SERVING":
        raise ArtifactError("artifact is missing its experimental-only status")
    if manifest.get("productionDecision") != "UNKNOWN":
        raise ArtifactError("artifact production decision must remain UNKNOWN until its gate passes")

    files = manifest.get("files")
    if not isinstance(files, dict) or not REQUIRED_FILES.issubset(files):
        raise ArtifactError("artifact manifest does not list every required bundle file")
    if "artifact-manifest.json" in files or "artifact.sha256" in files:
        raise ArtifactError("artifact manifest cannot recursively hash its own checksum files")

    for name, metadata in files.items():
        if not isinstance(name, str) or Path(name).name != name or name in {".", ".."}:
            raise ArtifactError("artifact manifest contains an unsafe file path")
        file_path = root / name
        if file_path.is_symlink() or not file_path.is_file() or file_path.resolve().parent != root:
            raise ArtifactError(f"artifact file is missing or unsafe: {name}")
        raw = file_path.read_bytes()
        if not isinstance(metadata, dict):
            raise ArtifactError(f"artifact file metadata is invalid: {name}")
        if len(raw) != metadata.get("bytes") or hashlib.sha256(raw).hexdigest() != metadata.get("sha256"):
            raise ArtifactError(f"artifact file checksum mismatch: {name}")

    return manifest


def load_artifact_bundle(bundle_dir: Path, expected_model_version: str) -> dict:
    manifest = verify_artifact_bundle(bundle_dir, expected_model_version)
    root = Path(bundle_dir).resolve()
    calibration = _read_json(root / "calibration.json")
    metrics = _read_json(root / "metrics.json")
    dataset_manifest = _read_json(root / "dataset-manifest.json")
    _verify_runtime_lock(root / "requirements.lock")
    if calibration.get("modelVersionCandidate") != expected_model_version:
        raise ArtifactError("calibration model version does not match the artifact")
    if metrics.get("modelVersion") != expected_model_version:
        raise ArtifactError("metrics model version does not match the artifact")
    if dataset_manifest.get("manifestVersion") is None:
        raise ArtifactError("artifact dataset manifest is invalid")

    # joblib can execute code while deserializing. Only load after every hash
    # has been checked and only from a locally built bundle.
    model = load(root / "model.joblib")
    if not isinstance(model, Pipeline) or not {"features", "clf"}.issubset(model.named_steps):
        raise ArtifactError("artifact model is not the expected TF-IDF/logistic pipeline")
    classes = set(model.named_steps["clf"].classes_)
    if classes != {"organic", "manipulated"}:
        raise ArtifactError("artifact model has an unexpected class set")
    return {
        "manifest": manifest,
        "model": model,
        "calibration": calibration,
        "metrics": metrics,
        "datasetManifest": dataset_manifest,
    }
