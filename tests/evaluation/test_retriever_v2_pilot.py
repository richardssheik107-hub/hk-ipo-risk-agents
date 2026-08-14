"""Aggregation contracts for the four-case Retriever V2 pilot."""

from __future__ import annotations

from ipo_risk.evaluation.retriever_v2_pilot import aggregate_audits, compare_audits
from tests.evaluation.test_raw_retrieval_audit import _audit, _gold


def test_micro_recall_uses_all_evidence_as_denominator() -> None:
    first = _audit([10], [_gold(10), _gold(20)])
    second = _audit([30], [_gold(30)])
    aggregate = aggregate_audits([first, second])
    assert aggregate.evidence_count == 3
    assert aggregate.micro["evidence_recall"][20] == 2 / 3


def test_macro_case_recall_weights_cases_equally() -> None:
    first = _audit([10], [_gold(10), _gold(20)])
    second = _audit([30], [_gold(30)])
    aggregate = aggregate_audits([first, second])
    assert aggregate.macro_case["evidence_recall"][20] == 0.75


def test_comparison_reports_real_improvement_and_degradation() -> None:
    old = _audit([1], [_gold(2)])
    new = _audit([2], [_gold(2)])
    comparison = compare_audits([old], [new])
    assert comparison.micro_delta["required_recall"][3] == 1.0
    assert comparison.v2_beats_v1
    assert comparison.degradation_flags == []
