"""Build a traceable cash-runway risk from A3 financial extraction output."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)
from ipo_risk.skills.financial import cash_runway_from_operating_cash_flow


class CashRunwayBuildStatus(StrEnum):
    """Outcome of building the A4 calculation and risk item."""

    BUILT = "built"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class CashRunwayBuildResult(BaseModel):
    """Typed A4 result without changing the public cross-module schemas."""

    status: CashRunwayBuildStatus
    calculation: Calculation | None = None
    risk_item: RiskItem | None = None
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def cash_runway_risk_policy(runway_months: Decimal) -> tuple[RiskLevel, int]:
    """Map an exact cash runway to the shared deterministic v1 policy."""

    if runway_months < Decimal("3"):
        return RiskLevel.CRITICAL, 90
    if runway_months < Decimal("6"):
        return RiskLevel.HIGH, 80
    if runway_months < Decimal("12"):
        return RiskLevel.MEDIUM, 60
    return RiskLevel.LOW, 20


class CashRunwayRiskBuilder:
    """Validate A3 facts, invoke the deterministic Skill, and assemble A4 output."""

    def build(
        self,
        extraction: FinancialExtractionResult,
        evidence_by_id: Mapping[str, Evidence],
    ) -> CashRunwayBuildResult:
        """Build a pending cash-runway risk only when every source relation is proven."""

        cash = extraction.cash_and_cash_equivalents
        cash_flow = extraction.operating_cash_flow
        issues = self._validate_metrics(cash, cash_flow)
        evidence, evidence_issues = self._resolve_evidence(cash, cash_flow, evidence_by_id)
        issues.extend(evidence_issues)
        issues = list(dict.fromkeys(issues))
        if issues:
            return CashRunwayBuildResult(
                status=CashRunwayBuildStatus.NEEDS_REVIEW,
                issues=issues,
                metadata={"validation_stage": "pre_calculation"},
            )

        assert cash.normalized_value is not None
        assert cash_flow.normalized_value is not None
        assert cash_flow.period_months is not None
        assert cash.currency is not None
        assert cash.unit is not None
        assert cash.evidence_id is not None
        assert cash_flow.evidence_id is not None

        if cash_flow.normalized_value >= 0:
            return CashRunwayBuildResult(
                status=CashRunwayBuildStatus.NOT_APPLICABLE,
                issues=["operating_cash_flow_does_not_represent_cash_burn"],
                metadata={
                    "operating_cash_flow": str(cash_flow.normalized_value),
                    "reason": "no_negative_operating_cash_flow",
                },
            )

        evidence_ids = list(dict.fromkeys([cash.evidence_id, cash_flow.evidence_id]))
        skill_result = cash_runway_from_operating_cash_flow(
            cash.normalized_value,
            cash_flow.normalized_value,
            cash_flow.period_months,
            evidence_ids,
            currency=cash.currency,
            source_unit=cash.unit,
        )
        if not skill_result.success:
            return CashRunwayBuildResult(
                status=CashRunwayBuildStatus.NEEDS_REVIEW,
                issues=["cash_runway_skill_failed"],
                metadata={"skill_error": skill_result.error},
            )

        exact_runway = self._decimal(skill_result.value)
        monthly_burn = self._decimal(skill_result.metadata.get("monthly_burn"))
        rounded_runway = self._decimal(skill_result.metadata.get("rounded_months"))
        if exact_runway is None or monthly_burn is None or rounded_runway is None:
            return CashRunwayBuildResult(
                status=CashRunwayBuildStatus.NEEDS_REVIEW,
                issues=["cash_runway_skill_output_invalid"],
            )

        calculation = Calculation(
            skill_name="cash_runway",
            skill_version="1.1",
            inputs={
                "cash": str(cash.normalized_value),
                "operating_cash_flow": str(cash_flow.normalized_value),
                "period_months": cash_flow.period_months,
                "monthly_burn": str(monthly_burn),
                "currency": cash.currency,
                "source_unit": cash.unit,
                "cash_period_end": cash.period_end.isoformat(),
                "operating_cash_flow_period_end": cash_flow.period_end.isoformat(),
            },
            formula="cash / (abs(operating_cash_flow) / period_months)",
            # Persist the exact deterministic value for machine comparison.
            # Rounded output remains available in metadata and the conclusion.
            result=str(exact_runway),
            unit="months",
            evidence_ids=evidence_ids,
            success=True,
            error=None,
        )
        level, score = cash_runway_risk_policy(exact_runway)
        risk_item = RiskItem(
            risk_id=str(
                uuid5(
                    NAMESPACE_URL,
                    "cash-runway:"
                    + ":".join(
                        [
                            *evidence_ids,
                            str(cash.normalized_value),
                            str(cash_flow.normalized_value),
                            str(cash_flow.period_months),
                        ]
                    ),
                )
            ),
            risk_code="cash_runway",
            category=RiskCategory.FINANCIAL,
            risk_type="Insufficient cash runway",
            level=level,
            score=score,
            conclusion=(
                f"Based on reported cash of {cash.normalized_value} {cash.currency} {cash.unit} "
                f"and {cash_flow.period_months}-month operating cash outflow of "
                f"{abs(cash_flow.normalized_value)} {cash.currency} {cash.unit}, the estimated "
                f"cash runway is approximately {rounded_runway} months. This is a deterministic "
                "rule calculation, not a probability of post-listing price decline."
            ),
            evidence=evidence,
            calculation=calculation,
            agent_name="financial",
            confidence=0.90,
            verification_status=VerificationStatus.PENDING,
            verification_notes="",
            metadata={
                "canonical_code": "FIN_CASH_RUNWAY",
                "policy_version": "cash_runway_rule_v1",
                "score_is_rule_based": True,
                "score_is_probability": False,
                "runway_months_exact": str(exact_runway),
                "runway_months_rounded": str(rounded_runway),
                "monthly_burn": str(monthly_burn),
                "currency": cash.currency,
                "source_unit": cash.unit,
                "period_months": cash_flow.period_months,
                "cash_extraction_method": cash.extraction_method,
                "operating_cash_flow_extraction_method": cash_flow.extraction_method,
            },
        )
        return CashRunwayBuildResult(
            status=CashRunwayBuildStatus.BUILT,
            calculation=calculation,
            risk_item=risk_item,
            metadata={"skill_name": skill_result.skill_name, "skill_version": skill_result.skill_version},
        )

    @staticmethod
    def _validate_metrics(
        cash: FinancialMetricValue, cash_flow: FinancialMetricValue
    ) -> list[str]:
        issues: list[str] = []
        if cash.metric_name != "cash_and_cash_equivalents":
            issues.append("cash_metric_name_invalid")
        if cash_flow.metric_name != "operating_cash_flow":
            issues.append("operating_cash_flow_metric_name_invalid")
        if cash.status != ExtractionStatus.EXTRACTED:
            issues.append("cash_status_not_extracted")
        if cash_flow.status != ExtractionStatus.EXTRACTED:
            issues.append("operating_cash_flow_status_not_extracted")
        if cash.issues:
            issues.append("cash_extraction_has_issues")
        if cash_flow.issues:
            issues.append("operating_cash_flow_extraction_has_issues")
        if cash.normalized_value is None:
            issues.append("cash_value_missing")
        elif cash.normalized_value < 0:
            issues.append("cash_value_negative")
        if cash_flow.normalized_value is None:
            issues.append("operating_cash_flow_value_missing")
        if cash_flow.period_months not in range(1, 13):
            issues.append("operating_cash_flow_period_months_invalid")
        if cash.period_months is not None:
            issues.append("cash_period_months_should_be_none")
        if not cash.document_id or not cash_flow.document_id:
            issues.append("source_document_missing")
        elif cash.document_id != cash_flow.document_id:
            issues.append("source_document_mismatch")
        if cash.currency is None or cash_flow.currency is None:
            issues.append("currency_missing")
        elif cash.currency != cash_flow.currency:
            issues.append("currency_mismatch")
        if cash.unit is None or cash_flow.unit is None:
            issues.append("unit_missing")
        elif cash.unit != cash_flow.unit:
            issues.append("unit_mismatch")
        if cash.period_end is None or cash_flow.period_end is None:
            issues.append("period_end_missing")
        elif cash.period_end != cash_flow.period_end:
            issues.append("period_end_mismatch")
        if not cash.evidence_id:
            issues.append("cash_evidence_id_missing")
        if not cash_flow.evidence_id:
            issues.append("operating_cash_flow_evidence_id_missing")
        return issues

    @staticmethod
    def _resolve_evidence(
        cash: FinancialMetricValue,
        cash_flow: FinancialMetricValue,
        evidence_by_id: Mapping[str, Evidence],
    ) -> tuple[list[Evidence], list[str]]:
        resolved: list[Evidence] = []
        issues: list[str] = []
        for label, metric in (("cash", cash), ("operating_cash_flow", cash_flow)):
            if not metric.evidence_id:
                continue
            evidence = evidence_by_id.get(metric.evidence_id)
            if evidence is None:
                issues.append(f"{label}_evidence_not_found")
                continue
            mismatch_fields = [
                field
                for field in ("evidence_id", "document_id", "chunk_id", "page")
                if getattr(evidence, field) != getattr(metric, field)
            ]
            if mismatch_fields:
                issues.extend(f"{label}_evidence_{field}_mismatch" for field in mismatch_fields)
                continue
            if evidence.source_type != EvidenceSourceType.PROSPECTUS:
                issues.append("evidence_source_type_invalid")
                continue
            if all(item.evidence_id != evidence.evidence_id for item in resolved):
                resolved.append(evidence)
        if len(resolved) == 2 and resolved[0].document_id != resolved[1].document_id:
            issues.append("evidence_document_mismatch")
        return resolved, issues

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            return value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
