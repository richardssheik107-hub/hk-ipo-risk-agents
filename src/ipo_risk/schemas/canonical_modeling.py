"""Versioned PR-D canonical modeling contracts.

These contracts are additive.  They do not mutate the historical document-only
V1 or the 120-position Extended market join.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import MarketDatasetSplit
from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget


V04_CANONICAL_MODELING_DATASET_VERSION = "v04_canonical_modeling_dataset_v1"
V04_CANONICAL_MODEL_MATRIX_VERSION = "v04_canonical_model_matrix_v1"


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class V04FeatureComponent(StrEnum):
    MARKET_CORE = "market_core"
    MARKET_EXTENDED = "market_extended"
    PRODUCTION_DOCUMENT = "production_document"
    ORACLE_DOCUMENT = "oracle_document"


class V04ModelFeatureGroup(StrEnum):
    M = "M"
    P = "P"
    O = "O"
    PM = "PM"
    OM = "OM"


class V04CanonicalCohort(StrEnum):
    FULL_PRODUCTION = "full_production"
    ORACLE_INTERSECTION = "oracle_intersection"


class V04CanonicalFeatureBlock(BaseModel):
    """One immutable feature component with explicit schema and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    component: V04FeatureComponent
    schema_version: str = Field(min_length=1)
    policy_version: str | None = None
    manifest_hash: str = Field(min_length=64, max_length=64)
    artifact_hash: str = Field(min_length=64, max_length=64)
    feature_names: tuple[str, ...]
    feature_values: tuple[int | float | None, ...]
    evaluation_only: bool = False

    @model_validator(mode="after")
    def validate_block(self) -> "V04CanonicalFeatureBlock":
        if len(self.feature_names) != len(self.feature_values):
            raise ValueError("feature block names and values must have equal length")
        if not self.feature_names or len(self.feature_names) != len(set(self.feature_names)):
            raise ValueError("feature block names must be non-empty and unique")
        if self.component is V04FeatureComponent.ORACLE_DOCUMENT:
            if not self.evaluation_only:
                raise ValueError("Oracle feature block must remain evaluation-only")
        elif self.evaluation_only:
            raise ValueError("Production/Market feature blocks cannot be evaluation-only")
        return self


class V04CanonicalModelingRecord(BaseModel):
    """One non-blind IPO row with Core, Production, optional Oracle/Extended and y."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_version: str = V04_CANONICAL_MODELING_DATASET_VERSION
    case_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    cohort_year: int
    listing_date: date
    dataset_split: MarketDatasetSplit
    market_core: V04CanonicalFeatureBlock
    production_document: V04CanonicalFeatureBlock
    market_extended: V04CanonicalFeatureBlock | None = None
    oracle_document: V04CanonicalFeatureBlock | None = None
    target: FiveDayOutcomeTarget
    source_manifest_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def validate_record(self) -> "V04CanonicalModelingRecord":
        if self.dataset_version != V04_CANONICAL_MODELING_DATASET_VERSION:
            raise ValueError("unsupported canonical modeling dataset version")
        if self.dataset_split is MarketDatasetSplit.BLIND or self.cohort_year == 2025:
            raise ValueError("Blind outcomes cannot form canonical modeling records")
        if self.listing_date.year != self.cohort_year:
            raise ValueError("canonical listing date conflicts with cohort year")
        pairs = {
            "case_id": (self.case_id, self.target.case_id),
            "stock_code": (self.stock_code, self.target.stock_code),
            "cohort_year": (self.cohort_year, self.target.cohort_year),
            "listing_date": (self.listing_date.isoformat(), self.target.listing_date),
            "dataset_split": (self.dataset_split, self.target.dataset_split),
        }
        mismatches = [name for name, (left, right) in pairs.items() if left != right]
        if mismatches:
            raise ValueError("canonical target join mismatch: " + ", ".join(mismatches))
        if self.target.raw_return_5d is None or self.target.poor_performer_5d is None:
            raise ValueError("canonical modeling records require an available target")
        if self.market_core.component is not V04FeatureComponent.MARKET_CORE:
            raise ValueError("market_core block has the wrong component")
        if (
            self.production_document.component
            is not V04FeatureComponent.PRODUCTION_DOCUMENT
        ):
            raise ValueError("production_document block has the wrong component")
        if self.market_extended is not None and (
            self.market_extended.component is not V04FeatureComponent.MARKET_EXTENDED
        ):
            raise ValueError("market_extended block has the wrong component")
        if self.oracle_document is not None and (
            self.oracle_document.component is not V04FeatureComponent.ORACLE_DOCUMENT
        ):
            raise ValueError("oracle_document block has the wrong component")
        return self

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class V04CanonicalModelingDataset(BaseModel):
    """A deterministic Development or Validation cohort from the PR-D builder."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_version: str = V04_CANONICAL_MODELING_DATASET_VERSION
    cohort: V04CanonicalCohort
    dataset_split: MarketDatasetSplit
    source_manifest_hash: str = Field(min_length=64, max_length=64)
    target_policy_hash: str = Field(min_length=64, max_length=64)
    target_threshold_hash: str = Field(min_length=64, max_length=64)
    records: tuple[V04CanonicalModelingRecord, ...]

    @model_validator(mode="after")
    def validate_dataset(self) -> "V04CanonicalModelingDataset":
        if self.dataset_version != V04_CANONICAL_MODELING_DATASET_VERSION:
            raise ValueError("unsupported canonical modeling dataset version")
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("Blind labels cannot form a canonical dataset")
        case_ids = [row.case_id for row in self.records]
        if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
            raise ValueError("canonical dataset rows must be unique and ordered")
        if any(row.dataset_split is not self.dataset_split for row in self.records):
            raise ValueError("canonical dataset contains another split")
        if any(row.source_manifest_hash != self.source_manifest_hash for row in self.records):
            raise ValueError("canonical dataset contains another source manifest")
        if any(row.target.policy_hash != self.target_policy_hash for row in self.records):
            raise ValueError("canonical dataset target policy drifted")
        if any(row.target.threshold_hash != self.target_threshold_hash for row in self.records):
            raise ValueError("canonical dataset threshold drifted")
        if self.cohort is V04CanonicalCohort.ORACLE_INTERSECTION and any(
            row.oracle_document is None for row in self.records
        ):
            raise ValueError("Oracle intersection contains a row without Oracle X")
        return self

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class V04CanonicalModelMatrix(BaseModel):
    """Fair-comparison matrix for one of M/P/O/PM/OM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    matrix_version: str = V04_CANONICAL_MODEL_MATRIX_VERSION
    dataset_version: str = V04_CANONICAL_MODELING_DATASET_VERSION
    cohort: V04CanonicalCohort
    dataset_split: MarketDatasetSplit
    feature_group: V04ModelFeatureGroup
    source_dataset_hash: str = Field(min_length=64, max_length=64)
    feature_manifest_hash: str = Field(min_length=64, max_length=64)
    target_policy_hash: str = Field(min_length=64, max_length=64)
    target_threshold_hash: str = Field(min_length=64, max_length=64)
    case_ids: tuple[str, ...]
    feature_names: tuple[str, ...]
    feature_values: tuple[tuple[int | float | None, ...], ...]
    raw_return_5d: tuple[Decimal, ...]
    poor_performer_5d: tuple[bool, ...]

    @model_validator(mode="after")
    def validate_matrix(self) -> "V04CanonicalModelMatrix":
        if self.matrix_version != V04_CANONICAL_MODEL_MATRIX_VERSION:
            raise ValueError("unsupported canonical model matrix version")
        if self.dataset_split is MarketDatasetSplit.BLIND:
            raise ValueError("Blind labels cannot form a model matrix")
        row_count = len(self.case_ids)
        if self.case_ids != tuple(sorted(self.case_ids)) or len(set(self.case_ids)) != row_count:
            raise ValueError("matrix case IDs must be unique and ordered")
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("matrix feature names must be non-empty and unique")
        if not (
            len(self.feature_values)
            == len(self.raw_return_5d)
            == len(self.poor_performer_5d)
            == row_count
        ):
            raise ValueError("matrix X/y row counts disagree")
        if any(len(row) != len(self.feature_names) for row in self.feature_values):
            raise ValueError("matrix feature row width disagrees with manifest")
        if self.feature_group in {V04ModelFeatureGroup.O, V04ModelFeatureGroup.OM} and (
            self.cohort is not V04CanonicalCohort.ORACLE_INTERSECTION
        ):
            raise ValueError("Oracle matrices require the Oracle intersection cohort")
        return self

