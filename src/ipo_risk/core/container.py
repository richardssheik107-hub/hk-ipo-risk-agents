"""Named component registry and configuration-driven dependency assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.agents.business_verifier import V03BusinessVerifier
from ipo_risk.agents.disabled import (
    DisabledBusinessAgent,
    DisabledLegalAgent,
    DisabledMarketAgent,
)
from ipo_risk.agents.final_supervisor import GatePendingFinalSupervisor, V04FinalSupervisor
from ipo_risk.agents.financial import CashRunwayFinancialAgent
from ipo_risk.agents.financial_v03 import V03FinancialAgent
from ipo_risk.agents.financial_verifier import V03FinancialVerifier
from ipo_risk.agents.legal import LegalAgent
from ipo_risk.agents.market_context import (
    GatePendingMarketContextProvider,
    GovernedPRBMarketContextProvider,
    SnapshotMarketContextProvider,
)
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
from ipo_risk.extraction.financial import (
    TableAwareV03FinancialFactExtractor,
    V03FinancialFactExtractor,
)
from ipo_risk.parsers.mock import AlternateMockDocumentParser, MockDocumentParser
from ipo_risk.parsers.pymupdf_parser import (
    PyMuPDFDocumentParser,
    PyMuPDFTableDocumentParser,
)
from ipo_risk.predictors.fault import FaultPredictor
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.providers.catalog import CatalogIPODataProvider
from ipo_risk.providers.llm import (
    OpenAICompatibleLLMProvider,
    OpenAIResponsesLLMProvider,
    UnavailableLLMProvider,
)
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
from ipo_risk.reporting.v04 import V04ReportGenerator
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.mock import MockDocumentRetriever
from ipo_risk.modeling.frozen_model_evidence import (
    FrozenModelPredictionProvider,
    FrozenModelEvidenceError,
    load_frozen_cohort_evidence,
)
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


# Settings sentinel: this component is not built at all for this configuration.
NO_COMPONENT = "none"


def default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registrations = {
        "parser": {"mock": MockDocumentParser, "mock_alt": AlternateMockDocumentParser, "pymupdf": PyMuPDFDocumentParser, "pymupdf_table": PyMuPDFTableDocumentParser},
        "financial_extractor": {"regex": V03FinancialFactExtractor, "table": TableAwareV03FinancialFactExtractor},
        "retriever": {"mock": MockDocumentRetriever, "keyword": KeywordDocumentRetriever},
        "financial_agent": {"mock": MockFinancialAgent, "cash_runway": CashRunwayFinancialAgent, "v03": V03FinancialAgent},
        "legal_agent": {"mock": MockLegalAgent, "disabled": DisabledLegalAgent, "v03": LegalAgent},
        "business_agent": {"mock": MockBusinessAgent, "disabled": DisabledBusinessAgent, "v03": V03BusinessAgent},
        "market_agent": {"mock": MockMarketAgent, "disabled": DisabledMarketAgent},
        "verifier": {"rule": RuleVerifier},
        "supervisor": {"rule": RuleSupervisor, "v03": V03Supervisor},
        "predictor": {"rule_based": RuleBasedPredictor, "fault": FaultPredictor},
        "llm_provider": {
            "mock": MockLLMProvider,
            "openai_compatible": OpenAICompatibleLLMProvider,
            "openai_responses": OpenAIResponsesLLMProvider,
            "unavailable": UnavailableLLMProvider,
        },
        "market_data_provider": {"mock": MockMarketDataProvider, "unavailable": UnavailableMarketDataProvider},
        "ipo_data_provider": {"mock": MockIPODataProvider, "request": RequestIPODataProvider, "catalog": CatalogIPODataProvider},
        "report_generator": {"mock": MockReportGenerator, "v03": V03ReportGenerator, "v04": V04ReportGenerator},
        # PR-G channels. Settings default to "none", so only a config that names
        # one of these reaches them; every pre-v0.4 config builds nothing.
        "market_context": {
            "gate_pending": GatePendingMarketContextProvider,
            "governed_pr_b_core": GovernedPRBMarketContextProvider,
            "snapshot": SnapshotMarketContextProvider,
        },
        "final_supervisor": {"gate_pending": GatePendingFinalSupervisor},
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
        # Keyword-only with None defaults: callers that construct a workflow with
        # the historical nine positional arguments keep working unchanged.
        channels = {
            "market_context": self._create_channel("market_context", self.settings.market_context),
            "model_prediction_provider": self._model_prediction_provider(),
            "final_supervisor": self._create_channel("final_supervisor", self.settings.final_supervisor),
        }
        if self.settings.workflow_version == "mvp_v1":
            return MVPWorkflow(*arguments, **channels)
        if self.settings.workflow_version == "enhanced_v2":
            return EnhancedV2Workflow(*arguments, **channels)
        raise ComponentConfigurationError(
            f"Unregistered workflow version: {self.settings.workflow_version!r}"
        )

    def _create_channel(self, kind: str, name: str):
        """Build an optional PR-G channel; "none" means build nothing at all."""
        if name == NO_COMPONENT:
            return None
        if kind == "final_supervisor" and name == "v04":
            return V04FinalSupervisor(self._frozen_cohort_evidence())
        if kind == "market_context" and name == "governed_pr_b_core":
            return self.registry.create(
                kind,
                name,
                feature_dir=self.settings.market_feature_dir,
                official_bridge_path=self.settings.market_official_bridge,
                extended_readiness_path=self.settings.market_extended_readiness,
            )
        return self.registry.create(kind, name)

    def _frozen_cohort_evidence(self):
        """Tier-1 frozen PR-F evidence; absent manifest degrades, never crashes."""
        try:
            return load_frozen_cohort_evidence(Path(self.settings.report_dir) / "frozen")
        except FrozenModelEvidenceError:
            return None

    def _model_prediction_provider(self):
        """Build the local-only frozen model channel only when explicitly configured."""
        if not self.settings.pr_f_run_dir:
            return None
        return FrozenModelPredictionProvider(
            run_dir=self.settings.pr_f_run_dir,
            frozen_dir=Path(self.settings.report_dir) / "frozen",
        )

    def _create_agent(self, kind: str, name: str, retriever, llm_provider):
        if name == "cash_runway":
            return self.registry.create(kind, name, retriever=retriever)
        if name == "v03":
            kwargs = {"retriever": retriever}
            if kind in {"legal_agent", "business_agent"}:
                kwargs["llm_provider"] = llm_provider
            if kind == "financial_agent":
                kwargs["extractor"] = self.registry.create(
                    "financial_extractor", self.settings.financial_extractor
                )
            return self.registry.create(kind, name, **kwargs)
        return self.registry.create(kind, name)

    def create_repository(self):
        if self.settings.repository == "json":
            return JsonAnalysisRepository(f"{self.settings.data_dir}/results")
        return self.registry.create("repository", self.settings.repository)

    def create_llm_provider(self):
        """Create one configured provider instance for all structured Agents."""

        remote_providers = {"openai_compatible", "openai_responses"}
        if self.settings.llm_provider not in remote_providers:
            return self.registry.create("llm_provider", self.settings.llm_provider)
        if not all(
            (self.settings.llm_api_key, self.settings.llm_base_url, self.settings.llm_model)
        ):
            provider_label = (
                "Responses API" if self.settings.llm_provider == "openai_responses"
                else "OpenAI-compatible LLM"
            )
            return self.registry.create(
                "llm_provider",
                "unavailable",
                reason=f"{provider_label} configuration is incomplete",
            )
        return self.registry.create(
            "llm_provider",
            self.settings.llm_provider,
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            model=self.settings.llm_model,
            timeout_seconds=self.settings.llm_timeout_seconds,
            max_retries=self.settings.llm_max_retries,
        )
