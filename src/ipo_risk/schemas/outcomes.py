"""Versioned PR-C contracts for the governed five-session outcome target."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import (
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelMissingReason,
)


V04_FIVE_DAY_OUTCOME_POLICY_VERSION = "v04_5d_outcome_policy_v1"
V04_FIVE_DAY_TARGET_SCHEMA_VERSION = "v04_5d_outcome_target_v1"


class FiveDayThresholdMethod(StrEnum):
    """Development-only method used to freeze the binary target boundary."""

    DEVELOPMENT_NEAREST_RANK_QUANTILE = "development_nearest_rank_quantile"


class AbnormalReturnPolicy(StrEnum):
    """Benchmark behavior frozen for the first PR-C target policy."""

    UNAVAILABLE_WITHOUT_GOVERNED_BENCHMARK = (
        "unavailable_without_governed_benchmark"
    )


class FiveDayOutcomePolicy(BaseModel):
    """Policy selected without inspecting Validation or Blind outcomes."""

    model_config = ConfigDict(frozen=True)

    version: str = V04_FIVE_DAY_OUTCOME_POLICY_VERSION
    target_schema_version: str = V04_FIVE_DAY_TARGET_SCHEMA_VERSION
    horizon: str = "5D"
    return_formula: str = "target_close_5d / official_listing_price - 1"
    target_session: str = "fifth_observed_eligible_session_on_or_after_listing_date"
    suspension_behavior: str = "skip_dates_without_an_observed_valid_bar"
    missing_data_behavior: str = "emit_unavailable_target_without_fallback"
    poor_performer_operator: str = "raw_return_5d <= frozen_threshold"
    threshold_method: FiveDayThresholdMethod = (
        FiveDayThresholdMethod.DEVELOPMENT_NEAREST_RANK_QUANTILE
    )
    threshold_quantile: Decimal = Field(
        default=Decimal("0.25"), gt=0, lt=1, allow_inf_nan=False
    )
    abnormal_return_policy: AbnormalReturnPolicy = (
        AbnormalReturnPolicy.UNAVAILABLE_WITHOUT_GOVERNED_BENCHMARK
    )
    development_year_start: int = 2020
    development_year_end: int = 2023
    validation_year: int = 2024
    blind_year: int = 2025

    @model_validator(mode="after")
    def validate_frozen_policy(self) -> "FiveDayOutcomePolicy":
        if self.version != V04_FIVE_DAY_OUTCOME_POLICY_VERSION:
            raise ValueError("unsupported five-day outcome policy version")
        if self.target_schema_version != V04_FIVE_DAY_TARGET_SCHEMA_VERSION:
            raise ValueError("unsupported five-day target schema version")
        if self.horizon != "5D":
            raise ValueError("PR-C target policy must use the 5D horizon")
        if (self.development_year_start, self.development_year_end) != (2020, 2023):
            raise ValueError("PR-C development window must remain 2020-2023")
        if self.validation_year != 2024 or self.blind_year != 2025:
            raise ValueError("PR-C validation/blind years must remain 2024/2025")
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


class FrozenFiveDayThreshold(BaseModel):
    """Numeric threshold plus the exact Development provenance used to fit it."""

    model_config = ConfigDict(frozen=True)

    policy_version: str = V04_FIVE_DAY_OUTCOME_POLICY_VERSION
    policy_hash: str = Field(min_length=64, max_length=64)
    method: FiveDayThresholdMethod
    quantile: Decimal = Field(gt=0, lt=1, allow_inf_nan=False)
    threshold: Decimal = Field(allow_inf_nan=False)
    nearest_rank: int = Field(ge=1)
    development_sample_count: int = Field(ge=1)
    development_case_ids_hash: str = Field(min_length=64, max_length=64)
    development_returns_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_policy_identity(self) -> "FrozenFiveDayThreshold":
        if self.policy_version != V04_FIVE_DAY_OUTCOME_POLICY_VERSION:
            raise ValueError("threshold policy version mismatch")
        if self.nearest_rank > self.development_sample_count:
            raise ValueError("nearest rank exceeds Development sample count")
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


class FiveDayOutcomeTarget(BaseModel):
    """One governed PR-C target row; Blind rows are impossible by contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = V04_FIVE_DAY_TARGET_SCHEMA_VERSION
    policy_version: str = V04_FIVE_DAY_OUTCOME_POLICY_VERSION
    policy_hash: str = Field(min_length=64, max_length=64)
    threshold_hash: str = Field(min_length=64, max_length=64)
    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    dataset_split: MarketDatasetSplit
    listing_date: str | None = None
    target_trading_date: str | None = None
    raw_return_5d: Decimal | None = Field(default=None, allow_inf_nan=False)
    abnormal_return_5d: Decimal | None = Field(default=None, allow_inf_nan=False)
    poor_performer_5d: bool | None = None
    poor_performer_threshold: Decimal = Field(allow_inf_nan=False)
    availability: MarketLabelAvailability
    missing_reason: MarketLabelMissingReason | None = None
    source_label_policy_version: str = Field(min_length=1)
    source_label_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_target(self) -> "FiveDayOutcomeTarget":
        if self.schema_version != V04_FIVE_DAY_TARGET_SCHEMA_VERSION:
            raise ValueError("unsupported five-day target schema version")
        if self.policy_version != V04_FIVE_DAY_OUTCOME_POLICY_VERSION:
            raise ValueError("unsupported five-day outcome policy version")
        if self.dataset_split is MarketDatasetSplit.BLIND or self.cohort_year == 2025:
            raise ValueError("2025 Blind outcomes cannot form PR-C target rows")
        if self.abnormal_return_5d is not None:
            raise ValueError("abnormal return is unavailable without a governed benchmark")
        if self.availability is MarketLabelAvailability.AVAILABLE:
            if self.raw_return_5d is None or self.poor_performer_5d is None:
                raise ValueError("available target requires raw and binary outcomes")
            if self.target_trading_date is None or self.missing_reason is not None:
                raise ValueError("available target has inconsistent availability fields")
        else:
            if self.missing_reason is None:
                raise ValueError("unavailable target requires a missing reason")
            if self.raw_return_5d is not None or self.poor_performer_5d is not None:
                raise ValueError("unavailable target cannot carry outcome values")
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
