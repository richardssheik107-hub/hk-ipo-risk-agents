from decimal import Decimal

import pytest

from ipo_risk.skills.financial import (
    cash_runway,
    cash_runway_from_operating_cash_flow,
)


def test_legacy_cash_runway_remains_compatible() -> None:
    assert cash_runway(120, 10).value == 12


def test_real_case_uses_decimal_and_preserves_audit_metadata() -> None:
    result = cash_runway_from_operating_cash_flow(
        Decimal("77208"),
        Decimal("-83918"),
        3,
        ["cash-evidence", "ocf-evidence"],
        currency="CNY",
        source_unit="thousand",
    )

    assert result.success
    assert isinstance(result.value, Decimal)
    assert result.value == Decimal("77208") * Decimal("3") / Decimal("83918")
    assert result.metadata["monthly_burn"] == Decimal("83918") / Decimal("3")
    assert result.metadata["rounded_months"] == Decimal("2.76")
    assert result.metadata["rounding"] == "ROUND_HALF_UP to 2 decimal places"
    assert result.evidence_ids == ["cash-evidence", "ocf-evidence"]


@pytest.mark.parametrize("period_months", [3, 6, 9, 12])
def test_supported_period_lengths_use_the_reported_period(period_months: int) -> None:
    result = cash_runway_from_operating_cash_flow(Decimal("120"), Decimal("-60"), period_months)
    assert result.success
    assert result.value == Decimal("120") * Decimal(period_months) / Decimal("60")


def test_zero_cash_is_a_valid_zero_month_runway() -> None:
    result = cash_runway_from_operating_cash_flow(Decimal("0"), Decimal("-10"), 3)
    assert result.success
    assert result.value == Decimal("0")
    assert result.metadata["rounded_months"] == Decimal("0.00")


@pytest.mark.parametrize(
    ("cash", "cash_flow", "period_months", "error"),
    [
        (Decimal("-1"), Decimal("-10"), 3, "cash must be non-negative"),
        (Decimal("10"), Decimal("0"), 3, "operating_cash_flow must be negative"),
        (Decimal("10"), Decimal("1"), 3, "operating_cash_flow must be negative"),
        (Decimal("10"), Decimal("-1"), None, "period_months must be one of"),
        (Decimal("10"), Decimal("-1"), 2, "period_months must be one of"),
    ],
)
def test_invalid_inputs_fail_without_division(
    cash: Decimal, cash_flow: Decimal, period_months: int | None, error: str
) -> None:
    result = cash_runway_from_operating_cash_flow(cash, cash_flow, period_months)
    assert not result.success
    assert error in (result.error or "")
    assert result.value is None


def test_repeated_skill_execution_is_deterministic() -> None:
    args = (Decimal("100"), Decimal("-25"), 3, ["a", "b"])
    assert cash_runway_from_operating_cash_flow(*args) == cash_runway_from_operating_cash_flow(*args)
