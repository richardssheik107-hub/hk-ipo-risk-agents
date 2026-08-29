from __future__ import annotations

from decimal import Decimal

import pytest

from ipo_risk.extraction import ExtractionStatus, V03FinancialFactExtractor
from ipo_risk.schemas import DocumentChunk, Evidence


def extract_series(
    metric_name: str,
    row: str,
    *,
    header: str = "人民币千元\n截至2022年12月31日止年度\n截至2023年12月31日止年度",
    evidence_id: str = "e-row",
    evidence_metadata: dict[str, object] | None = None,
):
    row_chunk = DocumentChunk(
        document_id="doc", chunk_id="row", page=11, section="財務資料", text=row
    )
    header_chunk = DocumentChunk(
        document_id="doc", chunk_id="header", page=10, section="財務資料", text=header
    )
    evidence = Evidence(
        evidence_id=evidence_id,
        document_id="doc",
        chunk_id="row",
        page=11,
        text=row,
        metadata=evidence_metadata or {},
    )
    extractor = V03FinancialFactExtractor()
    mapping = {"row": row_chunk, "header": header_chunk}
    result = extractor._extract_period_series(metric_name, [evidence], mapping)
    return result


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("年內╱期內虧損 (1,234) （2,345）", [Decimal("-1234"), Decimal("-2345")]),
        ("年内亏损 1，234 2，345", [Decimal("-1234"), Decimal("-2345")]),
        ("loss for the year -1,234 -2,345", [Decimal("-1234"), Decimal("-2345")]),
        ("net profit 1 234 2 345", [Decimal("1234"), Decimal("2345")]),
    ],
)
def test_extracts_traditional_simplified_english_and_number_formats(
    row: str, expected: list[Decimal]
) -> None:
    result = extract_series("net_result", row)

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.normalized_value for item in result.observations] == expected
    assert result.evidence_ids == ["e-row"]
    assert all(item.context_chunk_ids == ["header"] for item in result.observations)
    assert all(item.context_pages == [10] for item in result.observations)


@pytest.mark.parametrize("label", ["收入", "收益", "營業收入", "revenue", "turnover"])
def test_extracts_chinese_and_english_revenue_rows(label: str) -> None:
    result = extract_series("revenue", f"{label} 1,000.25 800.10")

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.normalized_value for item in result.observations] == [
        Decimal("1000.25"),
        Decimal("800.10"),
    ]
    assert [item.period_months for item in result.observations] == [12, 12]
    assert [item.currency for item in result.observations] == ["CNY", "CNY"]
    assert [item.unit for item in result.observations] == ["thousand", "thousand"]


def test_mixed_annual_and_interim_periods_are_preserved_not_compared() -> None:
    result = extract_series(
        "revenue",
        "收入 1,000 600",
        header=(
            "港元千元\n截至2022年12月31日止年度\n"
            "截至2023年6月30日止六個月"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert [item.period_months for item in result.observations] == [12, 6]
    assert [item.period_end.isoformat() for item in result.observations] == [
        "2022-12-31",
        "2023-06-30",
    ]


def test_formal_revenue_dash_is_zero_with_explicit_normalization() -> None:
    result = extract_series(
        "revenue",
        "收入 44,242 –",
        evidence_metadata={"primary_statement_context": True},
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.observations[1].normalized_value == Decimal("0")
    assert result.observations[1].metadata["normalization"] == "formal_revenue_dash_to_zero"


def test_ambiguous_dash_needs_review_instead_of_becoming_zero() -> None:
    result = extract_series("revenue", "收入 44,242 –")

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.observations[1].normalized_value is None
    assert "ambiguous_empty_value_symbol" in result.observations[1].issues


@pytest.mark.parametrize(
    ("header", "issue"),
    [
        ("人民币千元", "missing_period"),
        ("千元\n截至2022年12月31日止年度\n截至2023年12月31日止年度", "missing_currency"),
        ("人民币\n截至2022年12月31日止年度\n截至2023年12月31日止年度", "missing_unit"),
    ],
)
def test_missing_period_currency_or_unit_is_diagnostic(header: str, issue: str) -> None:
    result = extract_series("revenue", "收入 100 90", header=header)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert issue in result.issues or any(issue in item.issues for item in result.observations)
    assert result.evidence_ids == ["e-row"]


def test_value_period_count_mismatch_is_needs_review() -> None:
    result = extract_series("net_result", "年內虧損 (100) (90) (80)")

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "value_period_count_mismatch" in result.issues


@pytest.mark.parametrize(
    "non_target",
    [
        "經營虧損 (100) (200)",
        "毛利 100 200",
        "利息收入 100 200",
        "其他收入 100 200",
        "Revenue from Product A 100 200",
    ],
)
def test_non_target_financial_rows_are_not_extracted(non_target: str) -> None:
    metric = "revenue" if "收入" in non_target or "revenue" in non_target.lower() else "net_result"
    result = extract_series(metric, non_target)

    assert result.status == ExtractionStatus.NOT_FOUND
    assert result.observations == []


def test_same_period_conflicting_values_are_retained_and_flagged() -> None:
    header = DocumentChunk(
        document_id="doc", chunk_id="header", page=10, text="人民币千元\n截至2023年12月31日止年度"
    )
    chunks = {"header": header}
    evidence = []
    for index, value in enumerate(["100", "90"], start=1):
        chunk_id = f"row-{index}"
        text = f"收入 {value}"
        chunks[chunk_id] = DocumentChunk(
            document_id="doc", chunk_id=chunk_id, page=11, text=text
        )
        evidence.append(
            Evidence(
                evidence_id=f"e-{index}", document_id="doc", chunk_id=chunk_id, page=11, text=text
            )
        )

    result = V03FinancialFactExtractor()._extract_period_series("revenue", evidence, chunks)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_values_for_same_period" in result.issues
    assert result.evidence_ids == ["e-1", "e-2"]


def test_summary_and_primary_statement_conflict_is_explicit() -> None:
    header = DocumentChunk(
        document_id="doc", chunk_id="header", page=10, text="人民币千元\n截至2023年12月31日止年度"
    )
    chunks = {"header": header}
    evidence = []
    for index, (value, source_context) in enumerate(
        [("100", "summary"), ("90", "primary_statement")], start=1
    ):
        chunk_id = f"row-{index}"
        chunks[chunk_id] = DocumentChunk(
            document_id="doc", chunk_id=chunk_id, page=11, text=f"收入 {value}"
        )
        evidence.append(
            Evidence(
                evidence_id=f"e-{index}",
                document_id="doc",
                chunk_id=chunk_id,
                page=11,
                text=f"收入 {value}",
                metadata={"source_context": source_context},
            )
        )

    result = V03FinancialFactExtractor()._extract_period_series("revenue", evidence, chunks)

    assert "conflicting_values_for_same_period" in result.issues
    assert "summary_primary_statement_conflict" in result.issues


def test_summary_only_value_requires_review_even_when_complete() -> None:
    result = extract_series(
        "revenue",
        "收入 100 90",
        evidence_metadata={"source_context": "summary"},
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "summary_or_risk_context_requires_review" in result.issues


def test_unsupported_row_layout_is_diagnostic() -> None:
    result = extract_series("net_result", "年內虧損 詳情載於附註")

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.issues == ["unsupported_layout"]


def concentration(
    concentration_type: str,
    text: str,
    *,
    evidence_id: str = "e-concentration",
    header: str | None = None,
):
    chunk = DocumentChunk(document_id="doc", chunk_id="c", page=20, text=text)
    evidence = Evidence(
        evidence_id=evidence_id,
        document_id="doc",
        chunk_id="c",
        page=20,
        text=text,
    )
    chunks = {"c": chunk}
    if header is not None:
        chunks["header"] = DocumentChunk(
            document_id="doc", chunk_id="header", page=19, text=header
        )
    return V03FinancialFactExtractor()._extract_concentration(
        concentration_type, [evidence], chunks
    )


@pytest.mark.parametrize(
    ("concentration_type", "party", "largest", "top_five"),
    [
        ("customer", "客戶", Decimal("37.5"), Decimal("68.0")),
        ("supplier", "供應商", Decimal("22.6"), Decimal("68.0")),
    ],
)
def test_extracts_customer_and_supplier_concentration(
    concentration_type: str,
    party: str,
    largest: Decimal,
    top_five: Decimal,
) -> None:
    result = concentration(
        concentration_type,
        f"截至2020年8月31日止八個月，最大{party}佔比{largest}%，五大{party}佔比{top_five}%。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end.isoformat() == "2020-08-31"
    assert result.period_months == 8
    assert result.largest_counterparty_pct == largest
    assert result.top_five_pct == top_five
    assert result.metadata["percentage_semantics"] == "0_to_100_percent"
    assert result.evidence_ids == ["e-concentration"]


def test_chinese_word_date_is_counted_and_parsed_as_a_narrative_period() -> None:
    result = concentration(
        "supplier",
        "截至二零一九年十二月三十一日止年度，最大供應商佔比45%，五大供應商佔比80%。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end.isoformat() == "2019-12-31"
    assert result.period_months == 12


def test_multiple_period_concentration_selects_latest_aligned_percentages() -> None:
    result = concentration(
        "customer",
        (
            "於2017年、2018年及2019年以及截至2020年5月31日止五個月，"
            "最大客戶佔總收益1.5%、1.7%、1.8%及2.4%，"
            "前五大客戶佔總收益3.7%、4.2%、4.8%及5.1%。"
        ),
        header=(
            "截至2017年12月31日止年度\n截至2018年12月31日止年度\n"
            "截至2019年12月31日止年度\n截至2020年5月31日止五個月"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end.isoformat() == "2020-05-31"
    assert result.period_months == 5
    assert result.largest_counterparty_pct == Decimal("2.4")
    assert result.top_five_pct == Decimal("5.1")


def test_spaced_decimal_percentages_are_not_truncated_to_fractional_digits() -> None:
    result = concentration(
        "supplier",
        (
            "於2017年、2018年、2019年及截至2020年6月30日止六個月，"
            "最大供應商佔採購總額的36 .0%、22 .8%、36 .8%及32 .7%，"
            "五大供應商佔採購總額的88 .0%、77 .7%、85 .9%及67 .2%。"
        ),
        header=(
            "截至2017年12月31日止年度\n截至2018年12月31日止年度\n"
            "截至2019年12月31日止年度\n截至2020年6月30日止六個月"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("32.7")
    assert result.top_five_pct == Decimal("67.2")


def test_aligned_label_local_period_outranks_newer_adjacent_context_date() -> None:
    result = concentration(
        "supplier",
        (
            "於2017年、2018年、2019年及截至2020年6月30日止六個月，"
            "最大供應商佔採購總額的36.0%、22.8%、36.8%及32.7%，"
            "五大供應商佔採購總額的88.0%、77.7%、85.9%及67.2%。"
        ),
        header="產品專利於2023年5月24日屆滿。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end.isoformat() == "2020-06-30"
    assert result.period_months == 6
    assert result.largest_counterparty_pct == Decimal("32.7")
    assert result.top_five_pct == Decimal("67.2")
    assert (
        result.metadata["candidate_diagnostics"][0]["period_reconciliation"]
        == "already_chronological_latest"
    )


def test_repeated_layout_can_align_a_companion_concentration_series() -> None:
    result = concentration(
        "customer",
        (
            "五大客戶佔收益93.7%、93.5%、87.6%及97.3%，"
            "最大客戶佔收益57.9%、40.4%、30.5%及85.9%。"
            "客戶D（2017年、2018年、2019年及截至2020年2月29日止兩個月最大客戶）"
            "分別佔收益57.9%、40.4%、30.5%及85.9%。"
        ),
        header="一項產品專利於2023年5月24日屆滿。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.period_end.isoformat() == "2020-02-29"
    assert result.period_months == 2
    assert result.largest_counterparty_pct == Decimal("85.9")
    assert result.top_five_pct == Decimal("97.3")
    candidate = result.metadata["candidate_diagnostics"][0]
    assert candidate["percentage_occurrence_selection"]["top_five"] == (
        "companion_series_period_count"
    )
    assert candidate["concentration_period_selection"] == (
        "companion_series_label_local_period"
    )


def test_equal_companion_series_use_shared_local_period_when_bare_years_are_unavailable() -> None:
    result = concentration(
        "customer",
        (
            "截至2020年8月31日止八個月，"
            "最大客戶佔收益10.1%、11.8%、13.5%及37.5%，"
            "五大客戶佔收益34.3%、36.5%、36.6%及68.0%。"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.period_end.isoformat() == "2020-08-31"
    assert result.period_months == 8
    assert result.largest_counterparty_pct == Decimal("37.5")
    assert result.top_five_pct == Decimal("68.0")
    candidate = result.metadata["candidate_diagnostics"][0]
    assert candidate["percentage_occurrence_selection"] == {
        "largest": "companion_series_period_count",
        "top_five": "companion_series_period_count",
    }
    assert candidate["concentration_period_selection"] == (
        "companion_series_label_local_period"
    )


def test_companion_series_does_not_override_mismatched_value_counts() -> None:
    result = concentration(
        "customer",
        (
            "五大客戶佔收益93.7%、93.5%及97.3%，"
            "最大客戶佔收益57.9%、40.4%、30.5%及85.9%。"
            "客戶D（2017年、2018年、2019年及截至2020年2月29日止兩個月最大客戶）"
            "分別佔收益57.9%、40.4%、30.5%及85.9%。"
        ),
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "value_period_count_mismatch" in result.issues


def test_bare_years_are_not_guessed_as_calendar_year_ends() -> None:
    result = concentration(
        "customer",
        "於2017年及2018年，最大客戶佔比10%及20%，五大客戶佔比30%及40%。",
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.period_end is None
    assert "missing_period" in result.issues


@pytest.mark.parametrize(
    ("text", "issue"),
    [
        (
            "截至2023年12月31日止年度，最大客戶佔比101%，五大客戶佔比99%。",
            "percentage_out_of_range",
        ),
        (
            "截至2023年12月31日止年度，最大客戶佔比-1%，五大客戶佔比60%。",
            "percentage_out_of_range",
        ),
        (
            "截至2023年12月31日止年度，最大客戶佔比70%，五大客戶佔比60%。",
            "largest_percentage_exceeds_top_five",
        ),
        (
            "截至2023年12月31日止年度，最大客戶為人民幣10百萬元，五大客戶為人民幣20百萬元。",
            "concentration_percentage_missing",
        ),
        (
            "截至2023年12月31日止年度，最大客戶比例0.375，五大客戶比例0.68。",
            "concentration_percentage_missing",
        ),
    ],
)
def test_concentration_invalid_or_ambiguous_values_need_review(text: str, issue: str) -> None:
    result = concentration("customer", text)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert issue in result.issues


def test_customer_and_supplier_labels_are_not_mixed() -> None:
    result = concentration(
        "supplier",
        "截至2023年12月31日止年度，最大客戶佔比30%，五大客戶佔比60%。",
    )

    assert result.status == ExtractionStatus.NOT_FOUND
    assert result.issues == ["concentration_label_not_found"]


def test_concentration_fields_can_merge_from_two_evidence_items() -> None:
    texts = [
        "截至2023年6月30日止六個月，最大客戶佔總收益13.5%。",
        "截至2023年6月30日止六個月，五大客戶佔總收益45.9%。",
    ]
    chunks = {
        f"c-{index}": DocumentChunk(
            document_id="doc", chunk_id=f"c-{index}", page=20 + index, text=text
        )
        for index, text in enumerate(texts)
    }
    evidence = [
        Evidence(
            evidence_id=f"e-{index}",
            document_id="doc",
            chunk_id=f"c-{index}",
            page=20 + index,
            text=text,
        )
        for index, text in enumerate(texts)
    ]

    result = V03FinancialFactExtractor()._extract_concentration(
        "customer", evidence, chunks
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("13.5")
    assert result.top_five_pct == Decimal("45.9")
    assert result.evidence_ids == ["e-0", "e-1"]


def test_empty_evidence_and_missing_chunk_have_stable_diagnostics() -> None:
    extractor = V03FinancialFactExtractor()
    empty = extractor._extract_period_series("revenue", [], {})
    missing = extractor._extract_period_series(
        "revenue",
        [Evidence(evidence_id="missing", chunk_id="absent", text="收入 1")],
        {},
    )

    assert empty.status == ExtractionStatus.NOT_FOUND
    assert empty.issues == ["evidence_candidates_empty"]
    assert missing.status == ExtractionStatus.NEEDS_REVIEW
    assert missing.issues == ["evidence_chunk_missing"]
    assert missing.evidence_ids == ["missing"]


def test_stage_one_shortest_text_values_regress_without_company_rules() -> None:
    loss = extract_series("net_result", "年╱期內虧損 (732,949) (402,894)")
    revenue = extract_series("revenue", "收入 5,067 538")
    customer = concentration(
        "customer",
        "截至2020年8月31日止八個月，最大客戶佔總收益37.5%，五大客戶佔總收益68.0%。",
    )

    assert [item.normalized_value for item in loss.observations] == [
        Decimal("-732949"),
        Decimal("-402894"),
    ]
    assert [item.normalized_value for item in revenue.observations] == [
        Decimal("5067"),
        Decimal("538"),
    ]
    assert customer.largest_counterparty_pct == Decimal("37.5")
    assert customer.top_five_pct == Decimal("68.0")


def concentration_from_many(concentration_type: str, texts: list[str]):
    """Run the concentration path over several evidence items on one period."""
    chunks = {
        f"c-{index}": DocumentChunk(
            document_id="doc", chunk_id=f"c-{index}", page=20 + index, text=text
        )
        for index, text in enumerate(texts)
    }
    evidence = [
        Evidence(
            evidence_id=f"e-{index}",
            document_id="doc",
            chunk_id=f"c-{index}",
            page=20 + index,
            text=text,
        )
        for index, text in enumerate(texts)
    ]
    return V03FinancialFactExtractor()._extract_concentration(
        concentration_type, evidence, chunks
    )


def test_a_label_split_by_a_hard_line_wrap_still_matches() -> None:
    """PDF text wraps mid-label ("最大客\\n戶"), which used to lose the label."""
    result = concentration(
        "customer",
        "截至2023年6月30日止六個月，來自我們最大客\n戶的收入佔總收入的25.8%，"
        "而前五大客戶佔總收入的50.3%。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("25.8")
    assert result.top_five_pct == Decimal("50.3")


def test_an_unmatched_label_does_not_donate_its_percentages_to_the_previous_one() -> None:
    """The failure mode is a wrong value, not a missing one.

    When a wrapped label went unmatched its percentages fell inside the
    preceding label's segment, so the top-five figure silently became the
    largest-customer figure.
    """
    result = concentration(
        "customer",
        "截至2023年6月30日止六個月，前五大客戶佔總收入的50.3%，"
        "而最大客\n戶佔總收入的25.8%。",
    )

    assert result.top_five_pct == Decimal("50.3")
    assert result.largest_counterparty_pct == Decimal("25.8")


def test_a_supplier_paragraph_does_not_donate_percentages_to_a_customer_label() -> None:
    """Both kinds of label bound a segment even though only one collects values."""
    result = concentration(
        "customer",
        "截至2023年6月30日止六個月，最大客戶佔總收入的25.8%。"
        "最大供應商佔採購總額的24.9%，前五大供應商佔採購總額的62.4%。",
    )

    assert result.largest_counterparty_pct == Decimal("25.8")
    assert result.top_five_pct is None


def test_the_wrap_tolerance_does_not_join_distant_text() -> None:
    """A bounded gap keeps unrelated table cells from forming a label."""
    result = concentration(
        "customer",
        "截至2023年6月30日止六個月\n最大\n\n\n\n客戶\n25.8%\n50.3%",
    )

    assert result.status == ExtractionStatus.NOT_FOUND
    assert result.issues == ["concentration_label_not_found"]


def test_a_narrative_period_series_validates_the_percentage_count() -> None:
    """The sentence names its own periods, and a later sentence refers back.

    Only the interim stub resolves to a date, so counting resolved dates alone
    made a correct four-value series look like a count mismatch.
    """
    result = concentration(
        "customer",
        "於2022年、2023年、2024年以及截至2025年6月30日止六個月，"
        "前五大客戶對總收入的貢獻分別為55.2%、55.9%、51.0%及50.3%。"
        "於往績記錄期間各年度╱期間，來自我們最大客\n戶的收入分別佔總收入的"
        "24.8%、30.0%、27.8%及25.8%。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end.isoformat() == "2025-06-30"
    assert result.period_months == 6
    assert result.top_five_pct == Decimal("50.3")
    assert result.largest_counterparty_pct == Decimal("25.8")


def test_a_lone_year_is_a_mention_not_a_period_series() -> None:
    """"於2011年上市" must not be read as a one-period series."""
    result = concentration(
        "customer",
        "客戶H於2011年上市。截至2023年6月30日止六個月，"
        "最大客戶佔30%及35%，五大客戶佔60%。",
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "value_period_count_mismatch" in result.issues


def test_a_page_that_read_no_percentages_cannot_veto_a_clean_reading() -> None:
    """A partial reading describes its own view, not a defect in the merge."""
    result = concentration_from_many(
        "customer",
        [
            "截至2023年6月30日止六個月，最大客戶佔總收入的25.8%，"
            "前五大客戶佔總收入的50.3%。",
            "以下為截至2023年6月30日止六個月來自前五大客戶的收入明細：客戶 收入 客戶類型",
        ],
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.largest_counterparty_pct == Decimal("25.8")
    assert result.top_five_pct == Decimal("50.3")


def test_a_contradicting_page_still_blocks_a_clean_reading() -> None:
    """Governing must not silence a genuine disagreement about the same period."""
    result = concentration_from_many(
        "customer",
        [
            "截至2023年6月30日止六個月，最大客戶佔總收入的25.8%，"
            "前五大客戶佔總收入的50.3%。",
            "截至2023年6月30日止六個月，最大客戶佔總收入的31.4%，"
            "前五大客戶佔總收入的50.3%。",
        ],
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_values_for_same_period" in result.issues
    assert result.largest_counterparty_pct is None


@pytest.mark.parametrize(
    ("concentration_type", "text"),
    [
        ("supplier", "截至2023年6月30日止六個月，最大供应商佔採購總額的22.6%，五大供应商佔68.0%。"),
        ("supplier", "截至2023年6月30日止六個月，最大供應商佔採購總額的22.6%，五大供應商佔68.0%。"),
        ("customer", "截至2023年6月30日止六個月，最大客户佔總收入的22.6%，五大客户佔68.0%。"),
        ("customer", "截至2023年6月30日止六個月，最大客戶佔總收入的22.6%，五大客戶佔68.0%。"),
    ],
)
def test_simplified_and_traditional_labels_are_both_recognised(
    concentration_type: str, text: str
) -> None:
    """A duplicated pattern block once left the simplified supplier labels dead.

    Both definitions were wrap-tolerant, so every behavioural test still passed
    while the later block silently shadowed the earlier one and dropped
    简体 supplier coverage. This pins the coverage itself.
    """
    result = concentration(concentration_type, text)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("22.6")
    assert result.top_five_pct == Decimal("68.0")


def test_the_sentence_outranks_a_header_that_names_more_periods() -> None:
    """A track-record table prints a comparative interim the narrative omits.

    The header resolves five periods, the sentence names four and quotes four
    percentages. Preferring whichever count was larger flagged the correct
    series as a mismatch.
    """
    result = concentration(
        "customer",
        "於2022年、2023年、2024年及截至2025年4月30日止四個月，"
        "前五大客戶佔總收入的48.6%、50.1%、47.6%和47.2%，"
        "最大客戶佔總收入的22.1%、24.4%、23.6%和23.2%。",
        header=(
            "截至2022年12月31日止年度\n截至2023年12月31日止年度\n"
            "截至2024年12月31日止年度\n截至2024年4月30日止四個月\n"
            "截至2025年4月30日止四個月"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.top_five_pct == Decimal("47.2")
    assert result.largest_counterparty_pct == Decimal("23.2")


def test_a_receivables_share_is_not_read_as_a_revenue_share() -> None:
    """Balance-sheet concentration is a different metric over the same parties."""
    result = concentration(
        "customer",
        "截至2025年4月30日止四個月，最大客戶的貿易應收款項佔貿易應收款項總額的16.61%，"
        "五大客戶的貿易應收款項佔貿易應收款項總額的28.4%。",
    )

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "concentration_percentage_missing" in result.issues
    assert result.largest_counterparty_pct is None
    assert result.top_five_pct is None


def test_a_revenue_share_survives_a_receivables_share_on_the_same_page() -> None:
    """Scope is judged per segment, so one page can carry both disclosures."""
    result = concentration(
        "customer",
        "截至2025年4月30日止四個月，最大客戶佔總收入的23.2%，前五大客戶佔總收入的47.2%。"
        "此外，最大客戶的貿易應收款項佔貿易應收款項總額的16.61%。",
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("23.2")
    assert result.top_five_pct == Decimal("47.2")


def test_a_span_phrase_is_not_counted_as_an_enumeration() -> None:
    """A track record may state its span instead of listing it.

    "截至2021年12月31日止三個年度及2022年首四個月" covers four periods while naming
    one date and one year. Counting the named periods under-counts the series,
    which flagged a correct four-value reading — a top-five supplier share of
    83.3%, a high risk — as a mismatch. Such a sentence now yields no count and
    the resolved periods govern instead.
    """
    result = concentration(
        "supplier",
        "於截至2021年12月31日止三個年度及2022年首四個月，"
        "我們五大供應商約佔我們採購總額的74.2%、65.1%、74.2%及83.3%，"
        "而最大供應商佔採購總額的36.8%、33.9%、62.6%及76.8%。",
        header=(
            "截至2019年12月31日止年度\n截至2020年12月31日止年度\n"
            "截至2021年12月31日止年度\n截至2022年4月30日止四個月"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.top_five_pct == Decimal("83.3")
    assert result.largest_counterparty_pct == Decimal("76.8")


def test_repeated_detail_label_does_not_overwrite_aggregate_series() -> None:
    result = concentration(
        "supplier",
        (
            "於2019年、2020年及2021年，五大供應商佔採購總額的"
            "68.3%、39.9%及34.8%，最大供應商佔採購總額的"
            "26.2%、17.3%及8.6%。"
            "五大供應商明細：供應商A佔9.4%，供應商B佔5.0%。"
        ),
        header=(
            "截至2019年12月31日止年度\n截至2020年12月31日止年度\n"
            "截至2021年12月31日止年度"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.largest_counterparty_pct == Decimal("8.6")
    assert result.top_five_pct == Decimal("34.8")
    candidate = result.metadata["candidate_diagnostics"][0]
    assert candidate["percentage_occurrence_selection"]["top_five"] == (
        "enumerated_period_count"
    )
    assert len(candidate["percentage_occurrences"]["top_five"]) == 2


def test_empty_first_label_yields_to_later_aligned_occurrence() -> None:
    result = concentration(
        "supplier",
        (
            "五大供應商資料。"
            "於2019年、2020年及2021年，五大供應商佔採購總額的"
            "68.3%、39.9%及34.8%，最大供應商佔採購總額的"
            "26.2%、17.3%及8.6%。"
        ),
        header=(
            "截至2019年12月31日止年度\n截至2020年12月31日止年度\n"
            "截至2021年12月31日止年度"
        ),
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.largest_counterparty_pct == Decimal("8.6")
    assert result.top_five_pct == Decimal("34.8")
    candidate = result.metadata["candidate_diagnostics"][0]
    assert len(candidate["percentage_occurrences"]["top_five"]) == 1
