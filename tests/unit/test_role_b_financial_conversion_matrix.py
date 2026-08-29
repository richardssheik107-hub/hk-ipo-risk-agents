from __future__ import annotations

import pytest

from scripts.audit_v046_financial_conversion_matrix import _classify, _diagnostic_code


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"risk_code": "redemption_rights"}, ("J", "unavailable_by_runtime_mode")),
        ({"correct": True}, ("I", "correct")),
        ({"top20_hit": False}, ("A", "candidate_missing")),
        (
            {"final_present": False, "deterministic_fact_created": True},
            ("C", "fact_but_no_risk"),
        ),
        ({"final_present": False}, ("B", "consumed_but_no_fact")),
        ({"status_match": False}, ("D", "risk_but_wrong_status")),
        ({"level_match": False}, ("E", "risk_but_wrong_level")),
        ({"evidence_match": False}, ("F", "risk_correct_but_evidence_lost")),
    ],
)
def test_conversion_matrix_classifies_first_failure(
    overrides: dict[str, object], expected: tuple[str, str]
) -> None:
    values: dict[str, object] = {
        "risk_code": "cash_runway",
        "correct": False,
        "top20_hit": True,
        "final_present": True,
        "status_match": True,
        "level_match": True,
        "evidence_match": True,
        "deterministic_fact_created": False,
        "diagnostic": "",
    }
    values.update(overrides)

    assert _classify(**values) == expected


def test_conversion_matrix_preserves_true_conflict_fail_closed() -> None:
    assert _classify(
        risk_code="supplier_concentration",
        correct=False,
        top20_hit=True,
        final_present=False,
        status_match=False,
        level_match=False,
        evidence_match=False,
        deterministic_fact_created=False,
        diagnostic="issues=['conflicting_values_for_same_period']",
    ) == ("H", "true_conflict_fail_closed")


def test_conversion_matrix_uses_residual_reconciliation_category() -> None:
    assert _classify(
        risk_code="customer_concentration",
        correct=False,
        top20_hit=True,
        final_present=True,
        status_match=True,
        level_match=True,
        evidence_match=True,
        deterministic_fact_created=True,
        diagnostic="",
    ) == ("G", "verifier_or_reconciliation_drop")


def test_conversion_matrix_reads_component_diagnostic_code() -> None:
    assert _diagnostic_code(
        "ComponentDiagnostic(risk_code='customer_concentration', "
        "code=<DiagnosticCode.NOT_APPLICABLE: 'not_applicable'>)"
    ) == "not_applicable"
