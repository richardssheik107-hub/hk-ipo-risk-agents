"""Higher-level V04 contract combining document and pre-listing market X."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import (
    MarketDatasetSplit,
    MarketLabelHorizon,
    MarketOutcomeLabel,
    MarketSecurityType,
)
from ipo_risk.schemas.market_features import MARKET_FEATURE_SCHEMA_VERSION
from ipo_risk.schemas.modeling import DOCUMENT_FEATURE_SCHEMA_VERSION


V04_MARKET_AUGMENTED_DATASET_VERSION = "v04_market_augmented_dataset_v1"


class V04CombinedFeatureVector(BaseModel):
    """Stable order: all document positions, then all market positions."""

    model_config = ConfigDict(frozen=True)

    document_feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    document_manifest_hash: str = Field(min_length=64, max_length=64)
    market_feature_schema_version: str = MARKET_FEATURE_SCHEMA_VERSION
    market_manifest_hash: str = Field(min_length=64, max_length=64)
    feature_names: tuple[str, ...]
    feature_values: tuple[int | float | None, ...]

    @model_validator(mode="after")
    def validate_shape(self) -> "V04CombinedFeatureVector":
        if self.document_feature_schema_version != DOCUMENT_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported document feature schema version")
        if self.market_feature_schema_version != MARKET_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported market feature schema version")
        if len(self.feature_names) != len(self.feature_values):
            raise ValueError("combined feature names and values must have the same length")
        if len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("combined feature names must be unique")
        return self


class V04MarketAugmentedModelingRecord(BaseModel):
    """Non-blind modeling row with document X, pre-listing market X, and y."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    document_id: str
    stock_code: str
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    security_type: MarketSecurityType
    eligibility_policy_version: str
    label_horizon: MarketLabelHorizon
    feature_vector: V04CombinedFeatureVector
    outcome_label: MarketOutcomeLabel
    source_analysis_id: str
    document_snapshot_hash: str = Field(min_length=64, max_length=64)
    market_snapshot_hash: str = Field(min_length=64, max_length=64)
    document_pipeline_version: str
    document_pipeline_commit: str
    workflow_version: str
    schema_version: str
    document_feature_schema_version: str
    document_manifest_hash: str = Field(min_length=64, max_length=64)
    market_feature_schema_version: str
    market_manifest_hash: str = Field(min_length=64, max_length=64)
    market_policy_version: str
    market_observation_date: date
    market_label_policy_version: str
    market_split_policy_version: str
    dataset_version: str = V04_MARKET_AUGMENTED_DATASET_VERSION

    @model_validator(mode="after")
    def validate_join(self) -> "V04MarketAugmentedModelingRecord":
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("blind outcomes cannot form market-augmented records")
        if self.market_observation_date >= self.listing_date:
            raise ValueError("market observation date must precede listing date")
        label = self.outcome_label
        pairs = {
            "case_id": (self.case_id, label.case_id),
            "stock_code": (self.stock_code, label.stock_code),
            "cohort_year": (self.cohort_year, label.cohort_year),
            "listing_date": (self.listing_date, label.listing_date),
            "dataset_split": (self.dataset_split, label.dataset_split),
            "label_horizon": (self.label_horizon, label.horizon),
            "label_policy_version": (
                self.market_label_policy_version,
                label.label_policy_version,
            ),
        }
        mismatches = [name for name, (left, right) in pairs.items() if left != right]
        if mismatches:
            raise ValueError(f"market-augmented join mismatch: {', '.join(mismatches)}")
        if self.document_manifest_hash != self.feature_vector.document_manifest_hash:
            raise ValueError("document manifest hash mismatch")
        if self.market_manifest_hash != self.feature_vector.market_manifest_hash:
            raise ValueError("market manifest hash mismatch")
        if self.dataset_version != V04_MARKET_AUGMENTED_DATASET_VERSION:
            raise ValueError("unsupported market-augmented dataset version")
        return self


class V04MarketAugmentedModelingDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_version: str = V04_MARKET_AUGMENTED_DATASET_VERSION
    dataset_split: MarketDatasetSplit
    document_feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    document_manifest_hash: str = Field(min_length=64, max_length=64)
    market_feature_schema_version: str = MARKET_FEATURE_SCHEMA_VERSION
    market_manifest_hash: str = Field(min_length=64, max_length=64)
    records: tuple[V04MarketAugmentedModelingRecord, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> "V04MarketAugmentedModelingDataset":
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("blind outcomes cannot form market-augmented dataset")
        keys = [(row.case_id, row.label_horizon.value) for row in self.records]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("market-augmented rows must be unique and ordered")
        if any(row.dataset_split is not self.dataset_split for row in self.records):
            raise ValueError("market-augmented dataset contains another split")
        return self


class V04MarketAugmentedBlindFeatureRecord(BaseModel):
    """2025 document+market X only; extra outcome/target fields are forbidden."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str
    document_id: str
    stock_code: str
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    security_type: MarketSecurityType
    eligibility_policy_version: str
    source_analysis_id: str
    document_snapshot_hash: str = Field(min_length=64, max_length=64)
    market_snapshot_hash: str = Field(min_length=64, max_length=64)
    feature_vector: V04CombinedFeatureVector
    document_pipeline_version: str
    document_pipeline_commit: str
    market_observation_date: date
    market_policy_version: str
    dataset_version: str = V04_MARKET_AUGMENTED_DATASET_VERSION

    @model_validator(mode="after")
    def validate_blind(self) -> "V04MarketAugmentedBlindFeatureRecord":
        if self.cohort_year != 2025 or self.dataset_split is not MarketDatasetSplit.BLIND:
            raise ValueError("market-augmented blind rows must be 2025 blind data")
        if self.market_observation_date >= self.listing_date:
            raise ValueError("market observation date must precede blind listing date")
        return self


class V04MarketAugmentedBlindFeatureDataset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_version: str = V04_MARKET_AUGMENTED_DATASET_VERSION
    dataset_split: MarketDatasetSplit = MarketDatasetSplit.BLIND
    document_manifest_hash: str = Field(min_length=64, max_length=64)
    market_manifest_hash: str = Field(min_length=64, max_length=64)
    records: tuple[V04MarketAugmentedBlindFeatureRecord, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> "V04MarketAugmentedBlindFeatureDataset":
        keys = [row.case_id for row in self.records]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("market-augmented blind rows must be unique and ordered")
        return self
