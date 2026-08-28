from __future__ import annotations

from pathlib import Path

import pytest

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.role_b_financial_v046 import (
    RoleBFinancialHighRecallRetriever,
)
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


def test_unknown_query_is_identical_to_released_keyword() -> None:
    chunks = [
        DocumentChunk(
            document_id="doc",
            chunk_id="doc:page:1",
            page=1,
            text="A generic disclosure contains an unrelated marker.",
        )
    ]

    expected = KeywordDocumentRetriever().retrieve(
        chunks, "unrelated marker", limit=5
    )
    observed = RoleBFinancialHighRecallRetriever().retrieve(
        chunks, "unrelated marker", limit=5
    )

    assert [item.model_dump(mode="json") for item in observed] == [
        item.model_dump(mode="json") for item in expected
    ]


def test_financial_pool_expands_relevant_context_with_a_hard_bound() -> None:
    target = "五大客戶佔總收益百分之八十"
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:10",
        page=10,
        text="x" * 2500 + target + "y" * 5000,
    )

    observed = RoleBFinancialHighRecallRetriever().retrieve_for_risk(
        [chunk], "customer_concentration", limit=1
    )

    assert len(observed) == 1
    assert target in observed[0].text
    assert len(observed[0].text) <= 6000
    assert observed[0].chunk_id == chunk.chunk_id
    assert observed[0].metadata["query_intent"] == "customer_concentration"
    assert observed[0].metadata["context_adapter"].startswith(
        "role_b_v046_hybrid_high_recall"
    )


def test_parser_search_variant_can_recover_an_anchor_missing_from_primary_text() -> None:
    target = "五大客戶佔總收益百分之八十"
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:11",
        page=11,
        text="客戶資料載於本頁，但預設閱讀順序遺失了表格列。",
        metadata={
            "search_text_variants": {
                "word_stream": f"業績記錄期 {target} 80%"
            }
        },
    )

    observed = RoleBFinancialHighRecallRetriever().retrieve_for_risk(
        [chunk], "customer_concentration", limit=5
    )

    assert observed
    assert any(target in item.text for item in observed)
    recovered = next(item for item in observed if target in item.text)
    assert recovered.chunk_id == chunk.chunk_id
    assert recovered.page == 11
    assert recovered.metadata["source_text_view"] == "word_stream"


def test_bm25_window_lane_recovers_non_exact_loss_language() -> None:
    target = "本集團於三個報告期間均錄得重大經營虧損"
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:12",
        page=12,
        text=f"財務資料 {target}，分別為100、120及140。",
    )

    observed = RoleBFinancialHighRecallRetriever().retrieve_for_risk(
        [chunk], "continuous_loss", limit=5
    )

    assert observed
    assert target in observed[0].text
    assert "bm25_window" in observed[0].metadata["retrieval_lanes"]
    assert observed[0].chunk_id == chunk.chunk_id
    assert observed[0].page == 12


def test_balanced_fusion_keeps_a_bm25_only_page_in_the_top_results() -> None:
    def candidate(page: int, lane: str) -> Evidence:
        return Evidence(
            evidence_id=f"{lane}:{page}",
            document_id="doc",
            chunk_id=f"doc:page:{page}",
            page=page,
            section="financial",
            text=f"candidate page {page}",
            source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=0.5,
            metadata={"retrieval_lane": lane},
        )

    domain = [candidate(page, "domain_v21") for page in range(1, 61)]
    bm25 = [candidate(999, "bm25_window")]

    observed = RoleBFinancialHighRecallRetriever()._fuse(
        "cash_runway",
        domain,
        bm25,
        limit=20,
    )
    pages = [item.page for item in observed]

    assert pages[:2] == [1, 999]
    recovered = observed[1]
    assert recovered.metadata["retrieval_lane"] == "balanced_rrf_fusion"
    assert recovered.metadata["domain_rank"] is None
    assert recovered.metadata["bm25_rank"] == 1


def test_legal_query_uses_high_recall_lane_without_minting_chunk_identity() -> None:
    target = "投資者所享安排在上市申請撤回後恢復"
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:20",
        page=20,
        text=target,
    )

    observed = RoleBFinancialHighRecallRetriever().retrieve(
        [chunk], "redemption_rights", limit=10
    )

    assert observed
    assert target in observed[0].text
    assert observed[0].chunk_id == chunk.chunk_id
    assert observed[0].page == chunk.page
    assert observed[0].metadata["query_intent"] == "redemption_rights"


def test_window_ranges_cover_the_tail_without_unbounded_text() -> None:
    ranges = RoleBFinancialHighRecallRetriever._window_ranges(12_345)

    assert ranges[0] == (0, 5200)
    assert ranges[-1] == (12_345 - 5200, 12_345)
    assert all(0 < end - start <= 5200 for start, end in ranges)


def test_financial_pool_rejects_non_financial_risk_codes() -> None:
    with pytest.raises(ValueError, match="unsupported Financial risk pool"):
        RoleBFinancialHighRecallRetriever().retrieve_for_risk(
            [], "redemption_rights"
        )


def test_adapter_has_no_case_or_gold_dependency() -> None:
    source = Path("src/ipo_risk/retrieval/role_b_financial_v046.py").read_text(
        encoding="utf-8"
    ).lower()
    for forbidden in (
        "existing_gold",
        "gold_unit",
        "stock_code",
        "company_name",
    ):
        assert forbidden not in source
