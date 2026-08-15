from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.quality.annotation_audit import STATUS_INSUFFICIENT, STATUS_PASS, STATUS_POLICY
from ipo_risk.quality.annotation_backfill_normalizers_v2 import canonicalize_record
from ipo_risk.quality.annotation_phase2b import run_phase2b

ROOT = Path(".")


def _record(case_id: str, risk_code: str):
    bundle = json.loads(
        (ROOT / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json").read_text(encoding="utf-8")
    )
    return next(row for row in bundle["risks"] if row["risk_code"] == risk_code)


def test_remaining_structured_aliases_resolve_without_prose_parsing():
    expected = {
        ("ipo_2020_01408", "supplier_concentration"): (STATUS_PASS, "high"),
        ("ipo_2020_01961", "revenue_growth"): (STATUS_PASS, "medium"),
        ("ipo_2020_01961", "supplier_concentration"): (STATUS_PASS, "medium"),
        ("ipo_2020_02135", "revenue_growth"): (STATUS_PASS, "high"),
        ("ipo_2020_08489", "supplier_concentration"): (STATUS_PASS, "medium"),
        ("ipo_2020_09986", "revenue_growth"): (STATUS_PASS, "high"),
        ("ipo_2021_02137", "supplier_concentration"): (STATUS_PASS, "high"),
        ("ipo_2021_02160", "continuous_loss"): (STATUS_PASS, "medium"),
        ("ipo_2021_02235", "continuous_loss"): (STATUS_PASS, "medium"),
    }
    for (case_id, risk_code), (status, level) in expected.items():
        result = canonicalize_record(_record(case_id, risk_code))
        assert result["re_audit_status"] == status, (case_id, risk_code, result)
        assert result["recomputed_level"] == level, (case_id, risk_code, result)


def test_cross_period_legacy_shapes_become_policy_not_false_insufficient():
    for case_id, risk_code in (
        ("ipo_2020_02599", "supplier_concentration"),
        ("ipo_2020_08489", "revenue_growth"),
        ("ipo_2021_09898", "revenue_growth"),
    ):
        result = canonicalize_record(_record(case_id, risk_code))
        assert result["re_audit_status"] == STATUS_POLICY, (case_id, risk_code, result)


def test_pre_revenue_customer_denominator_becomes_open01_policy():
    result = canonicalize_record(_record("ipo_2021_02137", "customer_concentration"))
    assert result["re_audit_status"] == STATUS_POLICY
    assert result["finding_code"] == "OPEN_01_ZERO_REVENUE_CONCENTRATION"


def test_02263_supplier_remains_true_numeric_evidence_gap():
    result = canonicalize_record(_record("ipo_2020_02263", "supplier_concentration"))
    assert result["re_audit_status"] == STATUS_INSUFFICIENT
    assert result["finding_code"] == "PHASE2B_CONCENTRATION_FACTS_STILL_INSUFFICIENT"


def test_full_phase2b_reduces_structured_insufficient_to_one(tmp_path):
    summary = run_phase2b(ROOT, tmp_path, write_backfills=False)
    assert summary["p0_records_targeted"] == 51
    assert summary["re_audit_status_counts"] == {
        "INSUFFICIENT_INPUT": 1,
        "PASS": 32,
        "POLICY_AMBIGUITY": 18,
    }
    assert summary["pass1_unchanged"] is True
