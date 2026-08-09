from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from ipo_risk.schemas import SkillResult


_RUNWAY_QUANTUM = Decimal("0.01")
_PERCENT_QUANTUM = Decimal("0.01")
_V03_FINANCIAL_SKILL_VERSION = "1.0"

NumericInput = Decimal | int | float | str | None


@dataclass(frozen=True, slots=True)
class FinancialPeriodInput:
    """Skill-layer financial value with period and Evidence traceability."""

    value: NumericInput
    period_end: date | str | None
    period_months: int | None
    currency: str | None
    source_unit: str | None
    evidence_ids: Sequence[str] = ()


def _as_decimal(value: NumericInput) -> Decimal | None:
    """Convert supported numeric inputs without performing binary-float arithmetic."""

    if value is None or isinstance(value, bool):
        return None
    try:
        converted = value if isinstance(value, Decimal) else Decimal(str(value))
        return converted if converted.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _as_date(value: date | str | None) -> date | None:
    """Convert an ISO date without accepting ambiguous date formats."""

    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _evidence_ids(*groups: Sequence[str]) -> list[str]:
    """Return non-empty Evidence IDs in stable first-seen order."""

    retained: list[str] = []
    for group in groups:
        values = (group,) if isinstance(group, str) else group
        for evidence_id in values:
            if evidence_id and evidence_id not in retained:
                retained.append(evidence_id)
    return retained


def _failure(
    skill_name: str,
    error: str,
    evidence_ids: Sequence[str],
    metadata: dict[str, Any],
) -> SkillResult:
    """Build a stable failed SkillResult without discarding diagnostic context."""

    return SkillResult(
        skill_name=skill_name,
        skill_version=_V03_FINANCIAL_SKILL_VERSION,
        success=False,
        evidence_ids=list(evidence_ids),
        error=error,
        metadata=metadata,
    )


def _normalised_label(value: str | None, *, upper: bool = False) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    cleaned = value.strip()
    return cleaned.upper() if upper else cleaned.lower()


def continuous_loss(
    observations: Sequence[FinancialPeriodInput] | None,
) -> SkillResult:
    """Count the latest consecutive losses across comparable reported periods.

    Negative values are losses. Zero and positive values interrupt the latest
    loss streak. All supplied observations must share period length, currency,
    and source unit; annual and interim observations are never mixed.
    """

    skill_name = "continuous_loss"
    items = list(observations or ())
    retained_evidence_ids = _evidence_ids(
        *(item.evidence_ids for item in items if isinstance(item, FinancialPeriodInput))
    )
    base_metadata: dict[str, Any] = {
        "rule": "count latest consecutive net_result values below zero",
        "zero_semantics": "zero is not a loss and interrupts the streak",
        "input_count": len(items),
        "output_unit": "periods",
    }
    if not items:
        return _failure(
            skill_name,
            "observations_required",
            retained_evidence_ids,
            base_metadata,
        )

    prepared: list[tuple[date, Decimal, int, str, str, list[str]]] = []
    for index, item in enumerate(items):
        if not isinstance(item, FinancialPeriodInput):
            return _failure(
                skill_name,
                "observation_type_invalid",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        numeric_value = _as_decimal(item.value)
        if numeric_value is None:
            return _failure(
                skill_name,
                "net_result_missing_or_invalid",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        period_end = _as_date(item.period_end)
        if period_end is None:
            return _failure(
                skill_name,
                "period_end_invalid",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        if (
            isinstance(item.period_months, bool)
            or not isinstance(item.period_months, int)
            or not 1 <= item.period_months <= 12
        ):
            return _failure(
                skill_name,
                "period_months_invalid",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        currency = _normalised_label(item.currency, upper=True)
        if currency is None:
            return _failure(
                skill_name,
                "currency_missing",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        source_unit = _normalised_label(item.source_unit)
        if source_unit is None:
            return _failure(
                skill_name,
                "source_unit_missing",
                retained_evidence_ids,
                {**base_metadata, "invalid_observation_index": index},
            )
        prepared.append(
            (
                period_end,
                numeric_value,
                item.period_months,
                currency,
                source_unit,
                _evidence_ids(item.evidence_ids),
            )
        )

    if len({item[0] for item in prepared}) != len(prepared):
        return _failure(
            skill_name,
            "duplicate_period_end",
            retained_evidence_ids,
            base_metadata,
        )
    if len({item[2] for item in prepared}) != 1:
        return _failure(
            skill_name,
            "period_months_mismatch",
            retained_evidence_ids,
            {
                **base_metadata,
                "period_months": sorted({item[2] for item in prepared}),
            },
        )
    if len({item[3] for item in prepared}) != 1:
        return _failure(
            skill_name,
            "currency_mismatch",
            retained_evidence_ids,
            {**base_metadata, "currencies": sorted({item[3] for item in prepared})},
        )
    if len({item[4] for item in prepared}) != 1:
        return _failure(
            skill_name,
            "source_unit_mismatch",
            retained_evidence_ids,
            {**base_metadata, "source_units": sorted({item[4] for item in prepared})},
        )

    ordered = sorted(prepared, key=lambda item: item[0])
    latest_loss_count = 0
    latest_loss_periods: list[str] = []
    for period_end, numeric_value, *_ in reversed(ordered):
        if numeric_value >= 0:
            break
        latest_loss_count += 1
        latest_loss_periods.append(period_end.isoformat())
    latest_loss_periods.reverse()
    inputs = [
        {
            "period_end": period_end.isoformat(),
            "period_months": period_months,
            "net_result": str(numeric_value),
            "currency": currency,
            "source_unit": source_unit,
            "evidence_ids": evidence,
        }
        for period_end, numeric_value, period_months, currency, source_unit, evidence in ordered
    ]
    return SkillResult(
        skill_name=skill_name,
        skill_version=_V03_FINANCIAL_SKILL_VERSION,
        success=True,
        value=latest_loss_count,
        evidence_ids=retained_evidence_ids,
        metadata={
            **base_metadata,
            "inputs": inputs,
            "period_months": ordered[0][2],
            "currency": ordered[0][3],
            "source_unit": ordered[0][4],
            "latest_loss_periods": latest_loss_periods,
            "latest_loss_period_count": latest_loss_count,
        },
    )


def revenue_growth(
    previous: FinancialPeriodInput,
    current: FinancialPeriodInput,
) -> SkillResult:
    """Calculate comparable-period revenue growth as an exact percentage."""

    skill_name = "revenue_growth"
    retained_evidence_ids = _evidence_ids(
        previous.evidence_ids if isinstance(previous, FinancialPeriodInput) else (),
        current.evidence_ids if isinstance(current, FinancialPeriodInput) else (),
    )
    base_metadata: dict[str, Any] = {
        "formula": "(current_revenue - previous_revenue) / previous_revenue * 100",
        "output_unit": "percent",
        "rounding": "ROUND_HALF_UP to 2 decimal places for display",
    }
    if not isinstance(previous, FinancialPeriodInput) or not isinstance(
        current, FinancialPeriodInput
    ):
        return _failure(
            skill_name,
            "period_input_type_invalid",
            retained_evidence_ids,
            base_metadata,
        )

    previous_value = _as_decimal(previous.value)
    current_value = _as_decimal(current.value)
    if previous_value is None or current_value is None:
        return _failure(
            skill_name,
            "revenue_missing_or_invalid",
            retained_evidence_ids,
            base_metadata,
        )
    if previous_value < 0 or current_value < 0:
        return _failure(
            skill_name,
            "revenue_must_be_non_negative",
            retained_evidence_ids,
            {
                **base_metadata,
                "previous_revenue": str(previous_value),
                "current_revenue": str(current_value),
            },
        )
    if previous_value == 0:
        return _failure(
            skill_name,
            "previous_revenue_must_be_positive",
            retained_evidence_ids,
            {
                **base_metadata,
                "previous_revenue": str(previous_value),
                "current_revenue": str(current_value),
            },
        )

    previous_end = _as_date(previous.period_end)
    current_end = _as_date(current.period_end)
    if previous_end is None or current_end is None:
        return _failure(
            skill_name,
            "period_end_invalid",
            retained_evidence_ids,
            base_metadata,
        )
    if current_end <= previous_end:
        return _failure(
            skill_name,
            "period_order_invalid",
            retained_evidence_ids,
            {
                **base_metadata,
                "previous_period_end": previous_end.isoformat(),
                "current_period_end": current_end.isoformat(),
            },
        )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 12
        for value in (previous.period_months, current.period_months)
    ):
        return _failure(
            skill_name,
            "period_months_invalid",
            retained_evidence_ids,
            base_metadata,
        )
    if previous.period_months != current.period_months:
        return _failure(
            skill_name,
            "period_months_mismatch",
            retained_evidence_ids,
            {
                **base_metadata,
                "period_months": [previous.period_months, current.period_months],
            },
        )

    previous_currency = _normalised_label(previous.currency, upper=True)
    current_currency = _normalised_label(current.currency, upper=True)
    if previous_currency is None or current_currency is None:
        return _failure(
            skill_name,
            "currency_missing",
            retained_evidence_ids,
            base_metadata,
        )
    if previous_currency != current_currency:
        return _failure(
            skill_name,
            "currency_mismatch",
            retained_evidence_ids,
            {
                **base_metadata,
                "currencies": [previous_currency, current_currency],
            },
        )
    previous_unit = _normalised_label(previous.source_unit)
    current_unit = _normalised_label(current.source_unit)
    if previous_unit is None or current_unit is None:
        return _failure(
            skill_name,
            "source_unit_missing",
            retained_evidence_ids,
            base_metadata,
        )
    if previous_unit != current_unit:
        return _failure(
            skill_name,
            "source_unit_mismatch",
            retained_evidence_ids,
            {**base_metadata, "source_units": [previous_unit, current_unit]},
        )

    exact_percentage = (
        (current_value - previous_value) / previous_value * Decimal("100")
    )
    rounded_percentage = exact_percentage.quantize(
        _PERCENT_QUANTUM, rounding=ROUND_HALF_UP
    )
    return SkillResult(
        skill_name=skill_name,
        skill_version=_V03_FINANCIAL_SKILL_VERSION,
        success=True,
        value=exact_percentage,
        evidence_ids=retained_evidence_ids,
        metadata={
            **base_metadata,
            "inputs": {
                "previous_revenue": str(previous_value),
                "current_revenue": str(current_value),
            },
            "periods": {
                "previous_period_end": previous_end.isoformat(),
                "current_period_end": current_end.isoformat(),
                "period_months": previous.period_months,
            },
            "currency": previous_currency,
            "source_unit": previous_unit,
            "rounded_percentage": rounded_percentage,
        },
    )


def counterparty_concentration(
    concentration_type: str,
    *,
    largest_counterparty_pct: NumericInput = None,
    top_five_pct: NumericInput = None,
    largest_counterparty_amount: NumericInput = None,
    top_five_amount: NumericInput = None,
    total_amount: NumericInput = None,
    evidence_ids: Sequence[str] = (),
    currency: str | None = None,
    source_unit: str | None = None,
    percentage_scale: str = "percent",
) -> SkillResult:
    """Validate or calculate customer/supplier concentration percentages.

    Direct percentage inputs always use percentage points in the 0..100 range.
    Fractional ratio scale inputs are rejected so 0.5 is never silently treated
    as 50 percent.
    """

    normalised_type = concentration_type.strip().lower() if isinstance(
        concentration_type, str
    ) else ""
    skill_name = (
        f"{normalised_type}_concentration"
        if normalised_type in {"customer", "supplier"}
        else "counterparty_concentration"
    )
    retained_evidence_ids = _evidence_ids(evidence_ids)
    base_metadata: dict[str, Any] = {
        "concentration_type": normalised_type or concentration_type,
        "output_unit": "percent",
        "percentage_scale": percentage_scale,
        "rounding": "ROUND_HALF_UP to 2 decimal places for display",
    }
    if normalised_type not in {"customer", "supplier"}:
        return _failure(
            skill_name,
            "concentration_type_invalid",
            retained_evidence_ids,
            base_metadata,
        )
    if percentage_scale != "percent":
        return _failure(
            skill_name,
            "percentage_scale_must_be_percent",
            retained_evidence_ids,
            base_metadata,
        )

    percentage_inputs_present = any(
        value is not None for value in (largest_counterparty_pct, top_five_pct)
    )
    amount_inputs_present = any(
        value is not None
        for value in (largest_counterparty_amount, top_five_amount, total_amount)
    )
    if percentage_inputs_present and amount_inputs_present:
        return _failure(
            skill_name,
            "mixed_percentage_and_amount_inputs",
            retained_evidence_ids,
            base_metadata,
        )
    if not percentage_inputs_present and not amount_inputs_present:
        return _failure(
            skill_name,
            "concentration_values_required",
            retained_evidence_ids,
            base_metadata,
        )

    largest_percentage: Decimal | None = None
    top_five_percentage: Decimal | None = None
    metadata = dict(base_metadata)
    if percentage_inputs_present:
        if largest_counterparty_pct is not None:
            largest_percentage = _as_decimal(largest_counterparty_pct)
            if largest_percentage is None:
                return _failure(
                    skill_name,
                    "largest_percentage_invalid",
                    retained_evidence_ids,
                    base_metadata,
                )
        if top_five_pct is not None:
            top_five_percentage = _as_decimal(top_five_pct)
            if top_five_percentage is None:
                return _failure(
                    skill_name,
                    "top_five_percentage_invalid",
                    retained_evidence_ids,
                    base_metadata,
                )
        metadata.update(
            {
                "input_mode": "disclosed_percentage",
                "formula": "use disclosed percentage points without rescaling",
                "inputs": {
                    "largest_counterparty_pct": (
                        str(largest_percentage)
                        if largest_percentage is not None
                        else None
                    ),
                    "top_five_pct": (
                        str(top_five_percentage)
                        if top_five_percentage is not None
                        else None
                    ),
                },
            }
        )
    else:
        total = _as_decimal(total_amount)
        if total is None:
            return _failure(
                skill_name,
                "total_amount_missing_or_invalid",
                retained_evidence_ids,
                base_metadata,
            )
        if total <= 0:
            return _failure(
                skill_name,
                "total_amount_must_be_positive",
                retained_evidence_ids,
                {**base_metadata, "total_amount": str(total)},
            )
        normalised_currency = _normalised_label(currency, upper=True)
        if normalised_currency is None:
            return _failure(
                skill_name,
                "currency_missing",
                retained_evidence_ids,
                base_metadata,
            )
        normalised_unit = _normalised_label(source_unit)
        if normalised_unit is None:
            return _failure(
                skill_name,
                "source_unit_missing",
                retained_evidence_ids,
                base_metadata,
            )
        largest_amount = (
            _as_decimal(largest_counterparty_amount)
            if largest_counterparty_amount is not None
            else None
        )
        top_five_amount_value = (
            _as_decimal(top_five_amount) if top_five_amount is not None else None
        )
        if largest_counterparty_amount is not None and largest_amount is None:
            return _failure(
                skill_name,
                "largest_amount_invalid",
                retained_evidence_ids,
                base_metadata,
            )
        if top_five_amount is not None and top_five_amount_value is None:
            return _failure(
                skill_name,
                "top_five_amount_invalid",
                retained_evidence_ids,
                base_metadata,
            )
        if largest_amount is None and top_five_amount_value is None:
            return _failure(
                skill_name,
                "concentration_numerator_required",
                retained_evidence_ids,
                base_metadata,
            )
        if any(
            value is not None and value < 0
            for value in (largest_amount, top_five_amount_value)
        ):
            return _failure(
                skill_name,
                "concentration_amount_must_be_non_negative",
                retained_evidence_ids,
                base_metadata,
            )
        largest_percentage = (
            largest_amount / total * Decimal("100")
            if largest_amount is not None
            else None
        )
        top_five_percentage = (
            top_five_amount_value / total * Decimal("100")
            if top_five_amount_value is not None
            else None
        )
        metadata.update(
            {
                "input_mode": "amount_ratio",
                "formula": "counterparty_amount / total_amount * 100",
                "inputs": {
                    "largest_counterparty_amount": (
                        str(largest_amount) if largest_amount is not None else None
                    ),
                    "top_five_amount": (
                        str(top_five_amount_value)
                        if top_five_amount_value is not None
                        else None
                    ),
                    "total_amount": str(total),
                },
                "currency": normalised_currency,
                "source_unit": normalised_unit,
            }
        )

    for label, value in (
        ("largest_counterparty_pct", largest_percentage),
        ("top_five_pct", top_five_percentage),
    ):
        if value is not None and not Decimal("0") <= value <= Decimal("100"):
            return _failure(
                skill_name,
                "percentage_out_of_range",
                retained_evidence_ids,
                {**metadata, "invalid_percentage": label, "value": str(value)},
            )
    if (
        largest_percentage is not None
        and top_five_percentage is not None
        and largest_percentage > top_five_percentage
    ):
        return _failure(
            skill_name,
            "largest_percentage_exceeds_top_five",
            retained_evidence_ids,
            {
                **metadata,
                "largest_counterparty_pct": str(largest_percentage),
                "top_five_pct": str(top_five_percentage),
            },
        )

    value = {
        "largest_counterparty_pct": largest_percentage,
        "top_five_pct": top_five_percentage,
    }
    rounded_percentages = {
        key: (
            percentage.quantize(_PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
            if percentage is not None
            else None
        )
        for key, percentage in value.items()
    }
    return SkillResult(
        skill_name=skill_name,
        skill_version=_V03_FINANCIAL_SKILL_VERSION,
        success=True,
        value=value,
        evidence_ids=retained_evidence_ids,
        metadata={**metadata, "rounded_percentages": rounded_percentages},
    )


def customer_concentration(**kwargs: Any) -> SkillResult:
    """Calculate or validate customer concentration percentages."""

    return counterparty_concentration("customer", **kwargs)


def supplier_concentration(**kwargs: Any) -> SkillResult:
    """Calculate or validate supplier concentration percentages."""

    return counterparty_concentration("supplier", **kwargs)


def cash_runway(cash: float | None, monthly_burn: float | None) -> SkillResult:
    if cash is None or monthly_burn is None or monthly_burn <= 0:
        return SkillResult(skill_name="cash_runway", success=False, error="cash and positive monthly_burn are required")
    return SkillResult(skill_name="cash_runway", success=True, value=cash / monthly_burn, metadata={"unit": "months"})


def cash_runway_from_operating_cash_flow(
    cash: Decimal | int | float | str | None,
    operating_cash_flow: Decimal | int | float | str | None,
    period_months: int | None,
    evidence_ids: Sequence[str] = (),
    *,
    currency: str | None = None,
    source_unit: str | None = None,
) -> SkillResult:
    """Calculate cash runway from a reported operating cash outflow using Decimal."""

    retained_evidence_ids = list(evidence_ids)
    cash_value = _as_decimal(cash)
    cash_flow_value = _as_decimal(operating_cash_flow)
    base_metadata = {
        "formula": "cash / (abs(operating_cash_flow) / period_months)",
        "rounding": "ROUND_HALF_UP to 2 decimal places",
        "currency": currency,
        "source_unit": source_unit,
        "period_months": period_months,
    }
    if cash_value is None or cash_flow_value is None:
        return SkillResult(
            skill_name="cash_runway",
            skill_version="1.1",
            success=False,
            evidence_ids=retained_evidence_ids,
            error="cash and operating_cash_flow must be valid numeric values",
            metadata=base_metadata,
        )
    if cash_value < 0:
        return SkillResult(
            skill_name="cash_runway",
            skill_version="1.1",
            success=False,
            evidence_ids=retained_evidence_ids,
            error="cash must be non-negative",
            metadata=base_metadata,
        )
    if cash_flow_value >= 0:
        return SkillResult(
            skill_name="cash_runway",
            skill_version="1.1",
            success=False,
            evidence_ids=retained_evidence_ids,
            error="operating_cash_flow must be negative to represent cash burn",
            metadata={**base_metadata, "no_cash_burn": cash_flow_value > 0},
        )
    if period_months not in {3, 6, 9, 12}:
        return SkillResult(
            skill_name="cash_runway",
            skill_version="1.1",
            success=False,
            evidence_ids=retained_evidence_ids,
            error="period_months must be one of 3, 6, 9, or 12",
            metadata=base_metadata,
        )

    months = Decimal(period_months)
    monthly_burn = abs(cash_flow_value) / months
    # Use the algebraically equivalent direct ratio so a repeating monthly-burn
    # Decimal cannot move exact policy boundaries such as 6.00 or 12.00 months.
    exact_runway = cash_value * months / abs(cash_flow_value)
    rounded_runway = exact_runway.quantize(_RUNWAY_QUANTUM, rounding=ROUND_HALF_UP)
    return SkillResult(
        skill_name="cash_runway",
        skill_version="1.1",
        success=True,
        value=exact_runway,
        evidence_ids=retained_evidence_ids,
        metadata={
            **base_metadata,
            "monthly_burn": monthly_burn,
            "rounded_months": rounded_runway,
            "unit": "months",
        },
    )

def concentration_ratio(top_customer_revenue: float | None, total_revenue: float | None) -> SkillResult:
    if top_customer_revenue is None or total_revenue is None or total_revenue <= 0:
        return SkillResult(skill_name="concentration_ratio", success=False, error="valid revenue values are required")
    return SkillResult(skill_name="concentration_ratio", success=True, value=top_customer_revenue / total_revenue)
