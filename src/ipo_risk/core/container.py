"""Named component registry and configuration-driven dependency assembly."""
from collections.abc import Callable
from dataclasses import dataclass
from ipo_risk.agents.disabled import DisabledBusinessAgent, DisabledLegalAgent, DisabledMarketAgent
from ipo_risk.agents.financial import CashRunwayFinancialAgent
from ipo_risk.agents.mock import MockBusinessAgent, MockFinancialAgent, MockLegalAgent, MockMarketAgent
from ipo_risk.agents.rules import RuleSupervisor, RuleVerifier
from ipo_risk.core.config import ComponentConfigurationError, Settings
from ipo_risk.parsers.mock import AlternateMockDocumentParser, MockDocumentParser
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.predictors.fault import FaultPredictor
from ipo_risk.providers.mock import MockIPODataProvider, MockLLMProvider, MockMarketDataProvider
from ipo_risk.providers.llm import OpenAICompatibleLLMProvider, UnavailableLLMProvider
from ipo_risk.providers.unavailable import RequestIPODataProvider, UnavailableMarketDataProvider
from ipo_risk.reporting.mock import MockReportGenerator
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.retrieval.mock import MockDocumentRetriever
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.workflows.mvp_v1 import MVPWorkflow

class ComponentRegistry:
    def __init__(self): self._items: dict[str, dict[str, Callable[..., object]]] = {}
    def register(self, kind: str, name: str, factory: Callable[..., object]) -> None: self._items.setdefault(kind, {})[name] = factory
    def create(self, kind: str, name: str, **kwargs):
        try: return self._items[kind][name](**kwargs)
        except KeyError as exc: raise ComponentConfigurationError(f"Unregistered {kind} component: {name!r}") from exc

def default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    for kind, factory in {
        "parser": MockDocumentParser, "retriever": MockDocumentRetriever, "financial_agent": MockFinancialAgent,
        "legal_agent": MockLegalAgent, "business_agent": MockBusinessAgent, "market_agent": MockMarketAgent,
        "verifier": RuleVerifier, "supervisor": RuleSupervisor, "predictor": RuleBasedPredictor,
        "llm_provider": MockLLMProvider, "market_data_provider": MockMarketDataProvider,
        "ipo_data_provider": MockIPODataProvider, "report_generator": MockReportGenerator,
    }.items(): registry.register(kind, "mock" if kind not in {"verifier", "supervisor", "predictor"} else ("rule" if kind in {"verifier", "supervisor"} else "rule_based"), factory)
    registry.register("predictor", "fault", FaultPredictor)
    registry.register("parser", "mock_alt", AlternateMockDocumentParser)
    registry.register("parser", "pymupdf", PyMuPDFDocumentParser)
    registry.register("retriever", "keyword", KeywordDocumentRetriever)
    registry.register(
        "financial_agent",
        "cash_runway",
        lambda retriever=None: CashRunwayFinancialAgent(retriever=retriever),
    )
    registry.register("legal_agent", "disabled", DisabledLegalAgent)
    registry.register("business_agent", "disabled", DisabledBusinessAgent)
    registry.register("market_agent", "disabled", DisabledMarketAgent)
    registry.register(
        "market_data_provider", "unavailable", UnavailableMarketDataProvider
    )
    registry.register("ipo_data_provider", "request", RequestIPODataProvider)
    registry.register("llm_provider", "openai_compatible", OpenAICompatibleLLMProvider)
    registry.register("llm_provider", "unavailable", UnavailableLLMProvider)
    return registry

@dataclass
class DependencyContainer:
    settings: Settings
    registry: ComponentRegistry
    def create_workflow(self):
        retriever = self.registry.create("retriever", self.settings.retriever)
        financial_agent = (
            self.registry.create(
                "financial_agent", self.settings.financial_agent, retriever=retriever
            )
            if self.settings.financial_agent == "cash_runway"
            else self.registry.create("financial_agent", self.settings.financial_agent)
        )
        return MVPWorkflow(
            self.registry.create("parser", self.settings.parser), retriever,
            [financial_agent, self.registry.create("legal_agent", self.settings.legal_agent), self.registry.create("business_agent", self.settings.business_agent), self.registry.create("market_agent", self.settings.market_agent)],
            self.registry.create("verifier", self.settings.verifier), self.registry.create("supervisor", self.settings.supervisor),
            self.registry.create("predictor", self.settings.predictor), self.registry.create("report_generator", self.settings.report_generator),
            self.registry.create("market_data_provider", self.settings.market_data_provider), self.registry.create("ipo_data_provider", self.settings.ipo_data_provider),
        )
    def create_repository(self):
        if self.settings.repository == "json": return JsonAnalysisRepository(f"{self.settings.data_dir}/results")
        return self.registry.create("repository", self.settings.repository)
    def create_llm_provider(self):
        """Create the configured provider for future real Agent implementations."""
        if self.settings.llm_provider != "openai_compatible":
            return self.registry.create("llm_provider", self.settings.llm_provider)
        if not all(
            (
                self.settings.llm_api_key,
                self.settings.llm_base_url,
                self.settings.llm_model,
            )
        ):
            return self.registry.create(
                "llm_provider",
                "unavailable",
                reason="OpenAI-compatible LLM configuration is incomplete",
            )
        return self.registry.create(
            "llm_provider",
            "openai_compatible",
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            model=self.settings.llm_model,
            timeout_seconds=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )
