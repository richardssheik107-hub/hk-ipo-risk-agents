"""Evaluator-only helpers for source-edition fact recoverability audits.

Gold text may be supplied to these pure helpers after runtime completion.  The
helpers return booleans only and must never be imported by runtime discovery,
retrieval, agents, prompts, or verification code.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable


_NUMBER = re.compile(r"(?<![A-Za-z])\(?-?\d[\d,]*(?:\.\d+)?\)?%?")
_RISK_TERMS = {
    "customer_concentration": (("客戶", "客户"),),
    "supplier_concentration": (("供應商", "供应商"),),
    "cash_burn_pressure": (("現金", "现金"), ("經營", "经营", "消耗", "流出")),
    "redemption_rights": (("贖回", "赎回"), ("權", "权")),
}
_REDEMPTION_LIFECYCLE = ("終止", "终止", "停止", "失效", "上市")


def normalize_audit_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def distinctive_numeric_tokens(value: str) -> frozenset[str]:
    """Return stable numeric tokens while excluding noisy years/small ordinals."""

    tokens: set[str] = set()
    for match in _NUMBER.findall(normalize_audit_text(value)):
        token = match.replace(",", "").strip("()")
        plain = token.removesuffix("%").lstrip("-")
        try:
            number = float(plain)
        except ValueError:
            continue
        if not token.endswith("%") and number.is_integer():
            integer = int(number)
            if integer < 10 or 1900 <= integer <= 2100:
                continue
        tokens.add(token)
    return frozenset(tokens)


def page_supports_risk_fact(
    page_text: str,
    *,
    risk_family: str,
    gold_anchor_texts: Iterable[str],
) -> bool:
    """Prove fact availability without returning or persisting source text."""

    normalized = normalize_audit_text(page_text)
    term_groups = _RISK_TERMS.get(risk_family)
    if not term_groups or not all(any(term in normalized for term in group) for group in term_groups):
        return False
    anchor_tokens = frozenset().union(
        *(distinctive_numeric_tokens(anchor) for anchor in gold_anchor_texts)
    )
    if anchor_tokens:
        page_tokens = distinctive_numeric_tokens(normalized)
        required = 1 if len(anchor_tokens) == 1 else 2
        return len(anchor_tokens & page_tokens) >= required
    return risk_family == "redemption_rights" and any(
        term in normalized for term in _REDEMPTION_LIFECYCLE
    )


def document_supports_risk_fact(
    page_texts: Iterable[str],
    *,
    risk_family: str,
    gold_anchor_texts: Iterable[str],
) -> bool:
    anchors = tuple(gold_anchor_texts)
    return any(
        page_supports_risk_fact(
            page, risk_family=risk_family, gold_anchor_texts=anchors
        )
        for page in page_texts
    )
