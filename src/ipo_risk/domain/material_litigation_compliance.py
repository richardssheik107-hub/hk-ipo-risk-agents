"""Deterministic v0.3 builder for material litigation and compliance matters."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from ipo_risk.extraction import ExtractionStatus, LegalMatterObservation
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


class MaterialLitigationComplianceBuildStatus(StrEnum):
    BUILT = "built"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class MaterialLitigationComplianceBuildResult(BaseModel):
    status: MaterialLitigationComplianceBuildStatus
    risk_item: RiskItem | None = None
    diagnostic: ComponentDiagnostic | None = None
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MaterialLitigationComplianceRiskBuilder:
    """Apply frozen legal-matter rules without making the final verification decision."""

    risk_code = "material_litigation_compliance"
    policy_version = "v03_contract_v1"
    provisional_level = RiskLevel.MEDIUM
    provisional_score = 50
    proceeding_types = {
        "litigation",
        "arbitration",
        "tax",
        "regulatory_investigation",
    }
    remediation_relevant_types = {
        "administrative_penalty",
        "non_compliance",
        "environmental_penalty",
        "data_privacy",
    }
    integrity_issue_codes = {
        "unsupported_matter_type",
        "unknown_evidence_ids",
        "evidence_not_found",
        "amount_negative",
        "currency_missing_for_amount",
        "currency_unsupported",
        "llm_reported_uncertainty",
        "pending_status_conflict",
        "resolved_status_conflict",
        "remediation_status_conflict",
        "pending_and_resolved_conflict",
        "no_actual_matter_conflicts_with_status",
    }

    def build(
        self,
        observation: LegalMatterObservation,
        evidence_by_id: Mapping[str, Evidence],
    ) -> MaterialLitigationComplianceBuildResult:
        evidence, evidence_issues = self._resolve_evidence(observation, evidence_by_id)
        reported_issues = list(dict.fromkeys([*observation.issues, *evidence_issues]))
        blocking_issues = list(
            dict.fromkeys(
                [
                    *evidence_issues,
                    *(
                        issue
                        for issue in observation.issues
                        if issue in self.integrity_issue_codes
                    ),
                ]
            )
        )

        if observation.status == ExtractionStatus.NOT_FOUND or not evidence:
            if "evidence_not_found" not in reported_issues:
                reported_issues.append("evidence_not_found")
            return self._diagnostic_result(
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                DiagnosticCode.EVIDENCE_NOT_FOUND,
                "No validated prospectus Evidence supports a legal-matter decision.",
                observation,
                reported_issues,
            )

        if observation.matter_type == "none":
            no_matter_conflict = (
                observation.is_pending is True
                or observation.is_resolved is True
                or observation.is_remediated is True
                or observation.current_status != "not_applicable"
            )
            if no_matter_conflict:
                reported_issues.append("no_actual_matter_conflicts_with_status")
                blocking_issues.append("no_actual_matter_conflicts_with_status")
            if observation.status != ExtractionStatus.EXTRACTED or blocking_issues:
                return self._diagnostic_result(
                    MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                    DiagnosticCode.NEEDS_REVIEW,
                    "The no-actual-matter finding is incomplete or internally inconsistent.",
                    observation,
                    reported_issues or ["no_actual_matter_finding_uncertain"],
                )
            return self._diagnostic_result(
                MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE,
                DiagnosticCode.NOT_APPLICABLE,
                "Evidence is an explicit negative statement or generic/template future risk, "
                "not an actual legal matter.",
                observation,
                [],
            )

        decision, decision_reason, decision_issues = self._decide(observation)
        blocking_issues.extend(decision_issues)
        blocking_issues.extend(self._review_signal_issues(observation, decision))
        blocking_issues = list(dict.fromkeys(blocking_issues))
        reported_issues = list(dict.fromkeys([*reported_issues, *blocking_issues]))
        if blocking_issues:
            decision = MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW

        if decision == MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE:
            return self._diagnostic_result(
                decision,
                DiagnosticCode.NOT_APPLICABLE,
                "The disclosed legal matter is clearly resolved, remediated, or expressly "
                "assessed as non-material with no unresolved impact.",
                observation,
                reported_issues,
                decision_reason,
            )

        if decision == MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW:
            review_issues = reported_issues or ["legal_matter_status_or_impact_unclear"]
            risk_item = self._risk_item(
                observation,
                evidence,
                VerificationStatus.NEEDS_REVIEW,
                "An actual legal matter is disclosed, but its identity, closure, remediation, "
                "materiality, or operational impact is not sufficiently established.",
                review_issues,
                decision_reason or "legal_matter_requires_review",
            )
            return MaterialLitigationComplianceBuildResult(
                status=decision,
                risk_item=risk_item,
                diagnostic=ComponentDiagnostic(
                    risk_code=self.risk_code,
                    code=DiagnosticCode.NEEDS_REVIEW,
                    message="The actual legal matter requires further legal review.",
                    evidence_ids=observation.evidence_ids,
                    metadata={"issues": review_issues},
                ),
                issues=review_issues,
                metadata={"policy_version": self.policy_version},
            )

        return MaterialLitigationComplianceBuildResult(
            status=MaterialLitigationComplianceBuildStatus.BUILT,
            risk_item=self._risk_item(
                observation,
                evidence,
                VerificationStatus.PENDING,
                self._pending_conclusion(observation),
                [],
                decision_reason,
            ),
            issues=[],
            metadata={
                "policy_version": self.policy_version,
                "decision_reason": decision_reason,
            },
        )

    def _decide(
        self,
        observation: LegalMatterObservation,
    ) -> tuple[MaterialLitigationComplianceBuildStatus, str, list[str]]:
        pending = observation.is_pending is True or observation.current_status in {
            "pending",
            "ongoing",
        }
        resolved = observation.is_resolved is True or observation.current_status == "resolved"
        remediated = (
            observation.is_remediated is True
            or observation.current_status == "remediated"
        )
        materiality = observation.management_materiality

        if pending and resolved:
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "matter_status_conflict",
                ["pending_and_resolved_conflict"],
            )

        if observation.matter_type == "unknown":
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "matter_type_unclear",
                ["matter_type_unknown"],
            )

        if (
            materiality not in {"material", "not_material"}
            or observation.metadata.get("materiality_stated") is False
        ):
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "matter_materiality_unclear",
                ["management_materiality_not_established"],
            )

        if observation.matter_type in self.proceeding_types:
            return self._decide_proceeding(
                pending=pending,
                resolved=resolved,
                materiality=materiality,
                impact_text=observation.potential_impact,
            )
        if observation.matter_type in self.remediation_relevant_types:
            return self._decide_remediation(
                observation,
                pending=pending,
                resolved=resolved,
                remediated=remediated,
            )
        if observation.matter_type == "license_permit":
            return self._decide_license(
                observation,
                pending=pending,
                resolved=resolved,
            )

        return (
            MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
            "legal_matter_status_unclear",
            ["current_status_not_established"],
        )

    def _decide_proceeding(
        self,
        *,
        pending: bool,
        resolved: bool,
        materiality: str,
        impact_text: str,
    ) -> tuple[MaterialLitigationComplianceBuildStatus, str, list[str]]:
        if resolved and not pending:
            return (
                MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE,
                "matter_resolved",
                [],
            )
        if materiality == "not_material" and self._impact_unclear(impact_text):
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "potential_impact_unclear",
                ["potential_impact_not_established"],
            )
        if materiality == "not_material" and (
            not impact_text or self._impact_cleared(impact_text)
        ):
            return (
                MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE,
                "matter_expressly_not_material_without_continuing_impact",
                [],
            )
        if pending:
            return (
                MaterialLitigationComplianceBuildStatus.BUILT,
                (
                    "material_pending_matter"
                    if materiality == "material"
                    else "impactful_pending_matter"
                ),
                [],
            )
        return (
            MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
            "matter_closure_status_unclear",
            ["current_status_not_established"],
        )

    def _decide_remediation(
        self,
        observation: LegalMatterObservation,
        *,
        pending: bool,
        resolved: bool,
        remediated: bool,
    ) -> tuple[MaterialLitigationComplianceBuildStatus, str, list[str]]:
        if pending or observation.is_remediated is False:
            return (
                MaterialLitigationComplianceBuildStatus.BUILT,
                "unresolved_compliance_or_penalty_matter",
                [],
            )
        if remediated:
            if self._impact_unclear(observation.potential_impact):
                return (
                    MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                    "remediated_matter_impact_unclear",
                    ["potential_impact_not_established"],
                )
            if self._impact_unresolved(observation.potential_impact):
                return (
                    MaterialLitigationComplianceBuildStatus.BUILT,
                    "remediation_completed_but_impact_unresolved",
                    [],
                )
            return (
                MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE,
                "matter_remediated",
                [],
            )
        if resolved:
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "remediation_status_unclear",
                ["remediation_status_not_established"],
            )
        return (
            MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
            "matter_closure_and_remediation_status_unclear",
            ["current_status_not_established", "remediation_status_not_established"],
        )

    def _decide_license(
        self,
        observation: LegalMatterObservation,
        *,
        pending: bool,
        resolved: bool,
    ) -> tuple[MaterialLitigationComplianceBuildStatus, str, list[str]]:
        if not observation.license_impact:
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "license_impact_unclear",
                ["license_impact_not_established"],
            )
        impact_cleared = self._license_impact_cleared(observation.license_impact)
        impact_unresolved = self._license_impact_unresolved(observation.license_impact)
        if impact_unresolved:
            return (
                MaterialLitigationComplianceBuildStatus.BUILT,
                "unresolved_core_license_impact",
                [],
            )
        if resolved and impact_cleared:
            return (
                MaterialLitigationComplianceBuildStatus.NOT_APPLICABLE,
                "license_issue_resolved",
                [],
            )
        if pending and impact_cleared:
            return (
                MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
                "license_status_impact_conflict",
                ["license_status_conflict"],
            )
        if pending:
            return (
                MaterialLitigationComplianceBuildStatus.BUILT,
                "unresolved_core_license_impact",
                [],
            )
        return (
            MaterialLitigationComplianceBuildStatus.NEEDS_REVIEW,
            "license_status_unclear",
            ["license_status_not_established"],
        )

    def _review_signal_issues(
        self,
        observation: LegalMatterObservation,
        decision: MaterialLitigationComplianceBuildStatus,
    ) -> list[str]:
        if decision != MaterialLitigationComplianceBuildStatus.BUILT:
            return []
        if not observation.subject and not observation.counterparty_or_regulator:
            return ["matter_identity_not_established"]
        regulator_required_types = {
            "regulatory_investigation",
            *self.remediation_relevant_types,
            "license_permit",
        }
        if (
            observation.matter_type in regulator_required_types
            and not observation.counterparty_or_regulator
        ):
            return ["regulator_not_identified"]
        return []

    @staticmethod
    def _impact_cleared(value: str) -> bool:
        normalized = value.lower()
        return any(
            term in normalized
            for term in (
                "no continuing impact",
                "no operational impact",
                "no material adverse effect",
                "not material to operations",
                "without continuing impact",
                "无持续影响",
                "無持續影響",
                "无运营影响",
                "無運營影響",
                "无重大不利影响",
                "無重大不利影響",
            )
        )

    @staticmethod
    def _impact_unclear(value: str) -> bool:
        return value.strip().lower() in {
            "unknown",
            "unclear",
            "not established",
            "不清楚",
            "不明确",
            "不明確",
            "未确定",
            "未確定",
        }

    @staticmethod
    def _impact_unresolved(value: str) -> bool:
        normalized = value.lower()
        return any(
            term in normalized
            for term in (
                "continuing impact",
                "ongoing impact",
                "follow-up enforcement",
                "operations remain affected",
                "持续影响",
                "持續影響",
                "后续执法",
                "後續執法",
                "经营仍受影响",
                "經營仍受影響",
            )
        )

    @staticmethod
    def _license_impact_cleared(value: str) -> bool:
        normalized = value.lower()
        return any(
            term in normalized
            for term in (
                "renewed",
                "no operational impact",
                "not affected",
                "unaffected",
                "已续期",
                "已續期",
                "无运营影响",
                "無運營影響",
            )
        ) and not MaterialLitigationComplianceRiskBuilder._license_impact_unresolved(value)

    @staticmethod
    def _license_impact_unresolved(value: str) -> bool:
        normalized = value.lower()
        return any(
            term in normalized
            for term in (
                "not renewed",
                "has not been renewed",
                "suspend",
                "unable to operate",
                "not yet obtained",
                "尚未续期",
                "尚未續期",
                "尚未取得",
                "暂停运营",
                "暫停運營",
            )
        )

    def _risk_item(
        self,
        observation: LegalMatterObservation,
        evidence: list[Evidence],
        verification_status: VerificationStatus,
        conclusion: str,
        issues: list[str],
        decision_reason: str,
    ) -> RiskItem:
        identity = ":".join(
            [
                self.risk_code,
                observation.matter_type,
                observation.subject,
                observation.current_status,
                str(observation.event_date),
                str(observation.amount),
                *observation.evidence_ids,
            ]
        )
        return RiskItem(
            risk_id=str(uuid5(NAMESPACE_URL, identity)),
            risk_code=self.risk_code,
            category=RiskCategory.LEGAL,
            risk_type="Material litigation or compliance matter requiring legal verification",
            level=self.provisional_level,
            score=self.provisional_score,
            conclusion=conclusion,
            evidence=evidence,
            calculation=None,
            agent_name="legal",
            confidence=0.75 if verification_status == VerificationStatus.PENDING else 0.50,
            verification_status=verification_status,
            verification_notes="",
            metadata={
                "canonical_code": "LEGAL_MATERIAL_LITIGATION_COMPLIANCE",
                "policy_version": self.policy_version,
                "decision_reason": decision_reason,
                "level_is_provisional": True,
                "score_is_rule_based": True,
                "score_is_probability": False,
                "matter_type": observation.matter_type,
                "subject": observation.subject,
                "counterparty_or_regulator": observation.counterparty_or_regulator,
                "event_date": (
                    observation.event_date.isoformat() if observation.event_date else None
                ),
                "amount": str(observation.amount) if observation.amount is not None else None,
                "currency": observation.currency,
                "amount_unit": observation.amount_unit,
                "current_status": observation.current_status,
                "is_pending": observation.is_pending,
                "is_resolved": observation.is_resolved,
                "is_remediated": observation.is_remediated,
                "management_materiality": observation.management_materiality,
                "potential_impact": observation.potential_impact,
                "license_impact": observation.license_impact,
                "observation_status": observation.status.value,
                "observation_issues": observation.issues,
                "builder_issues": issues,
                "extraction_method": observation.extraction_method,
            },
        )

    @staticmethod
    def _pending_conclusion(observation: LegalMatterObservation) -> str:
        amount = ""
        if observation.amount is not None:
            amount = (
                f" with a disclosed amount of {observation.amount} "
                f"{observation.currency} {observation.amount_unit}"
            )
        subject = f" concerning {observation.subject}" if observation.subject else ""
        return (
            f"The prospectus discloses an unresolved {observation.matter_type} matter"
            f"{subject}{amount}; its legal and operational effect requires verification."
        )

    def _diagnostic_result(
        self,
        status: MaterialLitigationComplianceBuildStatus,
        code: DiagnosticCode,
        message: str,
        observation: LegalMatterObservation,
        issues: list[str],
        decision_reason: str = "",
    ) -> MaterialLitigationComplianceBuildResult:
        return MaterialLitigationComplianceBuildResult(
            status=status,
            diagnostic=ComponentDiagnostic(
                risk_code=self.risk_code,
                code=code,
                message=message,
                evidence_ids=observation.evidence_ids,
                metadata={"issues": issues, "matter_type": observation.matter_type},
            ),
            issues=issues,
            metadata={
                "policy_version": self.policy_version,
                "decision_reason": decision_reason,
            },
        )

    @staticmethod
    def _resolve_evidence(
        observation: LegalMatterObservation,
        evidence_by_id: Mapping[str, Evidence],
    ) -> tuple[list[Evidence], list[str]]:
        resolved: list[Evidence] = []
        issues: list[str] = []
        seen: set[str] = set()
        for evidence_id in observation.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                issues.append("evidence_not_found")
                continue
            if evidence.source_type != EvidenceSourceType.PROSPECTUS:
                issues.append("evidence_source_type_invalid")
                continue
            if evidence.evidence_id not in seen:
                seen.add(evidence.evidence_id)
                resolved.append(evidence)
        document_ids = {item.document_id for item in resolved if item.document_id}
        if len(document_ids) > 1:
            issues.append("evidence_document_mismatch")
        return resolved, issues
