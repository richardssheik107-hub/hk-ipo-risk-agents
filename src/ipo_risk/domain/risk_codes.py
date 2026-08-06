"""Stable risk metadata used by deterministic verification."""
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskRequirement:
    requires_evidence: bool = True
    requires_calculation: bool = False

RISK_REQUIREMENTS = {
    "continuous_loss": RiskRequirement(),
    "redemption_rights": RiskRequirement(),
    "material_litigation_compliance": RiskRequirement(),
    "precommercial_product": RiskRequirement(),
    "weak_ipo_market": RiskRequirement(),
    "cash_runway": RiskRequirement(requires_calculation=True),
    "customer_concentration": RiskRequirement(requires_calculation=True),
    "supplier_concentration": RiskRequirement(requires_calculation=True),
    "revenue_growth": RiskRequirement(requires_calculation=True),
}

V03_RISK_OWNERS = {
    "cash_runway": "financial",
    "continuous_loss": "financial",
    "revenue_growth": "financial",
    "customer_concentration": "financial",
    "supplier_concentration": "financial",
    "redemption_rights": "legal",
    "material_litigation_compliance": "legal",
    "precommercial_product": "business",
}

V03_ENABLED_RISK_CODES = frozenset(V03_RISK_OWNERS)

def requirement_for(risk_code: str) -> RiskRequirement:
    return RISK_REQUIREMENTS.get(risk_code, RiskRequirement())
