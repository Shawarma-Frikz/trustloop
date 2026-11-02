"""Strict internal scoring request and response models for contract v1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from app.contract_constants import MAX_REVIEW_CHARS, MAX_REVIEWS_PER_REQUEST, MAX_SIGNALS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReviewInput(StrictModel):
    reviewKey: StrictStr = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    text: StrictStr = Field(min_length=1, max_length=MAX_REVIEW_CHARS)
    batchDuplicate: StrictBool


class ScoreRequest(StrictModel):
    reviews: list[ReviewInput] = Field(min_length=1, max_length=MAX_REVIEWS_PER_REQUEST)


SignalKind = Literal[
    "REPEATED_PHRASING",
    "CROSS_REVIEW_DUPLICATE",
    "GENERIC_WORDING",
    "PROMOTIONAL_TONE",
    "EXTREME_CLAIMS",
    "CONCRETE_DETAIL",
    "LEXICAL_VARIETY",
]
Verdict = Literal[
    "STRONG_MANIPULATION_SIGNALS",
    "LIKELY_MANIPULATED",
    "INCONCLUSIVE",
    "MIXED_SIGNALS",
    "LIKELY_ORGANIC",
    "STRONG_ORGANIC_SIGNALS",
]
ReasonCode = Literal[
    "INSUFFICIENT_TEXT",
    "UNSUPPORTED_LANGUAGE",
    "SCORING_TIMEOUT",
    "SCORING_UNAVAILABLE",
]


class Signal(StrictModel):
    kind: SignalKind
    summary: StrictStr = Field(min_length=1, max_length=200)
    contribution: float | None = Field(default=None, ge=-1, le=1)


class ScoreResult(StrictModel):
    reviewKey: StrictStr = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    status: Literal["SCORED", "SIGNALS_ONLY", "UNKNOWN"]
    trustScore: int | None = Field(default=None, ge=0, le=100)
    pOrganic: float | None = Field(default=None, ge=0, le=1)
    verdict: Verdict | None = None
    evidenceQuality: Literal["LOW", "ADEQUATE"] | None = None
    reasonCode: ReasonCode | None = None
    signals: list[Signal] = Field(max_length=MAX_SIGNALS)
    modelVersion: StrictStr | None = Field(default=None, pattern=r"^tl-text-\d+\.\d+\.\d+$")
    engine: Literal["MODEL", "SIGNALS_ONLY"]


class ScoreResponse(StrictModel):
    results: list[ScoreResult] = Field(min_length=1)


class HealthResponse(StrictModel):
    status: Literal["ready", "not_ready"]


class VersionResponse(StrictModel):
    service: Literal["trustloop-api"]
    version: StrictStr = Field(min_length=1)
    contractVersion: Literal["v1"]
    expectedModelVersion: StrictStr = Field(pattern=r"^tl-text-\d+\.\d+\.\d+$")
    engine: Literal["MODEL", "SIGNALS_ONLY"]


class ErrorDetail(StrictModel):
    code: Literal["INVALID_REQUEST", "PAYLOAD_TOO_LARGE", "RATE_LIMITED", "INTERNAL_ERROR"]
    message: StrictStr = Field(min_length=1, max_length=200)


class ErrorResponse(StrictModel):
    requestId: StrictStr = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")
    error: ErrorDetail
