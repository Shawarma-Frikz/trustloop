import json
from pathlib import Path

from jsonschema import Draft202012Validator


CONTRACTS = Path(__file__).resolve().parents[1] / "v1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixtures_validate_as_their_names_promise():
    for fixture_path in sorted((CONTRACTS / "fixtures").glob("*.json")):
        message, expectation, _ = fixture_path.name.split(".")
        schema = read_json(CONTRACTS / f"{message}.schema.json")
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(read_json(fixture_path)))

        if expectation.startswith("valid-") or expectation == "valid":
            assert not errors, f"{fixture_path.name} should be valid: {errors}"
        else:
            assert errors, f"{fixture_path.name} should be invalid"
