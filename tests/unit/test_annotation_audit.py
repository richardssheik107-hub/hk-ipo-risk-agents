from __future__ import annotations

from pathlib import Path

import pytest

from ipo_risk.quality.annotation_audit import (
    STATUS_HARD,
    STATUS_POLICY,
    _state_is_valid,
    audit_case,
    audit_cash_runway,
    audit_concentration,
    audit_continuous_loss,
    audit_revenue_growth,
)


def record(risk_code: str, *, applicable=True, status="verified", level="medium", inputs=None):
    return {
        "risk_code": risk_code,
        "applicable": applicable,
        "expected_status": status,
        "expected_level": level,
        "calculation_required": risk_code
        in {"cash_runway", "revenue_growth", "customer_concentration", "supplier_concentration"},
        "calculation_inputs": inputs,
        "calculation_result": {},
    }


@pytest.mark.parametrize(
    ("months", "level"),
    [
        (2.999, "critical"),
        (3.0, "high"),
        (5.999, "high"),
        (6.0, "medium"),
        (11.999, "medium"),
        (12.0, "not_applicable"),
    ],
)
def test_cash_runway_boundaries(months: float, level: str):
    cash = 120.0
    monthly_burn = cash / months
    if level == "not_applicable":
        r = record("cash_runway", applicable=False, status="rejected", level="not_applicable",
                   inputs={"cash": cash, "monthly_cash_burn": monthly_burn})
    else:
        r = record("cash_runway", level=level, inputs={"cash": cash, "monthly_cash_burn": monthly_burn})
    assert audit_cash_runway("fixture", r).audit_status == "PASS"


@pytest.mark.parametrize(
    ("largest", "top5", "level"),
    [
        (29.9, 59.9, "not_applicable"),
        (30.0, 10.0, "medium"),
        (10.0, 60.0, "medium"),
        (50.0, 10.0, "high"),
        (10.0, 80.0, "high"),
    ],
)
def test_concentration_boundaries(largest: float, top5: float, level: str):
    kwargs = {}
    if level == "not_applicable":
        kwargs = {"applicable": False, "status": "rejected", "level": "not_applicable"}
    else:
        kwargs = {"level": level}
    r = record(
        "customer_concentration",
        inputs={"largest_customer_pct": largest, "top_five_customer_pct": top5},
        **kwargs,
    )
    assert audit_concentration("fixture", r, "customer").audit_status == "PASS"


@pytest.mark.parametrize(
    ("previous", "current", "level"),
    [
        (100.0, 80.0, "high"),
        (100.0, 79.9, "high"),
        (100.0, 99.9, "medium"),
        (100.0, 100.0, "not_applicable"),
        (100.0, 120.0, "not_applicable"),
    ],
)
def test_revenue_growth_boundaries(previous: float, current: float, level: str):
    kwargs = {}
    if level == "not_applicable":
        kwargs = {"applicable": False, "status": "rejected", "level": "not_applicable"}
    else:
        kwargs = {"level": level}
    r = record(
        "revenue_growth",
        inputs={"previous_revenue": previous, "current_revenue": current},
        **kwargs,
    )
    assert audit_revenue_growth("fixture", r).audit_status == "PASS"


def test_continuous_loss_three_comparable_periods_is_high():
    r = record(
        "continuous_loss",
        level="high",
        inputs={
            "loss_periods": [
                {"period": "year ended December 31, 2019", "loss": -1},
                {"period": "year ended December 31, 2020", "loss": -2},
                {"period": "year ended December 31, 2021", "loss": -3},
            ]
        },
    )
    assert audit_continuous_loss("fixture", r).audit_status == "PASS"


def test_continuous_loss_mixed_period_types_requires_policy_review():
    r = record(
        "continuous_loss",
        level="high",
        inputs={
            "loss_periods": [
                {"period": "year ended December 31, 2020", "loss": -1},
                {"period": "year ended December 31, 2021", "loss": -2},
                {"period": "eight months ended August 31, 2021", "loss": -3},
                {"period": "eight months ended August 31, 2022", "loss": -4},
            ]
        },
    )
    finding = audit_continuous_loss("fixture", r)
    assert finding.audit_status == STATUS_POLICY
    assert finding.finding_code == "COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS"


def test_state_table_rejects_inconsistent_rejected_level():
    assert not _state_is_valid(
        {"applicable": False, "expected_status": "rejected", "expected_level": "medium"}
    )


@pytest.mark.parametrize(
    ("case_id", "risk_code"),
    [
        ("ipo_2022_02145", "cash_runway"),
        ("ipo_2022_06922", "customer_concentration"),
        ("ipo_2022_09863", "supplier_concentration"),
    ],
)
def test_known_regression_cases_are_caught(case_id: str, risk_code: str):
    path = Path("expert_results") / case_id / "pass1" / "expert_annotation_v1.json"
    assert path.exists(), f"missing regression fixture: {path}"
    result = audit_case(path)
    finding = next(row for row in result["findings"] if row["risk_code"] == risk_code)
    assert finding["audit_status"] == STATUS_HARD
    assert finding["recomputed_level"] in {"medium", "not_applicable"}


def test_regression_values_are_not_hard_coded_in_production_source():
    source = Path("src/ipo_risk/quality/annotation_audit.py").read_text(encoding="utf-8")
    for case_id in ("ipo_2022_02145", "ipo_2022_06922", "ipo_2022_09863"):
        assert case_id not in source
