"""Versioned internal domain prompts for structured LLM extraction."""

from __future__ import annotations

from types import MappingProxyType

from ipo_risk.retrieval.llm_reranker_prompts import PROMPT_VERSION, RISK_FACETS, instruction


SHAREHOLDER_RIGHTS_INSTRUCTION = """\
Extract only shareholder-right facts explicitly supported by the supplied Evidence.
Distinguish historical from current rights and before-listing, on-listing and
after-listing timing. Treat termination and restoration as separate facts. Never
invent a holder, termination event or restoration condition. Use null/empty values
when the Evidence is incomplete. Cite only supplied evidence_ids. Do not assess a
final risk score, risk level, verification status or investment recommendation."""


LITIGATION_COMPLIANCE_INSTRUCTION = """\
Extract only actual litigation or compliance facts supported by the supplied
Evidence. Distinguish actual events from generic future-risk language and explicit
negative statements. Preserve historical/current and pending/resolved/settled/
closed/remediated status. Do not infer materiality, amount, regulator, counterparty
or case status unless explicit. Cite only supplied evidence_ids. Do not assess a
final risk score, risk level, verification status or investment recommendation."""

MARKET_CONTEXT_INTERPRETATION_INSTRUCTION = """\
Interpret only the supplied governed MarketContext facts and deterministic skill
states. Return narrative language for an investment-research reader, with every
driver linked to supplied source_feature_ids. Do not create or restate numeric
values, change market_regime, ipo_heat, liquidity_condition or risk_level, use an
unavailable feature as evidence, infer industry performance, or invent comparable
IPOs. State governed missingness as uncertainty."""


_LEGAL_PROMPTS = MappingProxyType(
    {
        (
            "shareholder_rights_extract",
            "legal_shareholder_rights_v1",
        ): SHAREHOLDER_RIGHTS_INSTRUCTION,
        (
            "litigation_compliance_extract",
            "legal_litigation_compliance_v1",
        ): LITIGATION_COMPLIANCE_INSTRUCTION,
    }
)
_LEGAL_TASKS = frozenset(task for task, _ in _LEGAL_PROMPTS)
_LEGAL_VERSIONS = frozenset(version for _, version in _LEGAL_PROMPTS)

_MARKET_PROMPTS = MappingProxyType(
    {
        (
            "market_context_interpretation",
            "v04_market_interpretation_v1",
        ): MARKET_CONTEXT_INTERPRETATION_INSTRUCTION,
    }
)
_MARKET_TASKS = frozenset(task for task, _ in _MARKET_PROMPTS)
_MARKET_VERSIONS = frozenset(version for _, version in _MARKET_PROMPTS)

_RERANK_PROMPTS = MappingProxyType({(f"rerank_{risk}", PROMPT_VERSION): instruction(risk) for risk in RISK_FACETS})
_RERANK_TASKS = frozenset(task for task, _ in _RERANK_PROMPTS)


class PromptResolutionError(ValueError):
    """Raised when a known Legal prompt identity is incomplete or mismatched."""


def resolve_domain_instruction(task_name: str, prompt_version: str) -> str | None:
    """Resolve an exact Legal prompt pair while preserving generic callers."""

    instruction = (
        _LEGAL_PROMPTS.get((task_name, prompt_version))
        or _MARKET_PROMPTS.get((task_name, prompt_version))
        or _RERANK_PROMPTS.get((task_name, prompt_version))
    )
    if instruction is not None:
        return instruction
    if task_name in _LEGAL_TASKS or prompt_version in _LEGAL_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Legal prompt identity")
    if task_name in _MARKET_TASKS or prompt_version in _MARKET_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Market prompt identity")
    if task_name in _RERANK_TASKS or (prompt_version == PROMPT_VERSION and task_name not in _RERANK_TASKS):
        raise PromptResolutionError("Unknown or mismatched reranker prompt identity")
    return None
