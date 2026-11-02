"""Load runtime limits from the frozen shared contract constants."""

import json
from pathlib import Path


_PATH = Path(__file__).resolve().parents[2] / "contracts" / "v1" / "constants.json"
_DOCUMENT = json.loads(_PATH.read_text(encoding="utf-8"))
CONSTANTS = _DOCUMENT["constants"]

MAX_REVIEW_CHARS = int(CONSTANTS["MAX_REVIEW_CHARS"])
MAX_REVIEWS_PER_REQUEST = int(CONSTANTS["MAX_REVIEWS_PER_REQUEST"])
MAX_REQUEST_BYTES = int(CONSTANTS["MAX_REQUEST_BYTES"])
MIN_REVIEW_WORDS = int(CONSTANTS["MIN_REVIEW_WORDS"])
ADEQUATE_REVIEW_WORDS = int(CONSTANTS["ADEQUATE_REVIEW_WORDS"])
MAX_SIGNALS = int(CONSTANTS["MAX_SIGNALS"])
