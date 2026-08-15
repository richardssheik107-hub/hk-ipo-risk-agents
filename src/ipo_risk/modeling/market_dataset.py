"""Deterministic V04-3 joins above the unchanged V04-2 document contract."""

from __future__ import annotations

from collections.abc import Iterable

from ipo_risk.market.exceptions import BlindDataLeakageError
from ipo_risk.market.features import MARKET_FEATURE_MANIFEST_V1, vectorize_market_snapshot
from ipo_risk.modeling.exceptions import ModelingDatasetJoinError
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.schemas.market import MarketDatasetSplit
from ipo_risk.schemas.market_features import PreListingMarketFeatureSnapshot
from ipo_risk.schemas.market_modeling import (
    V04CombinedFeatureVector,
    V04MarketAugmentedBlindFeatureDataset,
    V04MarketAugmentedBlindFeatureRecord,
    V04MarketAugmentedModelingDataset,
    V04MarketAugmentedModelingRecord,
)
from ipo_risk.schemas.modeling import V04BlindFeatureRecord, V04ModelingRecord


def _combine(document_vector, market_snapshot) -> V04CombinedFeatureVector:
    market_vector = vectorize_market_snapshot(market_snapshot)
    return V04CombinedFeatureVector(
        document_manifest_hash=document_vector.manifest_hash,
        market_manifest_hash=market_vector.manifest_hash,
        feature_names=document_vector.feature_names + market_vector.feature_names,
        feature_values=document_vector.feature_values + market_vector.feature_values,
    )


def _require_identity(document_row, market_snapshot) -> None:
    if document_row.listing_date is None:
        raise ModelingDatasetJoinError("market feature join requires a listing date")
    mismatches = []
    for name, left, right in (
        ("case_id", document_row.case_id, market_snapshot.case_id),
        ("stock_code", document_row.stock_code, market_snapshot.stock_code),
        ("cohort_year", document_row.cohort_year, market_snapshot.cohort_year),
        ("listing_date", document_row.listing_date, market_snapshot.listing_date),
        ("dataset_split", document_row.dataset_split, market_snapshot.dataset_split),
    ):
        if left != right:
            mismatches.append(name)
    if mismatches:
        raise ModelingDatasetJoinError(
            f"document/market-feature join mismatch: {', '.join(mismatches)}"
        )
    if market_snapshot.observation_date is None:
        raise ModelingDatasetJoinError("market feature join requires an observation date")


class V04MarketAugmentedDatasetBuilder:
    """Join existing V04-2 records with pre-listing X; never mutate V04-2 V1."""

    def join(
        self,
        document_row: V04ModelingRecord,
        market_snapshot: PreListingMarketFeatureSnapshot,
    ) -> V04MarketAugmentedModelingRecord:
        _require_identity(document_row, market_snapshot)
        if document_row.dataset_split is MarketDatasetSplit.BLIND:
            raise BlindDataLeakageError("blind outcomes cannot enter market-augmented modeling")
        vector = _combine(document_row.feature_vector, market_snapshot)
        return V04MarketAugmentedModelingRecord(
            case_id=document_row.case_id,
            document_id=document_row.document_id,
            stock_code=document_row.stock_code,
            cohort_year=document_row.cohort_year,
            listing_date=document_row.listing_date,
            dataset_split=document_row.dataset_split,
            security_type=document_row.security_type,
            eligibility_policy_version=document_row.eligibility_policy_version,
            label_horizon=document_row.label_horizon,
            feature_vector=vector,
            outcome_label=document_row.outcome_label,
            source_analysis_id=document_row.source_analysis_id,
            document_snapshot_hash=document_row.snapshot_hash,
            market_snapshot_hash=market_snapshot.content_hash(),
            document_pipeline_version=document_row.document_pipeline_version,
            document_pipeline_commit=document_row.document_pipeline_commit,
            workflow_version=document_row.workflow_version,
            schema_version=document_row.schema_version,
            document_feature_schema_version=document_row.feature_schema_version,
            document_manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            market_feature_schema_version=market_snapshot.market_feature_schema_version,
            market_manifest_hash=MARKET_FEATURE_MANIFEST_V1.content_hash(),
            market_policy_version=market_snapshot.feature_policy_version,
            market_observation_date=market_snapshot.observation_date,
            market_label_policy_version=document_row.market_label_policy_version,
            market_split_policy_version=document_row.market_split_policy_version,
        )

    def build_development(
        self,
        pairs: Iterable[tuple[V04ModelingRecord, PreListingMarketFeatureSnapshot]],
    ) -> V04MarketAugmentedModelingDataset:
        return self._build(pairs, MarketDatasetSplit.DEVELOPMENT)

    def build_validation(
        self,
        pairs: Iterable[tuple[V04ModelingRecord, PreListingMarketFeatureSnapshot]],
    ) -> V04MarketAugmentedModelingDataset:
        return self._build(pairs, MarketDatasetSplit.VALIDATION)

    def _build(self, pairs, required_split) -> V04MarketAugmentedModelingDataset:
        rows = []
        for document_row, market_snapshot in pairs:
            if document_row.dataset_split is MarketDatasetSplit.BLIND:
                raise BlindDataLeakageError("2025 outcome cannot enter an augmented dataset")
            if document_row.dataset_split is not required_split:
                raise ModelingDatasetJoinError(
                    f"{document_row.case_id} is not {required_split.value} data"
                )
            rows.append(self.join(document_row, market_snapshot))
        rows.sort(key=lambda row: (row.case_id, row.label_horizon.value))
        return V04MarketAugmentedModelingDataset(
            dataset_split=required_split,
            document_manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            market_manifest_hash=MARKET_FEATURE_MANIFEST_V1.content_hash(),
            records=tuple(rows),
        )


class V04MarketAugmentedBlindFeatureExporter:
    """Join 2025 document X with pre-listing market X; accepts no label."""

    def export(
        self,
        pairs: Iterable[tuple[V04BlindFeatureRecord, PreListingMarketFeatureSnapshot]],
    ) -> V04MarketAugmentedBlindFeatureDataset:
        rows = []
        for document_row, market_snapshot in pairs:
            _require_identity(document_row, market_snapshot)
            if document_row.dataset_split is not MarketDatasetSplit.BLIND:
                raise ModelingDatasetJoinError(
                    f"{document_row.case_id} is not a blind feature row"
                )
            rows.append(
                V04MarketAugmentedBlindFeatureRecord(
                    case_id=document_row.case_id,
                    document_id=document_row.document_id,
                    stock_code=document_row.stock_code,
                    cohort_year=document_row.cohort_year,
                    listing_date=document_row.listing_date,
                    dataset_split=document_row.dataset_split,
                    security_type=document_row.security_type,
                    eligibility_policy_version=document_row.eligibility_policy_version,
                    source_analysis_id=document_row.source_analysis_id,
                    document_snapshot_hash=document_row.snapshot_hash,
                    market_snapshot_hash=market_snapshot.content_hash(),
                    feature_vector=_combine(document_row.feature_vector, market_snapshot),
                    document_pipeline_version=document_row.document_pipeline_version,
                    document_pipeline_commit=document_row.document_pipeline_commit,
                    market_observation_date=market_snapshot.observation_date,
                    market_policy_version=market_snapshot.feature_policy_version,
                )
            )
        rows.sort(key=lambda row: row.case_id)
        return V04MarketAugmentedBlindFeatureDataset(
            document_manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            market_manifest_hash=MARKET_FEATURE_MANIFEST_V1.content_hash(),
            records=tuple(rows),
        )
