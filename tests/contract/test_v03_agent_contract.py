from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import BaseModel

from ipo_risk.agents.business_models import CommercializationCandidate
from ipo_risk.agents.financial_models import ConcentrationObservation, LossObservation
from ipo_risk.agents.legal_models import LitigationComplianceCandidate
from ipo_risk.agents.mock import MockBusinessAgent, MockFinancialAgent, MockLegalAgent
from ipo_risk.domain.risk_codes import RISK_REQUIREMENTS, V03_ENABLED_RISK_CODES, V03_RISK_OWNERS
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    IPOProfile,
    SupervisionResult,
)


def test_v03_risk_catalog_has_unique_owners_and_requirements():
    assert set(V03_RISK_OWNERS) == V03_ENABLED_RISK_CODES
    assert len(V03_RISK_OWNERS) == 8
    assert all(code in RISK_REQUIREMENTS for code in V03_ENABLED_RISK_CODES)
    assert "weak_ipo_market" in RISK_REQUIREMENTS
    assert "weak_ipo_market" not in V03_ENABLED_RISK_CODES


def test_versioned_risk_config_matches_code_registry():
    config = yaml.safe_load(Path("configs/v03_risk_rules.yaml").read_text(encoding="utf-8"))
    assert config["version"] == "v03_contract_v1"
    assert set(config["risks"]) == V03_ENABLED_RISK_CODES
    assert {
        code: settings["owner"] for code, settings in config["risks"].items()
    } == V03_RISK_OWNERS
    assert config["disabled_in_v03"]["weak_ipo_market"]["planned_version"] == "v0.4"


def test_existing_specialist_agents_keep_common_return_contract():
    profile = IPOProfile(company_name="Contract Test")
    for agent in (MockFinancialAgent(), MockLegalAgent(), MockBusinessAgent()):
        risks = agent.analyze(profile, [])
        assert isinstance(risks, list)
        assert all(risk.agent_name == agent.name for risk in risks)
        assert all(V03_RISK_OWNERS[risk.risk_code] == agent.name for risk in risks)


def test_component_diagnostic_defaults_are_isolated():
    first = ComponentDiagnostic(
        risk_code="continuous_loss",
        code=DiagnosticCode.EVIDENCE_NOT_FOUND,
        message="no comparable statement found",
    )
    second = ComponentDiagnostic(
        risk_code="continuous_loss",
        code=DiagnosticCode.NOT_APPLICABLE,
        message="not applicable",
    )
    first.evidence_ids.append("e-1")
    assert second.evidence_ids == []


def test_supervision_result_is_backward_compatible_and_has_v03_channels():
    result = SupervisionResult(summary="ok")
    assert result.verified_risks == []
    assert result.duplicate_groups == []
    assert result.conflicts == []
    assert result.composite_findings == []
    assert result.metadata == {}


def test_frozen_internal_candidate_models_are_typed_and_evidence_linked():
    loss = LossObservation(
        period_end=date(2025, 12, 31),
        net_result=Decimal("-12.50"),
        currency="HKD",
        unit="million",
        evidence_ids=["e-loss"],
    )
    concentration = ConcentrationObservation(
        concentration_type="customer",
        period_end=date(2025, 12, 31),
        largest_counterparty_pct=Decimal("42.1"),
        evidence_ids=["e-customer"],
    )
    litigation = LitigationComplianceCandidate(
        matter_type="regulatory_inquiry",
        current_status="pending",
        evidence_ids=["e-legal"],
    )
    commercial = CommercializationCandidate(
        product_name="Product A",
        development_stage="phase_3",
        evidence_ids=["e-business"],
    )
    assert loss.net_result == Decimal("-12.50")
    assert concentration.largest_counterparty_pct == Decimal("42.1")
    assert litigation.evidence_ids == ["e-legal"]
    assert commercial.evidence_ids == ["e-business"]


def test_mock_llm_provider_validates_structured_output_and_records_metadata():
    class Candidate(BaseModel):
        finding: str

    provider = MockLLMProvider(responses={"legal_extract": {"finding": "candidate"}})
    result = provider.generate_structured(
        task_name="legal_extract",
        prompt_version="legal_v1",
        evidence=[],
        response_model=Candidate,
    )
    assert result == Candidate(finding="candidate")
    assert provider.last_call_metadata is not None
    assert provider.last_call_metadata.prompt_version == "legal_v1"
    assert len(provider.last_call_metadata.raw_response_hash) == 64
