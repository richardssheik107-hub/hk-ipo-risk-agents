"""Contracts for the PR-G Final Supervisor and its market-context channel.

Nothing here predicts anything.  The Final Supervisor is a pure composition
layer: it merges signals that other components already produced, preserves
their conflicts, and states plainly which channels were unavailable and which
gate is blocking them.  It never invents a risk, never cites evidence that was
not supplied, and never presents an uncalibrated score as a probability.

PR-G is COMPLETE / FROZEN and these types are its stable composition contract.
PR-H consumes that contract through governed Market-X and frozen model-runtime
projections without changing the public schema.

``score_semantics`` defaults to ``uncalibrated_model_score``, the term the frozen
PR-F output already uses (``lightgbm_modeling.py``), so the Final Supervisor
consumes the frozen score under the vocabulary that produced it.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas import CompositeFinding, PredictionResult, RiskConflict, SupervisionResult


class SupervisionChannel(StrEnum):
    """The four signal channels the final report has to reconcile."""

    DOCUMENT = "document"
    MARKET = "market"
    MODEL = "model"
    RULE = "rule"


class ChannelStatus(StrEnum):
    AVAILABLE = "available"
    # The channel is configured and the request is valid, but the governed
    # runtime has no supported data path for this case.  This is distinct from
    # both a disabled channel and a validation/IO failure.
    UNAVAILABLE = "unavailable"
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
ObservationAvailability = Literal["available", "unavailable"]

# Stable metric metadata is part of the observation contract, not a market
# value.  Keeping it available even when the value is PIT-blocked lets the UI,
# trace and strict-contract audit explain what the missing observation means
# without filling the missing fact with zero or a proxy.
_MARKET_OBSERVATION_SPECS: dict[str, tuple[str, str]] = {
    "hsi_return_5d": ("ratio", "HSI close(t)/close(t-5) - 1 over observed sessions"),
    "hsi_return_20d": ("ratio", "HSI close(t)/close(t-20) - 1 over observed sessions"),
    "industry_return_5d": ("ratio", "industry benchmark close(t)/close(t-5) - 1 over observed sessions"),
    "industry_return_20d": ("ratio", "industry benchmark close(t)/close(t-20) - 1 over observed sessions"),
    "recent_ipo_break_rate": ("ratio", "share of recent prior IPOs closing below offer on day one"),
    "recent_ipo_return_5d": ("ratio", "mean 5-session return of recent prior IPOs"),
    "recent_ipo_1d_sample_count": ("count", "count of governed recent IPO day-one observations"),
    "recent_ipo_5d_sample_count": ("count", "count of governed recent IPO five-session observations"),
    "market_turnover": ("currency", "aggregate market turnover at the observation date"),
    "market_turnover_20d_mean": ("currency", "mean aggregate market turnover over the prior 20 observed sessions"),
    "market_volatility": ("ratio", "realised volatility of the benchmark over the observation window"),
    "market_volatility_20d": ("ratio", "realised volatility of the benchmark over the prior 20 observed sessions"),
    "sentiment_score": ("index", "composite pre-listing sentiment index"),
    "ipo_count_30d": ("count", "count of governed prior IPOs in the 30-day pre-listing window"),
    "ipo_count_60d": ("count", "count of governed prior IPOs in the 60-day pre-listing window"),
    "log_prior_ipo_funds_raised_30d": ("log_currency", "log transformed governed prior-IPO funds raised in the 30-day window"),
    "log_prior_ipo_funds_raised_60d": ("log_currency", "log transformed governed prior-IPO funds raised in the 60-day window"),
    "prior_ipo_funds_raised_30d_sample_count": ("count", "count of governed prior IPO fund-raising observations in the 30-day window"),
    "prior_ipo_funds_raised_60d_sample_count": ("count", "count of governed prior IPO fund-raising observations in the 60-day window"),
    "same_industry_ipo_count_180d": ("count", "count of governed same-industry prior IPOs in the 180-day window"),
    "same_industry_recent_break_rate": ("ratio", "share of governed recent same-industry IPOs closing below offer on day one"),
    "same_industry_recent_return_5d": ("ratio", "mean five-session return of governed recent same-industry IPOs"),
    "same_industry_recent_1d_sample_count": ("count", "count of governed recent same-industry day-one observations"),
    "same_industry_recent_5d_sample_count": ("count", "count of governed recent same-industry five-session observations"),
}


class MarketObservation(BaseModel):
    """One market fact, carrying its own derivation and its own absence reason.

    ``value`` and ``missing_reason`` are mutually exclusive by validator: a stated
    number must say how it was derived, and an absent one must say why.  Stable
    unit/derivation metadata for known metrics is retained even when the value is
    unavailable; this describes the intended governed fact and never imputes it.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    value: float | None = None
    unit: str = ""
    availability: ObservationAvailability
    missing_reason: str | None = None
    derivation: str = ""
    source: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def populate_known_metric_metadata(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        name = str(value.get("name") or "")
        spec = _MARKET_OBSERVATION_SPECS.get(name)
        if spec is None:
            return value
        normalized = dict(value)
        unit, derivation = spec
        if not normalized.get("unit"):
            normalized["unit"] = unit
        if not normalized.get("derivation"):
            normalized["derivation"] = derivation
        return normalized

    @model_validator(mode="after")
    def validate_availability(self) -> "MarketObservation":
        if self.availability == "available":
            if self.value is None:
                raise ValueError("an available observation must carry a value")
            if not self.derivation:
                raise ValueError("an available observation must state its derivation")
        elif self.value is not None:
            raise ValueError("an unavailable observation cannot carry a value")
        elif not self.missing_reason:
            raise ValueError("an unavailable observation must state a missing reason")
        return self


class ModelDriver(BaseModel):
    """One SHAP contribution behind a frozen model score."""

    model_config = ConfigDict(frozen=True)

    feature: str = Field(min_length=1)
    component: str = Field(min_length=1)
    feature_value: float | None = None
    shap_value: float
    direction: Literal["increases", "decreases"]

    @model_validator(mode="after")
    def validate_direction(self) -> "ModelDriver":
        expected = "increases" if self.shap_value >= 0 else "decreases"
        if self.direction != expected:
            raise ValueError("driver direction must agree with the sign of its SHAP value")
        return self


class MarketContextView(BaseModel):
    """Read-only pre-listing market context handed to the Final Supervisor."""

    model_config = ConfigDict(frozen=True)

    status: ChannelStatus
    reason: str = Field(min_length=1)
    blocking_gate: str | None = None
    observations: tuple[MarketObservation, ...] = ()
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
    score_semantics: str = "uncalibrated_model_score"
    calibration_status: CalibrationStatus = "uncalibrated"
    calibration_provenance_id: str | None = None
    alert: bool | None = None
    alert_policy: str | None = None
    drivers: tuple[ModelDriver, ...] = ()


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
    # Conflicts are preserved, never resolved.  Arbitration is CH-4, after PR-H.
    conflicts: tuple[RiskConflict, ...] = ()
    market_context: MarketContextView | None = None
    model_prediction: ModelPredictionView | None = None
    uncertainty_statement: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
