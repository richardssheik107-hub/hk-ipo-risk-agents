from ipo_risk.agents.disabled import (
    DisabledBusinessAgent,
    DisabledLegalAgent,
    DisabledMarketAgent,
)
from ipo_risk.agents.financial import CashRunwayFinancialAgent
from ipo_risk.agents.mock import MockFinancialAgent, MockLegalAgent
from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.mock import MockMarketDataProvider
from ipo_risk.providers.unavailable import (
    RequestIPODataProvider,
    UnavailableMarketDataProvider,
)


def test_real_pdf_configuration_selects_honest_real_slice_components() -> None:
    settings = load_settings("configs/real_pdf.yaml")
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    assert isinstance(workflow.agents[0], CashRunwayFinancialAgent)
    assert isinstance(workflow.agents[1], DisabledLegalAgent)
    assert isinstance(workflow.agents[2], DisabledBusinessAgent)
    assert isinstance(workflow.agents[3], DisabledMarketAgent)
    assert isinstance(workflow.market_provider, UnavailableMarketDataProvider)
    assert isinstance(workflow.ipo_provider, RequestIPODataProvider)
    assert workflow.agents[0].retriever is workflow.retriever


def test_mock_configuration_remains_unchanged() -> None:
    settings = load_settings("configs/mock.yaml")
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    assert isinstance(workflow.agents[0], MockFinancialAgent)
    assert isinstance(workflow.agents[1], MockLegalAgent)
    assert isinstance(workflow.market_provider, MockMarketDataProvider)
