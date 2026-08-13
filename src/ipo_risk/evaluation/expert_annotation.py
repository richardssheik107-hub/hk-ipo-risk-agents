"""Evaluation-only models for blind external-expert annotations."""

from __future__ import annotations

from enum import StrEnum
import math
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


class ExpertExpectedStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ExpertExpectedLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    NOT_APPLICABLE = "not_applicable"


class EvidenceRole(StrEnum):
    PRIMARY = "primary"
    SUPPORTING = "supporting"
    CONTEXT = "context"
    CROSS_CHECK = "cross_check"


class EvidenceRequirement(StrEnum):
    REQUIRED = "required"
    ALTERNATIVE = "alternative"
    SUPPORTING_ONLY = "supporting_only"


class SourceAuthority(StrEnum):
    AUDITED_FINANCIAL_STATEMENT = "audited_financial_statement"
    ACCOUNTANTS_REPORT = "accountants_report"
    FINANCIAL_INFORMATION = "financial_information"
    BUSINESS_SECTION = "business_section"
    LEGAL_DISCLOSURE = "legal_disclosure"
    CORPORATE_STRUCTURE = "corporate_structure"
    PRE_IPO_INVESTMENT = "pre_ipo_investment"
    SUMMARY = "summary"
    RISK_FACTORS = "risk_factors"
    OTHER = "other"


class ExpertRiskAnnotation(BaseModel):
    """One independently assessed risk instance for one prospectus."""

    model_config = ConfigDict(extra="forbid")

    annotation_version: Literal["gpt_expert_v1", "gpt_expert_v1.1"] = "gpt_expert_v1.1"
    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    risk_code: str
    applicable: bool
    expected_status: ExpertExpectedStatus
    expected_level: ExpertExpectedLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)
    calculation_required: bool = False
    calculation_method: str | None = None
    calculation_inputs: dict[str, Any] | None = None
    calculation_result: dict[str, Any] | None = None
    review_outcome: Literal["expert_first_pass"] = "expert_first_pass"
    annotator_type: Literal["external_gpt_expert"] = "external_gpt_expert"

    @model_validator(mode="after")
    def validate_semantics(self) -> "ExpertRiskAnnotation":
        if self.risk_code not in V03_ENABLED_RISK_CODES:
            raise ValueError(f"unsupported active risk_code: {self.risk_code}")
        if self.applicable:
            if self.expected_status == ExpertExpectedStatus.REJECTED:
                raise ValueError("applicable risk cannot have rejected status")
            if self.expected_level == ExpertExpectedLevel.NOT_APPLICABLE:
                raise ValueError("applicable risk cannot have not_applicable level")
        else:
            if self.expected_status != ExpertExpectedStatus.REJECTED:
                raise ValueError("non-applicable risk must have rejected status")
            if self.expected_level != ExpertExpectedLevel.NOT_APPLICABLE:
                raise ValueError("non-applicable risk must have not_applicable level")
        if self.calculation_required and not self.calculation_method:
            raise ValueError("calculation_method is required when calculation_required=true")
        return self


class ExpertEvidenceAnnotation(BaseModel):
    """One evidence record linked to a risk instance."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    risk_code: str
    page: int = Field(ge=1)
    evidence_role: EvidenceRole
    requirement: EvidenceRequirement
    source_authority: SourceAuthority
    exact_text: str = Field(min_length=1)
    evidence_reason: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_risk_code(self) -> "ExpertEvidenceAnnotation":
        if self.risk_code not in V03_ENABLED_RISK_CODES:
            raise ValueError(f"unsupported active risk_code: {self.risk_code}")
        return self


class ExpertAnnotationMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    blind_annotation: Literal[True] = True
    human_golden_visible_to_annotator: Literal[False] = False


class ExpertAnnotationBundle(BaseModel):
    """Complete blind annotation returned for a single case."""

    model_config = ConfigDict(extra="forbid")

    annotation_version: Literal["gpt_expert_v1", "gpt_expert_v1.1"] = "gpt_expert_v1.1"
    case_id: str = Field(min_length=1)
    stock_code: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    risks: list[ExpertRiskAnnotation]
    evidence: list[ExpertEvidenceAnnotation] = Field(default_factory=list)
    metadata: ExpertAnnotationMetadata = Field(default_factory=ExpertAnnotationMetadata)

    @model_validator(mode="after")
    def validate_relationships(self) -> "ExpertAnnotationBundle":
        risk_codes = [risk.risk_code for risk in self.risks]
        if len(risk_codes) != len(set(risk_codes)):
            raise ValueError("risk_code must be unique within a case bundle")
        if set(risk_codes) != set(V03_ENABLED_RISK_CODES):
            missing = sorted(set(V03_ENABLED_RISK_CODES) - set(risk_codes))
            extra = sorted(set(risk_codes) - set(V03_ENABLED_RISK_CODES))
            raise ValueError(f"bundle must assess every active risk code; missing={missing}, extra={extra}")
        for risk in self.risks:
            if (risk.case_id, risk.stock_code, risk.company_name, risk.document_id) != (
                self.case_id,
                self.stock_code,
                self.company_name,
                self.document_id,
            ):
                raise ValueError(f"risk identity mismatch for {risk.risk_code}")
        evidence_by_risk: dict[str, int] = {}
        for item in self.evidence:
            if item.case_id != self.case_id:
                raise ValueError(f"evidence case_id mismatch for {item.risk_code}")
            if item.risk_code not in risk_codes:
                raise ValueError(f"evidence references absent risk: {item.risk_code}")
            evidence_by_risk[item.risk_code] = evidence_by_risk.get(item.risk_code, 0) + 1
        for risk in self.risks:
            if risk.applicable and evidence_by_risk.get(risk.risk_code, 0) == 0:
                raise ValueError(f"applicable risk requires evidence: {risk.risk_code}")
        return self


@dataclass(frozen=True)
class ExpertAnnotationValidationIssue:
    code: str
    path: str
    message: str
    severity: str = "error"


def _number(mapping: dict[str, Any] | None, key: str) -> float | None:
    if not mapping or key not in mapping:
        return None
    try:
        return float(mapping[key])
    except (TypeError, ValueError):
        return None


def calculation_conflicts(bundle: ExpertAnnotationBundle) -> list[ExpertAnnotationValidationIssue]:
    """Report deterministic numeric conflicts; never alter expert semantics."""
    issues: list[ExpertAnnotationValidationIssue] = []
    for index, risk in enumerate(bundle.risks):
        inputs, result = risk.calculation_inputs, risk.calculation_result
        expected: float | None = None
        observed: float | None = None
        if risk.risk_code == "cash_runway":
            cash = _number(inputs, "cash")
            burn = _number(inputs, "monthly_cash_burn")
            observed = _number(result, "months")
            if cash is not None and burn not in (None, 0):
                expected = cash / abs(burn)
        elif risk.risk_code == "revenue_growth":
            current = _number(inputs, "current_revenue")
            previous = _number(inputs, "previous_revenue")
            observed = _number(result, "growth_pct")
            if current is not None and previous not in (None, 0):
                expected = (current - previous) / abs(previous) * 100
        elif risk.risk_code in {"customer_concentration", "supplier_concentration"}:
            numerator = _number(inputs, "numerator")
            denominator = _number(inputs, "denominator")
            observed = _number(result, "ratio_pct")
            if numerator is not None and denominator not in (None, 0):
                expected = numerator / denominator * 100
        elif risk.risk_code == "continuous_loss":
            periods = inputs.get("loss_periods") if inputs else None
            observed = _number(result, "loss_period_count")
            if isinstance(periods, list):
                expected = float(len(periods))
        if expected is not None and observed is not None and not math.isclose(expected, observed, rel_tol=1e-6, abs_tol=1e-6):
            issues.append(ExpertAnnotationValidationIssue(
                code="CALCULATION_CONFLICT",
                path=f"risks[{index}].calculation_result",
                message=f"reported={observed}, deterministic={expected}",
            ))
    return issues


def validate_expert_annotation_payload(
    payload: dict[str, Any], *, page_count: int
) -> tuple[ExpertAnnotationBundle | None, list[ExpertAnnotationValidationIssue]]:
    """Validate schema, relationships, pages, and deterministic calculations."""
    from pydantic import ValidationError

    try:
        bundle = ExpertAnnotationBundle.model_validate(payload)
    except ValidationError as exc:
        return None, [
            ExpertAnnotationValidationIssue("SCHEMA_INVALID", ".".join(map(str, err["loc"])), err["msg"])
            for err in exc.errors()
        ]
    issues = [
        ExpertAnnotationValidationIssue(
            "PAGE_OUT_OF_RANGE",
            f"evidence[{index}].page",
            f"page {item.page} exceeds PDF page count {page_count}",
        )
        for index, item in enumerate(bundle.evidence)
        if item.page > page_count
    ]
    issues.extend(calculation_conflicts(bundle))
    return bundle, issues
