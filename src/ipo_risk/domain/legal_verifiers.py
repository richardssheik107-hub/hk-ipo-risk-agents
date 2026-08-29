"""Deterministic legal-domain verifier rules for v0.3 integration."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from ipo_risk.extraction import (
    LegalMatterEvidenceKind,
    classify_legal_matter_evidence,
)
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    VerificationStatus,
)


class LegalVerificationResult(BaseModel):
    """Typed professional-verifier result for the public verifier to route."""

    status: VerificationStatus
    verified_risk: RiskItem | None = None
    reviewed_risk: RiskItem
    issues: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


_RIGHT_TERMS = re.compile(
    r"赎回权|贖回權|清算优先权|清算優先權|反摊薄|反攤薄|优先认购权|優先認購權|"
    r"回购权|回購權|否决权|否決權|董事提名权|董事提名權|特殊权利|特殊權利|"
    r"对赌安排|對賭安排|\bredemption rights?\b|\bliquidation preference\b|"
    r"\banti[- ]dilution(?: right)?\b|\bpre[- ]emptive right\b|\bpre[- ]emption right\b|"
    r"\brepurchase right\b|\bbuyback right\b|\bveto right\b|"
    r"\bdirector nomination right\b|\bspecial rights?\b|"
    r"\bvaluation adjustment mechanism\b|\bVAM\b",
    re.I,
)
_TERMINATION = re.compile(
    r"终止|終止|失效|届满|屆滿|\bterminat(?:e|ed|ion)\b|\bcease[ds]?\b|"
    r"\blapse[ds]?\b|\bexpir(?:e|ed|y)\b",
    re.I,
)
_WAIVER = re.compile(r"豁免|放弃|放棄|\bwaiv(?:e|ed|er)\b", re.I)
_RESTORATION = re.compile(
    r"恢复|恢復|重新生效|重启|重啟|可予行使|再次行使|"
    r"\brestor(?:e|ed|ation)\b|\brev(?:ive|ived)\b|\breinstate[dm]?\b|"
    r"\bresume[ds]?\b|\b(?:become|becomes|became) exercisable\b|"
    r"\bmay (?:again )?be exercised\b",
    re.I,
)
_RESTORATION_NEGATED = re.compile(
    r"不会恢复|不予恢复|不再恢复|不會恢復|不予恢復|不再恢復|"
    r"\b(?:will|shall|would|does) not be restor(?:e|ed)\b|\bnot be reinstated\b",
    re.I,
)
_LISTING = re.compile(r"上市|首次公开发售|首次公開發售|\blisting\b|\bIPO\b", re.I)
_HISTORICAL = re.compile(
    r"历史|歷史|此前|先前|上市前|\bhistorical(?:ly)?\b|\bpreviously\b|"
    r"\bprior to (?:the )?listing\b|\bbefore (?:the )?listing\b",
    re.I,
)
_CURRENT = re.compile(
    r"仍然有效|继续有效|繼續有效|上市后仍|上市後仍|\bremain(?:s|ed)? effective\b|"
    r"\bcontinue[ds]? (?:to be )?effective\b|\bsurvive[ds]? (?:the )?listing\b",
    re.I,
)
_SPECIAL_INVESTOR = re.compile(
    r"投资者|投資者|优先股股东|優先股股東|首次公开发售前|首次公開發售前|"
    r"\binvestors?\b|\bpreferred shareholders?\b|\bpre[- ]IPO\b|\bseries [a-z0-9]+\b",
    re.I,
)
_ORDINARY_RIGHTS = re.compile(
    r"公司章程|組織章程|组织章程|全体股东|全體股東|普通股股东|普通股股東|"
    r"\barticles of association\b|\ball shareholders?\b|\bordinary shareholders?\b",
    re.I,
)

_STATUS_PENDING = re.compile(
    r"未决|未決|仍在审理|仍在審理|仍在进行|仍在進行|尚未解决|尚未解決|"
    r"\bpending\b|\bongoing\b|\bremain(?:s|ed)? unresolved\b",
    re.I,
)
_STATUS_RESOLVED = re.compile(
    r"已结案|已結案|已和解|已经和解|已解决|已解決|\bresolved\b|\bsettled\b|\bclosed\b",
    re.I,
)
_STATUS_REMEDIATED = re.compile(
    r"已整改|整改完成|完成整改|\bremediated\b|\brectified\b|\bremediation (?:was |is )?completed\b",
    re.I,
)
_NOT_MATERIAL = re.compile(
    r"不重大|无重大不利影响|無重大不利影響|\bnot material\b|"
    r"\bno material adverse (?:effect|impact)\b",
    re.I,
)
_MATERIAL = re.compile(
    r"重大|重大性|显著|顯著|\bmaterial\b|\bsignificant\b",
    re.I,
)
_LICENSE = re.compile(r"牌照|许可证|許可證|许可|許可|\blicen[cs]e\b|\bpermit\b", re.I)
_LICENSE_UNRESOLVED = re.compile(
    r"尚未续期|尚未續期|未获续期|未獲續期|尚未取得|暂停运营|暫停運營|"
    r"\bnot (?:yet )?renewed\b|\bhas not (?:yet )?been renewed\b|\bnot yet obtained\b|"
    r"\bsuspend(?:ed|s|ing)? operations?\b|\boperations? may be suspended\b",
    re.I,
)
_LICENSE_CLEARED = re.compile(
    r"已续期|已續期|已取得|无运营影响|無運營影響|\bhas been renewed\b|"
    r"\bwas renewed\b|\bno operational impact\b",
    re.I,
)
_IMPACT = re.compile(
    r"重大影响|重大影響|经营影响|經營影響|运营影响|運營影響|业务中断|業務中斷|"
    r"罚款|罰款|损失|損失|\bmaterial impact\b|\boperational impact\b|"
    r"\bbusiness interruption\b|\bfine\b|\bpenalty\b|\bloss(?:es)?\b",
    re.I,
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


class _LegalVerifierBase:
    policy_version = "v03_legal_verifier_rules_v1"

    @staticmethod
    def _record(
        checks: dict[str, bool],
        issues: list[str],
        name: str,
        passed: bool,
        issue: str,
    ) -> None:
        checks[name] = passed
        if not passed:
            issues.append(issue)

    def _resolve_evidence(
        self,
        risk: RiskItem,
        available_evidence: Mapping[str, Evidence],
        checks: dict[str, bool],
        issues: list[str],
    ) -> list[Evidence]:
        self._record(checks, issues, "evidence_present", bool(risk.evidence), "evidence_missing")
        resolved: list[Evidence] = []
        seen: set[str] = set()
        for embedded in risk.evidence:
            available = available_evidence.get(embedded.evidence_id)
            if available is None:
                issues.append("evidence_unavailable")
                continue
            identity_ok = all(
                getattr(embedded, field) == getattr(available, field)
                for field in ("evidence_id", "document_id", "chunk_id", "page", "source_type")
            )
            text_ok = _normalize(embedded.text) == _normalize(available.text)
            source_ok = available.source_type == EvidenceSourceType.PROSPECTUS
            if not identity_ok:
                issues.append("evidence_identity_mismatch")
            if not text_ok:
                issues.append("evidence_text_mismatch")
            if not source_ok:
                issues.append("evidence_source_type_invalid")
            if identity_ok and text_ok and source_ok and available.evidence_id not in seen:
                seen.add(available.evidence_id)
                resolved.append(available)
        evidence_resolved = len(resolved) == len(risk.evidence) and bool(resolved)
        checks["evidence_resolved"] = evidence_resolved
        if not evidence_resolved:
            issues.append("evidence_set_incomplete")
        document_ids = {item.document_id for item in resolved if item.document_id}
        same_document = len(document_ids) == 1
        self._record(
            checks,
            issues,
            "evidence_same_document",
            same_document,
            "evidence_document_mismatch",
        )
        return resolved

    def _result(
        self,
        risk: RiskItem,
        status: VerificationStatus,
        issues: list[str],
        checks: dict[str, bool],
        verifier_name: str,
    ) -> LegalVerificationResult:
        issues = list(dict.fromkeys(issues))
        notes = (
            f"{verifier_name} {status.value}: " + ", ".join(issues)
            if issues
            else f"{verifier_name} verified the legal Evidence and lifecycle/status conclusion."
        )
        reviewed = risk.model_copy(
            update={
                "verification_status": status,
                "verification_notes": notes,
                "metadata": {
                    **risk.metadata,
                    "legal_verifier": verifier_name,
                    "legal_verifier_policy_version": self.policy_version,
                    "legal_verifier_issues": issues,
                },
            }
        )
        return LegalVerificationResult(
            status=status,
            verified_risk=reviewed if status == VerificationStatus.VERIFIED else None,
            reviewed_risk=reviewed,
            issues=issues,
            checks=checks,
            metadata={
                "verifier_name": verifier_name,
                "policy_version": self.policy_version,
            },
        )


class LegalRightsVerifier(_LegalVerifierBase):
    """Verify special-investor rights and their complete listing lifecycle."""

    risk_code = "redemption_rights"
    verifier_name = "legal_rights_verifier"

    def verify(
        self,
        risk: RiskItem,
        available_evidence: Mapping[str, Evidence],
    ) -> LegalVerificationResult:
        issues: list[str] = []
        checks: dict[str, bool] = {}
        invalid_identity = (
            risk.risk_code != self.risk_code
            or risk.category != RiskCategory.LEGAL
            or risk.agent_name != "legal"
            or risk.metadata.get("canonical_code") != "LEGAL_REDEMPTION_RIGHTS"
        )
        checks["risk_identity"] = not invalid_identity
        if invalid_identity:
            issues.append("legal_rights_risk_identity_invalid")

        evidence = self._resolve_evidence(risk, available_evidence, checks, issues)
        if not risk.evidence or (risk.evidence and not evidence):
            status = (
                VerificationStatus.REJECTED
                if invalid_identity
                else VerificationStatus.PENDING
            )
            return self._result(risk, status, issues, checks, self.verifier_name)

        text = _normalize(" ".join(item.text for item in evidence))
        right_present = bool(_RIGHT_TERMS.search(text))
        lifecycle_present = bool(
            _TERMINATION.search(text)
            or _WAIVER.search(text)
            or _RESTORATION.search(text)
            or _CURRENT.search(text)
        )
        listing_context = bool(_LISTING.search(text))
        special_investor = bool(_SPECIAL_INVESTOR.search(text))
        ordinary_only = bool(_ORDINARY_RIGHTS.search(text)) and not special_investor
        holder = str(risk.metadata.get("holder", "")).strip()
        holder_supported = bool(holder) and _normalize(holder).lower() in text.lower()
        termination = bool(_TERMINATION.search(text) or _WAIVER.search(text))
        restoration = bool(_RESTORATION.search(text)) and not bool(
            _RESTORATION_NEGATED.search(text)
        )
        current = bool(_CURRENT.search(text))
        historical = bool(_HISTORICAL.search(text))

        self._record(checks, issues, "right_clause_present", right_present, "special_right_clause_not_found")
        self._record(checks, issues, "lifecycle_context", lifecycle_present, "termination_waiver_restoration_context_incomplete")
        self._record(checks, issues, "listing_context", listing_context, "listing_timing_not_supported")
        self._record(checks, issues, "holder_supported", holder_supported, "holder_not_supported_by_evidence")
        checks["special_investor_context"] = special_investor and not ordinary_only
        if ordinary_only:
            issues.append("ordinary_articles_right_misclassified_as_special_investor_right")
        elif not special_investor:
            issues.append("special_investor_context_not_established")

        metadata_survives = risk.metadata.get("survives_listing")
        metadata_restoration = risk.metadata.get("restoration_clause")
        lifecycle_conflict = (
            (metadata_survives is True and termination and not restoration and not current)
            or (termination and current and not restoration)
            or (metadata_restoration is False and restoration)
            or (metadata_restoration is True and not restoration)
        )
        checks["lifecycle_consistent"] = not lifecycle_conflict
        if lifecycle_conflict:
            issues.append("conflicting_rights_lifecycle_evidence")

        historical_terminated = historical and termination and not restoration and not current
        if historical_terminated:
            issues.append("historical_terminated_right_presented_as_current")

        human_review = (
            risk.verification_status == VerificationStatus.NEEDS_REVIEW
            or bool(risk.metadata.get("builder_issues"))
            or bool(risk.metadata.get("fact_issues"))
        )
        checks["no_prior_legal_uncertainty"] = not human_review
        if human_review:
            issues.append("manual_legal_judgment_required")

        # A historical right is not automatically a negative finding when the
        # builder has explicitly kept lifecycle uncertainty open for review.
        # Reject only an unsupported *current* presentation; otherwise retain
        # the fail-closed needs-review outcome.
        historical_misstatement = (
            historical_terminated
            and risk.verification_status != VerificationStatus.NEEDS_REVIEW
        )
        if invalid_identity or ordinary_only or historical_misstatement:
            status = VerificationStatus.REJECTED
        elif issues:
            status = VerificationStatus.NEEDS_REVIEW
        else:
            status = VerificationStatus.VERIFIED
        return self._result(risk, status, issues, checks, self.verifier_name)


class LitigationComplianceVerifier(_LegalVerifierBase):
    """Verify actual, current and evidenced litigation/compliance conclusions."""

    risk_code = "material_litigation_compliance"
    verifier_name = "litigation_compliance_verifier"

    def verify(
        self,
        risk: RiskItem,
        available_evidence: Mapping[str, Evidence],
    ) -> LegalVerificationResult:
        issues: list[str] = []
        checks: dict[str, bool] = {}
        invalid_identity = (
            risk.risk_code != self.risk_code
            or risk.category != RiskCategory.LEGAL
            or risk.agent_name != "legal"
            or risk.metadata.get("canonical_code")
            != "LEGAL_MATERIAL_LITIGATION_COMPLIANCE"
        )
        checks["risk_identity"] = not invalid_identity
        if invalid_identity:
            issues.append("litigation_compliance_risk_identity_invalid")

        evidence = self._resolve_evidence(risk, available_evidence, checks, issues)
        if not risk.evidence or (risk.evidence and not evidence):
            status = (
                VerificationStatus.REJECTED
                if invalid_identity
                else VerificationStatus.PENDING
            )
            return self._result(risk, status, issues, checks, self.verifier_name)

        text = _normalize(" ".join(item.text for item in evidence))
        classifications = [classify_legal_matter_evidence(item).kind for item in evidence]
        actual = LegalMatterEvidenceKind.ACTUAL_MATTER in classifications
        negative_or_template = any(
            kind
            in {
                LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
                LegalMatterEvidenceKind.GENERIC_FUTURE_RISK,
                LegalMatterEvidenceKind.TEMPLATE_STATEMENT,
            }
            for kind in classifications
        )
        only_negative_or_template = bool(classifications) and all(
            kind
            in {
                LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
                LegalMatterEvidenceKind.GENERIC_FUTURE_RISK,
                LegalMatterEvidenceKind.TEMPLATE_STATEMENT,
            }
            for kind in classifications
        )
        pending = bool(_STATUS_PENDING.search(text))
        resolved = bool(_STATUS_RESOLVED.search(text))
        remediated = bool(_STATUS_REMEDIATED.search(text))
        not_material = bool(_NOT_MATERIAL.search(text))
        material = bool(_MATERIAL.search(text)) and not not_material
        historical = bool(_HISTORICAL.search(text))
        license_matter = risk.metadata.get("matter_type") == "license_permit"
        license_unresolved = bool(_LICENSE_UNRESOLVED.search(text))
        license_cleared = bool(_LICENSE_CLEARED.search(text))
        impact_supported = bool(_IMPACT.search(text))

        checks["actual_matter"] = actual
        if not actual and not only_negative_or_template:
            issues.append("actual_matter_not_established")
        checks["not_only_negative_or_template"] = not only_negative_or_template
        if only_negative_or_template:
            issues.append("general_risk_or_negative_statement_misclassified_as_actual_matter")
        checks["no_conflicting_negative_evidence"] = not (actual and negative_or_template)
        if actual and negative_or_template:
            issues.append("conflicting_actual_and_negative_evidence")

        status_conflict = pending and (resolved or remediated)
        checks["status_consistent"] = not status_conflict
        if status_conflict:
            issues.append("conflicting_matter_status_evidence")
        if not pending and not resolved and not remediated and not license_unresolved:
            issues.append("closure_status_not_established")

        resolved_historical = (resolved or remediated) and not pending
        if resolved_historical:
            issues.append("resolved_or_remediated_matter_presented_as_current")
        if historical and resolved_historical:
            issues.append("historical_resolved_matter_presented_as_current")
        if not_material and resolved_historical:
            issues.append("resolved_non_material_matter_presented_as_current")
        elif not_material and not impact_supported:
            issues.append("management_explicitly_not_material")
        elif not_material and impact_supported:
            issues.append("management_materiality_conflicts_with_impact")

        if license_matter:
            checks["license_mentioned"] = bool(_LICENSE.search(text))
            if not checks["license_mentioned"]:
                issues.append("license_or_permit_not_supported_by_evidence")
            if not license_unresolved and not license_cleared:
                issues.append("license_impact_not_established")
            if license_cleared and not license_unresolved:
                issues.append("resolved_license_impact_presented_as_current")

        matter_type = str(risk.metadata.get("matter_type", ""))
        if matter_type in {
            "administrative_penalty",
            "non_compliance",
            "environmental_penalty",
            "data_privacy",
        }:
            declared_remediated = risk.metadata.get("is_remediated")
            if declared_remediated is None and not remediated:
                issues.append("remediation_status_not_established")
            if declared_remediated is True and not remediated:
                issues.append("remediation_metadata_not_supported_by_evidence")
            if declared_remediated is False and remediated:
                issues.append("remediation_status_conflict")

        declared_pending = risk.metadata.get("is_pending")
        declared_resolved = risk.metadata.get("is_resolved")
        if declared_pending is True and not (pending or license_unresolved):
            issues.append("pending_status_not_supported_by_evidence")
        if declared_resolved is True and not (resolved or remediated or license_cleared):
            issues.append("resolved_status_not_supported_by_evidence")
        if declared_pending is False and pending:
            issues.append("pending_status_conflicts_with_metadata")
        if declared_resolved is False and resolved:
            issues.append("resolved_status_conflicts_with_metadata")

        declared_impact = bool(str(risk.metadata.get("potential_impact", "")).strip())
        if declared_impact and not impact_supported and not license_unresolved:
            issues.append("material_impact_not_supported_by_evidence")
        checks["impact_supported"] = impact_supported or not declared_impact or license_unresolved
        declared_materiality = str(risk.metadata.get("management_materiality", "")).strip()
        if declared_materiality == "material" and not (material or impact_supported or license_unresolved):
            issues.append("materiality_not_supported_by_evidence")
        if declared_materiality == "not_material" and not not_material:
            issues.append("non_materiality_not_supported_by_evidence")

        nonblocking_observation_issues = {
            "subject_not_identified",
            "counterparty_or_regulator_not_identified",
            "potential_impact_not_established",
        }
        substantive_observation_issues = set(
            risk.metadata.get("observation_issues", [])
        ) - nonblocking_observation_issues
        human_review = (
            risk.verification_status == VerificationStatus.NEEDS_REVIEW
            or bool(risk.metadata.get("builder_issues"))
            or bool(substantive_observation_issues)
        )
        checks["no_prior_legal_uncertainty"] = not human_review
        if human_review:
            issues.append("manual_legal_judgment_required")

        rejection_issues = {
            "litigation_compliance_risk_identity_invalid",
            "general_risk_or_negative_statement_misclassified_as_actual_matter",
            "resolved_or_remediated_matter_presented_as_current",
            "historical_resolved_matter_presented_as_current",
            "resolved_non_material_matter_presented_as_current",
            "management_explicitly_not_material",
            "resolved_license_impact_presented_as_current",
        }
        if any(issue in rejection_issues for issue in issues):
            status = VerificationStatus.REJECTED
        elif invalid_identity:
            status = VerificationStatus.REJECTED
        elif issues:
            status = VerificationStatus.NEEDS_REVIEW
        else:
            status = VerificationStatus.VERIFIED
        return self._result(risk, status, issues, checks, self.verifier_name)
