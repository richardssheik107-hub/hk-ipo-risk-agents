"""Versioned contracts joining final v0.3 document risks to V04 labels."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import (
    MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION,
    MarketDatasetSplit,
    MarketLabelHorizon,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
    MarketSecurityEligibilityDecision,
    MarketSecurityEligibilityReason,
    MarketSecurityType,
    expected_market_split,
)


DOCUMENT_FEATURE_SCHEMA_VERSION = "v04_document_features_v1"
V04_MODELING_DATASET_VERSION = "v04_modeling_dataset_v1"


class DocumentRiskFeatureState(StrEnum):
    VERIFIED = "verified"
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    NOT_EMITTED = "not_emitted"
    UNAVAILABLE = "unavailable"


class DocumentFeatureDType(StrEnum):
    INT8 = "int8"
    INT32 = "int32"
    FLOAT64 = "float64"


class DocumentRiskFeature(BaseModel):
    """Lossless state for one canonical v0.3 risk position."""

    model_config = ConfigDict(frozen=True)

    risk_code: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    state: DocumentRiskFeatureState
    score: float | None = Field(default=None, ge=0, le=100)
    level: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_count: int = Field(ge=0)
    has_calculation: bool
    calculation_success: bool | None = None
    source_risk_id: str | None = None
    missing_reason: str | None = None

    @model_validator(mode="after")
    def validate_state_payload(self) -> "DocumentRiskFeature":
        absent = self.state in {
            DocumentRiskFeatureState.NOT_EMITTED,
            DocumentRiskFeatureState.UNAVAILABLE,
        }
        if absent:
            if any(
                value is not None
                for value in (
                    self.score,
                    self.level,
                    self.confidence,
                    self.source_risk_id,
                )
            ):
                raise ValueError("absent risk state cannot carry a source risk payload")
            if self.evidence_count != 0 or self.has_calculation:
                raise ValueError("absent risk state cannot carry evidence or calculation")
            if not self.missing_reason:
                raise ValueError("absent risk state requires a missing reason")
        elif self.source_risk_id is None:
            raise ValueError("emitted risk state requires source_risk_id")
        return self


class DocumentFeatureDefinition(BaseModel):
    """One frozen numeric feature position."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    dtype: DocumentFeatureDType
    source: str = Field(min_length=1)
    missing_semantics: str = Field(min_length=1)


class DocumentFeatureManifest(BaseModel):
    """Ordered, versioned definition of the canonical document vector."""

    model_config = ConfigDict(frozen=True)

    version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    features: tuple[DocumentFeatureDefinition, ...]
    level_ordinal_mapping: tuple[tuple[str, int], ...]

    @model_validator(mode="after")
    def validate_order(self) -> "DocumentFeatureManifest":
        indexes = [item.index for item in self.features]
        names = [item.name for item in self.features]
        if indexes != list(range(len(self.features))):
            raise ValueError("feature indexes must be contiguous and ordered")
        if len(names) != len(set(names)):
            raise ValueError("feature names must be unique")
        if self.version != DOCUMENT_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported document feature schema version")
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


class DocumentFeatureVector(BaseModel):
    """Values bound to the exact ordered manifest used to produce them."""

    model_config = ConfigDict(frozen=True)

    feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    manifest_hash: str = Field(min_length=64, max_length=64)
    feature_names: tuple[str, ...]
    feature_values: tuple[int | float | None, ...]

    @model_validator(mode="after")
    def validate_shape(self) -> "DocumentFeatureVector":
        if self.feature_schema_version != DOCUMENT_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported document feature schema version")
        if len(self.feature_names) != len(self.feature_values):
            raise ValueError("feature names and values must have the same length")
        if len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("feature vector names must be unique")
        return self


class DocumentRiskSnapshotBuildContext(BaseModel):
    """Explicit identity and code provenance absent from legacy result fields."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date | None = None
    dataset_split: MarketDatasetSplit
    official_ipo_universe_member: bool = False
    security_type: MarketSecurityType = MarketSecurityType.UNKNOWN
    modeling_eligibility: MarketSecurityEligibility = MarketSecurityEligibility.INELIGIBLE
    eligibility_reason: MarketSecurityEligibilityReason = (
        MarketSecurityEligibilityReason.NOT_OFFICIAL_IPO_UNIVERSE_MEMBER
    )
    eligibility_policy_version: str = MARKET_SECURITY_ELIGIBILITY_POLICY_VERSION
    document_pipeline_version: str = Field(min_length=1)
    document_pipeline_commit: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_governance(self) -> "DocumentRiskSnapshotBuildContext":
        expected = expected_market_split(self.cohort_year)
        if self.dataset_split is not expected:
            raise ValueError("snapshot split conflicts with cohort year")
        if self.listing_date is not None and self.listing_date.year != self.cohort_year:
            raise ValueError("snapshot listing date conflicts with cohort year")
        if self.feature_schema_version != DOCUMENT_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported document feature schema version")
        MarketSecurityEligibilityDecision(
            official_ipo_universe_member=self.official_ipo_universe_member,
            security_type=self.security_type,
            eligibility=self.modeling_eligibility,
            reason=self.eligibility_reason,
            policy_version=self.eligibility_policy_version,
        )
        return self


class V03DocumentRiskSnapshot(BaseModel):
    """Deterministic document-only risk state plus immutable provenance."""

    model_config = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date | None = None
    dataset_split: MarketDatasetSplit
    official_ipo_universe_member: bool
    security_type: MarketSecurityType
    modeling_eligibility: MarketSecurityEligibility
    eligibility_reason: MarketSecurityEligibilityReason
    eligibility_policy_version: str
    workflow_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    document_pipeline_version: str = Field(min_length=1)
    document_pipeline_commit: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    source_analysis_id: str = Field(min_length=1)
    source_analysis_status: str = Field(min_length=1)
    generated_from_result_version: str = Field(min_length=1)
    risk_features: tuple[DocumentRiskFeature, ...]
    unknown_risk_codes: tuple[str, ...] = ()
    conflict_count: int | None = Field(default=None, ge=0)
    rule_predictor_version: str | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "V03DocumentRiskSnapshot":
        expected = expected_market_split(self.cohort_year)
        if self.dataset_split is not expected:
            raise ValueError("snapshot split conflicts with cohort year")
        if self.listing_date is not None and self.listing_date.year != self.cohort_year:
            raise ValueError("snapshot listing date conflicts with cohort year")
        codes = [item.risk_code for item in self.risk_features]
        if len(codes) != len(set(codes)):
            raise ValueError("snapshot risk positions must be unique")
        if self.feature_schema_version != DOCUMENT_FEATURE_SCHEMA_VERSION:
            raise ValueError("unsupported document feature schema version")
        MarketSecurityEligibilityDecision(
            official_ipo_universe_member=self.official_ipo_universe_member,
            security_type=self.security_type,
            eligibility=self.modeling_eligibility,
            reason=self.eligibility_reason,
            policy_version=self.eligibility_policy_version,
        )
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


class V04ModelingRecord(BaseModel):
    """One document feature vector joined to one non-blind outcome label."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    document_id: str
    stock_code: str
    cohort_year: int
    listing_date: date | None = None
    dataset_split: MarketDatasetSplit
    official_ipo_universe_member: bool
    security_type: MarketSecurityType
    eligibility_policy_version: str
    label_horizon: MarketLabelHorizon
    feature_vector: DocumentFeatureVector
    outcome_label: MarketOutcomeLabel
    source_analysis_id: str
    snapshot_hash: str = Field(min_length=64, max_length=64)
    document_pipeline_version: str
    document_pipeline_commit: str
    workflow_version: str
    schema_version: str
    feature_schema_version: str
    market_label_policy_version: str
    market_split_policy_version: str
    dataset_version: str = V04_MODELING_DATASET_VERSION

    @model_validator(mode="after")
    def validate_join(self) -> "V04ModelingRecord":
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("blind outcome labels cannot form modeling records")
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
            raise ValueError(f"modeling join mismatch: {', '.join(mismatches)}")
        if self.feature_schema_version != self.feature_vector.feature_schema_version:
            raise ValueError("feature schema version mismatch")
        if self.dataset_version != V04_MODELING_DATASET_VERSION:
            raise ValueError("unsupported modeling dataset version")
        return self


class V04ModelingDataset(BaseModel):
    """Deterministically ordered development or validation records."""

    model_config = ConfigDict(frozen=True)

    dataset_version: str = V04_MODELING_DATASET_VERSION
    dataset_split: MarketDatasetSplit
    feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    manifest_hash: str = Field(min_length=64, max_length=64)
    records: tuple[V04ModelingRecord, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> "V04ModelingDataset":
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("blind labels cannot form a modeling dataset")
        keys = [(row.case_id, row.label_horizon.value) for row in self.records]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("modeling records must be uniquely and deterministically ordered")
        if any(row.dataset_split is not self.dataset_split for row in self.records):
            raise ValueError("modeling dataset contains a different split")
        if any(row.feature_schema_version != self.feature_schema_version for row in self.records):
            raise ValueError("modeling dataset contains a different feature schema")
        if any(row.feature_vector.manifest_hash != self.manifest_hash for row in self.records):
            raise ValueError("modeling dataset contains a different manifest hash")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


class V04BlindFeatureRecord(BaseModel):
    """A 2025 feature row that deliberately has no outcome-label field."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    document_id: str
    stock_code: str
    cohort_year: int
    listing_date: date | None = None
    dataset_split: MarketDatasetSplit
    official_ipo_universe_member: bool
    security_type: MarketSecurityType
    eligibility_policy_version: str
    source_analysis_id: str
    snapshot_hash: str = Field(min_length=64, max_length=64)
    feature_vector: DocumentFeatureVector
    document_pipeline_version: str
    document_pipeline_commit: str

    @model_validator(mode="after")
    def validate_blind_row(self) -> "V04BlindFeatureRecord":
        if self.dataset_split is not MarketDatasetSplit.BLIND or self.cohort_year != 2025:
            raise ValueError("blind feature rows must be 2025 blind data")
        return self


class V04BlindFeatureDataset(BaseModel):
    """Feature-only blind export; by schema it cannot expose an outcome."""

    model_config = ConfigDict(frozen=True)

    dataset_version: str = V04_MODELING_DATASET_VERSION
    dataset_split: MarketDatasetSplit = MarketDatasetSplit.BLIND
    feature_schema_version: str = DOCUMENT_FEATURE_SCHEMA_VERSION
    manifest_hash: str = Field(min_length=64, max_length=64)
    records: tuple[V04BlindFeatureRecord, ...]

    @model_validator(mode="after")
    def validate_rows(self) -> "V04BlindFeatureDataset":
        if self.dataset_split is not MarketDatasetSplit.BLIND:
            raise ValueError("blind feature dataset must use the blind split")
        keys = [row.case_id for row in self.records]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("blind feature rows must be uniquely and deterministically ordered")
        if any(row.feature_vector.manifest_hash != self.manifest_hash for row in self.records):
            raise ValueError("blind feature dataset contains a different manifest hash")
        return self
