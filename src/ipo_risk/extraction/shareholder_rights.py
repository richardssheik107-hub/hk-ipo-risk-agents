"""Structured LLM candidate extraction followed by deterministic legal normalization."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.extraction.models import ExtractionStatus, ShareholderRightsFact
from ipo_risk.providers.base import LLMProvider
from ipo_risk.schemas import Evidence


_RIGHT_TYPE_ALIASES = {
    "none": "none",
    "no_special_right": "none",
    "no_special_rights": "none",
    "无特殊权利": "none",
    "無特殊權利": "none",
    "redemption_right": "redemption_right",
    "redemption_rights": "redemption_right",
    "赎回权": "redemption_right",
    "贖回權": "redemption_right",
    "liquidation_preference": "liquidation_preference",
    "清算优先权": "liquidation_preference",
    "清算優先權": "liquidation_preference",
    "anti_dilution": "anti_dilution_right",
    "anti_dilution_right": "anti_dilution_right",
    "反摊薄": "anti_dilution_right",
    "反攤薄": "anti_dilution_right",
    "pre_emptive_right": "pre_emptive_right",
    "pre_emption_right": "pre_emptive_right",
    "优先认购权": "pre_emptive_right",
    "優先認購權": "pre_emptive_right",
    "repurchase_right": "repurchase_right",
    "buyback_right": "repurchase_right",
    "回购权": "repurchase_right",
    "回購權": "repurchase_right",
    "veto_right": "veto_right",
    "否决权": "veto_right",
    "否決權": "veto_right",
    "director_nomination_right": "director_nomination_right",
    "董事提名权": "director_nomination_right",
    "董事提名權": "director_nomination_right",
    "special_right": "special_right",
    "special_rights": "special_right",
    "特殊权利": "special_right",
    "特殊權利": "special_right",
    "valuation_adjustment_mechanism": "valuation_adjustment_mechanism",
    "vam": "valuation_adjustment_mechanism",
    "对赌安排": "valuation_adjustment_mechanism",
    "對賭安排": "valuation_adjustment_mechanism",
}

_RESTORATION_TERMS = (
    "restore", "restored", "revive", "revived", "reinstated", "resume", "resumed",
    "恢复", "恢復", "重新生效", "自动恢复", "自動恢復",
)
_EXPLICITLY_INACTIVE_TERMS = (
    "已失效", "已終止", "已终止", "不再有效", "ceased to be exercisable",
    "have terminated", "has terminated", "were terminated", "expired as of",
)
_FAILED_LISTING_TERMS = (
    "listing is terminated",
    "listing is withdrawn",
    "listing application is withdrawn",
    "listing fails",
    "listing failure",
    "listing lapses",
    "listing application lapses",
    "上市失败",
    "上市失敗",
    "上市申请失效",
    "上市申請失效",
    "上市申请撤回",
    "上市申請撤回",
    "上市终止",
    "上市終止",
)
_RESTORATIVE_RIGHT_ACTION_TERMS = (
    "require", "repurchase", "purchase their shares", "buy back", "buyback", "redeem",
    "要求", "购回", "購回", "回购", "回購", "赎回", "贖回",
)

_EXPLICIT_SPECIAL_RIGHT = re.compile(
    r"赎回权|贖回權|回购权|回購權|清算优先权|清算優先權|反摊薄|反攤薄|"
    r"对赌安排|對賭安排|特殊权利|特殊權利|\bredemption rights?\b|"
    r"\brepurchase right\b|\bbuyback right\b|\bliquidation preference\b|"
    r"\banti[- ]dilution(?: right)?\b|\bspecial rights?\b|"
    r"\bvaluation adjustment mechanism\b|\bVAM\b",
    re.I,
)
_EXPLICIT_GRANTED_STANDARD_RIGHT = re.compile(
    r"(?:授予|授出|獲授|获授|享有|擁有|拥有|持有).{0,80}(?:特别权利|特別權利)|"
    r"(?:撤资权|撤資權)",
    re.I | re.S,
)
_EXPLICIT_NEGATED_STANDARD_RIGHT = re.compile(
    r"(?:並無|并无|概無|概无|沒有|没有|不會|不会).{0,80}"
    r"(?:特别权利|特別權利|撤资权|撤資權)|"
    r"(?:無|无).{0,24}(?:任何|其他).{0,16}(?:特别权利|特別權利)|"
    r"\b(?:no|not (?:have|hold|enjoy))\b.{0,40}\bspecial rights?\b",
    re.I | re.S,
)
_MANAGEMENT_ADVISER_TERMINATION = re.compile(r"終止|终止", re.I)
_MANAGEMENT_ADVISER_RIGHT_AFTER_TERMINATION = re.compile(
    r"^[\s，,、:：]*(?:其|該|该)?\s*(?:管理顧問權|管理顾问权)", re.I
)
_NEGATED_TERMINATION_PREFIX = re.compile(
    r"(?:並無|并无|概無|概无|沒有|没有|尚未|未曾|並未|并未|"
    r"不會|不会|不予|未予).{0,8}$",
    re.I | re.S,
)
_EXPLICIT_SPECIAL_INVESTOR = re.compile(
    r"投资者|投資者|优先股股东|優先股股東|首次公开发售前|首次公開發售前|"
    r"\binvestors?\b|\bpreferred shareholders?\b|\bpre[- ]IPO\b|"
    r"\bseries [a-z0-9]+\b",
    re.I,
)
_EXPLICIT_LISTING_CONTEXT = re.compile(
    r"上市|首次公开发售|首次公開發售|\blisting\b|\bIPO\b",
    re.I,
)
_EXPLICIT_LIFECYCLE_CONTEXT = re.compile(
    r"终止|終止|失效|届满|屆滿|豁免|放弃|放棄|恢复|恢復|重新生效|"
    r"重启|重啟|可予行使|再次行使|仍然有效|继续有效|繼續有效|上市后仍|"
    r"上市後仍|不會[\s\S]{0,8}上市後存續|不会[\s\S]{0,8}上市后存续|"
    r"\bterminat(?:e|ed|ion)\b|\bcease[ds]?\b|\blapse[ds]?\b|"
    r"\bexpir(?:e|ed|y)\b|\bwaiv(?:e|ed|er)\b|\brestor(?:e|ed|ation)\b|"
    r"\brev(?:ive|ived)\b|\breinstate[dm]?\b|\bresume[ds]?\b|"
    r"\bremain(?:s|ed)? effective\b|\bcontinue[ds]? (?:to be )?effective\b|"
    r"\bsurvive[ds]? (?:the )?listing\b",
    re.I,
)
_EXPLICIT_REVIEW_SUPPORT_RIGHT = re.compile(
    _EXPLICIT_SPECIAL_RIGHT.pattern
    + r"|特别权利|特別權利|优先购买权|優先購買權|优先认购权|優先認購權|"
    r"随售权|隨售權|否决权|否決權|董事提名权|董事提名權|"
    r"\bright of first refusal\b|\bpre[- ]emptive rights?\b|\bveto rights?\b|"
    r"\bdirector nomination rights?\b",
    re.I,
)
_MAX_EXPLICIT_PRIMARY_EVIDENCE = 5
_MAX_EXPLICIT_SUPPORTING_EVIDENCE = 2


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def _key(value: str) -> str:
    normalized = _compact(value).lower().replace("-", "_").replace("/", "_")
    return re.sub(r"[^\w\u3400-\u9fff]+", "_", normalized).strip("_")


def _contains(value: str, terms: Sequence[str]) -> bool:
    normalized = _compact(value).lower()
    return any(_compact(term).lower() in normalized for term in terms)


def _describes_failed_listing_restoration(value: str) -> bool:
    """Recognize an explicit contingent right, not generic listing termination."""

    return _contains(value, _FAILED_LISTING_TERMS) and _contains(
        value, _RESTORATIVE_RIGHT_ACTION_TERMS
    )


def _has_terminated_management_adviser_right(value: str) -> bool:
    """Bind an affirmative termination token to a nearby adviser-right mention."""

    for clause in re.split(r"[；;。.!?！？\r\n]+", value):
        for termination in _MANAGEMENT_ADVISER_TERMINATION.finditer(clause):
            after = clause[termination.end() : termination.end() + 16]
            if not _MANAGEMENT_ADVISER_RIGHT_AFTER_TERMINATION.search(after):
                continue
            negation_window = clause[
                max(0, termination.start() - 12) : termination.start()
            ]
            if _NEGATED_TERMINATION_PREFIX.search(negation_window):
                continue
            return True
    return False


def _has_explicit_special_right(value: str) -> bool:
    """Accept established signals or an affirmatively granted standard right."""

    if _EXPLICIT_SPECIAL_RIGHT.search(value):
        return True
    if _has_terminated_management_adviser_right(value):
        return True
    return bool(
        _EXPLICIT_GRANTED_STANDARD_RIGHT.search(value)
        and not _EXPLICIT_NEGATED_STANDARD_RIGHT.search(value)
    )


class ShareholderRightsExtractor:
    """Ask an LLM for typed facts, then normalize them without making a risk decision."""

    task_name = "shareholder_rights_extract"
    prompt_version = "legal_shareholder_rights_v1"
    max_evidence = 10
    explicit_review_max_evidence = 20

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def extract(self, evidence_candidates: Sequence[Evidence]) -> ShareholderRightsFact:
        evidence = list(evidence_candidates[: self.max_evidence])
        if not evidence:
            return ShareholderRightsFact(
                right_type="unknown",
                status=ExtractionStatus.NOT_FOUND,
                issues=["evidence_not_found"],
                uncertainty_reason="No shareholder-rights Evidence was supplied.",
                metadata={
                    "task_name": self.task_name,
                    "prompt_version": self.prompt_version,
                },
            )

        candidate = self.llm_provider.generate_structured(
            task_name=self.task_name,
            prompt_version=self.prompt_version,
            evidence=evidence,
            response_model=ShareholderRightCandidate,
        )
        if not isinstance(candidate, ShareholderRightCandidate):
            candidate = ShareholderRightCandidate.model_validate(candidate)
        return self.normalize(candidate, evidence)

    def extract_explicit_needs_review(
        self, evidence_candidates: Sequence[Evidence]
    ) -> ShareholderRightsFact | None:
        """Preserve only a strong explicit rights signal when the provider is absent.

        This fail-closed path deliberately does not infer the holder, effectiveness,
        survival, termination timing, or restoration status.  It merely keeps a
        same-Evidence conjunction of a special right, a special-investor context,
        Listing context, and lifecycle language available for legal review.
        """

        review_evidence = evidence_candidates[: self.explicit_review_max_evidence]
        matched = [
            item
            for item in review_evidence
            if _has_explicit_special_right(item.text)
            and _EXPLICIT_SPECIAL_INVESTOR.search(item.text)
            and _EXPLICIT_LISTING_CONTEXT.search(item.text)
            and _EXPLICIT_LIFECYCLE_CONTEXT.search(item.text)
        ]
        if not matched:
            return None
        primary = matched[:_MAX_EXPLICIT_PRIMARY_EVIDENCE]
        matched_ids = {item.evidence_id for item in matched}
        supporting = [
            item
            for item in review_evidence
            if item.evidence_id not in matched_ids
            and _EXPLICIT_REVIEW_SUPPORT_RIGHT.search(item.text)
            and _EXPLICIT_SPECIAL_INVESTOR.search(item.text)
            and _EXPLICIT_LISTING_CONTEXT.search(item.text)
        ][:_MAX_EXPLICIT_SUPPORTING_EVIDENCE]
        selected = [*primary, *supporting]
        right_type = (
            "redemption_right"
            if any(
                re.search(
                    r"赎回权|贖回權|回购权|回購權|\bredemption rights?\b|"
                    r"\brepurchase right\b|\bbuyback right\b",
                    item.text,
                    re.I,
                )
                for item in selected
            )
            else "special_right"
        )
        return ShareholderRightsFact(
            right_type=right_type,
            evidence_ids=[item.evidence_id for item in selected],
            uncertainty_reason=(
                "The structured provider is unavailable. Explicit special-right, "
                "investor, Listing, and lifecycle language requires legal review."
            ),
            status=ExtractionStatus.NEEDS_REVIEW,
            issues=[
                "llm_provider_unavailable",
                "deterministic_explicit_right_signal_only",
                "holder_not_identified",
                "effectiveness_not_established",
                "termination_condition_not_established",
                "restoration_status_not_established",
            ],
            extraction_method="deterministic_explicit_signal_needs_review_v1",
            metadata={
                "task_name": self.task_name,
                "prompt_version": self.prompt_version,
                "provider_name": self.llm_provider.name,
                "fallback_reason": "provider_unavailable",
                "matched_evidence_count": len(matched),
                "primary_evidence_count": len(primary),
                "supporting_evidence_count": len(supporting),
                "selected_evidence_count": len(selected),
            },
        )

    def normalize(
        self,
        candidate: ShareholderRightCandidate,
        evidence: Sequence[Evidence],
    ) -> ShareholderRightsFact:
        issues: list[str] = []
        uncertainty: list[str] = []

        raw_right_type = _compact(candidate.right_type)
        right_type = _RIGHT_TYPE_ALIASES.get(_key(raw_right_type), "unknown")
        if right_type == "unknown":
            issues.append("unsupported_right_type")
            uncertainty.append(f"Unsupported right type: {raw_right_type or 'empty'}")

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

        holder = _compact(candidate.holder)
        if right_type != "none" and not holder:
            issues.append("holder_not_identified")
            uncertainty.append("The rights holder was not identified.")

        legacy_clause = _compact(candidate.trigger_or_termination)
        termination_event = self._termination_event(candidate.termination_event, legacy_clause)
        termination_timing = self._termination_timing(candidate.termination_timing, legacy_clause)
        restoration_condition = _compact(candidate.restoration_condition)
        restoration_clause = candidate.restoration_clause
        restoration_inferred_from_legacy_clause = False
        if restoration_clause is None and (
            restoration_condition or _contains(legacy_clause, _RESTORATION_TERMS)
        ):
            restoration_clause = True
        if restoration_clause is False and _describes_failed_listing_restoration(
            legacy_clause
        ):
            # The typed boolean occasionally contradicts the same structured
            # candidate's explicit contingent repurchase clause.  Canonicalize
            # only this narrow, issuer-agnostic combination; a generic right
            # that merely terminates on listing remains non-restorable.
            restoration_clause = True
            restoration_condition = legacy_clause
            restoration_inferred_from_legacy_clause = True
        if restoration_clause and not restoration_condition:
            if _contains(legacy_clause, _RESTORATION_TERMS):
                restoration_condition = legacy_clause
            else:
                issues.append("restoration_condition_missing")
                uncertainty.append("A restoration clause was indicated without its condition.")

        is_effective = candidate.is_effective
        if is_effective is None and candidate.survives_listing is True:
            is_effective = True
        if is_effective is None and _contains(legacy_clause, _EXPLICITLY_INACTIVE_TERMS):
            is_effective = False
        if is_effective is False and candidate.survives_listing is True:
            issues.append("conflicting_effectiveness_status")
            uncertainty.append("Current effectiveness conflicts with the survives-listing flag.")
        if right_type != "none" and is_effective is None:
            issues.append("effectiveness_not_established")
            uncertainty.append("The current effectiveness of the right was not established.")
        if (
            restoration_clause is None
            and right_type != "none"
            and (is_effective is False or candidate.survives_listing is False)
        ):
            issues.append("restoration_status_not_established")
            uncertainty.append("The Evidence did not establish whether terminated rights can revive.")

        llm_uncertainty = _compact(candidate.uncertainty_reason)
        if llm_uncertainty:
            issues.append("llm_reported_uncertainty")
            uncertainty.append(llm_uncertainty)

        status = ExtractionStatus.EXTRACTED
        if issues:
            status = ExtractionStatus.NEEDS_REVIEW
        if not evidence_ids:
            status = ExtractionStatus.NOT_FOUND

        return ShareholderRightsFact(
            right_type=right_type,
            holder=holder,
            is_effective=is_effective,
            survives_listing=candidate.survives_listing,
            termination_event=termination_event,
            termination_timing=termination_timing,
            restoration_clause=restoration_clause,
            restoration_condition=restoration_condition,
            impact_on_public_shareholders=_compact(candidate.impact_on_public_shareholders),
            evidence_ids=evidence_ids,
            uncertainty_reason=" ".join(uncertainty),
            status=status,
            issues=list(dict.fromkeys(issues)),
            metadata={
                "task_name": self.task_name,
                "prompt_version": self.prompt_version,
                "provider_name": self.llm_provider.name,
                "raw_right_type": raw_right_type,
                "legacy_trigger_or_termination": legacy_clause,
                "survives_listing": candidate.survives_listing,
                "retrieved_evidence_count": len(evidence),
                "unknown_evidence_ids": unknown_evidence_ids,
                "restoration_inferred_from_legacy_clause": (
                    restoration_inferred_from_legacy_clause
                ),
            },
        )

    @staticmethod
    def _termination_event(explicit: str, legacy_clause: str) -> str:
        value = _compact(explicit)
        if value:
            normalized = _key(value)
            if normalized in {"listing", "上市", "全球发售", "全球發售"}:
                return "listing"
            if normalized in {
                "listing_application", "上市申请", "上市申請", "submission_of_listing_application"
            }:
                return "listing_application"
            return value
        clause = _compact(legacy_clause).lower()
        if _contains(clause, ("listing application", "上市申请", "上市申請")):
            return "listing_application"
        if _contains(clause, ("listing", "上市", "global offering", "全球发售", "全球發售")):
            return "listing"
        return ""

    @staticmethod
    def _termination_timing(explicit: str, legacy_clause: str) -> str:
        value = _compact(explicit)
        if value:
            normalized = _key(value)
            aliases = {
                "before_listing": "before_listing",
                "prior_to_listing": "before_listing",
                "上市前": "before_listing",
                "upon_listing": "on_listing",
                "at_listing": "on_listing",
                "on_listing": "on_listing",
                "上市时": "on_listing",
                "上市時": "on_listing",
                "after_listing": "after_listing",
                "上市后": "after_listing",
                "上市後": "after_listing",
                "on_listing_application": "on_listing_application",
                "upon_submission_of_listing_application": "on_listing_application",
                "提交上市申请": "on_listing_application",
                "提交上市申請": "on_listing_application",
                "as_of_last_practicable_date": "as_of_last_practicable_date",
                "截至最后实际可行日期": "as_of_last_practicable_date",
                "截至最後實際可行日期": "as_of_last_practicable_date",
            }
            return aliases.get(normalized, normalized)
        clause = _compact(legacy_clause).lower()
        patterns = (
            (("before listing", "prior to listing", "上市前"), "before_listing"),
            (("upon listing", "at listing", "on listing", "上市时", "上市時"), "on_listing"),
            (("after listing", "上市后", "上市後"), "after_listing"),
            (
                ("upon submission of the listing application", "提交上市申请", "提交上市申請"),
                "on_listing_application",
            ),
            (
                ("as of the latest practicable date", "截至最后实际可行日期", "截至最後實際可行日期"),
                "as_of_last_practicable_date",
            ),
        )
        for terms, normalized in patterns:
            if _contains(clause, terms):
                return normalized
        return ""
