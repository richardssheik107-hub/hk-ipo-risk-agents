"""Private Role-B contracts for Evidence-bounded document semantics.

These models are intentionally not public ``RiskItem`` contracts.  They let
Legal/Business LLM callers validate citations and reconcile semantic facts
without registering a new production risk code or changing the workflow.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from ipo_risk.schemas import Evidence


class SemanticStatus(StrEnum):
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"


class PipelineStage(StrEnum):
    DISCOVERY = "discovery"
    PRECLINICAL = "preclinical"
    PHASE_I = "phase_i"
    PHASE_II = "phase_ii"
    PHASE_III = "phase_iii"
    REGISTRATION = "registration"
    APPROVED = "approved"
    LAUNCHED = "launched"
    UNKNOWN = "unknown"


class RevenueSource(StrEnum):
    PRODUCT_SALES = "product_sales"
    LICENSING = "licensing"
    SERVICE = "service"
    MILESTONE = "milestone"
    COLLABORATION = "collaboration"
    NONE = "none"
    UNKNOWN = "unknown"


class RelatedPartyTransactionFact(BaseModel):
    """Internal proposal only; no public risk code or RiskItem is registered."""

    counterparty: str
    relationship: str
    transaction_nature: str
    is_ongoing: bool | None = None
    materiality: str = "unknown"
    amount: float | None = None
    currency: str = ""
    evidence_ids: list[str] = Field(min_length=1)
    uncertainty: str = ""


class BusinessSemanticFact(BaseModel):
    product_name: str
    is_core_product: bool | None = None
    pipeline_stage: PipelineStage = PipelineStage.UNKNOWN
    is_commercialized: bool | None = None
    has_product_sales_revenue: bool | None = None
    revenue_sources: list[RevenueSource] = Field(default_factory=list)
    evidence_ids: list[str] = Field(min_length=1)
    uncertainty: str = ""


class DisclosureToneFact(BaseModel):
    tone_risk: bool | None = None
    hedging_language: list[str] = Field(default_factory=list)
    obfuscation_signal: bool | None = None
    missing_quantification: bool | None = None
    supporting_evidence_ids: list[str] = Field(min_length=1)
    uncertainty: str = ""


class SemanticReconciliation(BaseModel):
    status: SemanticStatus
    facts: dict[str, Any]
    conflicts: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceScopeError(ValueError):
    """Raised when a structured candidate cites outside bounded Evidence."""


ScopedModel = TypeVar("ScopedModel", bound=BaseModel)


def cited_evidence_ids(candidate: BaseModel) -> list[str]:
    """Read the single citation field supported by private semantic models."""

    for field in ("evidence_ids", "supporting_evidence_ids"):
        value = getattr(candidate, field, None)
        if value is not None:
            return list(value)
    raise TypeError("structured semantic model has no Evidence citation field")


def validate_evidence_scope(
    candidate: ScopedModel,
    evidence: Sequence[Evidence],
) -> ScopedModel:
    """Fail closed on empty, duplicate, or out-of-scope citations."""

    allowed = {item.evidence_id for item in evidence}
    cited = cited_evidence_ids(candidate)
    if not cited:
        raise EvidenceScopeError("structured semantic output has no Evidence citations")
    if len(cited) != len(set(cited)):
        raise EvidenceScopeError("structured semantic output has duplicate Evidence citations")
    unknown = sorted(set(cited) - allowed)
    if unknown:
        raise EvidenceScopeError("structured semantic output cites Evidence outside bounded input")
    return candidate


def extract_scoped(
    provider: Any,
    *,
    task_name: str,
    prompt_version: str,
    evidence: Sequence[Evidence],
    response_model: type[ScopedModel],
) -> ScopedModel:
    """Run one provider call and apply the Role-B citation guard."""

    bounded = list(evidence)
    candidate = provider.generate_structured(
        task_name=task_name,
        prompt_version=prompt_version,
        evidence=bounded,
        response_model=response_model,
    )
    if not isinstance(candidate, response_model):
        candidate = response_model.model_validate(candidate)
    return validate_evidence_scope(candidate, bounded)


def reconcile_business_fact(
    deterministic: Mapping[str, Any],
    llm_fact: BusinessSemanticFact,
) -> SemanticReconciliation:
    """Keep deterministic facts authoritative and surface every disagreement."""

    llm_values = {
        "product_name": llm_fact.product_name,
        "is_core_product": llm_fact.is_core_product,
        "pipeline_stage": llm_fact.pipeline_stage.value,
        "is_commercialized": llm_fact.is_commercialized,
        "has_product_sales_revenue": llm_fact.has_product_sales_revenue,
        "revenue_sources": [item.value for item in llm_fact.revenue_sources],
    }
    facts: dict[str, Any] = {}
    conflicts: list[str] = []
    for name, llm_value in llm_values.items():
        deterministic_value = deterministic.get(name)
        deterministic_known = deterministic_value not in (None, "", "unknown", [])
        llm_known = llm_value not in (None, "", "unknown", [])
        if deterministic_known:
            facts[name] = deterministic_value
            if llm_known and deterministic_value != llm_value:
                conflicts.append(name)
        else:
            facts[name] = llm_value
    return SemanticReconciliation(
        status=SemanticStatus.NEEDS_REVIEW if conflicts else SemanticStatus.EXTRACTED,
        facts=facts,
        conflicts=conflicts,
        evidence_ids=list(llm_fact.evidence_ids),
    )
