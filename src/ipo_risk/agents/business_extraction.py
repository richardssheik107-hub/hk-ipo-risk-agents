"""Deterministic Business facts for the v0.3 pre-commercial rule."""

from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, Field

from ipo_risk.agents.business_models import (
    CommercializationCandidate,
    CoreProductCandidate,
)
from ipo_risk.schemas import Evidence


class BusinessExtractionResult(BaseModel):
    """Internal typed result; frozen public candidate models stay unchanged."""

    commercialization: CommercializationCandidate | None = None
    core_product: CoreProductCandidate | None = None
    is_not_commercialized: bool | None = None
    has_product_revenue: bool | None = None
    revenue_source_types: list[str] = Field(default_factory=list)
    generic_revenue_ambiguous: bool = False
    conflicting_values: bool = False
    factual_evidence_ids: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


_CORE_TERMS = ("核心产品", "核心產品", "core product", "core products")
_NO_PRODUCT_REVENUE = (
    r"尚未.{0,12}(?:从|從)?产品销售产生任何收入",
    r"尚未.{0,12}(?:从|從)?產品銷售產生任何收入",
    r"(?:无|無|未产生|未產生|没有|沒有).{0,12}(?:产品|產品).{0,6}(?:销售|銷售).{0,6}(?:收入|收益)",
    r"no (?:revenue|income) (?:has been )?(?:generated )?from (?:the )?sales? of (?:our )?products?",
    r"no (?:revenue|income) (?:has been )?(?:generated )?from (?:our )?product sales",
    r"have not generated (?:any )?(?:revenue|income) from (?:the )?sales? of (?:our )?products?",
    r"have not generated (?:any )?(?:revenue|income) from (?:our )?product sales",
    r"no (?:product )?sales revenue",
)
_DIRECT_PRODUCT_REVENUE = (
    r"(?:产品|產品)所产生的(?:收入|收益)",
    r"(?:产品|產品)(?:销售|銷售)(?:收入|收益)为",
    r"来自(?:销售|銷售).{0,30}(?:产品|產品)的(?:收入|收益)",
    r"revenue (?:generated |derived )?from (?:the )?sales? of .{0,40}products?",
    r"product sales revenue (?:was|were|amounted|of)",
)
_NOT_COMMERCIALIZED = (
    r"(?:产品|產品).{0,12}尚未获准进行商业销售",
    r"(?:产品|產品).{0,12}尚未獲准進行商業銷售",
    r"(?:尚未|未).{0,12}(?:商业化|商業化|上市销售|上市銷售|商业销售|商業銷售)",
    r"not yet commerciali[sz]ed",
    r"not (?:yet )?(?:launched|available for commercial sale)",
    r"no commerciali[sz]ed products?",
)
_COMMERCIALIZED = (
    r"我们生产及销售.{0,80}(?:产品|產品)",
    r"我們生產及銷售.{0,80}(?:产品|產品)",
    r"(?:已|已经|已經).{0,10}(?:上市销售|上市銷售|商业化|商業化|商业销售|商業銷售)",
    r"(?:commercial sales|commercial sale) (?:have )?(?:commenced|begun)",
    r"(?:has|have|was|were) commercially launched",
    r"we (?:produce|manufacture) and sell .{0,80}products?",
)
_NON_PRODUCT_REVENUE = {
    "licensing": (r"licen[cs](?:e|ing).{0,20}(?:revenue|income)", r"(?:授权|授權|许可|許可).{0,12}(?:收入|收益)"),
    "milestone": (r"milestone.{0,20}(?:revenue|income|payment)", r"里程碑.{0,12}(?:收入|收益|付款)"),
    "rd_service": (r"r\s*&\s*d.{0,12}service.{0,12}(?:revenue|income)", r"研发服务.{0,12}(?:收入|收益)", r"研發服務.{0,12}(?:收入|收益)"),
    "collaboration": (r"collaboration.{0,20}(?:revenue|income)", r"合作.{0,12}(?:收入|收益)"),
    "other_service": (r"other service.{0,12}(?:revenue|income)", r"其他服务.{0,12}(?:收入|收益)", r"其他服務.{0,12}(?:收入|收益)"),
}
_STAGES = (
    ("launched", (r"commercially launched", r"商业销售", r"商業銷售", r"上市销售", r"上市銷售")),
    ("approved", (r"marketing approval", r"获批", r"獲批", r"批准上市")),
    ("registration", (r"\bnda\b", r"\bbla\b", r"nmpa.{0,10}submission", r"注册申请", r"註冊申請")),
    ("phase_iii", (r"phase\s*(?:iii|3)\b", r"(?:临床|臨床)?(?:三期|iii期)")),
    ("phase_ii", (r"phase\s*(?:ii|2)\b", r"(?:临床|臨床)?(?:二期|ii期)")),
    ("phase_i", (r"phase\s*(?:i|1)\b", r"(?:临床|臨床)?(?:一期|i期)")),
    ("preclinical", (r"preclinical", r"临床前", r"臨床前")),
)


def normalize_business_text(text: str) -> str:
    """Normalize PDF whitespace and width while retaining business tokens."""

    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


class DeterministicBusinessExtractor:
    """Extract conservative Business candidates without network access."""

    def extract(self, evidence: list[Evidence]) -> BusinessExtractionResult:
        if not evidence:
            return BusinessExtractionResult(issues=["evidence_not_found"])
        normalized = [(item, normalize_business_text(item.text)) for item in evidence]
        factual = [(item, text) for item, text in normalized if not self._risk_only(item, text)]
        if not factual:
            return BusinessExtractionResult(
                factual_evidence_ids=[], issues=["risk_factor_only"]
            )

        combined = " \n ".join(text for _, text in factual)
        evidence_ids = [item.evidence_id for item, _ in factual]
        product_name = self._product_name(combined)
        is_core = bool(product_name and any(term in combined for term in _CORE_TERMS))
        not_commercialized = self._matches(combined, _NOT_COMMERCIALIZED)
        commercialized = self._matches(combined, _COMMERCIALIZED)
        stage = self._development_stage(
            combined,
            allow_launched=not not_commercialized,
        )
        no_product_revenue = self._matches(combined, _NO_PRODUCT_REVENUE)
        # A negative phrase such as "no revenue from sales of products" also
        # contains the positive lexical core "revenue from sales of products".
        # Remove only complete negative spans before positive detection so a
        # separate affirmative statement still produces a genuine conflict.
        positive_revenue_text = self._without_matches(combined, _NO_PRODUCT_REVENUE)
        direct_product_revenue = self._matches(
            positive_revenue_text, _DIRECT_PRODUCT_REVENUE
        )
        source_types = sorted(
            source
            for source, patterns in _NON_PRODUCT_REVENUE.items()
            if self._matches(combined, patterns)
        )

        issues: list[str] = []
        conflict = bool(
            (not_commercialized and commercialized)
            or (no_product_revenue and direct_product_revenue)
        )
        if conflict:
            issues.append("conflicting_commercialization_or_revenue")

        has_product_revenue: bool | None
        if no_product_revenue and not direct_product_revenue:
            has_product_revenue = False
        elif direct_product_revenue and not no_product_revenue:
            has_product_revenue = True
        else:
            has_product_revenue = None

        generic_revenue = bool(re.search(r"\b(?:revenue|income)\b|收入|收益", combined))
        generic_ambiguous = bool(
            generic_revenue
            and has_product_revenue is None
            and not self._non_product_only(combined, source_types)
        )
        if generic_ambiguous:
            issues.append("generic_revenue_attribution_unclear")
        if not product_name:
            issues.append("core_product_identity_unclear")
        if not stage and not not_commercialized and not commercialized:
            issues.append("commercialization_state_unclear")

        commercialization = CommercializationCandidate(
            product_name=product_name or "unknown",
            development_stage=stage or "unknown",
            has_product_revenue=has_product_revenue,
            commercialization_dependency=";".join(source_types),
            evidence_ids=evidence_ids,
        )
        core_product = (
            CoreProductCandidate(
                product_name=product_name,
                is_core_product=True,
                approval_status=(
                    "approved"
                    if stage == "approved"
                    else "not_approved"
                    if not_commercialized and "获准" in combined or "獲准" in combined
                    else ""
                ),
                launch_status=(
                    "launched"
                    if commercialized and not not_commercialized
                    else "not_launched"
                    if not_commercialized and not commercialized
                    else ""
                ),
                evidence_ids=evidence_ids,
            )
            if is_core
            else None
        )
        return BusinessExtractionResult(
            commercialization=commercialization,
            core_product=core_product,
            is_not_commercialized=(
                True
                if not_commercialized and not commercialized
                else False
                if commercialized and not not_commercialized
                else None
            ),
            has_product_revenue=has_product_revenue,
            revenue_source_types=source_types,
            generic_revenue_ambiguous=generic_ambiguous,
            conflicting_values=conflict,
            factual_evidence_ids=evidence_ids,
            issues=issues,
        )

    @staticmethod
    def _matches(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _without_matches(text: str, patterns: tuple[str, ...]) -> str:
        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _risk_only(evidence: Evidence, text: str) -> bool:
        section = normalize_business_text(evidence.section)
        risk_section = "risk factor" in section or "风险因素" in section or "風險因素" in section
        modal = bool(re.search(r"可能|倘若|若未能|may|could|might|if we fail", text))
        strong = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in (*_NO_PRODUCT_REVENUE, *_DIRECT_PRODUCT_REVENUE, *_NOT_COMMERCIALIZED, *_COMMERCIALIZED)
        )
        return risk_section and modal and not strong

    @staticmethod
    def _product_name(text: str) -> str:
        patterns = (
            r"([a-z][a-z0-9-]{2,})\s*[（(][^）)]{0,30}(?:(?:我们的|我們的)\s*(?:核心产品|核心產品)|our core product)",
            r"(?:核心产品|核心產品|core products?)\s*(?:为|為|是|[:：])?\s*([a-z][a-z0-9-]{2,})",
        )
        for pattern in patterns:
            if match := re.search(pattern, text, re.IGNORECASE):
                return match.group(1).upper()
        return ""

    @staticmethod
    def _development_stage(text: str, *, allow_launched: bool = True) -> str:
        for stage, patterns in _STAGES:
            if stage == "launched" and not allow_launched:
                continue
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return stage
        return ""

    @staticmethod
    def _non_product_only(text: str, source_types: list[str]) -> bool:
        if not source_types:
            return False
        return bool(
            re.search(r"only|solely|仅|僅|全部.{0,10}(?:来自|來自)", text)
            and not re.search(r"产品销售|產品銷售|product sales", text)
        )
