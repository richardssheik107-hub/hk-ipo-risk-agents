"""Stable risk metadata used by deterministic verification."""
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskRequirement:
    requires_evidence: bool = True
    requires_calculation: bool = False

RISK_REQUIREMENTS = {
    "continuous_loss": RiskRequirement(),
    "redemption_rights": RiskRequirement(),
    "precommercial_product": RiskRequirement(),
    "weak_ipo_market": RiskRequirement(),
    "cash_runway": RiskRequirement(requires_calculation=True),
    "customer_concentration": RiskRequirement(requires_calculation=True),
    "supplier_concentration": RiskRequirement(requires_calculation=True),
    "revenue_growth": RiskRequirement(requires_calculation=True),
}

def requirement_for(risk_code: str) -> RiskRequirement:
    return RISK_REQUIREMENTS.get(risk_code, RiskRequirement())
