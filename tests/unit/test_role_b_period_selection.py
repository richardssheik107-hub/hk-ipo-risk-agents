from ipo_risk.evaluation.role_b_period_selection import (
    PeriodSelectionEvidence,
    classify_period_selection,
    extract_component_metadata,
    period_candidates,
    summarize_candidates,
)


def evidence(**updates) -> PeriodSelectionEvidence:
    values = {
        "retrieved_candidate_present": True,
        "parser_text_present": True,
        "correct_period_candidate_present": True,
        "correct_value_candidate_present": True,
        "currency_unit_compatible": True,
        "compatible_pair_exists": True,
        "same_period_conflict_detected": False,
        "selected_period_matches": True,
    }
    values.update(updates)
    return PeriodSelectionEvidence(**values)


def test_selector_bug_requires_every_upstream_fact_and_wrong_selection() -> None:
    assert classify_period_selection(evidence(selected_period_matches=False)) == (
        "period_selection_bug"
    )
    assert classify_period_selection(evidence()) == "correct"


def test_missing_period_and_value_are_not_mislabeled_as_selector_bugs() -> None:
    assert classify_period_selection(
        evidence(correct_period_candidate_present=False, selected_period_matches=False)
    ) == "period_candidate_missing"
    assert classify_period_selection(
        evidence(correct_value_candidate_present=False, selected_period_matches=False)
    ) == "numeric_extraction_miss"


def test_real_same_period_conflict_remains_fail_closed() -> None:
    assert classify_period_selection(
        evidence(same_period_conflict_detected=True, selected_period_matches=False)
    ) == "conflict_fail_closed"


def test_missing_or_incompatible_pair_remains_unresolved() -> None:
    assert classify_period_selection(
        evidence(compatible_pair_exists=False, selected_period_matches=False)
    ) == "deterministic_fact_missing"
    assert classify_period_selection(
        evidence(currency_unit_compatible=False, selected_period_matches=False)
    ) == "deterministic_fact_missing"


def test_legacy_component_repr_is_decoded_without_eval() -> None:
    serialized = (
        "[ComponentDiagnostic(risk_code='cash_runway', code='x', "
        "metadata={'issues': ['missing_period'], 'financial_conversion': "
        "{'cash': {'value': '10', 'period_end': '2024-12-31'}}})]"
    )
    metadata = extract_component_metadata(serialized, "cash_runway")
    assert metadata is not None
    candidates = period_candidates(metadata, "cash_runway")
    summary = summarize_candidates(candidates)
    assert summary["parsed_period_candidate_count"] == 1
    assert summary["parsed_value_candidate_count"] == 1
    assert "10" not in str(summary)


def test_concentration_summary_never_persists_raw_values() -> None:
    metadata = {
        "candidate_diagnostics": [
            {
                "period_end": "2024-06-30",
                "period_months": 6,
                "largest_counterparty_pct": "31.2",
                "top_five_pct": "62.4",
                "status": "extracted",
                "issues": [],
                "selected_for_merge": True,
            }
        ]
    }
    summary = summarize_candidates(period_candidates(metadata, "customer_concentration"))
    assert summary["parsed_period_candidates"] == [
        {"period_end": "2024-06-30", "period_months": 6}
    ]
    assert "31.2" not in str(summary)
    assert "62.4" not in str(summary)
