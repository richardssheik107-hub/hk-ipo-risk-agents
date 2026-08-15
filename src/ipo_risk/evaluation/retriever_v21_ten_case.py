"""Ten-case Retriever V2.1 research evaluation helpers."""

from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any, Callable

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.raw_retrieval_audit import (
    PRODUCTION_QUERY_PLANS,
    RawRetrievalAudit,
    TOP_K_VALUES,
    build_raw_retrieval_audit,
)
from ipo_risk.evaluation.retriever_v2_pilot import aggregate_audits
from ipo_risk.retrieval.domain_aware_v2 import RISK_DOMAINS
from ipo_risk.schemas import DocumentChunk, Evidence


class RiskQueryAdapter:
    """Expose a risk-level ranking through the frozen query audit surface."""

    def __init__(self, name: str, retrieve: Callable[[list[DocumentChunk], str, int], list[Evidence]]) -> None:
        self.name = name
        self._retrieve = retrieve
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
            self._cache[key] = self._retrieve(chunks, risk_code, max(TOP_K_VALUES))
        return self._cache[key][:limit]


def build_candidate_audit(
    *,
    bundle: ExpertAnnotationBundle,
    chunks: list[DocumentChunk],
    annotation_sha256: str,
    pdf_sha256: str,
    pdf_page_count: int,
    parser_error_count: int,
    name: str,
    retrieve: Callable[[list[DocumentChunk], str, int], list[Evidence]],
) -> RawRetrievalAudit:
    """Build a raw audit for an unregistered risk-level candidate."""
    return build_raw_retrieval_audit(
        bundle=bundle,
        chunks=chunks,
        retriever=RiskQueryAdapter(name, retrieve),
        annotation_sha256=annotation_sha256,
        pdf_sha256=pdf_sha256,
        pdf_page_count=pdf_page_count,
        configured_retriever_name=f"{name}_not_registered",
        parser_error_count=parser_error_count,
    )


def extended_metrics(audits: list[RawRetrievalAudit]) -> dict[str, Any]:
    """Add rank-sensitive and source-authority metrics to the standard aggregate."""
    aggregate = aggregate_audits(audits).model_dump(mode="json")
    required = [record for audit in audits for record in audit.records if record.gold_requirement == "required"]
    ranks = [record.first_hit_rank for record in required]
    penalized = [rank if rank is not None else 21 for rank in ranks]
    aggregate["required_rank_metrics"] = {
        "mrr": sum((1.0 / rank) if rank else 0.0 for rank in ranks) / len(ranks) if ranks else 1.0,
        "mean_first_rank_missing_as_21": mean(penalized) if penalized else 0.0,
        "median_first_rank_missing_as_21": median(penalized) if penalized else 0.0,
        "not_retrieved_at_20": sum(rank is None for rank in ranks),
    }
    by_source: dict[str, dict[str, Any]] = {}
    for authority in sorted({record.gold_source_authority for record in required}):
        selected = [record for record in required if record.gold_source_authority == authority]
        by_source[authority] = {
            "count": len(selected),
            "recall": {
                str(k): sum(bool(getattr(record, f"hit_at_{k}")) for record in selected) / len(selected)
                for k in TOP_K_VALUES
            },
        }
    aggregate["required_by_source_authority"] = by_source
    return aggregate


def rank_matrix(
    v1: list[RawRetrievalAudit],
    v2: list[RawRetrievalAudit],
    v21: list[RawRetrievalAudit],
) -> dict[str, Any]:
    """Return head recovery, deep-gain retention and regression diagnostics."""
    def rows(audits: list[RawRetrievalAudit]) -> dict[tuple[str, str, int], Any]:
        return {
            (record.case_id, record.risk_code, record.evidence_index): record
            for audit in audits for record in audit.records
            if record.gold_requirement == "required"
        }

    old, current, candidate = rows(v1), rows(v2), rows(v21)
    head_recovery: list[dict[str, Any]] = []
    deep_gain: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    for key in sorted(old):
        a, b, c = old[key], current[key], candidate[key]
        row = {
            "case_id": key[0], "risk_code": key[1], "evidence_index": key[2],
            "gold_page": a.gold_page, "v1_rank": a.first_hit_rank,
            "v2_rank": b.first_hit_rank, "v21_rank": c.first_hit_rank,
        }
        if a.first_hit_rank is not None and a.first_hit_rank <= 5 and (b.first_hit_rank is None or b.first_hit_rank > 5):
            head_recovery.append(row)
        if (a.first_hit_rank is None or a.first_hit_rank > 20) and b.first_hit_rank is not None and b.first_hit_rank <= 20:
            deep_gain.append(row)
        if a.first_hit_rank is not None and a.first_hit_rank <= 5 and (c.first_hit_rank is None or c.first_hit_rank > 5):
            regressions.append(row)
    retained = sum(row["v21_rank"] is not None and row["v21_rank"] <= 20 for row in deep_gain)
    return {
        "head_recovery_matrix": head_recovery,
        "head_recovered_at_5": sum(row["v21_rank"] is not None and row["v21_rank"] <= 5 for row in head_recovery),
        "deep_gain_retention_matrix": deep_gain,
        "deep_gain_retained_at_20": retained,
        "deep_gain_total": len(deep_gain),
        "deep_gain_retention_rate": retained / len(deep_gain) if deep_gain else 1.0,
        "new_head_regression_matrix": regressions,
        "new_head_regression_count": len(regressions),
    }


def provenance_diagnostics(candidate_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize final-rank provenance without exposing document text."""
    top3 = [row for row in candidate_rows if row["rank"] <= 3]
    top5 = [row for row in candidate_rows if row["rank"] <= 5]
    def occupancy(rows: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(
            "neighbor" if row["is_neighbor_only"] else
            "round2" if row["is_round2_only"] else
            "boilerplate" if row["is_boilerplate"] else "direct"
            for row in rows
        ))
    return {
        "top3_occupancy": occupancy(top3),
        "top5_occupancy": occupancy(top5),
        "mean_query_multiplicity": mean([row["query_multiplicity"] for row in candidate_rows]) if candidate_rows else 0.0,
        "mean_query_family_multiplicity": mean([row["query_family_multiplicity"] for row in candidate_rows]) if candidate_rows else 0.0,
        "candidate_universe_regressions": sum(bool(row["v1_candidate_universe_missing_pages"]) for row in candidate_rows),
        "by_domain": {
            domain: occupancy([row for row in top5 if row["domain"] == domain])
            for domain in sorted(set(RISK_DOMAINS.values()))
        },
    }
