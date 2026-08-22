"""Contracts for the PR-G Final Supervisor and its market-context channel.

Nothing here predicts anything.  The Final Supervisor is a pure composition
layer: it merges signals that other components already produced, preserves
their conflicts, and states plainly which channels were unavailable and which
gate is blocking them.  It never invents a risk, never cites evidence that was
not supplied, and never presents an uncalibrated score as a probability.

PR-G is NOT STARTED.  These types are preparation only and are not wired into
any workflow, ``Settings`` field or config.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.schemas import CompositeFinding, PredictionResult, SupervisionResult


class SupervisionChannel(StrEnum):
    """The four signal channels the final report has to reconcile."""

    DOCUMENT = "document"
    MARKET = "market"
    MODEL = "model"
    RULE = "rule"


class ChannelStatus(StrEnum):
    AVAILABLE = "available"
    PENDING_GATE = "pending_gate"
    UNAVAILABLE_ERROR = "unavailable_error"
    DISABLED = "disabled"


class ChannelState(BaseModel):
    """Why a channel did or did not contribute, and what is blocking it."""

    model_config = ConfigDict(frozen=True)

    channel: SupervisionChannel
    status: ChannelStatus
    reason: str = Field(min_length=1)
    blocking_gate: str | None = None


CalibrationStatus = Literal["uncalibrated", "calibrated"]


class MarketContextView(BaseModel):
    """Read-only pre-listing market context handed to the Final Supervisor."""

    model_config = ConfigDict(frozen=True)

    status: ChannelStatus
    reason: str = Field(min_length=1)
    blocking_gate: str | None = None
    observations: tuple[str, ...] = ()
    feature_manifest_hash: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class ModelPredictionView(BaseModel):
    """A frozen model's output, deliberately without a ``probability`` field.

    A calibrated probability is a PR-F deliverable.  Until calibration exists and
    is provenance-tracked, the value is a ``score`` with explicit semantics, so no
    downstream renderer can accidentally read it as a likelihood.
    """

    model_config = ConfigDict(frozen=True)

    status: ChannelStatus
    reason: str = Field(min_length=1)
    blocking_gate: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    score: float | None = None
    score_semantics: str = "ordinal model score; not a calibrated probability"
    calibration_status: CalibrationStatus = "uncalibrated"
    calibration_provenance_id: str | None = None
    drivers: tuple[str, ...] = ()


class FinalSupervisionInput(BaseModel):
    """Everything the Final Supervisor is allowed to reason over."""

    model_config = ConfigDict(frozen=True)

    document_supervision: SupervisionResult | None = None
    market_context: MarketContextView | None = None
    model_prediction: ModelPredictionView | None = None
    rule_prediction: PredictionResult | None = None


class FinalSupervisionResult(BaseModel):
    """A composed report; it adds no new risk, evidence or prediction."""

    model_config = ConfigDict(frozen=True)

    summary: str
    channel_states: tuple[ChannelState, ...]
    referenced_risk_ids: tuple[str, ...] = ()
    referenced_evidence_ids: tuple[str, ...] = ()
    composite_findings: tuple[CompositeFinding, ...] = ()
    uncertainty_statement: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
