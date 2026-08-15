"""Versioned point-in-time contracts for V04 pre-listing market features."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import (
    MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketSecurityEligibility,
    MarketSecurityEligibilityDecision,
    MarketSecurityEligibilityReason,
    MarketSecurityType,
    expected_market_split,
)


MARKET_FEATURE_POLICY_VERSION = "v04_prelisting_market_features_v1"
MARKET_FEATURE_SCHEMA_VERSION = "v04_market_features_v1"

MARKET_RAW_FEATURE_ORDER = (
    "hsi_return_5d",
    "hsi_return_20d",
    "industry_return_5d",
    "industry_return_20d",
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "recent_ipo_1d_sample_count",
    "recent_ipo_5d_sample_count",
    "market_turnover_20d_mean",
    "market_volatility_20d",
)


class MarketFeatureAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MarketFeatureMissingReason(StrEnum):
    INSUFFICIENT_HISTORY = "insufficient_history"
    MISSING_BENCHMARK = "missing_benchmark"
    MISSING_INDUSTRY_MAPPING = "missing_industry_mapping"
    MISSING_INDUSTRY_SERIES = "missing_industry_series"
    NO_RECENT_IPO_SAMPLE = "no_recent_ipo_sample"
    MISSING_TURNOVER_SOURCE = "missing_turnover_source"
    SOURCE_UNAVAILABLE = "source_unavailable"


class MarketFeatureDType(StrEnum):
    INT8 = "int8"
    INT32 = "int32"
    FLOAT64 = "float64"


class PreListingMarketFeaturePolicy(BaseModel):
    """Frozen V1 engineering policy; parameters are not data-tuned."""

    model_config = ConfigDict(frozen=True)

    version: str = MARKET_FEATURE_POLICY_VERSION
    cutoff_semantics: str = "market_date_strictly_before_listing_date"
    benchmark_return_sessions: tuple[int, int] = (5, 20)
    industry_return_sessions: tuple[int, int] = (5, 20)
    volatility_sessions: int = 20
    volatility_return: str = "one_session_log_return"
    volatility_ddof: int = 0
    volatility_annualized: bool = False
    turnover_sessions: int = 20
    recent_ipo_calendar_days: int = 60
    recent_ipo_max_count: int = 20
    recent_ipo_security_type: MarketSecurityType = MarketSecurityType.ORDINARY_EQUITY

    @model_validator(mode="after")
    def validate_frozen_policy(self) -> "PreListingMarketFeaturePolicy":
        if self.version != MARKET_FEATURE_POLICY_VERSION:
            raise ValueError("unsupported pre-listing market feature policy version")
        if self.cutoff_semantics != "market_date_strictly_before_listing_date":
            raise ValueError("market feature cutoff must remain strictly pre-listing")
        if self.benchmark_return_sessions != (5, 20):
            raise ValueError("benchmark windows must remain 5 and 20 sessions")
        if self.industry_return_sessions != (5, 20):
            raise ValueError("industry windows must remain 5 and 20 sessions")
        if (
            self.volatility_sessions != 20
            or self.volatility_return != "one_session_log_return"
            or self.volatility_ddof != 0
            or self.volatility_annualized
        ):
            raise ValueError("volatility policy must remain 20-session population/non-annualized")
        if self.turnover_sessions != 20:
            raise ValueError("turnover window must remain 20 sessions")
        if self.recent_ipo_calendar_days != 60 or self.recent_ipo_max_count != 20:
            raise ValueError("recent IPO policy must remain 60 calendar days / max 20")
        if self.recent_ipo_security_type is not MarketSecurityType.ORDINARY_EQUITY:
            raise ValueError("recent IPO universe must remain ordinary-equity only")
        return self


class MarketFeatureProvenance(BaseModel):
    """Deterministic lineage for a raw or derived market feature."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    source_record_ids: tuple[str, ...] = ()
    derivation: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketReferenceBar(BaseModel):
    """One close for a governed benchmark or industry reference series."""

    model_config = ConfigDict(frozen=True)

    reference_id: str = Field(min_length=1)
    trading_date: date
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    provenance: MarketDataProvenance


class MarketActivityObservation(BaseModel):
    """Actual total-market turnover; never a single-stock volume proxy."""

    model_config = ConfigDict(frozen=True)

    trading_date: date
    turnover: Decimal = Field(ge=0, allow_inf_nan=False)
    provenance: MarketDataProvenance


class PriorIPOReference(BaseModel):
    """Authoritative identity and eligibility for a possible prior IPO peer."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    security_type: MarketSecurityType
    modeling_eligibility: MarketSecurityEligibility
    eligibility_reason: MarketSecurityEligibilityReason
    eligibility_policy_version: str = MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION
    provenance: MarketDataProvenance

    @model_validator(mode="after")
    def validate_governance(self) -> "PriorIPOReference":
        if self.listing_date.year != self.cohort_year:
            raise ValueError("prior IPO listing date conflicts with cohort year")
        if self.dataset_split is not expected_market_split(self.cohort_year):
            raise ValueError("prior IPO split conflicts with cohort year")
        MarketSecurityEligibilityDecision(
            security_type=self.security_type,
            eligibility=self.modeling_eligibility,
            reason=self.eligibility_reason,
            policy_version=self.eligibility_policy_version,
        )
        return self


class PreListingMarketFeatureContext(BaseModel):
    """Target identity and governed reference mapping for one feature snapshot."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    benchmark_reference_id: str = Field(min_length=1)
    industry_reference_id: str | None = None
    source: str = Field(min_length=1)
    provenance: MarketDataProvenance

    @model_validator(mode="after")
    def validate_identity(self) -> "PreListingMarketFeatureContext":
        if self.listing_date.year != self.cohort_year:
            raise ValueError("target listing date conflicts with cohort year")
        if self.dataset_split is not expected_market_split(self.cohort_year):
            raise ValueError("target split conflicts with cohort year")
        return self


class MarketFeatureValue(BaseModel):
    """One raw feature with explicit availability and lineage."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    value: Decimal | int | None = None
    availability: MarketFeatureAvailability
    missing_reason: MarketFeatureMissingReason | None = None
    provenance: MarketFeatureProvenance | None = None

    @model_validator(mode="after")
    def validate_state(self) -> "MarketFeatureValue":
        if self.availability is MarketFeatureAvailability.AVAILABLE:
            if self.value is None or self.missing_reason is not None or self.provenance is None:
                raise ValueError("available market feature requires value and provenance")
        elif self.value is not None or self.missing_reason is None:
            raise ValueError("unavailable market feature requires a missing reason and no value")
        return self


class PreListingMarketFeatureSnapshot(BaseModel):
    """Semantic point-in-time snapshot for one target IPO."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    stock_code: str
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    observation_date: date | None
    industry_reference_id: str | None = None
    benchmark_reference_id: str
    feature_policy_version: str = MARKET_FEATURE_POLICY_VERSION
    market_feature_schema_version: str = MARKET_FEATURE_SCHEMA_VERSION
    source: str
    provenance: MarketDataProvenance
    features: tuple[MarketFeatureValue, ...]

    @model_validator(mode="after")
    def validate_snapshot(self) -> "PreListingMarketFeatureSnapshot":
        if self.listing_date.year != self.cohort_year:
            raise ValueError("market snapshot listing date conflicts with cohort year")
        if self.dataset_split is not expected_market_split(self.cohort_year):
            raise ValueError("market snapshot split conflicts with cohort year")
        if self.observation_date is not None and self.observation_date >= self.listing_date:
            raise ValueError("market observation date must be strictly before listing date")
        if self.feature_policy_version != MARKET_FEATURE_POLICY_VERSION:
            raise ValueError("unsupported market feature policy version")
        if self.market_feature_schema_version != MARKET_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported market feature schema version")
        names = tuple(item.name for item in self.features)
        if names != MARKET_RAW_FEATURE_ORDER:
            raise ValueError("market snapshot features must use the canonical raw order")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class MarketFeatureDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    dtype: MarketFeatureDType
    source: str = Field(min_length=1)
    missing_semantics: str = Field(min_length=1)


class MarketFeatureManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = MARKET_FEATURE_SCHEMA_VERSION
    policy_version: str = MARKET_FEATURE_POLICY_VERSION
    features: tuple[MarketFeatureDefinition, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> "MarketFeatureManifest":
        if self.version != MARKET_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported market feature schema version")
        if self.policy_version != MARKET_FEATURE_POLICY_VERSION:
            raise ValueError("unsupported market feature policy version")
        indexes = [item.index for item in self.features]
        names = [item.name for item in self.features]
        if indexes != list(range(len(self.features))):
            raise ValueError("market feature indexes must be contiguous and ordered")
        if len(names) != len(set(names)):
            raise ValueError("market feature names must be unique")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class MarketFeatureVector(BaseModel):
    model_config = ConfigDict(frozen=True)

    market_feature_schema_version: str = MARKET_FEATURE_SCHEMA_VERSION
    manifest_hash: str = Field(min_length=64, max_length=64)
    feature_names: tuple[str, ...]
    feature_values: tuple[int | float | None, ...]

    @model_validator(mode="after")
    def validate_shape(self) -> "MarketFeatureVector":
        if self.market_feature_schema_version != MARKET_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported market feature schema version")
        if len(self.feature_names) != len(self.feature_values):
            raise ValueError("market feature names and values must have the same length")
        if len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("market feature vector names must be unique")
        return self
