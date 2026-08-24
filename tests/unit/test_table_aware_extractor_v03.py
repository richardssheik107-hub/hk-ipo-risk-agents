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


_MIXED_PERIOD_TABLE = {
    "table_id": "p:t0",
    "detector": "word_cluster",
    "n_cols": 6,
    "n_rows": 1,
    "value_anchors": [292.7, 342.3, 391.9, 441.5, 491.1],
    "header_lines": [
        "綜合損益表",
        "截至12月31日止年度",
        "截至9月30日止九個月",
        "2022年",
        "2023年",
        "2024年",
        "2024年",
        "2025年",
        "千美元",
    ],
    "period_header_cells": ["2022年", "2023年", "2024年", "2024年", "2025年"],
    "period_header_source": "block",
    "period_columns": [
        {"column": 0, "anchor": 292.7, "year_label": "2022年", "group_line": "截至12月31日止年度"},
        {"column": 1, "anchor": 342.3, "year_label": "2023年", "group_line": "截至12月31日止年度"},
        {"column": 2, "anchor": 391.9, "year_label": "2024年", "group_line": "截至12月31日止年度"},
        {"column": 3, "anchor": 441.5, "year_label": "2024年", "group_line": "截至9月30日止九個月"},
        {"column": 4, "anchor": 491.1, "year_label": "2025年", "group_line": "截至9月30日止九個月"},
    ],
    "period_group_lines": ["截至12月31日止年度", "截至9月30日止九個月"],
    "period_basis_mixed": True,
    "rows": [
        {
            # Dot leaders are real glyphs in the reconstructed label.
            "label": "收入.......................",
            "cells": ["1,155", "3,460", "30,523", "19,454", "53,437"],
            "y": 50.0,
        }
    ],
}


def _mixed_period_chunk() -> DocumentChunk:
    return DocumentChunk(
        document_id="doc",
        chunk_id="doc:page:542",
        page=542,
        section="財務資料",
        text=(
            "綜合損益表\n截至12月31日止年度 截至9月30日止九個月\n"
            "2022年 2023年 2024年 2024年 2025年\n千美元\n"
            "收入 1,155 3,460 30,523 19,454 53,437"
        ),
        metadata={"tables": [_MIXED_PERIOD_TABLE], "has_structured_tables": True},
    )


def _mixed_evidence(chunk: DocumentChunk) -> Evidence:
    return Evidence(
        evidence_id="e-542",
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text[:40],
    )


def test_mixed_period_table_dates_annual_and_interim_columns_separately() -> None:
    chunk = _mixed_period_chunk()
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_mixed_evidence(chunk)], {chunk.chunk_id: chunk}
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert "value_period_count_mismatch" not in result.issues
    # The repeated 2024年 becomes two distinct periods, not one.
    assert [
        (item.period_end.isoformat(), item.period_months)
        for item in result.observations
    ] == [
        ("2022-12-31", 12),
        ("2023-12-31", 12),
        ("2024-09-30", 9),
        ("2024-12-31", 12),
        ("2025-09-30", 9),
    ]


def test_mixed_period_facts_declare_their_reporting_basis() -> None:
    chunk = _mixed_period_chunk()
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_mixed_evidence(chunk)], {chunk.chunk_id: chunk}
    )

    by_period = {item.period_end.isoformat(): item for item in result.observations}
    assert by_period["2024-12-31"].metadata["period_basis"] == "annual"
    assert by_period["2024-09-30"].metadata["period_basis"] == "interim"
    assert by_period["2024-09-30"].metadata["period_group_line"] == "截至9月30日止九個月"
    assert all(
        item.metadata["period_axis"] == "period_column_map"
        and item.metadata["period_basis_mixed"] is True
        for item in result.observations
    )


def test_scale_before_currency_resolves_the_unit() -> None:
    """``千美元``/``千港元`` put the scale in front of the currency; the frozen
    base grammar only reads a trailing ``元`` and resolves no unit at all."""
    extractor = TableAwareV03FinancialFactExtractor()

    assert extractor._detect_currency_unit("千美元") == ("USD", "thousand")
    assert extractor._detect_currency_unit("千港元") == ("HKD", "thousand")
    assert extractor._detect_currency_unit("百萬港元") == ("HKD", "million")
    # The frozen base grammar is untouched.
    assert V03FinancialFactExtractor._detect_currency_unit("千港元") == ("HKD", None)
    # …and the form it already handled still resolves the same way.
    assert extractor._detect_currency_unit("人民幣千元") == ("CNY", "thousand")


def test_dot_leaders_do_not_hide_a_table_revenue_row() -> None:
    """The frozen revenue patterns require whitespace after the metric name, so
    an unnormalised leader run would push every reconstructed row to the
    lower-confidence flattened-text path."""
    chunk = _mixed_period_chunk()
    extractor = TableAwareV03FinancialFactExtractor()

    facts, issues = extractor._period_facts_from_tables(
        "revenue",
        _mixed_evidence(chunk),
        chunk,
        chunk.metadata["tables"],
        {chunk.chunk_id: chunk},
    )

    assert issues == []
    assert [item.raw_value for item in facts] == [
        "1,155",
        "3,460",
        "30,523",
        "19,454",
        "53,437",
    ]


def test_mixed_period_series_pairs_nine_months_against_nine_months() -> None:
    """The whole point of typing the basis: a growth rule must never divide a
    nine-month stub by the full year that precedes it."""
    from ipo_risk.agents.financial_builders import V03FinancialRiskBuilder
    from ipo_risk.agents.financial_policy import load_v03_financial_policy

    chunk = _mixed_period_chunk()
    extractor = TableAwareV03FinancialFactExtractor()
    series = extractor._extract_period_series(
        "revenue", [_mixed_evidence(chunk)], {chunk.chunk_id: chunk}
    )

    builder = V03FinancialRiskBuilder(load_v03_financial_policy())
    mapped, issue = builder._map_revenue_observations(series)
    assert issue is None
    pair, pair_issue = builder._latest_revenue_pair(mapped)
    assert pair_issue is None
    previous, current = pair
    assert (previous.period_end.isoformat(), previous.period_months) == ("2024-09-30", 9)
    assert (current.period_end.isoformat(), current.period_months) == ("2025-09-30", 9)


def _table(rows: list[dict], **overrides) -> dict:
    table = {
        "table_id": "p:t0",
        "detector": "word_cluster",
        "n_cols": 4,
        "n_rows": len(rows),
        "value_anchors": [330.0, 400.0, 470.0],
        "header_lines": ["截至12月31日止年度", "2021年", "2022年", "2023年", "千港元"],
        "period_header_cells": ["2021年", "2022年", "2023年"],
        "period_header_source": "block",
        "period_columns": [
            {"column": 0, "anchor": 330.0, "year_label": "2021年", "group_line": "截至12月31日止年度"},
            {"column": 1, "anchor": 400.0, "year_label": "2022年", "group_line": "截至12月31日止年度"},
            {"column": 2, "anchor": 470.0, "year_label": "2023年", "group_line": "截至12月31日止年度"},
        ],
        "period_group_lines": ["截至12月31日止年度"],
        "period_basis_mixed": False,
        "rows": rows,
    }
    table.update(overrides)
    return table


def _page(chunk_id: str, page: int, table: dict, text: str) -> DocumentChunk:
    return DocumentChunk(
        document_id="doc",
        chunk_id=chunk_id,
        page=page,
        section="財務資料",
        text=text,
        metadata={"tables": [table], "has_structured_tables": True},
    )


def _ev(chunk: DocumentChunk) -> Evidence:
    return Evidence(
        evidence_id=f"e-{chunk.page}",
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text[:40],
    )


_ROW = [{"label": "收益 .....", "cells": ["11,000", "12,000", "13,000"], "y": 50.0}]


def test_table_caption_decides_the_unit_when_the_page_text_is_ambiguous() -> None:
    """A summary page prints the grid in 千港元 while the prose beside it quotes
    百萬元; a whole-page scan sees two scales and resolves neither, then disagrees
    with the statement page about the unit of an identical figure."""
    chunk = _page(
        "doc:page:26",
        26,
        _table(_ROW),
        "概要\n截至12月31日止年度\n千港元\n收益 11,000 12,000 13,000\n"
        "我們的收益由2022年的12.0百萬元增加至2023年的13.0百萬元。",
    )
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_ev(chunk)], {chunk.chunk_id: chunk}
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert all(item.unit == "thousand" and item.currency == "HKD" for item in result.observations)


def test_the_same_figure_cited_by_three_pages_is_one_observation() -> None:
    """Un-merged, the growth rule takes the latest fact as current and its own
    duplicate as previous, and the skill rejects the pair as out of order."""
    pages = [
        _page(f"doc:page:{page}", page, _table(_ROW), "千港元\n收益 11,000 12,000 13,000")
        for page in (26, 340, 447)
    ]
    chunks = {chunk.chunk_id: chunk for chunk in pages}
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_ev(chunk) for chunk in pages], chunks
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.period_end.isoformat() for item in result.observations] == [
        "2021-12-31",
        "2022-12-31",
        "2023-12-31",
    ]
    # Merged, not discarded: every citing page is still traceable.
    assert all(len(item.evidence_ids) == 3 for item in result.observations)


def test_a_genuine_disagreement_between_pages_is_still_reported() -> None:
    other = [{"label": "收益 .....", "cells": ["11,000", "12,000", "99,999"], "y": 50.0}]
    pages = [
        _page("doc:page:340", 340, _table(_ROW), "千港元\n收益"),
        _page("doc:page:447", 447, _table(other), "千港元\n收益"),
    ]
    chunks = {chunk.chunk_id: chunk for chunk in pages}
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "revenue", [_ev(chunk) for chunk in pages], chunks
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_values_for_same_period" in result.issues


def test_flattened_text_cannot_invent_a_row_the_grid_does_not_have() -> None:
    """With no coordinates the text path matches the metric name anywhere — in
    prose, in a segment note, or as the tail of a wrapped caption."""
    grid = _table([{"label": "利息收入 ....", "cells": ["39", "40", "41"], "y": 50.0}])
    chunk = _page(
        "doc:page:570",
        570,
        grid,
        "千港元\n變動計入損益的金\n融資產的公允價值\n收益\n941\n788\n15,710",
    )
    extractor = TableAwareV03FinancialFactExtractor()

    facts, issues = extractor._period_facts_from_evidence(
        "revenue", _ev(chunk), {chunk.chunk_id: chunk}
    )

    assert facts == []
    assert issues == ["metric_label_not_found"]


def test_an_unreadable_page_does_not_discard_a_clean_series() -> None:
    """A statement of changes in equity has columns that are not periods at all;
    its readings arrive marked defective and must not outvote the income
    statement's."""
    equity = _table(
        [{"label": "年內虧損 ....", "cells": ["", "(59,834)", "(59,834)"], "y": 50.0}],
        period_columns=[
            {"column": 0, "anchor": 330.0, "year_label": "2021年", "group_line": None},
            {"column": 1, "anchor": 400.0, "year_label": "2022年", "group_line": None},
            {"column": 2, "anchor": 470.0, "year_label": "2023年", "group_line": None},
        ],
        header_lines=["於12月31日", "2021年", "2022年", "2023年", "千港元"],
    )
    statement = _table(
        [{"label": "年內虧損 ....", "cells": ["(73,728)", "(269,246)", "(465,238)"], "y": 50.0}]
    )
    pages = [
        _page("doc:page:29", 29, statement, "千港元\n年內虧損"),
        _page("doc:page:589", 589, equity, "千港元\n於12月31日\n年內虧損"),
    ]
    chunks = {chunk.chunk_id: chunk for chunk in pages}
    extractor = TableAwareV03FinancialFactExtractor()

    result = extractor._extract_period_series(
        "net_result", [_ev(chunk) for chunk in pages], chunks
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.normalized_value for item in result.observations] == [
        Decimal("-73728"),
        Decimal("-269246"),
        Decimal("-465238"),
    ]
    # The page that could not be read is recorded, not silently forgotten.
    assert result.metadata["unreadable_pages"] == [589]
