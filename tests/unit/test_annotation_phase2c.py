from pathlib import Path

from ipo_risk.quality.annotation_audit import STATUS_INSUFFICIENT, STATUS_POLICY
from ipo_risk.quality.annotation_phase2c import (
    period_signature_v112,
    resolve_canonical_outcome,
    run_phase2c,
)

ROOT = Path(__file__).resolve().parents[2]


def _record(status="needs_review", level=None, applicable=True):
    return {
        "risk_code": "revenue_growth",
        "applicable": applicable,
        "expected_status": status,
        "expected_level": level,
    }


def test_v112_recognizes_chinese_full_year_period():
    assert period_signature_v112("截至2020年12月31日止年度") == "FY"


def test_zero_revenue_growth_closes_as_not_applicable_without_fake_percentage():
    outcome = {
        "re_audit_status": STATUS_POLICY,
        "finding_code": "OPEN_01_ZERO_REVENUE_GROWTH",
        "normalized_facts": {"zero_revenue_fields": ["revenue_from", "revenue_to"]},
    }
    resolved = resolve_canonical_outcome(_record(), outcome)
    assert resolved["resolved_state"] == {
        "applicable": False,
        "expected_status": "rejected",
        "expected_level": "not_applicable",
    }
    assert resolved["action"] == "APPLY_AUDIT_OVERLAY_RELABEL"


def test_multi_period_policy_keeps_most_adverse_valid_state():
    record = {
        "risk_code": "supplier_concentration",
        "applicable": True,
        "expected_status": "verified",
        "expected_level": "high",
    }
    outcome = {
        "re_audit_status": STATUS_POLICY,
        "finding_code": "POLICY_AMBIGUITY_CONCENTRATION_PERIOD",
        "normalized_facts": [
            {"period": "FY2018", "level": "medium"},
            {"period": "FY2019", "level": "high"},
            {"period": "7M2020", "level": "not_applicable"},
        ],
    }
    resolved = resolve_canonical_outcome(record, outcome)
    assert resolved["resolved_state"]["expected_level"] == "high"
    assert resolved["action"] == "CONFIRM_EXISTING"


def test_true_numeric_gap_closes_as_explicit_review_state():
    record = {
        "risk_code": "supplier_concentration",
        "applicable": True,
        "expected_status": "needs_review",
        "expected_level": None,
    }
    outcome = {
        "re_audit_status": STATUS_INSUFFICIENT,
        "finding_code": "PHASE2B_CONCENTRATION_FACTS_STILL_INSUFFICIENT",
    }
    resolved = resolve_canonical_outcome(record, outcome)
    assert resolved["resolved_state"] == {
        "applicable": True,
        "expected_status": "needs_review",
        "expected_level": None,
    }
    assert resolved["closure_status"] == "CLOSED"
    assert resolved["action"] == "CONFIRM_EXISTING"


def test_full_repository_closes_frozen_financial_issue_set(tmp_path):
    summary = run_phase2c(ROOT, tmp_path, write_artifacts=False)
    assert summary["cases_scanned"] == 60
    assert summary["phase1_policy_records"] == 33
    assert summary["phase1_insufficient_records"] == 142
    assert summary["financial_issue_records_total"] == 175
    assert summary["financial_issue_records_closed"] == 175
    assert summary["remaining_unresolved"] == 0
    assert summary["insufficient_priority_counts"] == {
        "P0_POSITIVE_OR_NEEDS_REVIEW": 51,
        "P1_REJECTED_LABEL_BACKFILL": 91,
    }
    assert summary["pass1_unchanged"] is True
