"""Versioned internal domain prompts for structured LLM extraction."""

from __future__ import annotations

from types import MappingProxyType


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


class PromptResolutionError(ValueError):
    """Raised when a known Legal prompt identity is incomplete or mismatched."""


def resolve_domain_instruction(task_name: str, prompt_version: str) -> str | None:
    """Resolve an exact Legal prompt pair while preserving generic callers."""

    instruction = _LEGAL_PROMPTS.get((task_name, prompt_version))
    if instruction is not None:
        return instruction
    if task_name in _LEGAL_TASKS or prompt_version in _LEGAL_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Legal prompt identity")
    return None
