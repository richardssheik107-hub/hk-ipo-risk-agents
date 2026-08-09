from __future__ import annotations

from ipo_risk.agents.base import RiskAgent
from ipo_risk.agents.legal import LegalAgent
from ipo_risk.schemas import ComponentDiagnostic, IPOProfile, RiskItem


class EmptyRetriever:
    def retrieve(self, chunks, query, limit=3):
        return []


def test_legal_agent_keeps_frozen_analyze_shape_and_diagnostic_channel() -> None:
    agent: RiskAgent = LegalAgent(retriever=EmptyRetriever())

    result = agent.analyze(IPOProfile(company_name="IPO Case"), [])

    assert isinstance(result, list)
    assert all(isinstance(item, RiskItem) for item in result)
    assert isinstance(agent.last_diagnostics, list)
    assert len(agent.last_diagnostics) == 2
    assert all(isinstance(item, ComponentDiagnostic) for item in agent.last_diagnostics)
    assert {item.risk_code for item in agent.last_diagnostics} == {
        "redemption_rights",
        "material_litigation_compliance",
    }
