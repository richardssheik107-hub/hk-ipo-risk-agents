"""Frozen prompt identity and facet vocabulary for the research reranker."""

from __future__ import annotations

PROMPT_VERSION = "llm_evidence_reranker_v1"

RISK_FACETS: dict[str, tuple[str, ...]] = {
    "cash_runway": ("ending_cash", "operating_cash_flow", "reporting_period", "currency_unit", "cash_flow_statement_authority"),
    "continuous_loss": ("profit_loss", "multi_period_history", "reporting_period", "audited_financial_context"),
    "revenue_growth": ("revenue", "comparative_periods", "reporting_period", "currency_unit", "income_statement_authority"),
    "customer_concentration": ("largest_customer_ratio", "top_five_customer_ratio", "revenue_denominator", "customer_identity_context", "reporting_period"),
    "supplier_concentration": ("largest_supplier_ratio", "top_five_supplier_ratio", "purchase_denominator", "supplier_identity_context", "reporting_period"),
    "redemption_rights": ("actual_investor", "special_right", "redemption_put_repurchase", "termination", "restoration", "listing_condition", "current_status"),
    "material_litigation_compliance": ("actual_proceeding", "named_dispute", "regulatory_issue", "licence_permit", "materiality", "current_status", "remediation"),
    "precommercial_product": ("core_product", "development_stage", "clinical_stage", "commercialization", "product_sales", "no_product_sales", "revenue_generation"),
}


def task_name(risk_code: str) -> str:
    if risk_code not in RISK_FACETS:
        raise ValueError(f"unsupported reranker risk: {risk_code}")
    return f"rerank_{risk_code}"


def instruction(risk_code: str) -> str:
    facets = ", ".join(RISK_FACETS[risk_code])
    return (
        "Judge evidence quality only; do not decide whether the issuer has the risk and do not assign a final score or rank. "
        "Use only supplied candidate text. A negative statement can be strong evidence. "
        "Mark broad risk-factor boilerplate honestly. Allowed completeness_facets: " + facets + "."
    )
