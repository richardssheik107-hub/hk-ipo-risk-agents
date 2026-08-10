from __future__ import annotations

from pathlib import Path

import yaml

from ipo_risk.agents.legal_models import (
    LitigationComplianceCandidate,
    ShareholderRightCandidate,
)


SHAREHOLDER_RIGHT_FIELDS = {
    "right_type",
    "holder",
    "trigger_or_termination",
    "survives_listing",
    "is_effective",
    "termination_event",
    "termination_timing",
    "restoration_clause",
    "restoration_condition",
    "impact_on_public_shareholders",
    "uncertainty_reason",
    "evidence_ids",
}

LITIGATION_COMPLIANCE_FIELDS = {
    "matter_type",
    "subject",
    "counterparty_or_authority",
    "current_status",
    "event_date",
    "amount",
    "currency",
    "amount_unit",
    "is_pending",
    "is_resolved",
    "is_remediated",
    "management_materiality",
    "potential_impact",
    "license_impact",
    "materiality_stated",
    "uncertainty_reason",
    "evidence_ids",
}


def test_shareholder_right_candidate_fields_match_approved_contract() -> None:
    assert set(ShareholderRightCandidate.model_fields) == SHAREHOLDER_RIGHT_FIELDS
    assert "counterparty_or_regulator" not in ShareholderRightCandidate.model_fields


def test_litigation_candidate_fields_keep_candidate_layer_authority_name() -> None:
    assert set(LitigationComplianceCandidate.model_fields) == LITIGATION_COMPLIANCE_FIELDS
    assert "counterparty_or_authority" in LitigationComplianceCandidate.model_fields
    assert "counterparty_or_regulator" not in LitigationComplianceCandidate.model_fields


def test_old_minimal_shareholder_right_payload_remains_valid() -> None:
    candidate = ShareholderRightCandidate(
        right_type="redemption_right",
        evidence_ids=["e-rights"],
    )

    assert candidate.holder == ""
    assert candidate.survives_listing is None
    assert candidate.is_effective is None
    assert candidate.restoration_clause is None
    assert candidate.termination_event == ""
    assert candidate.uncertainty_reason == ""


def test_old_minimal_litigation_payload_remains_valid() -> None:
    candidate = LitigationComplianceCandidate(
        matter_type="litigation",
        current_status="pending",
        evidence_ids=["e-legal"],
    )

    assert candidate.subject == ""
    assert candidate.counterparty_or_authority == ""
    assert candidate.event_date is None
    assert candidate.amount is None
    assert candidate.is_pending is None
    assert candidate.is_resolved is None
    assert candidate.is_remediated is None
    assert candidate.management_materiality == ""
    assert candidate.license_impact == ""
    assert candidate.uncertainty_reason == ""


def test_legal_severity_configuration_matches_frozen_policy() -> None:
    config_path = Path(__file__).parents[2] / "configs" / "v03_risk_rules.yaml"
    rules = yaml.safe_load(config_path.read_text(encoding="utf-8"))["risks"]

    for risk_code in ("redemption_rights", "material_litigation_compliance"):
        severity = rules[risk_code]["candidate_severity"]
        assert severity == {
            "level": "medium",
            "score": 50,
            "level_is_provisional": True,
            "score_is_rule_based": True,
            "score_is_probability": False,
        }
