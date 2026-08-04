import pytest

from ipo_risk.agents.disabled import (
    DisabledBusinessAgent,
    DisabledLegalAgent,
    DisabledMarketAgent,
)
from ipo_risk.schemas import IPOProfile


@pytest.mark.parametrize(
    ("agent_type", "name"),
    [
        (DisabledLegalAgent, "legal"),
        (DisabledBusinessAgent, "business"),
        (DisabledMarketAgent, "market"),
    ],
)
def test_disabled_agent_is_explicitly_unavailable(agent_type, name) -> None:
    agent = agent_type()
    assert agent.name == name
    assert agent.analyze(IPOProfile(company_name="Demo"), []) == []
    assert agent.last_diagnostics.available is False
    assert agent.last_diagnostics.status == "component_not_implemented"
    assert "no_risk" not in agent.last_diagnostics.reason
