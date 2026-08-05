from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.extraction import ExtractionStatus, FinancialEvidenceExtractor
from ipo_risk.schemas import DocumentChunk, Evidence


def chunk(text: str, *, page: int = 10, chunk_id: str | None = None) -> DocumentChunk:
    return DocumentChunk(
        document_id="doc",
        chunk_id=chunk_id or f"doc:page:{page}",
        page=page,
        text=text,
    )


def evidence(source: DocumentChunk, *, score: float = 1.0, evidence_id: str | None = None) -> Evidence:
    return Evidence(
        evidence_id=evidence_id or f"e:{source.page}",
        document_id=source.document_id,
        chunk_id=source.chunk_id,
        page=source.page,
        text=source.text,
        relevance_score=score,
    )


def table(label: str, values: list[str], *, unit: str = "人民幣千元") -> str:
    return "\n".join(
        [
            "截至12月31日止年度",
            "截至3月31日止三個月",
            "2022年",
            "2023年",
            "2023年",
            "2024年",
            unit,
            label,
            *values,
        ]
    )


def extract_one(metric: str, source: DocumentChunk, mapping: dict[str, DocumentChunk] | None = None):
    candidates = [evidence(source)]
    result = FinancialEvidenceExtractor().extract(
        candidates if metric == "cash" else [],
        candidates if metric == "ocf" else [],
        mapping or {source.chunk_id: source},
    )
    return result.cash_and_cash_equivalents if metric == "cash" else result.operating_cash_flow


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("77,208", Decimal("77208")),
        ("(83,918)", Decimal("-83918")),
        ("（83，918）", Decimal("-83918")),
        ("−12.50", Decimal("-12.50")),
        ("1,234.56", Decimal("1234.56")),
        ("83 918", Decimal("83918")),
    ],
)
def test_normalizes_supported_amount_formats(raw: str, expected: Decimal) -> None:
    assert FinancialEvidenceExtractor._normalize_amount(raw) == expected


@pytest.mark.parametrize("raw", ["-", "—", "–", "not-a-number", "12 34"])
def test_rejects_missing_or_invalid_amounts(raw: str) -> None:
    assert FinancialEvidenceExtractor._normalize_amount(raw) is None


@pytest.mark.parametrize(
    "raw",
    [
        "(83,918",
        "83,918)",
        "（83,918",
        "83,918）",
        "(83,918）",
        "（83,918)",
        "(",
        ")",
        "（",
        "）",
    ],
)
def test_rejects_unbalanced_or_mismatched_parentheses(raw: str) -> None:
    assert FinancialEvidenceExtractor._normalize_amount(raw) is None


def test_extracts_latest_cash_column_and_keeps_cash_period_months_empty() -> None:
    source = chunk(table("現金流量表所述現金及現金等價物", ["90,762", "186,830", "111,745", "77,208"]))
    result = extract_one("cash", source)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.normalized_value == Decimal("77208")
    assert result.raw_value == "77,208"
    assert result.period_end == date(2024, 3, 31)
    assert result.period_months is None
    assert result.currency == "CNY"
    assert result.unit == "thousand"
    assert result.extraction_method == "page_text_rule"


def test_extracts_latest_operating_cash_flow_and_period_length() -> None:
    source = chunk(table("經營活動所用淨現金流量", ["(220,053)", "(200,944)", "(56,986)", "(83,918)"]))
    result = extract_one("ocf", source)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.normalized_value == Decimal("-83918")
    assert result.period_end == date(2024, 3, 31)
    assert result.period_months == 3


def test_prefers_specific_cash_flow_reconciliation_label_over_earlier_broad_row() -> None:
    source = chunk(
        table("年末╱期末現金及現金等價物", ["20", "90,762", "186,830", "111,745", "77,208"])
        + "\n現金流量表所述現金及現金等價物\n90,762\n186,830\n111,745\n77,208"
    )
    result = extract_one("cash", source)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.raw_label == "現金流量表所述現金及現金等價物"
    assert result.normalized_value == Decimal("77208")


@pytest.mark.parametrize(
    ("unit_line", "currency", "unit"),
    [
        ("人民幣千元", "CNY", "thousand"),
        ("港幣萬元", "HKD", "ten_thousand"),
        ("USD million", "USD", "million"),
        ("人民幣元", "CNY", "unit"),
        ("RMB unit", "CNY", "unit"),
    ],
)
def test_detects_currency_and_unit(unit_line: str, currency: str, unit: str) -> None:
    source = chunk(table("現金流量表所述現金及現金等價物", ["1", "2", "3", "4"], unit=unit_line))
    result = extract_one("cash", source)
    assert (result.currency, result.unit) == (currency, unit)


def test_uses_adjacent_page_only_for_missing_header_fields() -> None:
    target = chunk("現金流量表所述現金及現金等價物\n77,208", page=11)
    header = chunk("截至3月31日止三個月\n2024年\n人民幣千元", page=10)
    far = chunk("截至12月31日止年度\n2025年\n港幣萬元", page=9)
    result = extract_one("cash", target, {item.chunk_id: item for item in (target, header, far)})

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == date(2024, 3, 31)
    assert result.normalized_value == Decimal("77208")
    assert result.context_pages == [10, 11]
    assert result.extraction_method == "page_text_with_adjacent_context"
    assert far.chunk_id not in result.context_chunk_ids


def test_amount_must_come_from_target_page_not_neighbor() -> None:
    target = chunk("現金流量表所述現金及現金等價物", page=11)
    neighbor = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n999,999", page=10)
    result = extract_one("cash", target, {target.chunk_id: target, neighbor.chunk_id: neighbor})
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.normalized_value is None
    assert "target_row_has_no_values" in result.issues


def test_column_mismatch_requires_review_instead_of_guessing() -> None:
    source = chunk(table("經營活動所用淨現金流量", ["1", "2", "3"]))
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "period_value_column_count_mismatch" in result.issues


def test_uneven_period_groups_require_review_instead_of_inferred_column_split() -> None:
    source = chunk(
        "\n".join(
            [
                "截至12月31日止年度",
                "截至3月31日止三個月",
                "2020年",
                "2021年",
                "2022年",
                "2023年",
                "2024年",
                "人民幣千元",
                "經營活動所用淨現金流量",
                "1",
                "2",
                "3",
                "4",
                "5",
            ]
        )
    )
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "period_header_missing_or_ambiguous" in result.issues


def test_divisible_but_unproven_period_group_split_requires_review() -> None:
    source = chunk(
        "\n".join(
            [
                "截至12月31日止年度",
                "截至3月31日止三個月",
                "2021年",
                "2022年",
                "2023年",
                "2024年",
                "人民幣千元",
                "經營活動所用淨現金流量",
                "1",
                "2",
                "3",
                "—",
            ]
        )
    )
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.period_end is None
    assert "period_header_missing_or_ambiguous" in result.issues


def test_missing_currency_and_unit_requires_review() -> None:
    source = chunk("截至3月31日止三個月\n2024年\n現金流量表所述現金及現金等價物\n77,208")
    result = extract_one("cash", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "currency_missing_or_ambiguous" in result.issues
    assert "unit_missing_or_ambiguous" in result.issues


def test_missing_period_requires_review() -> None:
    source = chunk("人民幣千元\n經營活動所用淨現金流量\n(83,918)")
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.period_end is None
    assert "period_header_missing_or_ambiguous" in result.issues


def test_no_supported_label_is_not_found() -> None:
    source = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n其他項目\n77,208")
    result = extract_one("cash", source)
    assert result.status == ExtractionStatus.NOT_FOUND


def test_empty_top_five_is_not_found() -> None:
    result = FinancialEvidenceExtractor().extract([], [], {})
    assert result.cash_and_cash_equivalents.status == ExtractionStatus.NOT_FOUND
    assert result.operating_cash_flow.status == ExtractionStatus.NOT_FOUND


def test_missing_source_chunk_requires_review() -> None:
    source = chunk("現金流量表所述現金及現金等價物\n1")
    result = FinancialEvidenceExtractor().extract([evidence(source)], [], {})
    assert result.cash_and_cash_equivalents.status == ExtractionStatus.NEEDS_REVIEW
    assert "source_chunk_not_available" in result.cash_and_cash_equivalents.issues


def test_evidence_document_id_mismatch_requires_review() -> None:
    source = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n100")
    item = evidence(source).model_copy(update={"document_id": "different-document"})
    result = FinancialEvidenceExtractor().extract(
        [item], [], {source.chunk_id: source}
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.issues == ["evidence_chunk_identity_mismatch"]
    assert result.document_id == "different-document"
    assert result.metadata["mismatch_fields"] == ["document_id"]
    assert result.metadata["evidence_identity"]["document_id"] == "different-document"
    assert result.metadata["chunk_identity"]["document_id"] == "doc"


def test_evidence_page_mismatch_requires_review() -> None:
    source = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n100")
    item = evidence(source).model_copy(update={"page": 99})
    result = FinancialEvidenceExtractor().extract(
        [item], [], {source.chunk_id: source}
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.page == 99
    assert result.metadata["mismatch_fields"] == ["page"]


def test_evidence_chunk_id_mismatch_requires_review() -> None:
    evidence_source = chunk("現金流量表所述現金及現金等價物\n100")
    mapped_chunk = chunk(
        "截至2024年3月31日止三個月\n人民幣千元\n"
        "現金流量表所述現金及現金等價物\n100",
        chunk_id="different-chunk-id",
    )
    item = evidence(evidence_source)
    result = FinancialEvidenceExtractor().extract(
        [item], [], {item.chunk_id: mapped_chunk}
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.metadata["mismatch_fields"] == ["chunk_id"]
    assert result.chunk_id == evidence_source.chunk_id


def test_selects_best_complete_candidate_from_top_five() -> None:
    incomplete = chunk("人民幣千元\n現金流量表所述現金及現金等價物\n1", page=10)
    complete = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n2", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(incomplete, score=1), evidence(complete, score=0.8)],
        [],
        {item.chunk_id: item for item in (incomplete, complete)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.page == 20
    assert result.normalized_value == Decimal("2")


def test_same_period_conflicting_complete_values_require_review() -> None:
    first = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=10)
    second = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n200", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(first), evidence(second, score=0.9)],
        [],
        {item.chunk_id: item for item in (first, second)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_values_for_same_period" in result.issues
    assert len(result.metadata["conflicting_candidates"]) == 1
    evaluated = result.metadata["evaluated_candidates"]
    assert len(evaluated) == 2
    assert sum(item["selected"] for item in evaluated) == 1
    assert {item["raw_value"] for item in evaluated} == {"100", "200"}


def test_older_period_with_different_value_is_not_a_conflict() -> None:
    newest = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n200", page=10)
    older = chunk("截至12月31日止年度\n2023年\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(older), evidence(newest, score=0.9)],
        [],
        {item.chunk_id: item for item in (newest, older)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == date(2024, 3, 31)


def test_newer_needs_review_candidate_prevents_silent_older_extraction() -> None:
    older = chunk("截至2023年12月31日止年度\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=10)
    newer = chunk("截至2024年3月31日止三個月\n人民幣\n現金流量表所述現金及現金等價物\n80", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(older), evidence(newer, score=0.8)],
        [],
        {item.chunk_id: item for item in (older, newer)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.page == 20
    assert result.period_end == date(2024, 3, 31)
    assert result.normalized_value == Decimal("80")
    assert "unit_missing_or_ambiguous" in result.issues
    assert "newer_period_candidate_unresolved" in result.issues
    assert result.metadata["selection_reason"] == "latest_period_candidate_requires_review"


def test_same_value_different_currency_requires_review() -> None:
    cny = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=10)
    hkd = chunk("截至2024年3月31日止三個月\n港幣千元\n現金流量表所述現金及現金等價物\n100", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(cny), evidence(hkd)], [], {item.chunk_id: item for item in (cny, hkd)}
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_currency_for_same_period" in result.issues
    assert result.metadata["conflicting_candidates"][0]["conflict_fields"] == ["currency"]
    assert result.metadata["conflicting_candidates"][0]["currency"] == "HKD"
    assert all(
        "extraction_method" in candidate
        for candidate in result.metadata["evaluated_candidates"]
    )


def test_same_value_different_unit_requires_review() -> None:
    thousand = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=10)
    million = chunk("截至2024年3月31日止三個月\n人民幣百萬元\n現金流量表所述現金及現金等價物\n100", page=20)
    result = FinancialEvidenceExtractor().extract(
        [evidence(thousand), evidence(million)],
        [],
        {item.chunk_id: item for item in (thousand, million)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_unit_for_same_period" in result.issues
    assert result.metadata["conflicting_candidates"][0]["unit"] == "million"


def test_same_date_different_period_months_requires_review() -> None:
    three_months = chunk("截至2024年3月31日止三個月\n人民幣千元\n經營活動所用淨現金流量\n100", page=10)
    six_months = chunk("截至2024年3月31日止六個月\n人民幣千元\n經營活動所用淨現金流量\n100", page=20)
    result = FinancialEvidenceExtractor().extract(
        [],
        [evidence(three_months), evidence(six_months)],
        {item.chunk_id: item for item in (three_months, six_months)},
    ).operating_cash_flow
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_period_length_for_same_date" in result.issues
    assert result.metadata["conflicting_candidates"][0]["period_months"] == 6


@pytest.mark.parametrize(
    "header",
    [
        "截至2023年12月31日止年度及截至2024年3月31日止三個月",
        "year ended 31 December 2023 and three months ended 31 March 2024",
    ],
)
def test_multiple_explicit_dates_on_one_line_keep_separate_period_lengths(header: str) -> None:
    source = chunk(f"{header}\n人民幣千元\n經營活動所用淨現金流量\n120\n30")
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == date(2024, 3, 31)
    assert result.period_months == 3
    assert result.normalized_value == Decimal("30")
    assert result.metadata["period_candidates"] == [
        {"period_end": "2023-12-31", "period_months": 12},
        {"period_end": "2024-03-31", "period_months": 3},
    ]


def test_ambiguous_mixed_period_header_requires_review() -> None:
    source = chunk(
        "截至2023年12月31日及2024年3月31日止三個月\n"
        "人民幣千元\n經營活動所用淨現金流量\n120\n30"
    )
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.period_end is None
    assert "mixed_period_header_ambiguous" in result.issues


def test_output_records_source_traceability() -> None:
    source = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n77,208")
    result = extract_one("cash", source)
    assert result.evidence_id == "e:10"
    assert result.document_id == "doc"
    assert result.chunk_id == "doc:page:10"
    assert result.page == 10
    assert result.metadata["field_sources"]["value"] == source.chunk_id
    assert result.raw_value in source.text
    assert result.raw_label in source.text


@pytest.mark.parametrize(
    ("header", "expected_end", "expected_months"),
    [
        ("截至2024年3月31日止三个月", date(2024, 3, 31), 3),
        ("截至2024年6月30日止六個月", date(2024, 6, 30), 6),
        ("截至2024年9月30日止九個月", date(2024, 9, 30), 9),
        ("截至2024年12月31日止年度", date(2024, 12, 31), 12),
        ("three months ended 31 March 2024", date(2024, 3, 31), 3),
        ("six months ended June 30, 2024", date(2024, 6, 30), 6),
        ("nine months ended 30 September 2024", date(2024, 9, 30), 9),
        ("year ended 31 December 2024", date(2024, 12, 31), 12),
    ],
)
def test_parses_supported_period_headers(
    header: str, expected_end: date, expected_months: int
) -> None:
    source = chunk(f"{header}\n人民幣千元\n經營活動所用淨現金流量\n(100)")
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == expected_end
    assert result.period_months == expected_months


def test_correct_query_intent_outranks_higher_relevance_wrong_intent() -> None:
    wrong = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n100", page=10)
    correct = chunk("截至3月31日止三個月\n2024年\n人民幣千元\n現金流量表所述現金及現金等價物\n200", page=20)
    wrong_evidence = evidence(wrong, score=1)
    wrong_evidence.metadata["query_intent"] = "cash_balance"
    correct_evidence = evidence(correct, score=0.5)
    correct_evidence.metadata["query_intent"] = "cash_flow_ending_cash"
    result = FinancialEvidenceExtractor().extract(
        [wrong_evidence, correct_evidence],
        [],
        {item.chunk_id: item for item in (wrong, correct)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.normalized_value == Decimal("200")
    assert result.page == 20


def test_correct_intent_needing_review_outranks_complete_wrong_intent() -> None:
    wrong = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n999", page=10)
    correct = chunk("截至2024年3月31日止三個月\n現金流量表所述現金及現金等價物\n100", page=20)
    wrong_evidence = evidence(wrong)
    wrong_evidence.metadata["query_intent"] = "cash_balance"
    correct_evidence = evidence(correct)
    correct_evidence.metadata["query_intent"] = "cash_flow_ending_cash"
    result = FinancialEvidenceExtractor().extract(
        [wrong_evidence, correct_evidence],
        [],
        {item.chunk_id: item for item in (wrong, correct)},
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.page == 20
    assert result.normalized_value == Decimal("100")
    assert result.metadata["query_intent"] == "cash_flow_ending_cash"


def test_only_wrong_query_intent_cannot_be_extracted() -> None:
    source = chunk("截至2024年3月31日止三個月\n人民幣千元\n現金流量表所述現金及現金等價物\n999")
    item = evidence(source)
    item.metadata["query_intent"] = "cash_balance"
    result = FinancialEvidenceExtractor().extract(
        [item], [], {source.chunk_id: source}
    ).cash_and_cash_equivalents
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "unexpected_query_intent" in result.issues


def test_parses_day_first_english_group_header_with_separate_year_columns() -> None:
    source = chunk(
        "Three months ended 31 March\n2023\n2024\nRMB '000\n"
        "net cash used in operating activities\n(10)\n(20)"
    )
    result = extract_one("ocf", source)
    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == date(2024, 3, 31)
    assert result.period_months == 3
    assert result.normalized_value == Decimal("-20")


def test_conflicting_neighbor_currency_cannot_supply_target_unit() -> None:
    neighbor = chunk("HK$'000\nOther statement", page=10)
    target = chunk(
        "截至2024年3月31日止三個月\n人民幣\n"
        "現金流量表所述現金及現金等價物\n100",
        page=11,
    )
    result = extract_one(
        "cash", target, {target.chunk_id: target, neighbor.chunk_id: neighbor}
    )
    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert result.currency == "CNY"
    assert result.unit is None
    assert "context_currency_conflict" in result.issues
    assert "unit_missing_or_ambiguous" in result.issues
    assert result.context_pages == [10, 11]
