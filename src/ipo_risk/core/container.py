"""Named component registry and configuration-driven dependency assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.agents.business_verifier import V03BusinessVerifier
from ipo_risk.agents.disabled import (
    DisabledBusinessAgent,
    DisabledLegalAgent,
    DisabledMarketAgent,
)
from ipo_risk.agents.financial import CashRunwayFinancialAgent
from ipo_risk.agents.financial_v03 import V03FinancialAgent
from ipo_risk.agents.financial_verifier import V03FinancialVerifier
from ipo_risk.agents.legal import LegalAgent
from ipo_risk.agents.mock import (
    MockBusinessAgent,
    MockFinancialAgent,
    MockLegalAgent,
    MockMarketAgent,
)
from ipo_risk.agents.rules import RuleSupervisor, RuleVerifier
from ipo_risk.agents.supervisor_v03 import V03Supervisor
from ipo_risk.agents.verifier_router import SpecializedVerifierRouter
from ipo_risk.core.config import ComponentConfigurationError, Settings
from ipo_risk.domain.legal_verifiers import (
    LegalRightsVerifier,
    LitigationComplianceVerifier,
)
from ipo_risk.parsers.mock import AlternateMockDocumentParser, MockDocumentParser
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.predictors.fault import FaultPredictor
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.providers.llm import OpenAICompatibleLLMProvider, UnavailableLLMProvider
from ipo_risk.providers.mock import (
    MockIPODataProvider,
    MockLLMProvider,
    MockMarketDataProvider,
)
from ipo_risk.providers.unavailable import (
    RequestIPODataProvider,
    UnavailableMarketDataProvider,
)
from ipo_risk.reporting.mock import MockReportGenerator
from ipo_risk.reporting.v03 import V03ReportGenerator
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.mock import MockDocumentRetriever
from ipo_risk.workflows.enhanced_v2 import EnhancedV2Workflow
from ipo_risk.workflows.mvp_v1 import MVPWorkflow


class ComponentRegistry:
    """Create named component implementations and fail clearly on bad config."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Callable[..., object]]] = {}

    def register(self, kind: str, name: str, factory: Callable[..., object]) -> None:
        self._items.setdefault(kind, {})[name] = factory

    def create(self, kind: str, name: str, **kwargs):
        try:
            return self._items[kind][name](**kwargs)
        except KeyError as exc:
            raise ComponentConfigurationError(
                f"Unregistered {kind} component: {name!r}"
            ) from exc


def default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registrations = {
        "parser": {"mock": MockDocumentParser, "mock_alt": AlternateMockDocumentParser, "pymupdf": PyMuPDFDocumentParser},
        "retriever": {"mock": MockDocumentRetriever, "keyword": KeywordDocumentRetriever},
        "financial_agent": {"mock": MockFinancialAgent, "cash_runway": CashRunwayFinancialAgent, "v03": V03FinancialAgent},
        "legal_agent": {"mock": MockLegalAgent, "disabled": DisabledLegalAgent, "v03": LegalAgent},
        "business_agent": {"mock": MockBusinessAgent, "disabled": DisabledBusinessAgent, "v03": V03BusinessAgent},
        "market_agent": {"mock": MockMarketAgent, "disabled": DisabledMarketAgent},
        "verifier": {"rule": RuleVerifier},
        "supervisor": {"rule": RuleSupervisor, "v03": V03Supervisor},
        "predictor": {"rule_based": RuleBasedPredictor, "fault": FaultPredictor},
        "llm_provider": {"mock": MockLLMProvider, "openai_compatible": OpenAICompatibleLLMProvider, "unavailable": UnavailableLLMProvider},
        "market_data_provider": {"mock": MockMarketDataProvider, "unavailable": UnavailableMarketDataProvider},
        "ipo_data_provider": {"mock": MockIPODataProvider, "request": RequestIPODataProvider, "catalog": CatalogIPODataProvider},
        "report_generator": {"mock": MockReportGenerator, "v03": V03ReportGenerator},
    }
    for kind, values in registrations.items():
        for name, factory in values.items():
            registry.register(kind, name, factory)
    registry.register(
        "verifier",
        "specialized_v03",
        lambda: SpecializedVerifierRouter(
            financial_verifier=V03FinancialVerifier(),
            legal_rights_verifier=LegalRightsVerifier(),
            litigation_verifier=LitigationComplianceVerifier(),
            business_verifier=V03BusinessVerifier(),
        ),
    )
    return registry


@dataclass
class DependencyContainer:
    settings: Settings
    registry: ComponentRegistry

    def create_workflow(self):
        retriever = self.registry.create("retriever", self.settings.retriever)
        llm_provider = self.create_llm_provider()
        agents = [
            self._create_agent("financial_agent", self.settings.financial_agent, retriever, llm_provider),
            self._create_agent("legal_agent", self.settings.legal_agent, retriever, llm_provider),
            self._create_agent("business_agent", self.settings.business_agent, retriever, llm_provider),
            self.registry.create("market_agent", self.settings.market_agent),
        ]
        arguments = (
            self.registry.create("parser", self.settings.parser),
            retriever,
            agents,
            self.registry.create("verifier", self.settings.verifier),
            self.registry.create("supervisor", self.settings.supervisor),
            self.registry.create("predictor", self.settings.predictor),
            self.registry.create("report_generator", self.settings.report_generator),
            self.registry.create("market_data_provider", self.settings.market_data_provider),
            self.registry.create("ipo_data_provider", self.settings.ipo_data_provider),
        )
        if self.settings.workflow_version == "mvp_v1":
            return MVPWorkflow(*arguments)
        if self.settings.workflow_version == "enhanced_v2":
            return EnhancedV2Workflow(*arguments)
        raise ComponentConfigurationError(
            f"Unregistered workflow version: {self.settings.workflow_version!r}"
        )

    def _create_agent(self, kind: str, name: str, retriever, llm_provider):
        if name == "cash_runway":
            return self.registry.create(kind, name, retriever=retriever)
        if name == "v03":
            kwargs = {"retriever": retriever}
            if kind in {"legal_agent", "business_agent"}:
                kwargs["llm_provider"] = llm_provider
            return self.registry.create(kind, name, **kwargs)
        return self.registry.create(kind, name)

    def create_repository(self):
        if self.settings.repository == "json":
            return JsonAnalysisRepository(f"{self.settings.data_dir}/results")
        return self.registry.create("repository", self.settings.repository)

    def create_llm_provider(self):
        """Create one configured provider instance for all structured Agents."""

        if self.settings.llm_provider != "openai_compatible":
            return self.registry.create("llm_provider", self.settings.llm_provider)
        if not all(
            (self.settings.llm_api_key, self.settings.llm_base_url, self.settings.llm_model)
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
