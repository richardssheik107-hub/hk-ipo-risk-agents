from __future__ import annotations

from pathlib import Path

import pytest

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.role_b_financial_v046 import (
    RoleBFinancialHighRecallRetriever,
)
from ipo_risk.schemas import DocumentChunk


def test_non_financial_retrieve_is_identical_to_released_keyword() -> None:
    chunks = [
        DocumentChunk(
            document_id="doc",
            chunk_id="doc:page:1",
            page=1,
            text="The pre-IPO investor has redemption rights.",
        )
    ]

    expected = KeywordDocumentRetriever().retrieve(
        chunks, "redemption_rights", limit=5
    )
    observed = RoleBFinancialHighRecallRetriever().retrieve(
        chunks, "redemption_rights", limit=5
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
    assert observed[0].metadata["query_intent"] == "customer_concentration"
    assert observed[0].metadata["context_adapter"].startswith(
        "role_b_v046_financial_high_recall"
    )


def test_financial_pool_rejects_non_financial_risk_codes() -> None:
    with pytest.raises(ValueError, match="unsupported Financial risk pool"):
        RoleBFinancialHighRecallRetriever().retrieve_for_risk(
            [], "redemption_rights"
        )


def test_adapter_has_no_case_or_gold_dependency() -> None:
    source = Path("src/ipo_risk/retrieval/role_b_financial_v046.py").read_text(
        encoding="utf-8"
    ).lower()
    for forbidden in ("existing_gold", "gold_unit", "stock_code", "company_name"):
        assert forbidden not in source
