from decimal import Decimal

import pytest

from ipo_risk.agents.financial import (
    CashRunwayAgentStatus,
    CashRunwayFinancialAgent,
)
from ipo_risk.domain.cash_runway import CashRunwayBuildResult, CashRunwayBuildStatus
from ipo_risk.extraction import (
    ExtractionStatus,
    FinancialExtractionResult,
    FinancialMetricValue,
)
from ipo_risk.schemas import DocumentChunk, Evidence, IPOProfile, VerificationStatus


def financial_chunks(*, operating_value: str = "(83,918)") -> list[DocumentChunk]:
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
                "(56,986)\n"
                + operating_value
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


def test_real_financial_agent_builds_pending_cash_runway() -> None:
    agent = CashRunwayFinancialAgent()
    risks = agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())
    assert len(risks) == 1
    risk = risks[0]
    assert risk.risk_code == "cash_runway"
    assert risk.verification_status == VerificationStatus.PENDING
    assert risk.calculation is not None
    assert risk.calculation.result == "2.76"
    assert agent.last_diagnostics.status == CashRunwayAgentStatus.BUILT
    assert agent.last_diagnostics.pages == [2, 1]


class EmptyRetriever:
    def retrieve(self, chunks, query, limit=3):
        return []


class RiskPoolRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def retrieve_for_risk(self, chunks, risk_code, *, limit=20):
        self.calls.append((risk_code, limit))
        return [
            Evidence(
                evidence_id="shared",
                document_id=chunks[0].document_id,
                chunk_id=chunks[0].chunk_id,
                page=chunks[0].page,
                text=chunks[0].text,
            )
        ]


def test_cash_agent_uses_one_bounded_risk_specific_pool() -> None:
    retriever = RiskPoolRetriever()
    agent = CashRunwayFinancialAgent(retriever=retriever, extractor=ReviewExtractor())

    agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())

    assert retriever.calls == [("cash_runway", 10)]


def test_real_financial_agent_reports_retriever_no_result() -> None:
    agent = CashRunwayFinancialAgent(retriever=EmptyRetriever())
    assert agent.analyze(IPOProfile(company_name="Demo"), financial_chunks()) == []
    assert agent.last_diagnostics.status == CashRunwayAgentStatus.RETRIEVER_NO_RESULT
    assert set(agent.last_diagnostics.issues) == {
        "cash_evidence_not_found",
        "operating_cash_flow_evidence_not_found",
    }


class ReviewExtractor:
    def extract(self, *args):
        return FinancialExtractionResult(
            cash_and_cash_equivalents=FinancialMetricValue(
                metric_name="cash_and_cash_equivalents",
                status=ExtractionStatus.NEEDS_REVIEW,
                issues=["cash_review"],
            ),
            operating_cash_flow=FinancialMetricValue(
                metric_name="operating_cash_flow",
                status=ExtractionStatus.EXTRACTED,
                normalized_value=Decimal("-1"),
            ),
        )


def test_real_financial_agent_reports_extraction_review() -> None:
    agent = CashRunwayFinancialAgent(extractor=ReviewExtractor())
    assert agent.analyze(IPOProfile(company_name="Demo"), financial_chunks()) == []
    assert agent.last_diagnostics.status == CashRunwayAgentStatus.EXTRACTION_NEEDS_REVIEW
    assert "cash_review" in agent.last_diagnostics.issues


class ReviewBuilder:
    def build(self, extraction, evidence):
        return CashRunwayBuildResult(
            status=CashRunwayBuildStatus.NEEDS_REVIEW,
            issues=["builder_review"],
        )


def test_real_financial_agent_reports_builder_review() -> None:
    agent = CashRunwayFinancialAgent(risk_builder=ReviewBuilder())
    assert agent.analyze(IPOProfile(company_name="Demo"), financial_chunks()) == []
    assert agent.last_diagnostics.status == CashRunwayAgentStatus.BUILDER_NEEDS_REVIEW
    assert agent.last_diagnostics.issues == ["builder_review"]


def test_nonnegative_operating_cash_flow_is_not_applicable() -> None:
    agent = CashRunwayFinancialAgent()
    assert agent.analyze(
        IPOProfile(company_name="Demo"),
        financial_chunks(operating_value="83,918"),
    ) == []
    assert agent.last_diagnostics.status == CashRunwayAgentStatus.NOT_APPLICABLE


class ExplodingExtractor:
    def extract(self, *args):
        raise RuntimeError("extractor failed")


def test_extractor_exception_updates_component_failure_diagnostics() -> None:
    agent = CashRunwayFinancialAgent()
    assert agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())
    agent.extractor = ExplodingExtractor()

    with pytest.raises(RuntimeError, match="extractor failed"):
        agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())

    assert agent.last_diagnostics.status == CashRunwayAgentStatus.COMPONENT_FAILURE
    assert agent.last_diagnostics.issues == ["extractor_failure"]
    assert agent.last_diagnostics.metadata == {
        "component": "extractor",
        "error_type": "RuntimeError",
    }


class ExplodingBuilder:
    def build(self, extraction, evidence):
        raise RuntimeError("builder failed")


def test_builder_exception_updates_component_failure_diagnostics() -> None:
    agent = CashRunwayFinancialAgent()
    assert agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())
    agent.risk_builder = ExplodingBuilder()

    with pytest.raises(RuntimeError, match="builder failed"):
        agent.analyze(IPOProfile(company_name="Demo"), financial_chunks())

    assert agent.last_diagnostics.status == CashRunwayAgentStatus.COMPONENT_FAILURE
    assert agent.last_diagnostics.issues == ["risk_builder_failure"]
    assert agent.last_diagnostics.metadata == {
        "component": "risk_builder",
        "error_type": "RuntimeError",
    }
    assert agent.last_diagnostics.extraction_status == {
        "cash_and_cash_equivalents": "extracted",
        "operating_cash_flow": "extracted",
    }
