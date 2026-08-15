"""Versioned contracts for the v0.4 market-foundation track."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MarketExchange(StrEnum):
    HKEX = "HKEX"


class MarketLabelHorizon(StrEnum):
    ONE_DAY = "1D"
    FIVE_DAYS = "5D"
    TWENTY_DAYS = "20D"
    SIXTY_DAYS = "60D"

    @property
    def sessions(self) -> int:
        return {
            self.ONE_DAY: 1,
            self.FIVE_DAYS: 5,
            self.TWENTY_DAYS: 20,
            self.SIXTY_DAYS: 60,
        }[self]


class MarketLabelAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class MarketLabelMissingReason(StrEnum):
    MISSING_LISTING_METADATA = "missing_listing_metadata"
    MISSING_LISTING_DATE = "missing_listing_date"
    MISSING_BASE_PRICE = "missing_base_price"
    NO_ELIGIBLE_SESSION = "no_eligible_session"
    INSUFFICIENT_FORWARD_HISTORY = "insufficient_forward_history"
    INVALID_TARGET_PRICE = "invalid_target_price"


class MarketBasePriceSource(StrEnum):
    OFFICIAL_LISTING_PRICE = "official_listing_price"


class MarketDatasetSplit(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    BLIND = "blind"


class MarketSecurityType(StrEnum):
    ORDINARY_EQUITY = "ordinary_equity"
    REIT = "reit"
    SPAC = "spac"
    WARRANT = "warrant"
    UNKNOWN = "unknown"


class MarketSecurityEligibility(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class MarketSecurityEligibilityReason(StrEnum):
    ORDINARY_EQUITY_SUPPORTED = "ordinary_equity_supported"
    REIT_OUTSIDE_MODELING_UNIVERSE = "reit_outside_modeling_universe"
    SPAC_OUTSIDE_MODELING_UNIVERSE = "spac_outside_modeling_universe"
    WARRANT_OUTSIDE_MODELING_UNIVERSE = "warrant_outside_modeling_universe"
    UNKNOWN_SECURITY_TYPE = "unknown_security_type"


MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION = "v04_market_security_eligibility_v1"


class MarketValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


def expected_market_split(cohort_year: int) -> MarketDatasetSplit:
    """Return the frozen v0.4 chronological split, with no exceptions."""

    if 2020 <= cohort_year <= 2023:
        return MarketDatasetSplit.DEVELOPMENT
    if cohort_year == 2024:
        return MarketDatasetSplit.VALIDATION
    if cohort_year == 2025:
        return MarketDatasetSplit.BLIND
    raise ValueError(f"unsupported market cohort year: {cohort_year}")


def expected_security_eligibility(
    security_type: MarketSecurityType,
) -> tuple[MarketSecurityEligibility, MarketSecurityEligibilityReason]:
    """Return the frozen v1 modeling-universe decision for a known type."""

    mapping = {
        MarketSecurityType.ORDINARY_EQUITY: (
            MarketSecurityEligibility.ELIGIBLE,
            MarketSecurityEligibilityReason.ORDINARY_EQUITY_SUPPORTED,
        ),
        MarketSecurityType.REIT: (
            MarketSecurityEligibility.INELIGIBLE,
            MarketSecurityEligibilityReason.REIT_OUTSIDE_MODELING_UNIVERSE,
        ),
        MarketSecurityType.SPAC: (
            MarketSecurityEligibility.INELIGIBLE,
            MarketSecurityEligibilityReason.SPAC_OUTSIDE_MODELING_UNIVERSE,
        ),
        MarketSecurityType.WARRANT: (
            MarketSecurityEligibility.INELIGIBLE,
            MarketSecurityEligibilityReason.WARRANT_OUTSIDE_MODELING_UNIVERSE,
        ),
        MarketSecurityType.UNKNOWN: (
            MarketSecurityEligibility.INELIGIBLE,
            MarketSecurityEligibilityReason.UNKNOWN_SECURITY_TYPE,
        ),
    }
    return mapping[security_type]


class MarketSecurityEligibilityDecision(BaseModel):
    """Versioned, explicit decision about the v0.4 modeling universe."""

    model_config = ConfigDict(frozen=True)

    security_type: MarketSecurityType
    eligibility: MarketSecurityEligibility
    reason: MarketSecurityEligibilityReason
    policy_version: str = MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION

    @model_validator(mode="after")
    def validate_frozen_policy(self) -> "MarketSecurityEligibilityDecision":
        if self.policy_version != MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION:
            raise ValueError("unsupported market security eligibility policy version")
        expected_eligibility, expected_reason = expected_security_eligibility(
            self.security_type
        )
        if self.eligibility is not expected_eligibility or self.reason is not expected_reason:
            raise ValueError("security eligibility decision conflicts with frozen policy")
        return self


class MarketDataProvenance(BaseModel):
    """Trace one market record to a named, versioned upstream dataset."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    source_record_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "dataset_version", "source_record_id")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class MarketDailyBar(BaseModel):
    """One observed trading-session OHLCV record for a listed security."""

    stock_code: str = Field(min_length=1)
    trading_date: date
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    high: Decimal = Field(gt=0, allow_inf_nan=False)
    low: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    adjusted_close: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    volume: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    source: str = Field(min_length=1)
    provenance: MarketDataProvenance

    @field_validator("stock_code", "source")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_ohlc(self) -> "MarketDailyBar":
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be at least open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be at most open, high, and close")
        return self


class IPOMarketMetadata(BaseModel):
    """IPO identity and official offering facts needed by market labels."""

    case_id: str = Field(min_length=1)
    document_id: str | None = None
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date | None = None
    listing_price: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = None
    exchange: MarketExchange
    security_type: MarketSecurityType = MarketSecurityType.UNKNOWN
    modeling_eligibility: MarketSecurityEligibility = MarketSecurityEligibility.INELIGIBLE
    eligibility_reason: MarketSecurityEligibilityReason = (
        MarketSecurityEligibilityReason.UNKNOWN_SECURITY_TYPE
    )
    eligibility_policy_version: str = MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION
    source: str = Field(min_length=1)
    provenance: MarketDataProvenance

    @field_validator("case_id", "document_id", "stock_code", "currency", "source")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 3 or not value.isalpha() or value != value.upper()):
            raise ValueError("currency must be an uppercase ISO-4217-style code")
        return value

    @field_validator("cohort_year")
    @classmethod
    def validate_cohort_year(cls, value: int) -> int:
        expected_market_split(value)
        return value

    @model_validator(mode="after")
    def validate_market_governance(self) -> "IPOMarketMetadata":
        if self.listing_date is not None and self.listing_date.year != self.cohort_year:
            raise ValueError("listing date year must equal cohort year")
        decision = MarketSecurityEligibilityDecision(
            security_type=self.security_type,
            eligibility=self.modeling_eligibility,
            reason=self.eligibility_reason,
            policy_version=self.eligibility_policy_version,
        )
        if decision.policy_version != self.eligibility_policy_version:
            raise ValueError("security eligibility policy version mismatch")
        return self


class MarketLabelPolicy(BaseModel):
    """Frozen rules used to derive deterministic v0.4 outcome labels."""

    model_config = ConfigDict(frozen=True)

    version: str = "v04_market_label_policy_v1"
    horizons: tuple[MarketLabelHorizon, ...] = (
        MarketLabelHorizon.ONE_DAY,
        MarketLabelHorizon.FIVE_DAYS,
        MarketLabelHorizon.TWENTY_DAYS,
        MarketLabelHorizon.SIXTY_DAYS,
    )
    base_price_source: MarketBasePriceSource = MarketBasePriceSource.OFFICIAL_LISTING_PRICE
    session_counting: str = "observed_eligible_sessions_on_or_after_listing_date"
    suspension_behavior: str = "skip_dates_without_an_observed_valid_bar"
    missing_data_behavior: str = "emit_unavailable_label_without_fallback"
    benchmark_behavior: str = "optional_unavailable_without_reliable_source"

    @model_validator(mode="after")
    def validate_frozen_horizons(self) -> "MarketLabelPolicy":
        required = {
            MarketLabelHorizon.ONE_DAY,
            MarketLabelHorizon.FIVE_DAYS,
            MarketLabelHorizon.TWENTY_DAYS,
            MarketLabelHorizon.SIXTY_DAYS,
        }
        if set(self.horizons) != required or len(self.horizons) != len(required):
            raise ValueError("v0.4 policy must contain exactly 1D, 5D, 20D, and 60D")
        if not self.version.strip():
            raise ValueError("label policy version is required")
        return self


class MarketOutcomeLabel(BaseModel):
    """One horizon-specific post-listing return label or explicit absence."""

    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    dataset_split: MarketDatasetSplit
    listing_date: date | None = None
    horizon: MarketLabelHorizon
    base_price: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    base_price_source: MarketBasePriceSource
    target_trading_date: date | None = None
    target_close: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    raw_return: Decimal | None = Field(default=None, allow_inf_nan=False)
    benchmark_return: Decimal | None = Field(default=None, allow_inf_nan=False)
    excess_return: Decimal | None = Field(default=None, allow_inf_nan=False)
    availability: MarketLabelAvailability
    missing_reason: MarketLabelMissingReason | None = None
    label_policy_version: str = Field(min_length=1)
    source: str = Field(min_length=1)
    provenance: MarketDataProvenance

    @model_validator(mode="after")
    def validate_label_state(self) -> "MarketOutcomeLabel":
        expected = expected_market_split(self.cohort_year)
        if self.dataset_split is not expected:
            raise ValueError(
                f"cohort year {self.cohort_year} must use {expected.value} split"
            )
        if self.listing_date is not None and self.listing_date.year != self.cohort_year:
            raise ValueError("listing date year must equal cohort year")
        required = (self.listing_date, self.base_price, self.target_trading_date, self.target_close)
        if self.availability is MarketLabelAvailability.AVAILABLE:
            if any(value is None for value in required) or self.raw_return is None:
                raise ValueError("available label requires listing, base, target, and return values")
            if self.missing_reason is not None:
                raise ValueError("available label cannot have a missing reason")
        else:
            if self.missing_reason is None:
                raise ValueError("unavailable label requires a missing reason")
            if self.raw_return is not None:
                raise ValueError("unavailable label cannot carry a raw return")
        if self.benchmark_return is None and self.excess_return is not None:
            raise ValueError("excess return requires a benchmark return")
        return self


class MarketValidationIssue(BaseModel):
    severity: MarketValidationSeverity
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    stock_code: str | None = None
    case_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class MarketValidationResult(BaseModel):
    status: str
    errors: list[MarketValidationIssue] = Field(default_factory=list)
    warnings: list[MarketValidationIssue] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
