"""Contracts for the non-default domain-aware Retriever V2 candidate."""

from __future__ import annotations

import pytest

from ipo_risk.core.config import ComponentConfigurationError
from ipo_risk.core.container import default_registry
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2, V2_QUERY_PLANS
from ipo_risk.schemas import DocumentChunk


def _chunk(page: int, text: str) -> DocumentChunk:
    return DocumentChunk(
        document_id="synthetic",
        chunk_id=f"synthetic:page:{page}",
        page=page,
        text=text,
        section="unknown",
    )


def test_v2_keeps_one_global_top_k() -> None:
    chunks = [
        _chunk(1, "五大客戶佔總收益百分比"),
        _chunk(2, "客戶明細及收益表"),
        _chunk(9, "風險因素提及客戶"),
    ]
    result = DomainAwareRetrieverV2().retrieve_for_risk(
        chunks, "customer_concentration", limit=1
    )
    assert len(result) == 1
    assert result[0].metadata["global_rank"] == 1


def test_v2_expands_physical_neighbour_with_provenance() -> None:
    chunks = [
        _chunk(10, "五大供應商及最大供應商"),
        _chunk(11, "總計及採購總額 82.0%"),
    ]
    result = DomainAwareRetrieverV2().retrieve_for_risk(
        chunks, "supplier_concentration", limit=5
    )
    neighbour = next(item for item in result if item.page == 11)
    assert neighbour.metadata["neighbour_expansion"] is True
    assert neighbour.metadata["seed_pages"] == [10]


def test_v2_runs_at_most_two_query_rounds() -> None:
    result = DomainAwareRetrieverV2().retrieve_for_risk(
        [_chunk(1, "核心產品仍在臨床階段")],
        "precommercial_product",
        limit=10,
    )
    assert result
    assert all(set(item.metadata["query_rounds"]) <= {1, 2} for item in result)


def test_v2_is_deterministic() -> None:
    chunks = [_chunk(1, "重大訴訟及合規事宜"), _chunk(2, "牌照及許可證齊全")]
    retriever = DomainAwareRetrieverV2()
    first = retriever.retrieve_for_risk(chunks, "material_litigation_compliance", limit=5)
    second = retriever.retrieve_for_risk(chunks, "material_litigation_compliance", limit=5)
    assert [(item.evidence_id, item.page, item.relevance_score) for item in first] == [
        (item.evidence_id, item.page, item.relevance_score) for item in second
    ]


def test_v2_query_plans_have_no_case_specific_identifiers() -> None:
    serialized = repr(V2_QUERY_PLANS).lower()
    for forbidden in ("00368", "01167", "01408", "01961", "0368.hk", "1167.hk", "1408.hk", "1961.hk"):
        assert forbidden not in serialized


def test_v2_candidate_is_not_registered_as_the_default_retriever() -> None:
    with pytest.raises(ComponentConfigurationError, match="Unregistered retriever"):
        default_registry().create("retriever", "domain_aware_v2")
