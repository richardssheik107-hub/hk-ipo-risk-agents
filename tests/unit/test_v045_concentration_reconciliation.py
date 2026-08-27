from __future__ import annotations

from datetime import date
from decimal import Decimal

import ipo_risk.extraction.financial as legacy_financial
from ipo_risk.extraction import (
    ConcentrationFact,
    ExtractionStatus,
    TableAwareV03FinancialFactExtractor,
    V03FinancialFactExtractor,
)


def _fact(
    *,
    period_end: date,
    period_months: int,
    largest: str | None,
    top_five: str | None,
    page: int,
    status: ExtractionStatus = ExtractionStatus.EXTRACTED,
    issues: list[str] | None = None,
    metadata: dict | None = None,
) -> ConcentrationFact:
    return ConcentrationFact(
        concentration_type="customer",
        period_end=period_end,
        period_months=period_months,
        largest_counterparty_pct=Decimal(largest) if largest is not None else None,
        top_five_pct=Decimal(top_five) if top_five is not None else None,
        evidence_ids=[f"e-{page}"],
        document_id="doc",
        chunk_id=f"c-{page}",
        page=page,
        status=status,
        issues=issues or [],
        metadata=metadata or {},
    )


def test_package_and_legacy_module_share_reconciled_extractors() -> None:
    assert legacy_financial.V03FinancialFactExtractor is V03FinancialFactExtractor
    assert (
        legacy_financial.TableAwareV03FinancialFactExtractor
        is TableAwareV03FinancialFactExtractor
    )


def test_dual_series_can_reconcile_one_extra_context_period() -> None:
    fact = _fact(
        period_end=date(2022, 12, 31),
        period_months=12,
        largest="23.2",
        top_five="47.2",
        page=20,
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["value_period_count_mismatch"],
        metadata={
            "raw_percentages": {
                "largest": ["22.1%", "24.4%", "23.6%", "23.2%"],
                "top_five": ["48.6%", "50.1%", "47.6%", "47.2%"],
            },
            "period_candidates": [
                {"period_end": "2022-12-31", "period_months": 12},
                {"period_end": "2023-12-31", "period_months": 12},
                {"period_end": "2024-12-31", "period_months": 12},
                {"period_end": "2024-04-30", "period_months": 4},
                {"period_end": "2025-04-30", "period_months": 4},
            ],
        },
    )

    result = V03FinancialFactExtractor._reconcile_concentration_candidate(fact)

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.period_end == date(2025, 4, 30)
    assert result.period_months == 4
    assert result.metadata["value_period_count_reconciled"] is True
    assert (
        result.metadata["period_reconciliation"]
        == "chronological_latest_existing_candidate"
    )


def test_value_period_mismatch_stays_fail_closed_when_gap_is_larger_than_one() -> None:
    fact = _fact(
        period_end=date(2022, 12, 31),
        period_months=12,
        largest="23.2",
        top_five="47.2",
        page=20,
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["value_period_count_mismatch"],
        metadata={
            "raw_percentages": {
                "largest": ["23.6%", "23.2%"],
                "top_five": ["47.6%", "47.2%"],
            },
            "period_candidates": [
                {"period_end": "2021-12-31", "period_months": 12},
                {"period_end": "2022-12-31", "period_months": 12},
                {"period_end": "2023-12-31", "period_months": 12},
                {"period_end": "2024-12-31", "period_months": 12},
                {"period_end": "2025-04-30", "period_months": 4},
            ],
        },
    )

    result = V03FinancialFactExtractor._reconcile_concentration_candidate(fact)

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "value_period_count_mismatch" in result.issues
    assert result.metadata["value_period_count_reconciled"] is False


def test_later_candidate_without_values_cannot_veto_last_usable_observation() -> None:
    extractor = V03FinancialFactExtractor()
    valid = _fact(
        period_end=date(2024, 12, 31),
        period_months=12,
        largest="35.0",
        top_five="72.0",
        page=20,
    )
    later_empty = _fact(
        period_end=date(2025, 6, 30),
        period_months=6,
        largest=None,
        top_five=None,
        page=21,
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["concentration_percentage_missing", "incomplete_concentration_values"],
    )

    result = extractor._merge_concentration_facts("customer", [valid, later_empty])

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.period_end == date(2024, 12, 31)
    assert result.largest_counterparty_pct == Decimal("35.0")
    assert result.top_five_pct == Decimal("72.0")
    assert result.metadata["merge_selection_basis"] == "latest_usable_concentration_period"
    assert result.metadata["discarded_nonselected_candidate_count"] == 1


def test_same_date_period_length_disagreement_remains_fail_closed() -> None:
    extractor = V03FinancialFactExtractor()
    annual = _fact(
        period_end=date(2024, 12, 31),
        period_months=12,
        largest="35.0",
        top_five="72.0",
        page=20,
    )
    interim = _fact(
        period_end=date(2024, 12, 31),
        period_months=6,
        largest="35.0",
        top_five="72.0",
        page=21,
    )

    result = extractor._merge_concentration_facts("customer", [annual, interim])

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "period_months_conflict" in result.issues
    assert result.period_months is None


def test_clean_complete_candidate_governs_same_date_partial_conflict() -> None:
    extractor = V03FinancialFactExtractor()
    complete = _fact(
        period_end=date(2024, 12, 31),
        period_months=12,
        largest="35.0",
        top_five="72.0",
        page=20,
        metadata={"source_context": "primary_statement"},
    )
    partial = _fact(
        period_end=date(2024, 12, 31),
        period_months=6,
        largest="60.0",
        top_five=None,
        page=21,
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["incomplete_concentration_values"],
        metadata={"source_context": "summary"},
    )

    result = extractor._merge_concentration_facts("customer", [complete, partial])

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.issues == []
    assert result.period_months == 12
    assert result.largest_counterparty_pct == Decimal("35.0")
    assert result.top_five_pct == Decimal("72.0")
    assert result.evidence_ids == ["e-20", "e-21"]
    assert result.metadata["governing_candidate_count"] == 1
    assert result.metadata["value_candidate_count"] == 1
    assert result.metadata["merge_value_basis"] == "clean_complete_governing_candidates"
    assert len(result.metadata["candidate_diagnostics"]) == 2


def test_genuine_same_period_value_conflict_remains_fail_closed() -> None:
    extractor = V03FinancialFactExtractor()
    first = _fact(
        period_end=date(2024, 12, 31),
        period_months=12,
        largest="35.0",
        top_five="72.0",
        page=20,
    )
    second = _fact(
        period_end=date(2024, 12, 31),
        period_months=12,
        largest="35.0",
        top_five="74.0",
        page=21,
    )

    result = extractor._merge_concentration_facts("customer", [first, second])

    assert result.status == ExtractionStatus.NEEDS_REVIEW
    assert "conflicting_values_for_same_period" in result.issues
    assert result.top_five_pct is None
    assert "incomplete_concentration_values" in result.issues
    assert len(result.metadata["candidate_diagnostics"]) == 2
