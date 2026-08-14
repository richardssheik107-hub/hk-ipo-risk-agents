"""Synthetic contracts for the evaluation-only raw Retriever audit."""

from __future__ import annotations

import inspect

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation import raw_retrieval_audit as raw
from ipo_risk.evaluation.raw_retrieval_audit import (
    RetrievalFailure,
    build_raw_retrieval_audit,
)
from ipo_risk.schemas import DocumentChunk, Evidence


RISK_CODES = (
    "cash_runway", "continuous_loss", "revenue_growth", "customer_concentration",
    "supplier_concentration", "redemption_rights", "material_litigation_compliance",
    "precommercial_product",
)


def _bundle(evidence: list[dict[str, object]]) -> ExpertAnnotationBundle:
    risks = []
    for code in RISK_CODES:
        applicable = code == "cash_runway"
        risks.append({
            "annotation_version": "gpt_expert_v1.1", "case_id": "synthetic",
            "stock_code": "0000.HK", "company_name": "Synthetic", "document_id": "synthetic",
            "risk_code": code, "applicable": applicable,
            "expected_status": "needs_review" if applicable else "rejected",
            "expected_level": "medium" if applicable else "not_applicable",
            "confidence": 0.8, "reasoning": "Synthetic.", "calculation_required": False,
            "review_outcome": "expert_first_pass", "annotator_type": "external_gpt_expert",
        })
    return ExpertAnnotationBundle.model_validate({
        "annotation_version": "gpt_expert_v1.1", "case_id": "synthetic",
        "stock_code": "0000.HK", "company_name": "Synthetic", "document_id": "synthetic",
        "risks": risks, "evidence": evidence, "metadata": {},
    })


def _gold(page: int, *, requirement: str = "required", role: str = "primary") -> dict[str, object]:
    return {
        "case_id": "synthetic", "risk_code": "cash_runway", "page": page,
        "evidence_role": role, "requirement": requirement,
        "source_authority": "accountants_report", "exact_text": "经营活动现金流",
        "evidence_reason": "Synthetic.", "confidence": 0.9,
    }


class RankedFakeRetriever:
    name = "keyword"

    def __init__(self, pages: list[int]) -> None:
        self.pages = pages

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        return [
            Evidence(
                evidence_id=f"e-{query}-{page}", document_id="synthetic",
                chunk_id=f"synthetic:page:{page}", page=page, text="经营活动现金流",
                relevance_score=max(0.01, 1 - rank / 100),
                metadata={"query_intent": "operating_cash_flow", "matched_keywords": [query]},
            )
            for rank, page in enumerate(self.pages[:limit], start=1)
        ]


def _audit(pages: list[int], evidence: list[dict[str, object]]):
    chunks = [DocumentChunk(
        document_id="synthetic", chunk_id=f"synthetic:page:{page}", page=page,
        text="经营活动现金流",
    ) for page in sorted({int(item["page"]) for item in evidence})]
    return build_raw_retrieval_audit(
        bundle=_bundle(evidence), chunks=chunks, retriever=RankedFakeRetriever(pages),
        annotation_sha256="a" * 64, pdf_sha256="b" * 64, pdf_page_count=30,
        configured_retriever_name="keyword",
    )


def test_rank_two_hits_at_three_and_five_not_one() -> None:
    record = _audit([1, 2], [_gold(2)]).records[0]
    assert record.first_hit_rank == 2
    assert not record.hit_at_1
    assert record.hit_at_3 and record.hit_at_5
    assert record.primary_failure_code is RetrievalFailure.NONE


def test_rank_seven_is_cutoff_and_ranking_miss() -> None:
    record = _audit(list(range(1, 8)), [_gold(7)]).records[0]
    assert not record.hit_at_5 and record.hit_at_10
    assert record.primary_failure_code is RetrievalFailure.RANKING_MISS
    assert RetrievalFailure.TOPK_CUTOFF in record.secondary_flags


def test_top_twenty_absence_is_retrieval_miss() -> None:
    record = _audit(list(range(1, 21)), [_gold(25)]).records[0]
    assert record.first_hit_rank is None
    assert record.primary_failure_code is RetrievalFailure.RETRIEVAL_MISS
    assert RetrievalFailure.QUERY_TOO_BROAD in record.secondary_flags


def test_empty_result_is_classified_as_query_too_narrow() -> None:
    record = _audit([], [_gold(25)]).records[0]
    assert RetrievalFailure.EMPTY_RESULT in record.secondary_flags
    assert RetrievalFailure.QUERY_TOO_NARROW in record.secondary_flags


def test_adjacent_unreturned_gold_page_is_classified() -> None:
    record = _audit([9], [_gold(10)]).records[0]
    assert RetrievalFailure.NEIGHBOUR_PAGE_MISSING in record.secondary_flags


def test_any_valid_does_not_imply_required_completion() -> None:
    audit = _audit([10], [_gold(10), _gold(20)])
    risk = next(item for item in audit.risks if item.risk_code == "cash_runway")
    assert risk.any_hit_at_20
    assert not risk.required_complete_at_20


def test_supporting_only_is_excluded_from_required_denominator() -> None:
    audit = _audit([10], [_gold(10), _gold(20, requirement="supporting_only", role="supporting")])
    assert audit.metrics.total_gold_evidence == 2
    assert audit.metrics.total_required_evidence == 1
    assert audit.metrics.required_evidence_recall_at[20] == 1.0


def test_duplicate_physical_gold_page_is_unique_once() -> None:
    audit = _audit([10], [_gold(10), _gold(10, requirement="supporting_only", role="supporting")])
    assert audit.metrics.total_gold_evidence == 2
    assert audit.metrics.unique_gold_pages == 1
    assert audit.metrics.unique_gold_page_recall_at[20] == 1.0


def test_parallel_query_union_uses_one_global_top_k_cutoff() -> None:
    plan = raw.ProductionQueryPlan(
        family="synthetic",
        queries=("q1", "q2"),
        composition=raw.RetrievalComposition.PARALLEL_PER_QUERY_UNION,
    )
    executions = [
        raw.QueryAuditRecord(
            case_id="synthetic",
            risk_code="cash_runway",
            query_family="synthetic",
            query=query,
            retriever_name="fake",
            requested_limit=1,
            returned_count=1,
            results=[raw.RankedRetrievalResult(
                rank=1,
                page=page,
                chunk_id=f"page-{page}",
                relevance_score=1.0,
            )],
        )
        for query, page in (("q1", 10), ("q2", 20))
    ]

    assert raw._composed_pages(plan, executions, "cash_runway", 1) == [10]


def test_audit_does_not_import_or_call_agents_or_llm() -> None:
    source = inspect.getsource(raw)
    assert "ipo_risk.agents" not in source
    assert "ipo_risk.providers" not in source
    assert ".analyze(" not in source
    assert "generate_structured" not in source


def test_audit_does_not_modify_retriever_source() -> None:
    source = inspect.getsource(raw)
    assert "KeywordDocumentRetriever" not in source
    assert "QUERY_FAMILIES =" not in source


def test_evaluation_queries_match_frozen_production_agent_requests() -> None:
    from ipo_risk.agents.business_v03 import BUSINESS_EVIDENCE_QUERIES
    from ipo_risk.agents.financial import CashRunwayFinancialAgent
    from ipo_risk.agents.financial_v03 import FINANCIAL_EVIDENCE_QUERIES
    from ipo_risk.agents.legal import LegalAgent

    assert raw.PRODUCTION_QUERY_PLANS["continuous_loss"].queries == FINANCIAL_EVIDENCE_QUERIES["continuous_loss"]
    assert raw.PRODUCTION_QUERY_PLANS["revenue_growth"].queries == FINANCIAL_EVIDENCE_QUERIES["revenue_growth"]
    assert raw.PRODUCTION_QUERY_PLANS["customer_concentration"].queries == FINANCIAL_EVIDENCE_QUERIES["customer_concentration"]
    assert raw.PRODUCTION_QUERY_PLANS["supplier_concentration"].queries == FINANCIAL_EVIDENCE_QUERIES["supplier_concentration"]
    assert raw.PRODUCTION_QUERY_PLANS["redemption_rights"].queries == (LegalAgent.rights_query,)
    assert raw.PRODUCTION_QUERY_PLANS["material_litigation_compliance"].queries == (LegalAgent.litigation_query,)
    assert raw.PRODUCTION_QUERY_PLANS["precommercial_product"].queries == BUSINESS_EVIDENCE_QUERIES
    cash_source = inspect.getsource(CashRunwayFinancialAgent.analyze)
    assert all(query in cash_source for query in raw.PRODUCTION_QUERY_PLANS["cash_runway"].queries)
