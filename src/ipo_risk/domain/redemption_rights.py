"""Deterministic v0.3 risk builder for special shareholder rights."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from ipo_risk.extraction import ExtractionStatus, ShareholderRightsFact
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


class RedemptionRightsBuildStatus(StrEnum):
    BUILT = "built"
    NEEDS_REVIEW = "needs_review"
    NOT_APPLICABLE = "not_applicable"


class RedemptionRightsBuildResult(BaseModel):
    status: RedemptionRightsBuildStatus
    risk_item: RiskItem | None = None
    diagnostic: ComponentDiagnostic | None = None
    issues: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RedemptionRightsRiskBuilder:
    """Apply the frozen effective-or-restorable policy without verifying the risk."""

    risk_code = "redemption_rights"
    policy_version = "v03_contract_v1"
    provisional_level = RiskLevel.MEDIUM
    provisional_score = 50

    def build(
        self,
        fact: ShareholderRightsFact,
        evidence_by_id: Mapping[str, Evidence],
    ) -> RedemptionRightsBuildResult:
        evidence, evidence_issues = self._resolve_evidence(fact, evidence_by_id)
        issues = list(dict.fromkeys([*fact.issues, *evidence_issues]))

        if fact.status == ExtractionStatus.NOT_FOUND or not evidence:
            if "evidence_not_found" not in issues:
                issues.append("evidence_not_found")
            return self._diagnostic_result(
                RedemptionRightsBuildStatus.NEEDS_REVIEW,
                DiagnosticCode.EVIDENCE_NOT_FOUND,
                "No validated prospectus Evidence supports a shareholder-rights decision.",
                fact,
                issues,
            )

        if fact.right_type == "none":
            no_rights_conflict = (
                fact.is_effective is True
                or fact.survives_listing is True
                or fact.restoration_clause is True
            )
            if no_rights_conflict:
                issues.append("no_special_rights_conflicts_with_status")
            if fact.status != ExtractionStatus.EXTRACTED or issues:
                return self._diagnostic_result(
                    RedemptionRightsBuildStatus.NEEDS_REVIEW,
                    DiagnosticCode.NEEDS_REVIEW,
                    "The no-special-rights finding is incomplete or internally uncertain.",
                    fact,
                    issues or ["no_special_rights_finding_uncertain"],
                )
            return self._diagnostic_result(
                RedemptionRightsBuildStatus.NOT_APPLICABLE,
                DiagnosticCode.NOT_APPLICABLE,
                "The prospectus explicitly states that no special shareholder rights apply.",
                fact,
                [],
            )

        decision, decision_issues = self._decide(fact)
        issues = list(dict.fromkeys([*issues, *decision_issues]))
        if fact.status == ExtractionStatus.NEEDS_REVIEW or issues:
            decision = RedemptionRightsBuildStatus.NEEDS_REVIEW

        if decision == RedemptionRightsBuildStatus.NOT_APPLICABLE:
            return self._diagnostic_result(
                decision,
                DiagnosticCode.NOT_APPLICABLE,
                "The disclosed right terminates by listing and has no restoration clause.",
                fact,
                issues,
            )

        if decision == RedemptionRightsBuildStatus.NEEDS_REVIEW:
            risk_item = self._risk_item(
                fact,
                evidence,
                VerificationStatus.NEEDS_REVIEW,
                "The special shareholder right is disclosed, but its post-listing termination "
                "or restoration status is incomplete or uncertain.",
                issues or ["termination_or_restoration_status_unclear"],
                "ambiguous_terms_require_review",
            )
            return RedemptionRightsBuildResult(
                status=decision,
                risk_item=risk_item,
                diagnostic=ComponentDiagnostic(
                    risk_code=self.risk_code,
                    code=DiagnosticCode.NEEDS_REVIEW,
                    message="Shareholder-rights terms require legal review.",
                    evidence_ids=fact.evidence_ids,
                    metadata={"issues": issues},
                ),
                issues=issues or ["termination_or_restoration_status_unclear"],
                metadata={"policy_version": self.policy_version},
            )

        reason = (
            "restoration_condition_requires_verification"
            if fact.restoration_clause is True
            else "right_survives_listing"
        )
        if fact.restoration_clause is True:
            conclusion = (
                f"The disclosed {fact.right_type} held by {fact.holder} may be restored if "
                f"{fact.restoration_condition}; the conditional legal effect requires verification."
            )
        else:
            conclusion = (
                f"The disclosed {fact.right_type} held by {fact.holder} survives listing; "
                "its legal effect requires verification."
            )
        return RedemptionRightsBuildResult(
            status=RedemptionRightsBuildStatus.BUILT,
            risk_item=self._risk_item(
                fact,
                evidence,
                VerificationStatus.PENDING,
                conclusion,
                [],
                reason,
            ),
            issues=[],
            metadata={"policy_version": self.policy_version, "decision_reason": reason},
        )

    @staticmethod
    def _decide(
        fact: ShareholderRightsFact,
    ) -> tuple[RedemptionRightsBuildStatus, list[str]]:
        if fact.right_type == "unknown":
            return RedemptionRightsBuildStatus.NEEDS_REVIEW, ["right_type_unknown"]
        if fact.survives_listing is True:
            if fact.is_effective is False:
                return RedemptionRightsBuildStatus.NEEDS_REVIEW, [
                    "conflicting_effectiveness_status"
                ]
            return RedemptionRightsBuildStatus.BUILT, []
        if fact.restoration_clause is True:
            if not fact.restoration_condition:
                return RedemptionRightsBuildStatus.NEEDS_REVIEW, [
                    "restoration_condition_missing"
                ]
            return RedemptionRightsBuildStatus.BUILT, []
        if fact.termination_timing == "after_listing":
            return RedemptionRightsBuildStatus.NEEDS_REVIEW, [
                "right_may_remain_effective_after_listing"
            ]
        termination_is_clear = bool(fact.termination_event or fact.termination_timing)
        right_is_terminated = fact.is_effective is False or fact.survives_listing is False
        if termination_is_clear and right_is_terminated and fact.restoration_clause is False:
            return RedemptionRightsBuildStatus.NOT_APPLICABLE, []
        issues: list[str] = []
        if fact.survives_listing is None:
            issues.append("survival_after_listing_not_established")
        if not termination_is_clear:
            issues.append("termination_condition_not_established")
        if fact.restoration_clause is None:
            issues.append("restoration_status_not_established")
        return RedemptionRightsBuildStatus.NEEDS_REVIEW, issues

    def _risk_item(
        self,
        fact: ShareholderRightsFact,
        evidence: list[Evidence],
        verification_status: VerificationStatus,
        conclusion: str,
        issues: list[str],
        decision_reason: str,
    ) -> RiskItem:
        identity = ":".join(
            [
                self.risk_code,
                fact.right_type,
                fact.holder,
                str(fact.is_effective),
                str(fact.survives_listing),
                str(fact.restoration_clause),
                *fact.evidence_ids,
            ]
        )
        return RiskItem(
            risk_id=str(uuid5(NAMESPACE_URL, identity)),
            risk_code=self.risk_code,
            category=RiskCategory.LEGAL,
            risk_type="Special shareholder rights requiring legal verification",
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
                "canonical_code": "LEGAL_REDEMPTION_RIGHTS",
                "policy_version": self.policy_version,
                "decision_reason": decision_reason,
                "level_is_provisional": True,
                "score_is_rule_based": True,
                "score_is_probability": False,
                "right_type": fact.right_type,
                "holder": fact.holder,
                "is_effective": fact.is_effective,
                "survives_listing": fact.survives_listing,
                "termination_event": fact.termination_event,
                "termination_timing": fact.termination_timing,
                "restoration_clause": fact.restoration_clause,
                "restoration_condition": fact.restoration_condition,
                "impact_on_public_shareholders": fact.impact_on_public_shareholders,
                "fact_status": fact.status.value,
                "fact_issues": fact.issues,
                "builder_issues": issues,
                "extraction_method": fact.extraction_method,
            },
        )

    def _diagnostic_result(
        self,
        status: RedemptionRightsBuildStatus,
        code: DiagnosticCode,
        message: str,
        fact: ShareholderRightsFact,
        issues: list[str],
    ) -> RedemptionRightsBuildResult:
        return RedemptionRightsBuildResult(
            status=status,
            diagnostic=ComponentDiagnostic(
                risk_code=self.risk_code,
                code=code,
                message=message,
                evidence_ids=fact.evidence_ids,
                metadata={"issues": issues, "right_type": fact.right_type},
            ),
            issues=issues,
            metadata={"policy_version": self.policy_version},
        )

    @staticmethod
    def _resolve_evidence(
        fact: ShareholderRightsFact,
        evidence_by_id: Mapping[str, Evidence],
    ) -> tuple[list[Evidence], list[str]]:
        resolved: list[Evidence] = []
        issues: list[str] = []
        for evidence_id in fact.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                issues.append("evidence_not_found")
                continue
            if evidence.source_type != EvidenceSourceType.PROSPECTUS:
                issues.append("evidence_source_type_invalid")
                continue
            if evidence.evidence_id not in {item.evidence_id for item in resolved}:
                resolved.append(evidence)
        document_ids = {item.document_id for item in resolved if item.document_id}
        if len(document_ids) > 1:
            issues.append("evidence_document_mismatch")
        return resolved, issues
