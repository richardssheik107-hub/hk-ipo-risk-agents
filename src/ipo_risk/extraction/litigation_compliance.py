"""Unified litigation and compliance extraction with deterministic normalization."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from ipo_risk.agents.legal_models import LitigationComplianceCandidate
from ipo_risk.extraction.legal_matter_classifier import (
    LegalMatterEvidenceKind,
    classify_legal_matter_evidence,
)
from ipo_risk.extraction.models import ExtractionStatus, LegalMatterObservation
from ipo_risk.providers.base import LLMProvider
from ipo_risk.schemas import Evidence


_MATTER_TYPE_ALIASES = {
    "none": "none",
    "no_actual_matter": "none",
    "no_material_matter": "none",
    "不存在重大事项": "none",
    "不存在重大事項": "none",
    "litigation": "litigation",
    "material_litigation": "litigation",
    "lawsuit": "litigation",
    "legal_proceeding": "litigation",
    "重大诉讼": "litigation",
    "重大訴訟": "litigation",
    "诉讼": "litigation",
    "訴訟": "litigation",
    "arbitration": "arbitration",
    "仲裁": "arbitration",
    "administrative_penalty": "administrative_penalty",
    "行政处罚": "administrative_penalty",
    "行政處罰": "administrative_penalty",
    "regulatory_investigation": "regulatory_investigation",
    "regulatory_inquiry": "regulatory_investigation",
    "监管调查": "regulatory_investigation",
    "監管調查": "regulatory_investigation",
    "non_compliance": "non_compliance",
    "noncompliance": "non_compliance",
    "不合规": "non_compliance",
    "不合規": "non_compliance",
    "license": "license_permit",
    "licence": "license_permit",
    "permit": "license_permit",
    "license_permit": "license_permit",
    "牌照": "license_permit",
    "许可": "license_permit",
    "許可": "license_permit",
    "tax": "tax",
    "tax_dispute": "tax",
    "税务": "tax",
    "稅務": "tax",
    "environmental_penalty": "environmental_penalty",
    "environmental_non_compliance": "environmental_penalty",
    "环境处罚": "environmental_penalty",
    "環境處罰": "environmental_penalty",
    "data_privacy": "data_privacy",
    "privacy": "data_privacy",
    "数据隐私": "data_privacy",
    "數據隱私": "data_privacy",
}

_STATUS_ALIASES = {
    "pending": "pending",
    "unresolved": "pending",
    "未决": "pending",
    "未決": "pending",
    "尚未解决": "pending",
    "尚未解決": "pending",
    "ongoing": "ongoing",
    "in_progress": "ongoing",
    "仍在进行": "ongoing",
    "仍在進行": "ongoing",
    "resolved": "resolved",
    "settled": "resolved",
    "closed": "resolved",
    "已解决": "resolved",
    "已解決": "resolved",
    "已结案": "resolved",
    "已結案": "resolved",
    "已和解": "resolved",
    "remediated": "remediated",
    "rectified": "remediated",
    "已整改": "remediated",
    "整改完成": "remediated",
    "not_applicable": "not_applicable",
    "no_actual_matter": "not_applicable",
    "无实际事项": "not_applicable",
    "無實際事項": "not_applicable",
}

_CURRENCY_ALIASES = {
    "RMB": "CNY",
    "CNY": "CNY",
    "人民币": "CNY",
    "人民幣": "CNY",
    "HKD": "HKD",
    "港元": "HKD",
    "港币": "HKD",
    "港幣": "HKD",
    "USD": "USD",
    "美元": "USD",
    "EUR": "EUR",
    "欧元": "EUR",
    "歐元": "EUR",
}

_MATERIALITY_ALIASES = {
    "material": "material",
    "重大": "material",
    "significant": "material",
    "not_material": "not_material",
    "not_material_to_the_group": "not_material",
    "not_material_to_our_business": "not_material",
    "不重大": "not_material",
    "无重大不利影响": "not_material",
    "無重大不利影響": "not_material",
    "no_material_adverse_effect": "not_material",
}


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _key(value: str) -> str:
    normalized = _compact(value).lower().replace("-", "_").replace("/", "_")
    return re.sub(r"[^\w\u3400-\u9fff]+", "_", normalized).strip("_")


class LitigationComplianceExtractor:
    """Extract every supported legal matter through one typed LLM task."""

    task_name = "litigation_compliance_extract"
    prompt_version = "legal_litigation_compliance_v1"
    max_evidence = 10

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def extract(self, evidence_candidates: Sequence[Evidence]) -> LegalMatterObservation:
        evidence = list(evidence_candidates[: self.max_evidence])
        if not evidence:
            return LegalMatterObservation(
                matter_type="unknown",
                status=ExtractionStatus.NOT_FOUND,
                issues=["evidence_not_found"],
                uncertainty_reason="No litigation or compliance Evidence was supplied.",
                metadata={
                    "task_name": self.task_name,
                    "prompt_version": self.prompt_version,
                },
            )

        classifications = [classify_legal_matter_evidence(item) for item in evidence]
        kinds = {item.kind for item in classifications}
        if kinds and kinds.issubset(
            {
                LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
                LegalMatterEvidenceKind.GENERIC_FUTURE_RISK,
                LegalMatterEvidenceKind.TEMPLATE_STATEMENT,
            }
        ):
            return LegalMatterObservation(
                matter_type="none",
                current_status="not_applicable",
                is_pending=False,
                is_resolved=False,
                is_remediated=False,
                evidence_ids=[item.evidence_id for item in evidence],
                status=ExtractionStatus.EXTRACTED,
                metadata={
                    "task_name": self.task_name,
                    "prompt_version": self.prompt_version,
                    "extraction_short_circuit": "deterministic_no_actual_matter",
                    "evidence_classifications": [
                        item.model_dump(mode="json") for item in classifications
                    ],
                },
            )

        candidate = self.llm_provider.generate_structured(
            task_name=self.task_name,
            prompt_version=self.prompt_version,
            evidence=evidence,
            response_model=LitigationComplianceCandidate,
        )
        if not isinstance(candidate, LitigationComplianceCandidate):
            candidate = LitigationComplianceCandidate.model_validate(candidate)
        result = self.normalize(candidate, evidence)
        result.metadata["evidence_classifications"] = [
            item.model_dump(mode="json") for item in classifications
        ]
        return result

    def normalize(
        self,
        candidate: LitigationComplianceCandidate,
        evidence: Sequence[Evidence],
    ) -> LegalMatterObservation:
        issues: list[str] = []
        uncertainty: list[str] = []

        raw_matter_type = _compact(candidate.matter_type)
        matter_type = _MATTER_TYPE_ALIASES.get(_key(raw_matter_type), "unknown")
        if matter_type == "unknown":
            issues.append("unsupported_matter_type")
            uncertainty.append(f"Unsupported matter type: {raw_matter_type or 'empty'}")

        available_evidence_ids = {item.evidence_id for item in evidence}
        evidence_ids: list[str] = []
        unknown_evidence_ids: list[str] = []
        for evidence_id in candidate.evidence_ids:
            if evidence_id not in available_evidence_ids:
                unknown_evidence_ids.append(evidence_id)
            elif evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
        if unknown_evidence_ids:
            issues.append("unknown_evidence_ids")
            uncertainty.append(
                "Candidate cited Evidence outside the Retriever result: "
                + ", ".join(unknown_evidence_ids)
            )
        if not evidence_ids:
            issues.append("evidence_not_found")
            uncertainty.append("No candidate Evidence ID matched the Retriever result.")

        subject = _compact(candidate.subject)
        counterparty_or_regulator = _compact(candidate.counterparty_or_authority)
        if matter_type != "none" and not subject:
            issues.append("subject_not_identified")
            uncertainty.append("The legal matter subject was not identified.")
        if matter_type != "none" and not counterparty_or_regulator:
            issues.append("counterparty_or_regulator_not_identified")
            uncertainty.append("The counterparty or regulator was not identified.")
        if matter_type != "none" and candidate.event_date is None:
            issues.append("event_date_not_established")
            uncertainty.append("The event date was not established.")

        current_status = _STATUS_ALIASES.get(_key(candidate.current_status), "unknown")
        if matter_type == "none" and current_status == "unknown":
            current_status = "not_applicable"
        if matter_type != "none" and current_status == "unknown":
            issues.append("current_status_not_established")
            uncertainty.append("The current legal matter status was not established.")

        is_pending = candidate.is_pending
        is_resolved = candidate.is_resolved
        is_remediated = candidate.is_remediated
        if current_status in {"pending", "ongoing"} and is_pending is None:
            is_pending = True
        if current_status == "resolved":
            if is_resolved is None:
                is_resolved = True
            if is_pending is None:
                is_pending = False
        if current_status == "remediated" and is_remediated is None:
            is_remediated = True

        status_conflicts: list[str] = []
        if current_status in {"pending", "ongoing"} and is_pending is False:
            status_conflicts.append("pending_status_conflict")
        if current_status == "resolved" and is_resolved is False:
            status_conflicts.append("resolved_status_conflict")
        if current_status == "remediated" and is_remediated is False:
            status_conflicts.append("remediation_status_conflict")
        if is_pending is True and is_resolved is True:
            status_conflicts.append("pending_and_resolved_conflict")
        if matter_type == "none" and (
            current_status != "not_applicable"
            or is_pending is True
            or is_resolved is True
            or is_remediated is True
        ):
            status_conflicts.append("no_actual_matter_conflicts_with_status")
        if status_conflicts:
            issues.extend(status_conflicts)
            uncertainty.append("Legal matter status flags are internally inconsistent.")

        currency = ""
        raw_currency = _compact(candidate.currency)
        if raw_currency:
            currency = _CURRENCY_ALIASES.get(raw_currency.upper()) or _CURRENCY_ALIASES.get(
                raw_currency
            ) or "unknown"
        if candidate.amount is not None and candidate.amount < 0:
            issues.append("amount_negative")
            uncertainty.append("The extracted legal matter amount is negative.")
        if candidate.amount is not None and not currency:
            issues.append("currency_missing_for_amount")
            uncertainty.append("A monetary amount was extracted without a currency.")
        if currency == "unknown":
            issues.append("currency_unsupported")
            uncertainty.append(f"Unsupported currency: {raw_currency}")

        raw_materiality = _compact(candidate.management_materiality)
        management_materiality = _MATERIALITY_ALIASES.get(
            _key(raw_materiality), raw_materiality
        )
        potential_impact = _compact(candidate.potential_impact)
        license_impact = _compact(candidate.license_impact)
        if matter_type != "none" and not management_materiality:
            issues.append("management_materiality_not_established")
            uncertainty.append("Management's materiality assessment was not established.")
        if matter_type != "none" and not potential_impact:
            issues.append("potential_impact_not_established")
            uncertainty.append("The potential impact was not established.")
        if matter_type == "license_permit" and not license_impact:
            issues.append("license_impact_not_established")
            uncertainty.append("The operational impact on the license or permit was not established.")

        llm_uncertainty = _compact(candidate.uncertainty_reason)
        if llm_uncertainty:
            issues.append("llm_reported_uncertainty")
            uncertainty.append(llm_uncertainty)

        status = ExtractionStatus.EXTRACTED
        if issues:
            status = ExtractionStatus.NEEDS_REVIEW
        if not evidence_ids:
            status = ExtractionStatus.NOT_FOUND

        return LegalMatterObservation(
            matter_type=matter_type,
            subject=subject,
            counterparty_or_regulator=counterparty_or_regulator,
            event_date=candidate.event_date,
            amount=candidate.amount,
            currency=currency,
            amount_unit=_compact(candidate.amount_unit),
            current_status=current_status,
            is_pending=is_pending,
            is_resolved=is_resolved,
            is_remediated=is_remediated,
            management_materiality=management_materiality,
            potential_impact=potential_impact,
            license_impact=license_impact,
            evidence_ids=evidence_ids,
            uncertainty_reason=" ".join(uncertainty),
            status=status,
            issues=list(dict.fromkeys(issues)),
            metadata={
                "task_name": self.task_name,
                "prompt_version": self.prompt_version,
                "provider_name": self.llm_provider.name,
                "raw_matter_type": raw_matter_type,
                "raw_current_status": _compact(candidate.current_status),
                "materiality_stated": candidate.materiality_stated,
                "retrieved_evidence_count": len(evidence),
                "unknown_evidence_ids": unknown_evidence_ids,
            },
        )
