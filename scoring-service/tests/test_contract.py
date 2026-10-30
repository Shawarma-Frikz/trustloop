import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "v1"
FIXTURES = CONTRACTS / "fixtures"


def load(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "fixture",
    sorted(FIXTURES.glob("*.json")),
    ids=lambda path: path.name,
)
def test_fixture_validates_as_its_name_promises(fixture: Path) -> None:
    name = fixture.name
    segments = name.split(".")
    message = segments[0]
    schema = load(f"{message}.schema.json")
    instance = json.loads(fixture.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(instance))

    if segments[1].startswith("valid"):
        assert errors == [], f"{name} must be valid, got {errors}"
    else:
        assert errors, f"{name} must be invalid but validated cleanly"


def test_schemas_match_constants() -> None:
    constants = load("constants.json")
    values = constants["constants"]

    request = load("analyze-request.schema.json")
    assert request["properties"]["reviews"]["maxItems"] == values["MAX_REVIEWS_PER_REQUEST"]
    assert (
        request["properties"]["reviews"]["items"]["properties"]["text"]["maxLength"]
        == values["MAX_REVIEW_CHARS"]
    )

    response = load("analyze-response.schema.json")
    result_props = response["$defs"]["result"]["properties"]
    assert result_props["status"]["enum"] == constants["statuses"]
    assert result_props["engine"]["enum"] == constants["engines"]
    assert result_props["evidenceQuality"]["enum"] == constants["evidenceQualityLevels"]
    assert result_props["verdict"]["enum"] == [b["name"] for b in constants["bands"]]
    assert result_props["signals"]["maxItems"] == values["MAX_SIGNALS"]

    result_codes = [r["code"] for r in constants["reasonCodes"] if r["scope"] == "result"]
    assert result_props["reasonCode"]["enum"] == result_codes

    signal_kinds = [s["kind"] for s in constants["signals"]]
    assert response["$defs"]["signal"]["properties"]["kind"]["enum"] == signal_kinds

    version = load("version-response.schema.json")
    assert (
        version["properties"]["expectedModelVersion"]["pattern"]
        == values["MODEL_VERSION_FORMAT"]
    )

    error = load("error-response.schema.json")
    error_codes = [r["code"] for r in constants["reasonCodes"] if r["scope"] == "request_error"]
    assert error["properties"]["error"]["properties"]["code"]["enum"] == error_codes


def test_constants_are_complete_and_coherent() -> None:
    constants = load("constants.json")

    assert len(constants["constants"]) == 17
    assert len(constants["reasonCodes"]) == 10
    assert len(constants["signals"]) == 7
    assert len(constants["bands"]) == 6
    assert constants["constants"]["REQUEST_ID_HEADER"] == "X-Request-Id"

    bands = constants["bands"]
    assert bands[0]["min"] == 0
    assert bands[-1]["max"] == 100
    for previous, current in zip(bands, bands[1:]):
        assert current["min"] == previous["max"] + 1, "bands must cover 0-100 without gaps"


def test_internal_result_shape_is_public_shape_plus_p_organic() -> None:
    public = set(load("analyze-response.schema.json")["$defs"]["result"]["properties"])
    internal = set(load("score-response.schema.json")["$defs"]["result"]["properties"])

    assert internal - {"pOrganic"} == public
