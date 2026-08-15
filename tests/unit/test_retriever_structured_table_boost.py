"""The keyword retriever prefers pages whose reconstructed table has the row.

These tests pin the table-aware boost and, critically, that it stays inert when
a chunk carries no reconstructed tables (the default ``pymupdf`` parser and the
frozen 2410.HK slice), so their ranking is unchanged.
"""

from __future__ import annotations

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk

_REVENUE_TABLE = {
    "header_lines": ["截至12月31日止年度", "2021年", "2022年", "2023年", "人民幣千元"],
    "period_header_cells": ["2021年", "2022年", "2023年"],
    "rows": [{"label": "收益", "cells": ["593,660", "706,816", "862,247"], "y": 50.0}],
}


def _narrative_chunk(page: int) -> DocumentChunk:
    # Revenue-heavy prose that outranks the statement page without the boost.
    text = "收益 " * 12 + "本集團收益主要來自物業管理服務，收益持續增長。"
    return DocumentChunk(document_id="c", chunk_id=f"c:page:{page}", page=page, section="財務資料", text=text)


def _statement_chunk(page: int, *, with_tables: bool) -> DocumentChunk:
    text = "綜合損益表 截至12月31日止年度 2021年 2022年 2023年 人民幣千元 收益 593,660 706,816 862,247"
    metadata = {"tables": [_REVENUE_TABLE], "has_structured_tables": True} if with_tables else {}
    return DocumentChunk(
        document_id="c", chunk_id=f"c:page:{page}", page=page, section="財務資料", text=text, metadata=metadata
    )


def test_structured_row_page_outranks_narrative_page() -> None:
    retriever = KeywordDocumentRetriever()
    # Narrative page has the lower page number, so absent the boost it would win the tie.
    chunks = [_narrative_chunk(10), _statement_chunk(400, with_tables=True)]

    ranked = retriever.retrieve(chunks, "收益", limit=2)

    assert ranked[0].page == 400
    assert ranked[0].relevance_score > ranked[1].relevance_score


def test_boost_flips_tie_only_when_tables_present() -> None:
    retriever = KeywordDocumentRetriever()
    # Identical statement text on both pages: absent any boost they tie on score
    # and the lower page number wins. The boost on the higher page must flip that.
    low = _statement_chunk(10, with_tables=False)
    high_with = _statement_chunk(400, with_tables=True)
    high_without = _statement_chunk(400, with_tables=False)

    # Without tables anywhere -> tie -> lower page wins (boost is inert).
    assert retriever.retrieve([low, high_without], "收益", limit=1)[0].page == 10
    # Tables on the higher page -> boost flips the tie.
    assert retriever.retrieve([low, high_with], "收益", limit=1)[0].page == 400


def test_helper_is_gated_on_structured_tables() -> None:
    match = KeywordDocumentRetriever._structured_table_row_match
    with_tables = _statement_chunk(1, with_tables=True)
    without_tables = _statement_chunk(1, with_tables=False)

    assert match(with_tables, "收益", ("收益", "revenue")) is True
    assert match(without_tables, "收益", ("收益", "revenue")) is False


def test_boost_ignores_non_matching_table_rows() -> None:
    retriever = KeywordDocumentRetriever()
    # A structured table whose only row is an excluded label must not be boosted.
    other = DocumentChunk(
        document_id="c", chunk_id="c:page:400", page=400, section="財務資料",
        text="其他收入 100 200 300 人民幣千元",
        metadata={"tables": [{"header_lines": ["2022年", "2023年"],
                              "rows": [{"label": "其他收入", "cells": ["200", "300"], "y": 1.0}]}]},
    )
    ranked = retriever.retrieve([_narrative_chunk(10), other], "收益", limit=2)

    assert ranked[0].page == 10  # 其他收入 does not start with 收益 -> no boost
