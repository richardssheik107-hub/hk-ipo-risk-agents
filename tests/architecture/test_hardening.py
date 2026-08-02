from dataclasses import replace
from pathlib import Path
import pytest
from ipo_risk.agents.rules import RuleSupervisor, RuleVerifier
from ipo_risk.core.config import ComponentConfigurationError, Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.reporting.mock import MockReportGenerator
from ipo_risk.schemas import Calculation, Evidence, IPOAnalysisRequest, IPOProfile, RiskCategory, RiskItem, RiskLevel, VerificationStatus
from ipo_risk.services.analysis_service import IPOAnalysisService

def service(settings, registry=None):
    return IPOAnalysisService(container=DependencyContainer(settings, registry or default_registry()))

def test_yaml_component_name_selects_alternate_parser(tmp_path):
    config = tmp_path / "config.yaml"; config.write_text("parser: mock_alt\n", encoding="utf-8")
    settings = load_settings(str(config)); workflow = DependencyContainer(settings, default_registry()).create_workflow()
    assert workflow.parser.__class__.__name__ == "AlternateMockDocumentParser"

def test_unknown_component_has_clear_configuration_error():
    with pytest.raises(ComponentConfigurationError, match="Unregistered parser"):
        DependencyContainer(replace(Settings(), parser="missing"), default_registry()).create_workflow()

class Boom:
    def __getattr__(self, name):
        def fail(*args, **kwargs): raise RuntimeError("intentional failure")
        return fail

@pytest.mark.parametrize("component", ["ipo_data_provider", "market_data_provider", "retriever", "verifier", "supervisor", "predictor", "report_generator"])
def test_component_failures_return_partial_with_error_and_log(component):
    registry = default_registry(); registry.register(component, "boom", Boom)
    result = service(replace(Settings(), **{component: "boom"}), registry).analyze(IPOAnalysisRequest(company_name="Failure"))
    assert result.status.value in {"partial", "failed"}
    assert result.errors and any(log.status.value == "failed" for log in result.agent_logs)

def test_predictor_and_reporter_each_run_once():
    calls = {"predictor": 0, "reporter": 0}
    class CountingPredictor(RuleBasedPredictor):
        def predict(self, *args): calls["predictor"] += 1; return super().predict(*args)
    class CountingReporter(MockReportGenerator):
        def generate(self, *args): calls["reporter"] += 1; return super().generate(*args)
    registry = default_registry(); registry.register("predictor", "count", CountingPredictor); registry.register("report_generator", "count", CountingReporter)
    service(replace(Settings(), predictor="count", report_generator="count"), registry).analyze(IPOAnalysisRequest(company_name="Count"))
    assert calls == {"predictor": 1, "reporter": 1}

def test_repository_failure_returns_partial_result():
    class FailingRepository:
        def save(self, result): raise RuntimeError("cannot persist")
        def get(self, analysis_id): return None
    result = IPOAnalysisService(repository=FailingRepository()).analyze(IPOAnalysisRequest(company_name="Repository"))
    assert result.status.value == "partial" and any(error.component == "analysis_repository" for error in result.errors)

def risk(code, evidence=None, calculation=None):
    return RiskItem(risk_code=code, category=RiskCategory.FINANCIAL if code != "redemption_rights" else RiskCategory.LEGAL, risk_type=code, level=RiskLevel.HIGH, score=80, conclusion=code, agent_name="test", evidence=evidence or [], calculation=calculation)

def test_verifier_evidence_and_calculation_contract():
    verifier = RuleVerifier(); evidence = Evidence(text="source", document_id="d", page=1)
    assert verifier.verify([risk("continuous_loss")], {}).pending_risks
    assert verifier.verify([risk("cash_runway", [evidence])], {"cash_runway": [evidence]}).pending_risks
    invalid = Calculation(skill_name="x", formula="x", evidence_ids=["missing"])
    assert verifier.verify([risk("cash_runway", [evidence], invalid)], {"cash_runway": [evidence]}).pending_risks
    legal = verifier.verify([risk("redemption_rights", [evidence])], {"redemption_rights": [evidence]})
    assert legal.verified_risks and legal.verified_risks[0].verification_status is VerificationStatus.VERIFIED

def test_verifier_and_supervisor_contracts():
    evidence = Evidence(text="source", document_id="d", page=1)
    verified = RuleVerifier().verify([risk("redemption_rights", [evidence])], {"redemption_rights": [evidence]})
    supervised = RuleSupervisor().supervise(verified.verified_risks)
    assert supervised.verified_risks and supervised.summary

def test_ui_import_boundary_and_gitignore():
    app = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "IPOAnalysisService" in app
    for forbidden in ("ipo_risk.agents", "ipo_risk.parsers", "ipo_risk.repositories", "ipo_risk.predictors", "ipo_risk.providers"): assert forbidden not in app
    ignored = Path(".gitignore").read_text(encoding="utf-8")
    for value in (".env", "data/results", "reports", "*.docx", "models", "*.pkl", "*.joblib", "*.onnx", "*.bin", "*.ckpt"): assert value in ignored
