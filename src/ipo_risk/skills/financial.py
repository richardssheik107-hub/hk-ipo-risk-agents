from ipo_risk.schemas import SkillResult

def cash_runway(cash: float | None, monthly_burn: float | None) -> SkillResult:
    if cash is None or monthly_burn is None or monthly_burn <= 0:
        return SkillResult(skill_name="cash_runway", success=False, error="cash and positive monthly_burn are required")
    return SkillResult(skill_name="cash_runway", success=True, value=cash / monthly_burn, metadata={"unit": "months"})

def concentration_ratio(top_customer_revenue: float | None, total_revenue: float | None) -> SkillResult:
    if top_customer_revenue is None or total_revenue is None or total_revenue <= 0:
        return SkillResult(skill_name="concentration_ratio", success=False, error="valid revenue values are required")
    return SkillResult(skill_name="concentration_ratio", success=True, value=top_customer_revenue / total_revenue)
