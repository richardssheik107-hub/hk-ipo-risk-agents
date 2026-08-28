from dataclasses import replace
from decimal import Decimal

from ipo_risk.core.config import Settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.schemas import (
    DocumentChunk,
    IPOAnalysisRequest,
    RiskCategory,
    RiskItem,
    RiskLevel,
    TaskStatus,
    VerificationResult,
    VerificationStatus,
)
from ipo_risk.agents.rules import RuleVerifier
from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.workflows.mvp_v1 import MVPWorkflow
from ipo_risk.workflows.state import reduce_risks


def financial_chunks() -> list[DocumentChunk]:
    header = (
        "截至12月31日止年度\n截至3月31日止三個月\n"
        "2022年\n2023年\n2023年\n2024年\n人民幣千元\n"
    )
    return [
        DocumentChunk(
            document_id="doc",
            chunk_id="doc:page:1",
            page=1,
            text=(
                "附錄一\n會計師報告\n綜合現金流量表\n"
                + header
                + "經營活動所用淨現金流量\n(220,053)\n(200,944)\n"
                "(56,986)\n(83,918)"
            ),
        ),
        DocumentChunk(
            document_id="doc",
            chunk_id="doc:page:2",
            page=2,
            text=(
                header
                + "現金流量表所述現金及現金等價物\n"
                "90,762\n186,830\n111,745\n77,208"
            ),
        ),
    ]


class StaticParser:
    name = "pymupdf"
    last_errors = []

    def parse(self, request):
        return financial_chunks()


def real_settings(tmp_path) -> Settings:
    return replace(
        Settings(),
        use_mock=False,
        parser="pymupdf",
        retriever="keyword",
        financial_agent="cash_runway",
        legal_agent="disabled",
        business_agent="disabled",
        market_agent="disabled",
        market_data_provider="unavailable",
        ipo_data_provider="request",
        data_dir=str(tmp_path),
    )


def test_real_service_produces_verified_cash_runway_and_persists(tmp_path) -> None:
    registry = default_registry()
    registry.register("parser", "pymupdf", StaticParser)
    settings = real_settings(tmp_path)
    repository = JsonAnalysisRepository(tmp_path / "results")
    service = IPOAnalysisService(
        settings=settings,
        container=DependencyContainer(settings, registry),
        repository=repository,
    )
    result = service.analyze(
        IPOAnalysisRequest(
            company_name="Demo",
            stock_code="2410.HK",
            prospectus_path="ignored.pdf",
            use_mock=False,
        )
    )
    assert result.status == TaskStatus.COMPLETED
    cash_runway = next(risk for risk in result.verified_risks if risk.risk_code == "cash_runway")
    assert cash_runway.verification_status == VerificationStatus.VERIFIED
    assert cash_runway.calculation is not None
    assert cash_runway.calculation.result == str(
        Decimal("77208") * Decimal("3") / Decimal("83918")
    )
    assert cash_runway.metadata["runway_months_rounded"] == "2.76"
    assert result.prediction is not None
    assert result.prediction.risk_score == 90
    assert result.prediction.probabilities == {}
    assert result.prediction.metadata["degraded_mode"] is True
    assert result.prediction.metadata["degradation_reasons"] == [
        "market_sentiment_score_missing"
    ]
    assert result.metadata["component_modes"] == {
        "parser": "real",
        "retriever": "real",
        "financial_agent": "real",
        "legal_agent": "unavailable",
        "business_agent": "unavailable",
        "market_agent": "unavailable",
        "verifier": "deterministic",
        "predictor": "deterministic_rule",
        "market_data_provider": "unavailable",
        "ipo_data_provider": "request",
        "report_generator": "mock",
    }
    assert result.metadata["document"]["parsed_chunk_count"] == 2
    assert result.metadata["real_slice"]["cash_runway_verified"] is True
    assert not any(risk.risk_code.startswith("mock") for risk in result.verified_risks)
    restored = repository.get(result.analysis_id)
    assert restored is not None
    assert restored.model_dump() == result.model_dump()
    logged_components = {log.agent_name for log in result.agent_logs}
    assert {
        "ipo_data_provider",
        "market_data_provider",
        "document_parser",
        "financial",
        "verifier",
        "supervisor",
        "predictor",
        "report_generator",
        "analysis_repository",
    }.issubset(logged_components)


def risk(code: str) -> RiskItem:
    return RiskItem(
        risk_id=code,
        risk_code=code,
        category=RiskCategory.FINANCIAL,
        risk_type=code,
        level=RiskLevel.HIGH,
        score=80,
        conclusion=code,
        agent_name="test",
    )


class ExplodingRetriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, chunks, query, limit=3):
        self.calls.append(query)
        raise RuntimeError("retrieval failed")


class PendingVerifier:
    name = "verifier"

    def verify(self, risks, evidence):
        return VerificationResult(
            pending_risks=[
                item.model_copy(update={"verification_status": VerificationStatus.PENDING})
                for item in risks
            ]
        )


class ExplodingVerifier:
    name = "verifier"

    def verify(self, risks, evidence):
        raise RuntimeError("verification failed")


def workflow_with(retriever, verifier) -> MVPWorkflow:
    class Noop:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    return MVPWorkflow(
        Noop(), retriever, [], verifier, Noop(), Noop(), Noop(), Noop(), Noop()
    )


def test_cash_runway_is_not_retrieved_again() -> None:
    retriever = ExplodingRetriever()
    outcome = workflow_with(retriever, PendingVerifier()).verify(
        {"request": IPOAnalysisRequest(company_name="Demo"), "candidates": [risk("cash_runway")]}
    )
    assert retriever.calls == []
    assert outcome["errors"] == []


def test_single_retrieval_failure_is_recoverable() -> None:
    retriever = ExplodingRetriever()
    outcome = workflow_with(retriever, PendingVerifier()).verify(
        {
            "request": IPOAnalysisRequest(company_name="Demo"),
            "candidates": [risk("cash_runway"), risk("continuous_loss")],
        }
    )
    assert len(outcome["pending_risks"]) == 2
    assert len(outcome["errors"]) == 1
    assert outcome["errors"][0].recoverable is True


def test_retrieval_failure_cannot_verify_embedded_generic_evidence() -> None:
    from ipo_risk.schemas import Evidence

    embedded = Evidence(text="support", document_id="doc", page=1)
    item = risk("redemption_rights").model_copy(
        update={"category": RiskCategory.LEGAL, "evidence": [embedded]}
    )
    outcome = workflow_with(ExplodingRetriever(), RuleVerifier()).verify(
        {"request": IPOAnalysisRequest(company_name="Demo"), "candidates": [item]}
    )
    assert outcome["verified_risks"] == []
    assert outcome["pending_risks"][0].evidence == [embedded]
    assert outcome["pending_risks"][0].verification_status == VerificationStatus.PENDING


def test_verifier_failure_preserves_evidence_and_calculation() -> None:
    from ipo_risk.schemas import Calculation, Evidence

    evidence = Evidence(text="source", document_id="doc", page=1)
    item = risk("cash_runway").model_copy(
        update={
            "evidence": [evidence],
            "calculation": Calculation(skill_name="x", formula="x"),
        }
    )
    outcome = workflow_with(ExplodingRetriever(), ExplodingVerifier()).verify(
        {"request": IPOAnalysisRequest(company_name="Demo"), "candidates": [item]}
    )
    pending = outcome["pending_risks"][0]
    assert pending.evidence == [evidence]
    assert pending.calculation == item.calculation


def test_candidate_reducer_stably_replaces_duplicate_risk() -> None:
    first = risk("duplicate")
    updated = first.model_copy(update={"score": 82})
    assert reduce_risks([first], [updated]) == [updated]
