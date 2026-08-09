"""Deterministic guardrail for actual, negative, future, and template legal text."""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

from pydantic import BaseModel, Field

from ipo_risk.schemas import Evidence


class LegalMatterEvidenceKind(StrEnum):
    ACTUAL_MATTER = "actual_matter"
    EXPLICIT_NEGATIVE = "explicit_negative"
    GENERIC_FUTURE_RISK = "generic_future_risk"
    TEMPLATE_STATEMENT = "template_statement"
    AMBIGUOUS = "ambiguous"


class LegalMatterEvidenceClassification(BaseModel):
    evidence_id: str
    kind: LegalMatterEvidenceKind
    matched_patterns: list[str] = Field(default_factory=list)


_ACTUAL_PATTERNS = {
    "currently_subject_to": re.compile(
        r"\b(?:is|are|was|were)?\s*currently\s+subject\s+to\s+"
        r"(?:litigation|legal proceedings?|regulatory investigations?|administrative proceedings?)\b",
        re.I,
    ),
    "proceedings_remain_pending": re.compile(
        r"\b(?:proceedings?|litigation|claims?|cases?)\s+(?:remain|remains|are|is)\s+pending\b",
        re.I,
    ),
    "pending_case_count": re.compile(r"\b(?:there (?:are|were)|has|have)\s+\w*\s*pending\s+(?:cases?|claims?|proceedings?|litigation)\b", re.I),
    "regulator_imposed_penalty": re.compile(
        r"\b(?:regulator|authority|commission|agency)\b.{0,100}\b(?:imposed|levied|issued)\b.{0,60}\b(?:penalty|fine|sanction)\b",
        re.I,
    ),
    "company_was_fined": re.compile(r"\b(?:was|were|has been|have been)\s+(?:fined|penalized|sanctioned)\b", re.I),
    "license_not_renewed": re.compile(
        r"\blicen[cs]e\b.{0,60}\b(?:has not|have not|had not|not yet|remains? not)\b.{0,40}\brenewed\b",
        re.I,
    ),
    "chinese_pending_matter": re.compile(r"(?:未决|未決|仍在审理|仍在審理|正在进行|正在進行).{0,20}(?:诉讼|訴訟|仲裁|调查|調查|程序|案件)"),
    "chinese_matter_still_pending": re.compile(r"(?:诉讼|訴訟|仲裁|调查|調查|程序|案件).{0,20}(?:未决|未決|仍在审理|仍在審理|正在进行|正在進行)"),
    "chinese_penalty": re.compile(r"(?:监管机构|監管機構|主管部门|主管部門|当局|當局).{0,80}(?:作出|施加|处以|處以|发出|發出).{0,40}(?:处罚|處罰|罚款|罰款)"),
    "chinese_license_unresolved": re.compile(r"(?:牌照|许可证|許可證|许可|許可).{0,60}(?:尚未续期|尚未續期|尚未取得|未获续期|未獲續期)"),
}

_LOCALLY_NEGATED_ACTUAL_PATTERNS = {
    "not_currently_subject_to": re.compile(
        r"\b(?:is|are|was|were)\s+not\s+currently\s+subject\s+to\s+"
        r"(?:litigation|legal proceedings?|regulatory investigations?|administrative proceedings?)\b",
        re.I,
    ),
    "no_proceedings_remain_pending": re.compile(
        r"\bno\s+(?:proceedings?|litigation|claims?|cases?)\s+(?:remain|remains|are|is)\s+pending\b",
        re.I,
    ),
    "regulator_did_not_impose_penalty": re.compile(
        r"\b(?:regulator|authority|commission|agency)\b.{0,100}\b"
        r"(?:did not|has not|had not)\s+(?:impose|levy|issue)\b.{0,60}"
        r"\b(?:penalty|fine|sanction)\b",
        re.I,
    ),
    "chinese_no_pending_matter": re.compile(
        r"(?:不存在|并无|並無|没有|沒有).{0,20}(?:未决|未決|仍在审理|仍在審理|正在进行|正在進行)"
        r".{0,20}(?:诉讼|訴訟|仲裁|调查|調查|程序|案件)"
    ),
}

_NEGATIVE_PATTERNS = {
    "not_involved_material_litigation": re.compile(
        r"\b(?:the\s+)?(?:group|company|issuer|we)\s+(?:is|are|was|were)\s+not\s+involved\s+in\s+any\s+material\s+(?:litigation|arbitration|proceedings?|claims?)\b",
        re.I,
    ),
    "no_material_litigation": re.compile(
        r"\b(?:no|not aware of any)\s+(?:pending\s+or\s+threatened\s+)?material\s+(?:litigation|arbitration|proceedings?|claims?)\b",
        re.I,
    ),
    "directors_confirm_none": re.compile(
        r"\bdirectors?\s+(?:confirm|confirmed|are not aware).{0,120}\bno\s+material\s+(?:litigation|proceedings?|claims?)\b",
        re.I,
    ),
    "chinese_directors_confirm_none": re.compile(
        r"董事.{0,20}(?:确认|確認).{0,80}(?:不存在|并无|並無|概无|概無).{0,30}重大(?:诉讼|訴訟|仲裁|程序|申索)"
    ),
    "chinese_no_material_litigation": re.compile(
        r"(?:并无|並無|概无|概無|不存在|未涉及).{0,30}(?:任何)?重大(?:诉讼|訴訟|仲裁|程序|申索)"
    ),
}

_GENERIC_FUTURE_PATTERNS = {
    "may_be_exposed_future": re.compile(
        r"\b(?:we|the\s+group|the\s+company)\s+may\s+be\s+exposed\s+to\s+(?:litigation|legal proceedings?)(?:\s+in\s+the\s+future)?\b",
        re.I,
    ),
    "may_face_litigation": re.compile(
        r"\b(?:we|the\s+group|the\s+company)\s+(?:may|could)\s+(?:face|be subject to)\s+(?:litigation|legal proceedings?|claims?)\b",
        re.I,
    ),
    "chinese_future_litigation": re.compile(
        r"(?:本集团|本集團|本公司|我们|我們).{0,20}可能(?:面临|面臨|受到|涉及).{0,20}(?:诉讼|訴訟|法律程序|申索)"
    ),
}

_TEMPLATE_PATTERNS = {
    "ordinary_course_may": re.compile(
        r"\b(?:in|during)\s+the\s+ordinary\s+course\s+of\s+(?:business|operations).{0,120}\bmay\b.{0,80}\b(?:litigation|legal proceedings?|claims?)\b",
        re.I,
    ),
    "may_from_time_to_time": re.compile(
        r"\bmay\s+from\s+time\s+to\s+time\s+(?:become\s+)?(?:involved|subject).{0,80}\b(?:litigation|legal proceedings?|claims?)\b",
        re.I,
    ),
    "cannot_assure_no_future_matter": re.compile(
        r"\b(?:cannot|can not)\s+assure.{0,120}\bwill\s+not\b.{0,80}\b(?:litigation|investigation|penalty|claim)\b",
        re.I,
    ),
    "chinese_ordinary_course_may": re.compile(
        r"(?:日常业务|日常業務|一般业务|一般業務).{0,40}(?:可能|或会|或會|不时|不時).{0,40}(?:诉讼|訴訟|调查|調查|申索|法律程序)"
    ),
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def _matches(text: str, patterns: dict[str, re.Pattern[str]]) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(text)]


def classify_legal_matter_evidence(
    evidence: Evidence,
) -> LegalMatterEvidenceClassification:
    """Classify one Evidence while preserving local grammatical negation."""

    text = _normalize(evidence.text)
    locally_negated = _matches(text, _LOCALLY_NEGATED_ACTUAL_PATTERNS)
    if locally_negated:
        return LegalMatterEvidenceClassification(
            evidence_id=evidence.evidence_id,
            kind=LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
            matched_patterns=locally_negated,
        )
    actual = _matches(text, _ACTUAL_PATTERNS)
    if actual:
        return LegalMatterEvidenceClassification(
            evidence_id=evidence.evidence_id,
            kind=LegalMatterEvidenceKind.ACTUAL_MATTER,
            matched_patterns=actual,
        )
    negative = _matches(text, _NEGATIVE_PATTERNS)
    if negative:
        return LegalMatterEvidenceClassification(
            evidence_id=evidence.evidence_id,
            kind=LegalMatterEvidenceKind.EXPLICIT_NEGATIVE,
            matched_patterns=negative,
        )
    future = _matches(text, _GENERIC_FUTURE_PATTERNS)
    if future:
        return LegalMatterEvidenceClassification(
            evidence_id=evidence.evidence_id,
            kind=LegalMatterEvidenceKind.GENERIC_FUTURE_RISK,
            matched_patterns=future,
        )
    template = _matches(text, _TEMPLATE_PATTERNS)
    if template:
        return LegalMatterEvidenceClassification(
            evidence_id=evidence.evidence_id,
            kind=LegalMatterEvidenceKind.TEMPLATE_STATEMENT,
            matched_patterns=template,
        )
    return LegalMatterEvidenceClassification(
        evidence_id=evidence.evidence_id,
        kind=LegalMatterEvidenceKind.AMBIGUOUS,
    )
