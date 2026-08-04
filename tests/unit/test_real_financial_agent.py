from decimal import Decimal

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
from ipo_risk.schemas import DocumentChunk, IPOProfile, VerificationStatus


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
