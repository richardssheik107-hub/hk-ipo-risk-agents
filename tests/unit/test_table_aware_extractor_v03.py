"""Unit tests for the structured-first v0.3 financial extractor."""

from __future__ import annotations

from decimal import Decimal

from ipo_risk.extraction import (
    ExtractionStatus,
    TableAwareV03FinancialFactExtractor,
    V03FinancialFactExtractor,
)
from ipo_risk.schemas import DocumentChunk, Evidence


_REVENUE_TABLE = {
    "table_id": "p:t0",
    "detector": "word_cluster",
    "n_cols": 4,
    "n_rows": 1,
    "value_anchors": [330.0, 400.0, 470.0],
    "header_lines": ["截至12月31日止年度", "2021年", "2022年", "2023年", "人民幣千元"],
    "period_header_cells": ["2021年", "2022年", "2023年"],
    "rows": [{"label": "收益", "cells": ["593,660", "706,816", "862,247"], "y": 50.0}],
}


def _chunk_with_tables() -> DocumentChunk:
    return DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:447",
        page=447,
        section="財務資料",
        # Currency/unit are resolved from the page text, so the caption must appear here.
        text="綜合損益表\n截至12月31日止年度\n2021年 2022年 2023年\n人民幣千元\n收益 593,660 706,816 862,247",
        metadata={"tables": [_REVENUE_TABLE], "has_structured_tables": True},
    )


def _evidence(chunk: DocumentChunk) -> Evidence:
    return Evidence(
        evidence_id="e-447",
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text[:40],
    )


def test_structured_revenue_row_extracts_period_aligned_facts() -> None:
    chunk = _chunk_with_tables()
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_evidence(chunk)], {chunk.chunk_id: chunk}
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.normalized_value for item in result.observations] == [
        Decimal("593660"),
        Decimal("706816"),
        Decimal("862247"),
    ]
    assert [item.period_end.isoformat() for item in result.observations] == [
        "2021-12-31",
        "2022-12-31",
        "2023-12-31",
    ]
    assert all(item.currency == "CNY" and item.unit == "thousand" for item in result.observations)
    assert all(
        item.metadata.get("extraction_method") == "structured_table_v03"
        for item in result.observations
    )


def test_falls_back_to_regex_path_without_structured_tables() -> None:
    # Same flattened row, no metadata["tables"] — both extractors must agree.
    text = "人民幣千元\n截至2022年12月31日止年度\n截至2023年12月31日止年度\n收益 706,816 862,247"
    chunk = DocumentChunk(
        document_id="doc", chunk_id="doc:page:1", page=1, section="財務資料", text=text
    )
    evidence = Evidence(
        evidence_id="e-1", document_id="doc", chunk_id="doc:page:1", page=1, text=text[:20]
    )
    mapping = {chunk.chunk_id: chunk}

    table_aware = TableAwareV03FinancialFactExtractor()._extract_period_series(
        "revenue", [evidence], mapping
    )
    regex = V03FinancialFactExtractor()._extract_period_series(
        "revenue", [evidence], mapping
    )

    assert table_aware.status == regex.status
    assert [o.normalized_value for o in table_aware.observations] == [
        o.normalized_value for o in regex.observations
    ]


def test_non_statement_pages_do_not_contaminate_series_status() -> None:
    # One page carries the revenue table; the other is a non-statement page that
    # yields only `metric_label_not_found`. The clean fact must still win EXTRACTED.
    statement = _chunk_with_tables()
    other = DocumentChunk(
        document_id="doc", chunk_id="doc:page:389", page=389, section="財務資料",
        text="本集團收益主要來自物業管理服務，收益持續增長。",
    )
    mapping = {statement.chunk_id: statement, other.chunk_id: other}
    evidence = [_evidence(statement), Evidence(
        evidence_id="e-389", document_id="doc", chunk_id="doc:page:389", page=389, text="收益增長",
    )]

    result = TableAwareV03FinancialFactExtractor()._extract_period_series(
        "revenue", evidence, mapping
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert "metric_label_not_found" not in result.issues
    assert len(result.observations) == 3


def test_real_defect_still_blocks_series() -> None:
    # A per-fact defect (mismatched period count) must NOT be promoted to EXTRACTED.
    bad_table = {
        "header_lines": ["2022年", "2023年"],  # only 2 periods
        "rows": [{"label": "收益", "cells": ["1", "2", "3"], "y": 1.0}],  # 3 values
    }
    chunk = DocumentChunk(
        document_id="doc", chunk_id="doc:page:1", page=1, section="財務資料",
        text="收益 1 2 3 人民幣千元 2022年 2023年",
        metadata={"tables": [bad_table]},
    )
    evidence = Evidence(evidence_id="e", document_id="doc", chunk_id="doc:page:1", page=1, text="x")
    result = TableAwareV03FinancialFactExtractor()._extract_period_series(
        "revenue", [evidence], {chunk.chunk_id: chunk}
    )
    assert result.status == ExtractionStatus.NEEDS_REVIEW


_CASHFLOW_TABLE = {
    "header_lines": ["截至12月31日止年度", "2021年", "2022年", "2023年", "（人民幣千元）"],
    "period_header_cells": ["2021年", "2022年", "2023年"],
    "rows": [
        # Operating cash flow written as "…現金淨額" (net cash), which the base
        # label patterns miss but the table extractor's extended labels catch.
        {"label": "經營活動所得╱（所用）現金淨額", "cells": ["60,227", "(24,763)", "160,584"], "y": 50.0},
        {"label": "年末現金及現金等價物", "cells": ["248,585", "202,877", "257,430"], "y": 62.0},
    ],
}


def _cashflow_chunk() -> DocumentChunk:
    return DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:29",
        page=29,
        section="財務資料",
        # Page text deliberately mixes a "百萬元" (million) narrative with the
        # table's "千元" (thousand) caption, so a whole-page unit scan is ambiguous.
        text="淨利潤人民幣51.0百萬元。綜合現金流量表節選項目 人民幣千元 經營活動所得╱（所用）現金淨額 60,227 (24,763) 160,584 年末現金及現金等價物 248,585 202,877 257,430",
        metadata={"tables": [_CASHFLOW_TABLE], "has_structured_tables": True},
    )


def test_cash_flow_metrics_extract_from_structured_table() -> None:
    chunk = _cashflow_chunk()
    evidence = [_evidence_for(chunk)]
    result = TableAwareV03FinancialFactExtractor().extract(
        cash_evidence_candidates=evidence,
        operating_cash_flow_candidates=evidence,
        chunks_by_id={chunk.chunk_id: chunk},
    )

    cash = result.cash_and_cash_equivalents
    ocf = result.operating_cash_flow
    assert cash.status == ExtractionStatus.EXTRACTED
    assert cash.normalized_value == Decimal("257430")
    assert (cash.currency, cash.unit) == ("CNY", "thousand")  # resolved from table caption
    assert ocf.status == ExtractionStatus.EXTRACTED
    assert ocf.normalized_value == Decimal("160584")  # positive -> no cash burn
    assert ocf.period_months == 12


def test_cash_extraction_falls_back_without_tables() -> None:
    # No structured tables -> base flattened-text path (behaviour unchanged).
    chunk = DocumentChunk(
        document_id="doc", chunk_id="doc:page:29", page=29, section="財務資料",
        text="現金流量表\n人民幣千元\n年末現金及現金等價物\n257,430",
    )
    evidence = [_evidence_for(chunk)]
    base = FinancialEvidenceExtractor_extract(chunk, evidence)
    table = TableAwareV03FinancialFactExtractor().extract(
        cash_evidence_candidates=evidence, operating_cash_flow_candidates=[],
        chunks_by_id={chunk.chunk_id: chunk},
    ).cash_and_cash_equivalents
    assert table.status == base.status
    assert table.normalized_value == base.normalized_value


def _evidence_for(chunk: DocumentChunk) -> Evidence:
    return Evidence(
        evidence_id=f"e-{chunk.page}", document_id=chunk.document_id,
        chunk_id=chunk.chunk_id, page=chunk.page, text="x",
    )


def FinancialEvidenceExtractor_extract(chunk: DocumentChunk, evidence: list[Evidence]):
    from ipo_risk.extraction import V03FinancialFactExtractor
    return V03FinancialFactExtractor().extract(
        cash_evidence_candidates=evidence, operating_cash_flow_candidates=[],
        chunks_by_id={chunk.chunk_id: chunk},
    ).cash_and_cash_equivalents


def test_no_matching_table_row_falls_back() -> None:
    # A structured table is present, but it holds no revenue-labeled row.
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:9",
        page=9,
        section="財務資料",
        text="現金流量表\n人民幣千元\n利息收入 100 200",
        metadata={
            "tables": [
                {
                    "header_lines": ["2022年", "2023年"],
                    "period_header_cells": ["2022年", "2023年"],
                    "rows": [{"label": "利息收入", "cells": ["100", "200"], "y": 1.0}],
                }
            ]
        },
    )
    evidence = Evidence(
        evidence_id="e-9", document_id="doc", chunk_id="doc:page:9", page=9, text="x"
    )
    result = TableAwareV03FinancialFactExtractor()._extract_period_series(
        "revenue", [evidence], {chunk.chunk_id: chunk}
    )
    # 利息收入 is an excluded revenue label -> no structured match -> regex fallback -> not found.
    assert result.status == ExtractionStatus.NOT_FOUND
