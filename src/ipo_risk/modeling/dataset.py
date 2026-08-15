"""Deterministic V04 modeling joins with strict chronological boundaries."""

from __future__ import annotations

from collections.abc import Iterable

from ipo_risk.market.exceptions import (
    BlindDataLeakageError,
    IneligibleMarketSecurityError,
)
from ipo_risk.market.governance import MarketDatasetSplitPolicy
from ipo_risk.modeling.exceptions import ModelingDatasetJoinError
from ipo_risk.modeling.features import (
    DOCUMENT_FEATURE_MANIFEST_V1,
    vectorize_document_snapshot,
)
from ipo_risk.schemas.market import (
    MarketDatasetSplit,
    MarketOutcomeLabel,
    MarketSecurityEligibility,
)
from ipo_risk.schemas.modeling import (
    V03DocumentRiskSnapshot,
    V04BlindFeatureDataset,
    V04BlindFeatureRecord,
    V04ModelingDataset,
    V04ModelingRecord,
)


class V04ModelingDatasetBuilder:
    """Build only development or validation datasets; blind outcomes are forbidden."""

    def join(
        self,
        snapshot: V03DocumentRiskSnapshot,
        label: MarketOutcomeLabel,
    ) -> V04ModelingRecord:
        self._require_eligible(snapshot)
        mismatches = []
        for name, left, right in (
            ("case_id", snapshot.case_id, label.case_id),
            ("stock_code", snapshot.stock_code, label.stock_code),
            ("cohort_year", snapshot.cohort_year, label.cohort_year),
            ("listing_date", snapshot.listing_date, label.listing_date),
            ("dataset_split", snapshot.dataset_split, label.dataset_split),
        ):
            if left != right:
                mismatches.append(name)
        if mismatches:
            raise ModelingDatasetJoinError(
                f"document/market join mismatch: {', '.join(mismatches)}"
            )
        if snapshot.dataset_split is MarketDatasetSplit.BLIND:
            raise BlindDataLeakageError(
                "2025 outcome labels cannot form a modeling record"
            )
        vector = vectorize_document_snapshot(snapshot)
        return V04ModelingRecord(
            case_id=snapshot.case_id,
            document_id=snapshot.document_id,
            stock_code=snapshot.stock_code,
            cohort_year=snapshot.cohort_year,
            listing_date=snapshot.listing_date,
            dataset_split=snapshot.dataset_split,
            official_ipo_universe_member=snapshot.official_ipo_universe_member,
            security_type=snapshot.security_type,
            eligibility_policy_version=snapshot.eligibility_policy_version,
            label_horizon=label.horizon,
            feature_vector=vector,
            outcome_label=label,
            source_analysis_id=snapshot.source_analysis_id,
            snapshot_hash=snapshot.content_hash(),
            document_pipeline_version=snapshot.document_pipeline_version,
            document_pipeline_commit=snapshot.document_pipeline_commit,
            workflow_version=snapshot.workflow_version,
            schema_version=snapshot.schema_version,
            feature_schema_version=snapshot.feature_schema_version,
            market_label_policy_version=label.label_policy_version,
            market_split_policy_version=MarketDatasetSplitPolicy.version,
        )

    @staticmethod
    def _require_eligible(snapshot: V03DocumentRiskSnapshot) -> None:
        if (
            not snapshot.official_ipo_universe_member
            or snapshot.modeling_eligibility is not MarketSecurityEligibility.ELIGIBLE
        ):
            raise IneligibleMarketSecurityError(
                f"{snapshot.stock_code} is outside the V04 modeling universe: "
                f"{snapshot.eligibility_reason.value}"
            )

    def build_development(
        self,
        pairs: Iterable[tuple[V03DocumentRiskSnapshot, MarketOutcomeLabel]],
    ) -> V04ModelingDataset:
        return self._build(pairs, MarketDatasetSplit.DEVELOPMENT)

    def build_validation(
        self,
        pairs: Iterable[tuple[V03DocumentRiskSnapshot, MarketOutcomeLabel]],
    ) -> V04ModelingDataset:
        return self._build(pairs, MarketDatasetSplit.VALIDATION)

    def _build(
        self,
        pairs: Iterable[tuple[V03DocumentRiskSnapshot, MarketOutcomeLabel]],
        required_split: MarketDatasetSplit,
    ) -> V04ModelingDataset:
        records = []
        for snapshot, label in pairs:
            if snapshot.dataset_split is MarketDatasetSplit.BLIND:
                raise BlindDataLeakageError(
                    "2025 outcome labels cannot enter development or validation datasets"
                )
            if snapshot.dataset_split is not required_split:
                raise ModelingDatasetJoinError(
                    f"{snapshot.case_id} is not {required_split.value} data"
                )
            records.append(self.join(snapshot, label))
        records.sort(key=lambda row: (row.case_id, row.label_horizon.value))
        return V04ModelingDataset(
            dataset_split=required_split,
            manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            records=tuple(records),
        )


class V04BlindFeatureExporter:
    """Export 2025 X only; this API has no label input or target field."""

    def export(
        self, snapshots: Iterable[V03DocumentRiskSnapshot]
    ) -> V04BlindFeatureDataset:
        records: list[V04BlindFeatureRecord] = []
        for snapshot in snapshots:
            V04ModelingDatasetBuilder._require_eligible(snapshot)
            if snapshot.dataset_split is not MarketDatasetSplit.BLIND:
                raise ModelingDatasetJoinError(
                    f"{snapshot.case_id} is not a blind feature row"
                )
            records.append(
                V04BlindFeatureRecord(
                    case_id=snapshot.case_id,
                    document_id=snapshot.document_id,
                    stock_code=snapshot.stock_code,
                    cohort_year=snapshot.cohort_year,
                    listing_date=snapshot.listing_date,
                    dataset_split=snapshot.dataset_split,
                    official_ipo_universe_member=snapshot.official_ipo_universe_member,
                    security_type=snapshot.security_type,
                    eligibility_policy_version=snapshot.eligibility_policy_version,
                    source_analysis_id=snapshot.source_analysis_id,
                    snapshot_hash=snapshot.content_hash(),
                    feature_vector=vectorize_document_snapshot(snapshot),
                    document_pipeline_version=snapshot.document_pipeline_version,
                    document_pipeline_commit=snapshot.document_pipeline_commit,
                )
            )
        records.sort(key=lambda row: row.case_id)
        return V04BlindFeatureDataset(
            manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            records=tuple(records),
        )
