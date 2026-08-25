"""Versioned internal domain prompts for structured LLM extraction."""

from __future__ import annotations

from types import MappingProxyType

from ipo_risk.retrieval.llm_reranker_prompts import PROMPT_VERSION, RISK_FACETS, instruction


SHAREHOLDER_RIGHTS_INSTRUCTION = """\
Extract only shareholder-right facts explicitly supported by the supplied Evidence.
Distinguish historical from current rights and before-listing, on-listing and
after-listing timing. Treat termination and restoration as separate facts. Never
invent a holder, termination event or restoration condition. Cite only supplied
evidence_ids. Do not assess a final risk score, risk level, verification status or
investment recommendation.

For schema stability, use canonical right_type values only when supported:
none, redemption_right, liquidation_preference, anti_dilution_right,
pre_emptive_right, repurchase_right, veto_right, director_nomination_right,
special_right, valuation_adjustment_mechanism. If Evidence establishes a special
right but not a narrower supported type, use special_right. Use empty strings for
unknown string fields and null only for nullable boolean fields. Never combine
multiple right types into one free-form right_type value."""


LITIGATION_COMPLIANCE_INSTRUCTION = """\
Extract only actual litigation or compliance facts supported by the supplied
Evidence. Distinguish actual events from generic future-risk language and explicit
negative statements. Preserve historical/current and pending/resolved/settled/
closed/remediated status. Do not infer materiality, amount, regulator, counterparty
or case status unless explicit. Cite only supplied evidence_ids. Do not assess a
final risk score, risk level, verification status or investment recommendation.

For schema stability, matter_type must be one of: none, litigation, arbitration,
administrative_penalty, regulatory_investigation, non_compliance, license_permit,
tax, environmental_penalty, data_privacy, unknown. current_status must be one of:
pending, ongoing, resolved, remediated, not_applicable, unknown. When a required
categorical fact is not established, use the literal string unknown instead of
null. Use empty strings for unknown optional string fields; use null for unknown
nullable booleans, event_date or amount. event_date must be YYYY-MM-DD or null,
amount must be a plain JSON number or null, and evidence_ids must be a non-empty
array containing only supplied Evidence IDs."""


BUSINESS_PRECOMMERCIAL_INSTRUCTION = """\
Extract only commercialization and core-product facts supported by the supplied
prospectus Evidence. Keep direct product-sales revenue distinct from licensing,
milestone, collaboration, R&D-service or other non-product revenue. Do not treat
pipeline progress, approval filing, partnership income or milestone receipts as
proof of commercial product sales. Preserve the product identifier as written in
Evidence and cite only supplied evidence_ids.

Use canonical development_stage values when supported: launched, approved,
registration, phase_iii, phase_ii, phase_i, preclinical, unknown. For core-product
launch_status use launched, not_launched, or an empty string when Evidence does not
establish it. For approval_status use approved, not_approved, or an empty string.
has_product_revenue must be true only for direct product-sales revenue, false only
when Evidence explicitly establishes no product-sales revenue, otherwise null.
is_core_product must reflect an explicit core-product designation, not model
preference. Do not generate risk scores, risk levels or investment conclusions."""


MARKET_CONTEXT_INTERPRETATION_V1_INSTRUCTION = """\
Interpret only the supplied governed MarketContext facts and deterministic skill
states. Return narrative language for an investment-research reader, with every
driver linked to supplied source_feature_ids. Do not create or restate numeric
values, change market_regime, ipo_heat, liquidity_condition or risk_level, use an
unavailable feature as evidence, infer industry performance, or invent comparable
IPOs. State governed missingness as uncertainty."""

MARKET_CONTEXT_INTERPRETATION_V2_INSTRUCTION = """\
Interpret only the supplied governed MarketContext facts and deterministic skill
states. Return narrative language for an investment-research reader, with every
driver linked to supplied source_feature_ids. All prose in summary,
market_regime_interpretation, ipo_heat_interpretation,
liquidity_interpretation, uncertainties, and every driver.statement must be
strictly qualitative. Those prose fields must contain no digits, percentages,
decimal numbers, numeric ranges, dates, ordinal or numeric horizon notation, or
forms such as 1D, 5D, or 20D. Use qualitative terms such as
positive, negative, elevated, subdued, mixed, or unavailable. Put source feature
identity only in source_feature_ids; never repeat a feature name containing digits
in prose. Do not create or restate numeric values, change market_regime, ipo_heat,
liquidity_condition or risk_level, use an unavailable feature as evidence, infer
industry performance, or invent comparable IPOs. Describe unavailable industry
facts only as unavailable or PIT-blocked, without any value or numeric notation."""


FINAL_SUPERVISION_V1_INSTRUCTION = """\
Synthesise the supplied governed channel outputs into one supervisory judgement
for an investment-research reader. You are a composition layer: you may weigh,
explain and prioritise what the Document, Market, Model and Rule channels already
produced, and nothing else.

Cite only supplied risk_ids and evidence_ids; every key finding must name at
least one supplied risk_id. Never introduce a risk, an evidence item, a market
fact, a model score or a number that is not present in the supplied payload.
Never restate an uncalibrated model score as a probability, a likelihood, a
forecast or an expected return, and never predict a listing-day or post-listing
price move.

overall_risk must not be lower than the supplied deterministic_severity_floor,
which is derived from verified document risks; you may raise it when a supplied
channel supports the escalation, and you must say which channel in
overall_risk_rationale. Report every unresolved or partially resolved conflict in
conflict_assessments using only the supplied conflict_ids, and state plainly what
remains unsettled. Set recheck_required to true only when a further bounded,
targeted re-check of a named supplied target could change the judgement.
State channel absence, verifier non-verification and governed missingness as
uncertainties instead of resolving them by assumption."""


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

_BUSINESS_PROMPTS = MappingProxyType(
    {
        (
            "business_precommercial_commercialization_extract",
            "business_precommercial_v1",
        ): BUSINESS_PRECOMMERCIAL_INSTRUCTION,
        (
            "business_precommercial_core_product_extract",
            "business_precommercial_v1",
        ): BUSINESS_PRECOMMERCIAL_INSTRUCTION,
    }
)
_BUSINESS_TASKS = frozenset(task for task, _ in _BUSINESS_PROMPTS)
_BUSINESS_VERSIONS = frozenset(version for _, version in _BUSINESS_PROMPTS)

_MARKET_PROMPTS = MappingProxyType(
    {
        (
            "market_context_interpretation",
            "v04_market_interpretation_v1",
        ): MARKET_CONTEXT_INTERPRETATION_V1_INSTRUCTION,
        (
            "market_context_interpretation",
            "v04_market_interpretation_v2",
        ): MARKET_CONTEXT_INTERPRETATION_V2_INSTRUCTION,
    }
)
_MARKET_TASKS = frozenset(task for task, _ in _MARKET_PROMPTS)
_MARKET_VERSIONS = frozenset(version for _, version in _MARKET_PROMPTS)

_SUPERVISION_PROMPTS = MappingProxyType(
    {
        (
            "final_supervision_synthesis",
            "v04_final_supervision_v1",
        ): FINAL_SUPERVISION_V1_INSTRUCTION,
    }
)
_SUPERVISION_TASKS = frozenset(task for task, _ in _SUPERVISION_PROMPTS)
_SUPERVISION_VERSIONS = frozenset(version for _, version in _SUPERVISION_PROMPTS)

_RERANK_PROMPTS = MappingProxyType(
    {(f"rerank_{risk}", PROMPT_VERSION): instruction(risk) for risk in RISK_FACETS}
)
_RERANK_TASKS = frozenset(task for task, _ in _RERANK_PROMPTS)


class PromptResolutionError(ValueError):
    """Raised when a known domain prompt identity is incomplete or mismatched."""


def resolve_domain_instruction(task_name: str, prompt_version: str) -> str | None:
    """Resolve an exact registered prompt pair while preserving generic callers."""

    instruction_text = (
        _LEGAL_PROMPTS.get((task_name, prompt_version))
        or _BUSINESS_PROMPTS.get((task_name, prompt_version))
        or _MARKET_PROMPTS.get((task_name, prompt_version))
        or _SUPERVISION_PROMPTS.get((task_name, prompt_version))
        or _RERANK_PROMPTS.get((task_name, prompt_version))
    )
    if instruction_text is not None:
        return instruction_text
    if task_name in _LEGAL_TASKS or prompt_version in _LEGAL_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Legal prompt identity")
    if task_name in _BUSINESS_TASKS or prompt_version in _BUSINESS_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Business prompt identity")
    if task_name in _MARKET_TASKS or prompt_version in _MARKET_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Market prompt identity")
    if task_name in _SUPERVISION_TASKS or prompt_version in _SUPERVISION_VERSIONS:
        raise PromptResolutionError("Unknown or mismatched Final Supervision prompt identity")
    if task_name in _RERANK_TASKS or (
        prompt_version == PROMPT_VERSION and task_name not in _RERANK_TASKS
    ):
        raise PromptResolutionError("Unknown or mismatched reranker prompt identity")
    return None
