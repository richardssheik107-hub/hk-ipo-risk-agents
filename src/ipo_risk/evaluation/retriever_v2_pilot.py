"""Four-case V1/V2 Retriever pilot aggregation and comparison utilities."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.evaluation.raw_retrieval_audit import (
    PRODUCTION_QUERY_PLANS,
    RawRetrievalAudit,
    TOP_K_VALUES,
    build_raw_retrieval_audit,
)
from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2, RISK_DOMAINS
from ipo_risk.schemas import DocumentChunk, Evidence


class PilotAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_count: int
    evidence_count: int
    required_count: int
    primary_count: int
    risk_count: int
    micro: dict[str, dict[int, float]]
    macro_case: dict[str, dict[int, float]]
    by_domain: dict[str, dict[str, Any]]
    by_risk: dict[str, dict[str, Any]]
    first_valid_hit_rank_distribution: dict[str, int]
    all_required_complete_rank_distribution: dict[str, int]
    failure_taxonomy_counts: dict[str, int]


class PilotComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v1: PilotAggregate
    v2: PilotAggregate
    micro_delta: dict[str, dict[int, float]]
    per_case_delta: dict[str, dict[str, dict[int, float]]]
    v2_beats_v1: bool
    degradation_flags: list[str] = Field(default_factory=list)


class _V2ProductionQueryAdapter:
    """Expose one risk-level V2 ranking through the frozen V1 query surface."""

    name = DomainAwareRetrieverV2.name

    def __init__(self, retriever: DomainAwareRetrieverV2) -> None:
        self._retriever = retriever
        self._query_to_risk = {
            query: risk_code
            for risk_code, plan in PRODUCTION_QUERY_PLANS.items()
            for query in plan.queries
        }
        self._cache: dict[tuple[int, str], list[Evidence]] = {}

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        try:
            risk_code = self._query_to_risk[query]
        except KeyError as exc:
            raise ValueError(f"query is absent from frozen production plans: {query}") from exc
        key = (id(chunks), risk_code)
        if key not in self._cache:
            self._cache[key] = self._retriever.retrieve_for_risk(chunks, risk_code, limit=max(TOP_K_VALUES))
        return self._cache[key][:limit]


def build_v2_retrieval_audit(
    *,
    bundle: ExpertAnnotationBundle,
    chunks: list[DocumentChunk],
    annotation_sha256: str,
    pdf_sha256: str,
    pdf_page_count: int,
    parser_error_count: int = 0,
) -> RawRetrievalAudit:
    """Build the same audit schema with the globally-ranked V2 candidate."""
    return build_raw_retrieval_audit(
        bundle=bundle,
        chunks=chunks,
        retriever=_V2ProductionQueryAdapter(DomainAwareRetrieverV2()),
        annotation_sha256=annotation_sha256,
        pdf_sha256=pdf_sha256,
        pdf_page_count=pdf_page_count,
        configured_retriever_name="domain_aware_v2_candidate_not_registered",
        parser_error_count=parser_error_count,
    )


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _metric_slice(audits: list[RawRetrievalAudit], risk_codes: set[str]) -> dict[str, Any]:
    records = [record for audit in audits for record in audit.records if record.risk_code in risk_codes]
    risks = [risk for audit in audits for risk in audit.risks if risk.risk_code in risk_codes]
    required = [record for record in records if record.gold_requirement == "required"]
    primary = [record for record in records if record.gold_role == "primary"]
    unique_pages = {(record.case_id, record.gold_page) for record in records}
    output: dict[str, Any] = {
        "evidence_count": len(records),
        "required_count": len(required),
        "primary_count": len(primary),
        "risk_count": len(risks),
    }
    for key, selected in (
        ("evidence_recall", records),
        ("primary_recall", primary),
        ("required_recall", required),
    ):
        output[key] = {
            k: _rate(sum(bool(getattr(item, f"hit_at_{k}")) for item in selected), len(selected))
            for k in TOP_K_VALUES
        }
    output["unique_page_recall"] = {
        k: _rate(
            len({(item.case_id, item.gold_page) for item in records if getattr(item, f"hit_at_{k}")}),
            len(unique_pages),
        )
        for k in TOP_K_VALUES
    }
    output["any_valid_risk_hit"] = {
        k: _rate(sum(bool(getattr(item, f"any_hit_at_{k}")) for item in risks), len(risks))
        for k in TOP_K_VALUES
    }
    output["required_completion"] = {
        k: _rate(sum(bool(getattr(item, f"required_complete_at_{k}")) for item in risks), len(risks))
        for k in TOP_K_VALUES
    }
    return output


def aggregate_audits(audits: list[RawRetrievalAudit]) -> PilotAggregate:
    """Aggregate by evidence (micro), case (macro), domain and risk."""
    if not audits:
        raise ValueError("at least one audit is required")
    all_codes = set(RISK_DOMAINS)
    overall = _metric_slice(audits, all_codes)
    metric_names = (
        "evidence_recall", "primary_recall", "required_recall",
        "unique_page_recall", "any_valid_risk_hit", "required_completion",
    )
    macro = {
        name: {
            k: sum(
                {
                    "evidence_recall": audit.metrics.evidence_recall_at,
                    "primary_recall": audit.metrics.primary_evidence_recall_at,
                    "required_recall": audit.metrics.required_evidence_recall_at,
                    "unique_page_recall": audit.metrics.unique_gold_page_recall_at,
                    "any_valid_risk_hit": audit.metrics.any_valid_risk_hit_rate_at,
                    "required_completion": audit.metrics.required_evidence_completion_rate_at,
                }[name][k]
                for audit in audits
            ) / len(audits)
            for k in TOP_K_VALUES
        }
        for name in metric_names
    }
    domains = {
        domain: _metric_slice(audits, {code for code, owner in RISK_DOMAINS.items() if owner == domain})
        for domain in sorted(set(RISK_DOMAINS.values()))
    }
    by_risk = {code: _metric_slice(audits, {code}) for code in sorted(RISK_DOMAINS)}
    first_ranks = Counter(
        str(risk.first_valid_hit_rank) if risk.first_valid_hit_rank is not None else "not_retrieved"
        for audit in audits for risk in audit.risks
    )
    complete_ranks = Counter(
        str(risk.all_required_first_complete_k) if risk.all_required_first_complete_k is not None else "not_complete_at_20"
        for audit in audits for risk in audit.risks
    )
    failures = Counter()
    for audit in audits:
        failures.update(audit.metrics.failure_taxonomy_counts)
    return PilotAggregate(
        case_count=len(audits),
        evidence_count=overall["evidence_count"],
        required_count=overall["required_count"],
        primary_count=overall["primary_count"],
        risk_count=overall["risk_count"],
        micro={name: overall[name] for name in metric_names},
        macro_case=macro,
        by_domain=domains,
        by_risk=by_risk,
        first_valid_hit_rank_distribution=dict(sorted(first_ranks.items())),
        all_required_complete_rank_distribution=dict(sorted(complete_ranks.items())),
        failure_taxonomy_counts=dict(sorted(failures.items())),
    )


def compare_audits(
    v1_audits: list[RawRetrievalAudit], v2_audits: list[RawRetrievalAudit]
) -> PilotComparison:
    if [item.case_id for item in v1_audits] != [item.case_id for item in v2_audits]:
        raise ValueError("V1 and V2 case order/identity must match")
    v1, v2 = aggregate_audits(v1_audits), aggregate_audits(v2_audits)
    delta = {
        name: {k: v2.micro[name][k] - v1.micro[name][k] for k in TOP_K_VALUES}
        for name in v1.micro
    }
    per_case: dict[str, dict[str, dict[int, float]]] = {}
    for old, new in zip(v1_audits, v2_audits):
        per_case[old.case_id] = {
            "evidence_recall": {k: new.metrics.evidence_recall_at[k] - old.metrics.evidence_recall_at[k] for k in TOP_K_VALUES},
            "required_recall": {k: new.metrics.required_evidence_recall_at[k] - old.metrics.required_evidence_recall_at[k] for k in TOP_K_VALUES},
            "required_completion": {k: new.metrics.required_evidence_completion_rate_at[k] - old.metrics.required_evidence_completion_rate_at[k] for k in TOP_K_VALUES},
        }
    degradations = [
        f"{case}:{metric}@{k}"
        for case, metrics in per_case.items()
        for metric, values in metrics.items()
        for k, value in values.items()
        if value < -1e-12
    ]
    beats = (
        delta["required_recall"][3] > 0
        and delta["required_recall"][5] > 0
        and delta["required_completion"][5] >= 0
    )
    return PilotComparison(
        v1=v1,
        v2=v2,
        micro_delta=delta,
        per_case_delta=per_case,
        v2_beats_v1=beats,
        degradation_flags=degradations,
    )


def load_audits(root: Path, case_ids: tuple[str, ...]) -> list[RawRetrievalAudit]:
    return [
        RawRetrievalAudit.model_validate_json((root / case / "raw_retrieval_audit.json").read_text(encoding="utf-8"))
        for case in case_ids
    ]
