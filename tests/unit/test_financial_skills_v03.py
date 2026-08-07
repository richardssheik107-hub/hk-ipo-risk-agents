from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.skills.financial import (
    FinancialPeriodInput,
    continuous_loss,
    counterparty_concentration,
    customer_concentration,
    revenue_growth,
    supplier_concentration,
)


def period(
    value: Decimal | int | float | str | None,
    period_end: date | str | None,
    *,
    period_months: int | None = 12,
    currency: str | None = "CNY",
    source_unit: str | None = "thousand",
    evidence_ids: tuple[str, ...] = (),
) -> FinancialPeriodInput:
    return FinancialPeriodInput(
        value=value,
        period_end=period_end,
        period_months=period_months,
        currency=currency,
        source_unit=source_unit,
        evidence_ids=evidence_ids,
    )


@pytest.mark.parametrize("count", [2, 3])
def test_continuous_loss_counts_latest_comparable_annual_losses(count: int) -> None:
    observations = [
        period(f"-{index + 1}", date(2020 + index, 12, 31), evidence_ids=(f"e-{index}",))
        for index in range(count)
    ]

    result = continuous_loss(observations)

    assert result.success
    assert result.value == count
    assert result.skill_version == "1.0"
    assert result.metadata["latest_loss_period_count"] == count
    assert result.metadata["period_months"] == 12
    assert result.evidence_ids == [f"e-{index}" for index in range(count)]


def test_continuous_loss_is_order_independent_and_profit_interrupts_streak() -> None:
    result = continuous_loss(
        [
            period("-30", "2023-12-31", evidence_ids=("latest",)),
            period("10", "2022-12-31", evidence_ids=("profit",)),
            period("-10", "2021-12-31", evidence_ids=("old-loss",)),
        ]
    )

    assert result.success
    assert result.value == 1
    assert result.metadata["latest_loss_periods"] == ["2023-12-31"]
    assert result.evidence_ids == ["latest", "profit", "old-loss"]


@pytest.mark.parametrize("latest_value", ["0", "1"])
def test_continuous_loss_latest_zero_or_profit_has_no_latest_loss_streak(
    latest_value: str,
) -> None:
    result = continuous_loss(
        [period("-1", "2022-12-31"), period(latest_value, "2023-12-31")]
    )

    assert result.success
    assert result.value == 0


@pytest.mark.parametrize(
    ("changed", "error"),
    [
        ({"period_months": 6}, "period_months_mismatch"),
        ({"currency": "HKD"}, "currency_mismatch"),
        ({"source_unit": "million"}, "source_unit_mismatch"),
    ],
)
def test_continuous_loss_rejects_incomparable_periods(
    changed: dict[str, object], error: str
) -> None:
    first = period("-1", "2022-12-31", evidence_ids=("first",))
    second = period("-2", "2023-12-31", evidence_ids=("second",))
    second = FinancialPeriodInput(
        value=second.value,
        period_end=second.period_end,
        period_months=changed.get("period_months", second.period_months),
        currency=changed.get("currency", second.currency),
        source_unit=changed.get("source_unit", second.source_unit),
        evidence_ids=second.evidence_ids,
    )

    result = continuous_loss([first, second])

    assert not result.success
    assert result.error == error
    assert result.evidence_ids == ["first", "second"]


@pytest.mark.parametrize(
    ("observation", "error"),
    [
        (period(None, "2023-12-31", evidence_ids=("missing",)), "net_result_missing_or_invalid"),
        (period(True, "2023-12-31", evidence_ids=("bool",)), "net_result_missing_or_invalid"),
        (period("-1", "31/12/2023", evidence_ids=("date",)), "period_end_invalid"),
        (period("-1", "2023-12-31", period_months=None, evidence_ids=("months",)), "period_months_invalid"),
    ],
)
def test_continuous_loss_invalid_input_fails_and_retains_evidence(
    observation: FinancialPeriodInput, error: str
) -> None:
    result = continuous_loss([observation])

    assert not result.success
    assert result.error == error
    assert result.evidence_ids == list(observation.evidence_ids)


def test_stage_one_two_annual_losses_produce_count_two() -> None:
    result = continuous_loss(
        [
            period("-732949", "2021-12-31", evidence_ids=("loss-2021",)),
            period("-402894", "2022-12-31", evidence_ids=("loss-2022",)),
        ]
    )

    assert result.success
    assert result.value == 2


def growth_inputs(
    previous_value: Decimal | int | float | str | None,
    current_value: Decimal | int | float | str | None,
    **current_changes: object,
) -> tuple[FinancialPeriodInput, FinancialPeriodInput]:
    previous = period(
        previous_value,
        current_changes.get("previous_period_end", "2022-12-31"),
        period_months=current_changes.get("previous_period_months", 12),
        evidence_ids=("previous-evidence",),
    )
    current = period(
        current_value,
        current_changes.get("period_end", "2023-12-31"),
        period_months=current_changes.get("period_months", 12),
        currency=current_changes.get("currency", "CNY"),
        source_unit=current_changes.get("source_unit", "thousand"),
        evidence_ids=("current-evidence",),
    )
    return previous, current


@pytest.mark.parametrize(
    ("previous_value", "current_value", "expected"),
    [
        ("100", "120", Decimal("20")),
        ("100", "100", Decimal("0")),
        ("100", "99.999", Decimal("-0.001")),
        ("100", "80", Decimal("-20")),
        ("100", "79.999", Decimal("-20.001")),
        ("100", "0", Decimal("-100")),
    ],
)
def test_revenue_growth_uses_consistent_percentage_semantics(
    previous_value: str, current_value: str, expected: Decimal
) -> None:
    result = revenue_growth(*growth_inputs(previous_value, current_value))

    assert result.success
    assert isinstance(result.value, Decimal)
    assert result.value == expected
    assert result.metadata["output_unit"] == "percent"
    assert result.evidence_ids == ["previous-evidence", "current-evidence"]


def test_revenue_growth_keeps_exact_decimal_and_rounds_display_half_up() -> None:
    result = revenue_growth(*growth_inputs("8", "8.0804"))

    assert result.success
    assert result.value == Decimal("1.00500")
    assert result.metadata["rounded_percentage"] == Decimal("1.01")
    assert result.metadata["rounding"] == "ROUND_HALF_UP to 2 decimal places for display"


def test_revenue_growth_safely_accepts_float_compatibility_inputs() -> None:
    result = revenue_growth(*growth_inputs(100.0, 80.0))

    assert result.success
    assert result.value == Decimal("-20.0")


@pytest.mark.parametrize(
    ("previous_value", "current_value", "error"),
    [
        ("0", "1", "previous_revenue_must_be_positive"),
        ("-1", "1", "revenue_must_be_non_negative"),
        ("1", "-1", "revenue_must_be_non_negative"),
        (None, "1", "revenue_missing_or_invalid"),
        (True, "1", "revenue_missing_or_invalid"),
        ("not-a-number", "1", "revenue_missing_or_invalid"),
        ("NaN", "1", "revenue_missing_or_invalid"),
        ("Infinity", "1", "revenue_missing_or_invalid"),
    ],
)
def test_revenue_growth_rejects_invalid_values_and_retains_evidence(
    previous_value: object, current_value: object, error: str
) -> None:
    result = revenue_growth(*growth_inputs(previous_value, current_value))

    assert not result.success
    assert result.error == error
    assert result.evidence_ids == ["previous-evidence", "current-evidence"]


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"period_months": 6}, "period_months_mismatch"),
        ({"currency": "HKD"}, "currency_mismatch"),
        ({"source_unit": "million"}, "source_unit_mismatch"),
        ({"period_end": "2021-12-31"}, "period_order_invalid"),
        ({"period_end": "31/12/2023"}, "period_end_invalid"),
    ],
)
def test_revenue_growth_rejects_incomparable_periods(
    changes: dict[str, object], error: str
) -> None:
    result = revenue_growth(*growth_inputs("100", "90", **changes))

    assert not result.success
    assert result.error == error


@pytest.mark.parametrize(
    (
        "previous_value",
        "current_value",
        "previous_end",
        "current_end",
        "period_months",
        "rounded",
    ),
    [
        ("5067", "538", "2021-12-31", "2022-12-31", 12, Decimal("-89.38")),
        ("9917234", "8663655", "2019-05-31", "2020-05-31", 5, Decimal("-12.64")),
        ("44242", "0", "2022-12-31", "2023-12-31", 12, Decimal("-100.00")),
        ("371857", "495780", "2022-06-30", "2023-06-30", 6, Decimal("33.33")),
    ],
)
def test_stage_one_revenue_values_regress_through_generic_skill(
    previous_value: str,
    current_value: str,
    previous_end: str,
    current_end: str,
    period_months: int,
    rounded: Decimal,
) -> None:
    result = revenue_growth(
        *growth_inputs(
            previous_value,
            current_value,
            previous_period_end=previous_end,
            period_end=current_end,
            previous_period_months=period_months,
            period_months=period_months,
        )
    )

    assert result.success
    assert result.metadata["rounded_percentage"] == rounded
    assert result.metadata["periods"]["period_months"] == period_months


@pytest.mark.parametrize(
    ("largest", "top_five"),
    [
        ("29.99", "59.99"),
        ("30", "60"),
        ("50", "60"),
        ("30", "60"),
        ("50", "80"),
    ],
)
def test_concentration_preserves_threshold_boundary_percentages(
    largest: str, top_five: str
) -> None:
    result = customer_concentration(
        largest_counterparty_pct=largest,
        top_five_pct=top_five,
        evidence_ids=("largest-e", "top-five-e"),
    )

    assert result.success
    assert result.value == {
        "largest_counterparty_pct": Decimal(largest),
        "top_five_pct": Decimal(top_five),
    }
    assert result.metadata["output_unit"] == "percent"
    assert result.evidence_ids == ["largest-e", "top-five-e"]


def test_disclosed_point_five_percent_is_not_silently_scaled_to_fifty() -> None:
    small = customer_concentration(largest_counterparty_pct="0.5")
    fifty = customer_concentration(largest_counterparty_pct="50")

    assert small.value["largest_counterparty_pct"] == Decimal("0.5")
    assert fifty.value["largest_counterparty_pct"] == Decimal("50")


def test_fractional_ratio_scale_is_rejected_instead_of_mixed_with_percent() -> None:
    result = customer_concentration(
        largest_counterparty_pct="0.5", percentage_scale="ratio"
    )

    assert not result.success
    assert result.error == "percentage_scale_must_be_percent"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"largest_counterparty_pct": "100.01"}, "percentage_out_of_range"),
        ({"largest_counterparty_pct": "-0.01"}, "percentage_out_of_range"),
        (
            {"largest_counterparty_pct": "70", "top_five_pct": "60"},
            "largest_percentage_exceeds_top_five",
        ),
        ({"largest_counterparty_pct": True}, "largest_percentage_invalid"),
        ({}, "concentration_values_required"),
    ],
)
def test_concentration_rejects_invalid_disclosed_percentages(
    kwargs: dict[str, object], error: str
) -> None:
    result = customer_concentration(evidence_ids=("known",), **kwargs)

    assert not result.success
    assert result.error == error
    assert result.evidence_ids == ["known"]


def test_concentration_calculates_percentages_from_decimal_amounts() -> None:
    result = counterparty_concentration(
        "customer",
        largest_counterparty_amount=Decimal("37.5"),
        top_five_amount=Decimal("68"),
        total_amount=Decimal("100"),
        currency="HKD",
        source_unit="million",
        evidence_ids=("amounts", "total"),
    )

    assert result.success
    assert result.value == {
        "largest_counterparty_pct": Decimal("37.500"),
        "top_five_pct": Decimal("68.00"),
    }
    assert result.metadata["input_mode"] == "amount_ratio"
    assert result.metadata["currency"] == "HKD"
    assert result.metadata["source_unit"] == "million"


@pytest.mark.parametrize("total", ["0", "-1"])
def test_concentration_amount_denominator_must_be_positive(total: str) -> None:
    result = supplier_concentration(
        largest_counterparty_amount="1",
        total_amount=total,
        currency="CNY",
        source_unit="thousand",
        evidence_ids=("supplier",),
    )

    assert not result.success
    assert result.error == "total_amount_must_be_positive"
    assert result.evidence_ids == ["supplier"]


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"currency": None}, "currency_missing"),
        ({"source_unit": None}, "source_unit_missing"),
        ({"largest_counterparty_amount": "NaN"}, "largest_amount_invalid"),
    ],
)
def test_concentration_amount_inputs_require_diagnostic_context(
    changes: dict[str, object], error: str
) -> None:
    kwargs = {
        "largest_counterparty_amount": "10",
        "total_amount": "100",
        "currency": "CNY",
        "source_unit": "thousand",
        "evidence_ids": ("amount", "total"),
        **changes,
    }

    result = customer_concentration(**kwargs)

    assert not result.success
    assert result.error == error
    assert result.evidence_ids == ["amount", "total"]


def test_concentration_rejects_mixed_amount_and_percentage_modes() -> None:
    result = customer_concentration(
        largest_counterparty_pct="30",
        top_five_amount="60",
        total_amount="100",
    )

    assert not result.success
    assert result.error == "mixed_percentage_and_amount_inputs"


def test_concentration_type_is_explicit_in_skill_and_metadata() -> None:
    customer = customer_concentration(largest_counterparty_pct="30")
    supplier = supplier_concentration(largest_counterparty_pct="30")
    invalid = counterparty_concentration("partner", largest_counterparty_pct="30")

    assert customer.skill_name == "customer_concentration"
    assert customer.metadata["concentration_type"] == "customer"
    assert supplier.skill_name == "supplier_concentration"
    assert supplier.metadata["concentration_type"] == "supplier"
    assert not invalid.success
    assert invalid.error == "concentration_type_invalid"


@pytest.mark.parametrize(
    ("skill", "largest", "top_five"),
    [
        (customer_concentration, "37.5", "68.0"),
        (supplier_concentration, "22.6", "68.0"),
    ],
)
def test_stage_one_concentration_values_regress_through_generic_skills(
    skill, largest: str, top_five: str
) -> None:
    result = skill(
        largest_counterparty_pct=largest,
        top_five_pct=top_five,
        evidence_ids=("largest", "top-five"),
    )

    assert result.success
    assert result.value["largest_counterparty_pct"] == Decimal(largest)
    assert result.value["top_five_pct"] == Decimal(top_five)
    assert result.metadata["rounded_percentages"] == {
        "largest_counterparty_pct": Decimal(largest).quantize(Decimal("0.01")),
        "top_five_pct": Decimal(top_five).quantize(Decimal("0.01")),
    }
