"""Deterministic builder from final IPOAnalysisResult to document snapshot."""

from __future__ import annotations

from datetime import date
from typing import Any

from ipo_risk.domain.risk_codes import V03_RISK_OWNERS
from ipo_risk.modeling.exceptions import (
    DocumentSnapshotValidationError,
    DuplicateAuthoritativeRiskError,
)
from ipo_risk.modeling.features import CANONICAL_V03_RISK_ORDER
from ipo_risk.schemas import IPOAnalysisResult, RiskItem, TaskStatus, VerificationStatus
from ipo_risk.schemas.market import MarketDatasetSplit
from ipo_risk.schemas.modeling import (
    DocumentRiskFeature,
    DocumentRiskFeatureState,
    DocumentRiskSnapshotBuildContext,
    V03DocumentRiskSnapshot,
)


_GLOBAL_RISK_FAILURE_COMPONENTS = {
    "document_parser",
    "document_retriever",
    "parser",
    "retriever",
    "service",
    "ipoanalysisservice",
    "verifier",
    "supervisor",
    "workflow",
}
_SOURCE_SPLIT_ALIASES = {"blind_test": MarketDatasetSplit.BLIND.value}


class DocumentRiskSnapshotBuilder:
    """Build a lossless, reproducible view of final v0.3 risk state."""

    def build(
        self,
        result: IPOAnalysisResult,
        context: DocumentRiskSnapshotBuildContext,
    ) -> V03DocumentRiskSnapshot:
        self._validate_identity(result, context)
        if result.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
            raise DocumentSnapshotValidationError(
                "analysis result is not in a final status"
            )

        buckets = self._collect_final_items(result)
        unavailable = self._unavailable_risk_codes(result)
        risk_features: list[DocumentRiskFeature] = []
        for risk_code in CANONICAL_V03_RISK_ORDER:
            entries = buckets.get(risk_code, [])
            if len(entries) > 1:
                raise DuplicateAuthoritativeRiskError(
                    f"multiple final items for canonical risk {risk_code}"
                )
            if entries:
                bucket, risk = entries[0]
                risk_features.append(self._from_risk(bucket, risk))
            else:
                is_unavailable = risk_code in unavailable
                risk_features.append(
                    DocumentRiskFeature(
                        risk_code=risk_code,
                        owner=V03_RISK_OWNERS[risk_code],
                        state=(
                            DocumentRiskFeatureState.UNAVAILABLE
                            if is_unavailable
                            else DocumentRiskFeatureState.NOT_EMITTED
                        ),
                        evidence_count=0,
                        has_calculation=False,
                        missing_reason=(
                            "source_component_unavailable"
                            if is_unavailable
                            else "no_final_risk_item"
                        ),
                    )
                )

        unknown = tuple(sorted(set(buckets) - set(CANONICAL_V03_RISK_ORDER)))
        prediction_version = (
            result.prediction.model_version if result.prediction is not None else None
        )
        return V03DocumentRiskSnapshot(
            case_id=context.case_id,
            document_id=context.document_id,
            stock_code=context.stock_code,
            cohort_year=context.cohort_year,
            listing_date=context.listing_date,
            dataset_split=context.dataset_split,
            official_ipo_universe_member=context.official_ipo_universe_member,
            security_type=context.security_type,
            modeling_eligibility=context.modeling_eligibility,
            eligibility_reason=context.eligibility_reason,
            eligibility_policy_version=context.eligibility_policy_version,
            workflow_version=result.workflow_version,
            schema_version=result.schema_version,
            document_pipeline_version=context.document_pipeline_version,
            document_pipeline_commit=context.document_pipeline_commit.lower(),
            feature_schema_version=context.feature_schema_version,
            source_analysis_id=result.analysis_id,
            source_analysis_status=result.status.value,
            generated_from_result_version=result.schema_version,
            risk_features=tuple(risk_features),
            unknown_risk_codes=unknown,
            conflict_count=self._conflict_count(result),
            rule_predictor_version=prediction_version,
        )

    def _collect_final_items(
        self, result: IPOAnalysisResult
    ) -> dict[str, list[tuple[str, RiskItem]]]:
        grouped: dict[str, list[tuple[str, RiskItem]]] = {}
        for bucket, risks in (
            ("verified", result.verified_risks),
            ("pending", result.pending_risks),
            ("rejected", result.rejected_risks),
        ):
            for risk in risks:
                self._validate_bucket_state(bucket, risk)
                if risk.risk_code in V03_RISK_OWNERS:
                    expected_owner = V03_RISK_OWNERS[risk.risk_code]
                    if risk.category.value != expected_owner:
                        raise DocumentSnapshotValidationError(
                            f"{risk.risk_code} category does not match authoritative owner"
                        )
                grouped.setdefault(risk.risk_code, []).append((bucket, risk))
        return grouped

    @staticmethod
    def _validate_bucket_state(bucket: str, risk: RiskItem) -> None:
        allowed = {
            "verified": {VerificationStatus.VERIFIED},
            "pending": {VerificationStatus.PENDING, VerificationStatus.NEEDS_REVIEW},
            "rejected": {VerificationStatus.REJECTED},
        }[bucket]
        if risk.verification_status not in allowed:
            raise DocumentSnapshotValidationError(
                f"risk {risk.risk_id} state conflicts with {bucket} bucket"
            )

    @staticmethod
    def _from_risk(bucket: str, risk: RiskItem) -> DocumentRiskFeature:
        state = {
            "verified": DocumentRiskFeatureState.VERIFIED,
            "rejected": DocumentRiskFeatureState.REJECTED,
            "pending": (
                DocumentRiskFeatureState.NEEDS_REVIEW
                if risk.verification_status is VerificationStatus.NEEDS_REVIEW
                else DocumentRiskFeatureState.PENDING
            ),
        }[bucket]
        return DocumentRiskFeature(
            risk_code=risk.risk_code,
            owner=V03_RISK_OWNERS[risk.risk_code],
            state=state,
            score=risk.score,
            level=risk.level.value,
            confidence=risk.confidence,
            evidence_count=len(risk.evidence),
            has_calculation=risk.calculation is not None,
            calculation_success=(
                risk.calculation.success if risk.calculation is not None else None
            ),
            source_risk_id=risk.risk_id,
        )

    def _validate_identity(
        self,
        result: IPOAnalysisResult,
        context: DocumentRiskSnapshotBuildContext,
    ) -> None:
        if result.stock_code.strip() != context.stock_code:
            raise DocumentSnapshotValidationError("stock_code identity mismatch")
        source_case_id = result.metadata.get("case_id")
        if source_case_id is not None and source_case_id != context.case_id:
            raise DocumentSnapshotValidationError("case_id identity mismatch")
        document = result.metadata.get("document", {})
        if isinstance(document, dict):
            source_document_id = document.get("document_id")
            if source_document_id is not None and source_document_id != context.document_id:
                raise DocumentSnapshotValidationError("document_id identity mismatch")
        profile = result.metadata.get("ipo_profile", {})
        if isinstance(profile, dict):
            source_listing_date = self._parse_date(profile.get("listing_date"))
            if source_listing_date is not None and source_listing_date != context.listing_date:
                raise DocumentSnapshotValidationError("listing_date identity mismatch")
            source_stock = profile.get("stock_code")
            if source_stock and source_stock != context.stock_code:
                raise DocumentSnapshotValidationError("profile stock_code identity mismatch")
        source_split = result.metadata.get("dataset_split")
        if source_split is not None:
            normalized = _SOURCE_SPLIT_ALIASES.get(str(source_split), str(source_split))
            if normalized != context.dataset_split.value:
                raise DocumentSnapshotValidationError("dataset split identity mismatch")

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if value in {None, ""}:
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise DocumentSnapshotValidationError(
                "source listing_date is not ISO-8601"
            ) from exc

    def _unavailable_risk_codes(self, result: IPOAnalysisResult) -> set[str]:
        if result.status is TaskStatus.FAILED:
            return set(CANONICAL_V03_RISK_ORDER)
        unavailable: set[str] = set()
        for error in result.errors:
            component = error.component.lower()
            risk_code = error.context.get("risk_code")
            if risk_code in V03_RISK_OWNERS:
                unavailable.add(str(risk_code))
                continue
            owner = self._owner_from_component(component)
            if owner is not None:
                unavailable.update(
                    code for code, expected_owner in V03_RISK_OWNERS.items()
                    if expected_owner == owner
                )
            elif component in _GLOBAL_RISK_FAILURE_COMPONENTS:
                unavailable.update(CANONICAL_V03_RISK_ORDER)

        modes = result.metadata.get("component_modes", {})
        if isinstance(modes, dict):
            for owner in {"financial", "legal", "business"}:
                if modes.get(f"{owner}_agent") == "unavailable":
                    unavailable.update(
                        code for code, expected_owner in V03_RISK_OWNERS.items()
                        if expected_owner == owner
                    )
        diagnostics = result.metadata.get("component_diagnostics", {})
        if isinstance(diagnostics, dict):
            for owner in {"financial", "legal", "business"}:
                details = diagnostics.get(owner)
                if isinstance(details, dict) and details.get("failed") is True:
                    unavailable.update(
                        code for code, expected_owner in V03_RISK_OWNERS.items()
                        if expected_owner == owner
                    )
            for component in ("verifier", "supervisor"):
                details = diagnostics.get(component)
                if isinstance(details, dict) and details.get("failed") is True:
                    unavailable.update(CANONICAL_V03_RISK_ORDER)
        return unavailable

    @staticmethod
    def _owner_from_component(component: str) -> str | None:
        for owner in ("financial", "legal", "business"):
            if component == owner or component.startswith(f"{owner}_"):
                return owner
        return None

    @staticmethod
    def _conflict_count(result: IPOAnalysisResult) -> int | None:
        supervision = result.metadata.get("supervision")
        if not isinstance(supervision, dict) or supervision.get("failed") is True:
            return None
        conflicts = supervision.get("conflicts")
        return len(conflicts) if isinstance(conflicts, list) else None
