from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from ipo_risk.schemas import SkillResult


_RUNWAY_QUANTUM = Decimal("0.01")


def _as_decimal(value: Decimal | int | float | str | None) -> Decimal | None:
    """Convert supported numeric inputs without performing binary-float arithmetic."""

    if value is None or isinstance(value, bool):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

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
