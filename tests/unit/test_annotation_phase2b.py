from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.quality.annotation_audit import STATUS_PASS, STATUS_POLICY
from ipo_risk.quality.annotation_backfill_normalizers import canonicalize_record
from ipo_risk.quality.annotation_phase2b import run_phase2b


ROOT = Path(".")


def _record(case_id: str, risk_code: str):
    path = ROOT / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    return next(row for row in bundle["risks"] if row["risk_code"] == risk_code)


def test_legacy_cash_aliases_backfill_00368():
    result = canonicalize_record(_record("ipo_2020_00368", "cash_runway"))
    assert result["re_audit_status"] == STATUS_PASS
    assert result["recomputed_level"] == "critical"
    assert result["canonical_calculation_inputs"]["cash"] == 9529


def test_comparable_full_year_loss_alias_backfill_01167():
    result = canonicalize_record(_record("ipo_2020_01167", "continuous_loss"))
    assert result["re_audit_status"] == STATUS_PASS
    assert result["recomputed_level"] == "medium"
    assert len(result["canonical_calculation_inputs"]["loss_periods"]) == 2


def test_zero_revenue_growth_remains_policy_01167():
    result = canonicalize_record(_record("ipo_2020_01167", "revenue_growth"))
    assert result["re_audit_status"] == STATUS_POLICY
    assert result["finding_code"] == "REVENUE_GROWTH_DENOMINATOR_NONPOSITIVE"


def test_exact_amount_ratio_backfill_06063_customer():
    result = canonicalize_record(_record("ipo_2020_06063", "customer_concentration"))
    assert result["re_audit_status"] == STATUS_PASS
    assert result["recomputed_level"] == "high"
    assert result["canonical_calculation_inputs"]["top_five_customer_pct"] > 80


def test_multiple_comparable_duration_groups_same_level_are_safe_06628():
    result = canonicalize_record(_record("ipo_2021_06628", "continuous_loss"))
    assert result["re_audit_status"] == STATUS_PASS
    assert result["recomputed_level"] == "medium"


def test_concentration_period_state_change_stays_policy_06628():
    result = canonicalize_record(_record("ipo_2021_06628", "supplier_concentration"))
    assert result["re_audit_status"] == STATUS_POLICY
    assert result["finding_code"] == "POLICY_AMBIGUITY_CONCENTRATION_PERIOD"


def test_revenue_multiple_period_levels_stay_policy_00013():
    result = canonicalize_record(_record("ipo_2021_00013", "revenue_growth"))
    assert result["re_audit_status"] == STATUS_POLICY
    assert result["finding_code"] == "POLICY_AMBIGUITY_REVENUE_PERIOD_AGGREGATION"


def test_open01_single_zero_revenue_fact_stays_policy_02179():
    result = canonicalize_record(_record("ipo_2022_02179", "revenue_growth"))
    assert result["re_audit_status"] == STATUS_POLICY
    assert result["finding_code"] == "OPEN_01_ZERO_REVENUE_GROWTH"


def test_phase2b_targets_exactly_existing_p0_51_without_pass1_mutation(tmp_path):
    summary = run_phase2b(ROOT, tmp_path, write_backfills=False)
    assert summary["p0_records_targeted"] == 51
    assert summary["pass1_unchanged"] is True
    assert summary["pass1_file_count"] == 80
    assert sum(summary["re_audit_status_counts"].values()) == 51


def test_phase2b_production_code_does_not_hardcode_case_ids():
    source = (ROOT / "src/ipo_risk/quality/annotation_backfill_normalizers.py").read_text(encoding="utf-8")
    for case_id in (
        "ipo_2020_00368",
        "ipo_2020_01167",
        "ipo_2020_06063",
        "ipo_2021_00013",
        "ipo_2021_06628",
        "ipo_2022_02179",
    ):
        assert case_id not in source
