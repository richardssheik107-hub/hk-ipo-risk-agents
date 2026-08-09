"""Frozen v0.3 decision policy for Business risk candidates."""

from __future__ import annotations

import json
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.agents.business_extraction import BusinessExtractionResult
from ipo_risk.schemas import (
    Evidence,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


RULE_VERSION = "v03_contract_v1"
SEVERITY_POLICY = "business_candidate_medium_v1"


def stable_business_risk_id(
    extraction: BusinessExtractionResult, evidence_ids: list[str]
) -> str:
    """Build a stable identity from the frozen rule inputs."""

    commercial = extraction.commercialization
    core = extraction.core_product
    payload = json.dumps(
        {
            "risk_code": "precommercial_product",
            "evidence_ids": sorted(evidence_ids),
            "product_name": core.product_name if core else "",
            "development_stage": commercial.development_stage if commercial else "",
            "has_product_revenue": extraction.has_product_revenue,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return str(uuid5(NAMESPACE_URL, payload))


def build_precommercial_risk(
    extraction: BusinessExtractionResult, evidence: list[Evidence]
) -> RiskItem:
    """Create one pending rule candidate; verification remains downstream."""

    product_name = extraction.core_product.product_name
    stage = extraction.commercialization.development_stage
    evidence_ids = [item.evidence_id for item in evidence]
    return RiskItem(
        risk_id=stable_business_risk_id(extraction, evidence_ids),
        risk_code="precommercial_product",
        category=RiskCategory.BUSINESS,
        risk_type="Pre-commercial core product",
        level=RiskLevel.MEDIUM,
        score=60,
        conclusion=(
            f"Core product {product_name} is not yet commercialized and the "
            "selected prospectus evidence reports no direct product sales revenue."
        ),
        evidence=evidence,
        calculation=None,
        agent_name="business",
        confidence=0.8,
        verification_status=VerificationStatus.PENDING,
        metadata={
            "rule_version": RULE_VERSION,
            "severity_policy": SEVERITY_POLICY,
            "score_is_rule_based": True,
            "score_is_probability": False,
            "product_name": product_name,
            "development_stage": stage,
            "has_product_revenue": False,
            "revenue_source_types": extraction.revenue_source_types,
        },
    )
