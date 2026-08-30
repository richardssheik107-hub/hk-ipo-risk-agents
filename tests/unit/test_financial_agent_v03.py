from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.agents.financial import CashRunwayAgentDiagnostics, CashRunwayAgentStatus
from ipo_risk.agents.financial_builders import V03FinancialRiskBuilder
from ipo_risk.agents.financial_models import ConcentrationObservation
from ipo_risk.agents.financial_policy import load_v03_financial_policy
from ipo_risk.agents.financial_v03 import FINANCIAL_EVIDENCE_QUERIES, V03FinancialAgent
from ipo_risk.extraction import ConcentrationFact, ExtractionStatus, V03FinancialFactExtractor
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    IPOProfile,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SkillResult,
    VerificationStatus,
)


class NoCashRunwayAgent:
    def __init__(self, status: CashRunwayAgentStatus = CashRunwayAgentStatus.NOT_APPLICABLE):
        self.last_diagnostics = CashRunwayAgentDiagnostics(status=status)

    def analyze(self, profile, chunks, market=None):
        return []


class RiskSpecificRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def retrieve_for_risk(self, chunks, risk_code, *, limit=20):
        self.calls.append((risk_code, limit))
        return []


class EvidenceByRiskRetriever:
    def __init__(self, values: dict[str, list[Evidence]]) -> None:
        self.values = values

    def retrieve_for_risk(self, chunks, risk_code, *, limit=20):
        return list(self.values.get(risk_code, ()))[:limit]


def test_financial_agent_prefers_bounded_risk_specific_candidate_pool() -> None:
    retriever = RiskSpecificRetriever()
    agent = v03_agent(retriever=retriever)

    agent.analyze(IPOProfile(company_name="Demo"), [])

    assert retriever.calls == [
        ("continuous_loss", 10),
        ("revenue_growth", 10),
        ("customer_concentration", 20),
        ("supplier_concentration", 20),
    ]


@pytest.mark.parametrize(
    ("risk_code", "text", "signal_code"),
    [
        (
            "customer_concentration",
            "The company is pre-revenue and has not generated any product sales revenue.",
            "customer_denominator_unavailable_pre_revenue",
        ),
        (
            "supplier_concentration",
            "During the track record period the Group had no major suppliers.",
            "major_supplier_term_undefined",
        ),
    ],
)
def test_explicit_qualitative_concentration_ambiguity_creates_pending_review(
    risk_code: str,
    text: str,
    signal_code: str,
) -> None:
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="qualitative",
        page=7,
        text=text,
    )
    evidence = Evidence(
        evidence_id="e-qualitative",
        document_id="doc",
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text,
    )
    retriever = EvidenceByRiskRetriever({risk_code: [evidence]})
    agent = v03_agent(retriever=retriever)

    observed = agent.analyze(IPOProfile(company_name="Demo"), [chunk])
    risk = risk_by_code(observed, risk_code)

    assert risk is not None
    assert risk.verification_status == VerificationStatus.PENDING
    assert risk.level == RiskLevel.MEDIUM
    assert risk.calculation is None
    assert risk.metadata["issue"] == signal_code
    assert risk.metadata["percentage_inferred"] is False
    assert [item.evidence_id for item in risk.evidence] == [evidence.evidence_id]


def test_generic_concentration_language_does_not_create_qualitative_risk() -> None:
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="generic",
        page=8,
        text="We work with many customers and suppliers in the ordinary course.",
    )
    evidence = Evidence(
        evidence_id="e-generic",
        document_id="doc",
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text,
    )
    retriever = EvidenceByRiskRetriever(
        {
            "customer_concentration": [evidence],
            "supplier_concentration": [evidence],
        }
    )

    observed = v03_agent(retriever=retriever).analyze(
        IPOProfile(company_name="Demo"),
        [chunk],
    )

    assert risk_by_code(observed, "customer_concentration") is None
    assert risk_by_code(observed, "supplier_concentration") is None


def v03_agent(**kwargs) -> V03FinancialAgent:
    return V03FinancialAgent(cash_runway_agent=NoCashRunwayAgent(), **kwargs)


def period_chunks(
    prefix: str,
    page: int,
    row: str,
    periods: list[tuple[str, int]],
    *,
    currency_unit: str = "人民币千元",
) -> list[DocumentChunk]:
    header = "\n".join(
        [
            currency_unit,
            *[
                f"截至{period_end}止{'年度' if months == 12 else f'{months}個月'}"
                for period_end, months in periods
            ],
        ]
    )
    return [
        DocumentChunk(
            document_id="doc",
            chunk_id=f"{prefix}-header",
            page=page,
            section="財務資料",
            text=header,
        ),
        DocumentChunk(
            document_id="doc",
            chunk_id=f"{prefix}-row",
            page=page + 1,
            section="財務資料",
            text=row,
        ),
    ]


def loss_chunks(values: list[str], periods: list[tuple[str, int]] | None = None):
    periods = periods or [
        (f"{2022 + index}年12月31日", 12) for index in range(len(values))
    ]
    return period_chunks("loss", 10, f"年內虧損 {' '.join(values)}", periods)


def revenue_chunks(previous: str, current: str, *, months: int = 12):
    day = "12月31日" if months == 12 else "6月30日"
    return period_chunks(
        "revenue",
        20,
        f"收入 {previous} {current}",
        [(f"2022年{day}", months), (f"2023年{day}", months)],
    )


def concentration_chunk(
    kind: str,
    largest: str,
    top_five: str,
    *,
    page: int,
    months: int = 12,
) -> DocumentChunk:
    party = "客戶" if kind == "customer" else "供應商"
    date_text = "2023年12月31日" if months == 12 else "2023年6月30日"
    period_text = "年度" if months == 12 else f"{months}個月"
    return DocumentChunk(
        document_id="doc",
        chunk_id=f"{kind}-row",
        page=page,
        section="業務資料",
        text=(
            f"截至{date_text}止{period_text}，最大{party}佔比{largest}%，"
            f"五大{party}佔比{top_five}%。"
        ),
    )


def cash_chunks() -> list[DocumentChunk]:
    header = (
        "截至12月31日止年度\n截至3月31日止三個月\n"
        "2022年\n2023年\n2023年\n2024年\n人民幣千元\n"
    )
    return [
        DocumentChunk(
            document_id="doc",
            chunk_id="cash-flow",
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
            chunk_id="cash",
            page=2,
            text=(
                header
                + "現金流量表所述現金及現金等價物\n"
                "90,762\n186,830\n111,745\n77,208"
            ),
        ),
    ]


def risk_by_code(risks: list[RiskItem], risk_code: str) -> RiskItem | None:
    return next((item for item in risks if item.risk_code == risk_code), None)


def test_ranked_table_evidence_augments_existing_risk_without_changing_decision() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("supplier", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "supplier_concentration")
    assert risk is not None
    table_chunk = DocumentChunk(
        document_id="doc",
        chunk_id="supplier-table",
        page=31,
        text="ranked table source",
        metadata={
            "ranked_numeric_table": {
                "detector": "ranked_numeric_1_to_5_v1",
                "counterparty_type": "supplier",
                "largest_counterparty_pct": "45",
                "top_five_pct": "80",
                "rank_rows": [{"rank": rank} for rank in range(1, 6)],
            }
        },
    )
    table_evidence = Evidence(
        evidence_id="e-ranked-table",
        document_id="doc",
        chunk_id=table_chunk.chunk_id,
        page=table_chunk.page,
        text="ranked table source",
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "supplier_concentration",
        risk,
        [*risk.evidence, table_evidence],
        {table_chunk.chunk_id: table_chunk},
    )

    assert observed is not None
    assert [item.evidence_id for item in observed.evidence][-1] == "e-ranked-table"
    assert observed.level == risk.level
    assert observed.score == risk.score
    assert observed.verification_status == risk.verification_status
    assert observed.calculation == risk.calculation
    assert observed.metadata["ranked_table_evidence_augmented"] == 1


def test_ranked_table_evidence_cannot_cross_concentration_type() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("customer", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "customer_concentration")
    assert risk is not None
    chunk = DocumentChunk(
        document_id="doc",
        chunk_id="supplier-table",
        page=31,
        text="ranked table source",
        metadata={
            "ranked_numeric_table": {
                "detector": "ranked_numeric_1_to_5_v1",
                "counterparty_type": "supplier",
                "largest_counterparty_pct": "45",
                "top_five_pct": "80",
                "rank_rows": [{"rank": rank} for rank in range(1, 6)],
            }
        },
    )
    evidence = Evidence(
        evidence_id="e-wrong-type",
        document_id="doc",
        chunk_id=chunk.chunk_id,
        page=chunk.page,
        text=chunk.text,
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "customer_concentration", risk, [evidence], {chunk.chunk_id: chunk}
    )

    assert observed is risk


def test_parsed_concentration_support_is_retained_without_changing_decision() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("customer", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "customer_concentration")
    assert risk is not None
    supporting = Evidence(
        evidence_id="e-parsed-support",
        document_id="doc",
        chunk_id="supporting",
        page=31,
        text="五大客戶佔收益79%，最大客戶佔收益44%。",
    )
    extraction = ConcentrationFact(
        concentration_type="customer",
        status=ExtractionStatus.EXTRACTED,
        metadata={
            "candidate_diagnostics": [
                {
                    "largest_counterparty_pct": "44",
                    "top_five_pct": "79",
                    "evidence_ids": [supporting.evidence_id],
                    "issues": ["latest_period_months_ambiguous"],
                }
            ]
        },
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "customer_concentration",
        risk,
        [supporting],
        {supporting.chunk_id: DocumentChunk(
            document_id="doc", chunk_id="supporting", page=31, text=supporting.text
        )},
        extraction,
    )

    assert observed is not None
    assert [item.evidence_id for item in observed.evidence][-1] == supporting.evidence_id
    assert observed.level == risk.level
    assert observed.score == risk.score
    assert observed.verification_status == risk.verification_status
    assert observed.calculation == risk.calculation


def test_structurally_invalid_concentration_support_is_not_retained() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("supplier", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "supplier_concentration")
    assert risk is not None
    invalid = Evidence(
        evidence_id="e-invalid-support",
        document_id="doc",
        chunk_id="invalid",
        page=31,
        text="五大供應商佔採購753.1%。",
    )
    extraction = ConcentrationFact(
        concentration_type="supplier",
        status=ExtractionStatus.NEEDS_REVIEW,
        metadata={
            "candidate_diagnostics": [
                {
                    "largest_counterparty_pct": None,
                    "top_five_pct": "753.1",
                    "evidence_ids": [invalid.evidence_id],
                    "issues": ["percentage_out_of_range"],
                }
            ]
        },
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "supplier_concentration",
        risk,
        [invalid],
        {invalid.chunk_id: DocumentChunk(
            document_id="doc", chunk_id="invalid", page=31, text=invalid.text
        )},
        extraction,
    )

    assert observed is risk


def test_top_ranked_type_specific_disclosure_is_retained_as_evidence_only() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("supplier", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "supplier_concentration")
    assert risk is not None
    supporting = Evidence(
        evidence_id="e-principal-suppliers",
        document_id="doc",
        chunk_id="principal-suppliers",
        page=31,
        text="我們與190多家供應商合作，並將其中四家公司視為主要供應商。",
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "supplier_concentration",
        risk,
        [supporting],
        {},
    )

    assert observed is not None
    assert [item.evidence_id for item in observed.evidence][-1] == supporting.evidence_id
    assert observed.level == risk.level
    assert observed.score == risk.score
    assert observed.verification_status == risk.verification_status
    assert observed.calculation == risk.calculation
    assert observed.metadata["ranked_disclosure_evidence_augmented"] == 1


def test_ranked_disclosure_support_is_type_and_rank_bounded() -> None:
    base = v03_agent().analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("customer", "45", "80", page=30)],
    )
    risk = risk_by_code(base, "customer_concentration")
    assert risk is not None
    wrong_type = Evidence(
        evidence_id="e-wrong-type-disclosure",
        document_id="doc",
        chunk_id="wrong-type-disclosure",
        page=31,
        text="五大供應商的採購詳情。",
    )
    unrelated = [
        Evidence(
            evidence_id=f"e-unrelated-{index}",
            document_id="doc",
            chunk_id=f"unrelated-{index}",
            page=32 + index,
            text="一般業務資料。",
        )
        for index in range(4)
    ]
    rank_six = Evidence(
        evidence_id="e-rank-six-customer",
        document_id="doc",
        chunk_id="rank-six-customer",
        page=40,
        text="五大客戶的收入詳情。",
    )

    observed = V03FinancialAgent._augment_ranked_concentration_evidence(
        "customer_concentration",
        risk,
        [wrong_type, *unrelated, rank_six],
        {},
    )

    assert observed is risk


def diagnostic_by_code(agent: V03FinancialAgent, risk_code: str) -> ComponentDiagnostic:
    return next(item for item in agent.last_diagnostics if item.risk_code == risk_code)


def test_real_v03_agent_builds_all_five_pending_financial_risks() -> None:
    chunks = [
        *cash_chunks(),
        *loss_chunks(["(100)", "(200)"]),
        *revenue_chunks("5,067", "538"),
        concentration_chunk("customer", "37.5", "68.0", page=30),
        concentration_chunk("supplier", "22.6", "68.0", page=40),
    ]
    agent = V03FinancialAgent()

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert [item.risk_code for item in risks] == [
        "cash_runway",
        "continuous_loss",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    ]
    assert all(item.category == RiskCategory.FINANCIAL for item in risks)
    assert all(item.agent_name == "financial" for item in risks)
    assert all(item.verification_status == VerificationStatus.PENDING for item in risks)
    assert all(item.calculation and item.calculation.success for item in risks)
    assert [item.risk_code for item in agent.last_diagnostics] == [item.risk_code for item in risks]
    assert all(item.code == DiagnosticCode.RISK_GENERATED for item in agent.last_diagnostics)
    cash_runway = risk_by_code(risks, "cash_runway")
    assert cash_runway.calculation.result == str(
        Decimal("77208") * Decimal("3") / Decimal("83918")
    )
    assert cash_runway.metadata["runway_months_rounded"] == "2.76"


def test_agent_protocol_empty_input_returns_empty_list_and_five_diagnostics() -> None:
    agent = v03_agent()

    risks = agent.analyze(IPOProfile(company_name="Empty"), [])

    assert risks == []
    assert agent.name == "financial"
    assert len(agent.last_diagnostics) == 5
    assert all(isinstance(item, ComponentDiagnostic) for item in agent.last_diagnostics)
    assert diagnostic_by_code(agent, "cash_runway").code == DiagnosticCode.NOT_APPLICABLE
    assert all(
        diagnostic_by_code(agent, code).code == DiagnosticCode.EVIDENCE_NOT_FOUND
        for code in (
            "continuous_loss",
            "revenue_growth",
            "customer_concentration",
            "supplier_concentration",
        )
    )


@pytest.mark.parametrize(
    ("values", "expected_level", "expected_code"),
    [
        (["(100)", "(200)"], RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        (["(100)", "(200)", "(300)"], RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        (["(100)"], None, DiagnosticCode.NOT_APPLICABLE),
    ],
)
def test_continuous_loss_boundaries(
    values: list[str], expected_level: RiskLevel | None, expected_code: DiagnosticCode
) -> None:
    agent = v03_agent()
    risks = agent.analyze(IPOProfile(company_name="Demo"), loss_chunks(values))
    risk = risk_by_code(risks, "continuous_loss")

    assert (risk.level if risk else None) == expected_level
    assert diagnostic_by_code(agent, "continuous_loss").code == expected_code
    if risk:
        assert risk.calculation is not None
        assert set(risk.calculation.evidence_ids) <= {
            item.evidence_id for item in risk.evidence
        }


def test_latest_profit_interrupts_continuous_loss() -> None:
    chunks = period_chunks(
        "loss",
        10,
        "年╱期內溢利（虧損） (100) 200",
        [("2022年12月31日", 12), ("2023年12月31日", 12)],
    )
    agent = v03_agent()

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "continuous_loss") is None
    assert diagnostic_by_code(agent, "continuous_loss").code == DiagnosticCode.NOT_APPLICABLE


def test_latest_loss_period_without_comparable_peer_needs_review() -> None:
    periods = [
        ("2021年12月31日", 12),
        ("2022年12月31日", 12),
        ("2023年6月30日", 6),
    ]
    agent = v03_agent()
    risks = agent.analyze(
        IPOProfile(company_name="Demo"), loss_chunks(["(1)", "(2)", "(3)"], periods)
    )

    assert risk_by_code(risks, "continuous_loss") is None
    diagnostic = diagnostic_by_code(agent, "continuous_loss")
    assert diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert diagnostic.metadata["issue"] == "latest_loss_period_has_no_comparable_peer"


@pytest.mark.parametrize(
    ("previous", "current", "expected_level", "expected_code"),
    [
        ("5067", "538", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("9917234", "8663655", RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        ("44242", "0", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("100", "120", None, DiagnosticCode.NOT_APPLICABLE),
        ("100", "80", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("100", "100", None, DiagnosticCode.NOT_APPLICABLE),
    ],
)
def test_revenue_growth_boundaries(
    previous: str,
    current: str,
    expected_level: RiskLevel | None,
    expected_code: DiagnosticCode,
) -> None:
    agent = v03_agent()
    risks = agent.analyze(
        IPOProfile(company_name="Demo"), revenue_chunks(previous, current)
    )
    risk = risk_by_code(risks, "revenue_growth")

    assert (risk.level if risk else None) == expected_level
    assert diagnostic_by_code(agent, "revenue_growth").code == expected_code
    if risk:
        assert risk.calculation is not None
        assert len(risk.calculation.evidence_ids) == 1
        assert risk.calculation.unit == "percent"
        assert isinstance(risk.calculation.result, str)


@pytest.mark.parametrize(
    ("previous", "current", "expected_rounded"),
    [
        ("5067", "538", "-89.38"),
        ("9917234", "8663655", "-12.64"),
        ("44242", "0", "-100.00"),
    ],
)
def test_stage_one_revenue_values_keep_exact_decimal_calculations(
    previous: str, current: str, expected_rounded: str
) -> None:
    agent = v03_agent()
    risk = risk_by_code(
        agent.analyze(
            IPOProfile(company_name="Demo"), revenue_chunks(previous, current)
        ),
        "revenue_growth",
    )

    assert risk is not None and risk.calculation is not None
    assert risk.metadata["growth_pct_rounded"] == expected_rounded
    assert Decimal(risk.calculation.result).is_finite()


def test_revenue_calculation_can_trace_two_distinct_period_evidence_items() -> None:
    chunks = [
        *period_chunks("revenue-old", 20, "收入 100", [("2022年12月31日", 12)]),
        *period_chunks("revenue-new", 30, "收入 80", [("2023年12月31日", 12)]),
    ]
    agent = v03_agent()

    risk = risk_by_code(
        agent.analyze(IPOProfile(company_name="Demo"), chunks), "revenue_growth"
    )

    assert risk is not None and risk.calculation is not None
    assert len(risk.calculation.evidence_ids) == 2
    assert risk.calculation.evidence_ids == [item.evidence_id for item in risk.evidence]


def test_latest_revenue_period_without_comparable_peer_needs_review() -> None:
    chunks = period_chunks(
        "revenue",
        20,
        "收入 100 90",
        [("2022年12月31日", 12), ("2023年6月30日", 6)],
    )
    agent = v03_agent()

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "revenue_growth") is None
    assert diagnostic_by_code(agent, "revenue_growth").code == DiagnosticCode.NEEDS_REVIEW


@pytest.mark.parametrize(
    ("kind", "largest", "top_five", "expected_level", "expected_code"),
    [
        ("customer", "37.5", "68.0", RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        ("customer", "50", "60", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("customer", "30", "80", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("customer", "10", "20", None, DiagnosticCode.NOT_APPLICABLE),
        ("supplier", "22.6", "68.0", RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        ("supplier", "30", "40", RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        ("supplier", "50", "50", RiskLevel.HIGH, DiagnosticCode.RISK_GENERATED),
        ("supplier", "20", "60", RiskLevel.MEDIUM, DiagnosticCode.RISK_GENERATED),
        ("supplier", "10", "20", None, DiagnosticCode.NOT_APPLICABLE),
    ],
)
def test_concentration_policy_boundaries(
    kind: str,
    largest: str,
    top_five: str,
    expected_level: RiskLevel | None,
    expected_code: DiagnosticCode,
) -> None:
    risk_code = f"{kind}_concentration"
    agent = v03_agent()
    risks = agent.analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk(kind, largest, top_five, page=30)],
    )
    risk = risk_by_code(risks, risk_code)

    assert (risk.level if risk else None) == expected_level
    diagnostic = diagnostic_by_code(agent, risk_code)
    assert diagnostic.code == expected_code
    assert diagnostic.metadata["period_months"] == 12
    if risk:
        assert risk.calculation is not None
        assert risk.calculation.inputs["period_months"] == 12
        assert risk.metadata["period_months"] == 12
        assert risk.calculation.evidence_ids == [item.evidence_id for item in risk.evidence]


def test_concentration_builder_preserves_stronger_disclosed_track_record_pair() -> None:
    evidence = Evidence(
        evidence_id="e-track-record",
        document_id="doc",
        chunk_id="track-record-table",
        page=30,
        text=(
            "Largest supplier percentages were 38.3%, 43.5%, 50.1% and 41.1%; "
            "top-five supplier percentages were 43.9%, 47.3%, 57.5% and 53.3%."
        ),
    )
    chunk = DocumentChunk(
        document_id=evidence.document_id,
        chunk_id=evidence.chunk_id,
        page=evidence.page,
        text=evidence.text,
    )
    fact = ConcentrationFact(
        concentration_type="supplier",
        period_end=date(2020, 4, 30),
        period_months=4,
        largest_counterparty_pct=Decimal("41.1"),
        top_five_pct=Decimal("53.3"),
        evidence_ids=[evidence.evidence_id],
        document_id=evidence.document_id,
        chunk_id=evidence.chunk_id,
        page=evidence.page,
        status=ExtractionStatus.EXTRACTED,
        metadata={
            "candidate_diagnostics": [
                {
                    "status": "extracted",
                    "issues": [],
                    "period_end": "2020-04-30",
                    "period_months": 4,
                    "largest_counterparty_pct": "41.1",
                    "top_five_pct": "53.3",
                    "evidence_ids": [evidence.evidence_id],
                    "raw_percentages": {
                        "largest": ["38.3%", "43.5%", "50.1%", "41.1%"],
                        "top_five": ["43.9%", "47.3%", "57.5%", "53.3%"],
                    },
                }
            ]
        },
    )

    decision = V03FinancialRiskBuilder(
        load_v03_financial_policy()
    ).build_concentration(
        fact,
        {evidence.evidence_id: evidence},
        {chunk.chunk_id: chunk},
    )

    assert decision.risk is not None
    assert decision.risk.level == RiskLevel.HIGH
    assert decision.risk.metadata["decision_basis"] == (
        "track_record_peak_disclosed_series"
    )
    assert decision.risk.metadata["track_record_peak_index"] == 2
    assert decision.risk.calculation is not None
    assert decision.risk.calculation.inputs["largest_counterparty_pct"] == "50.1"
    assert decision.risk.calculation.inputs["top_five_pct"] == "57.5"
    assert "Across the disclosed track-record series" in decision.risk.conclusion


def test_concentration_builder_binds_paired_series_to_companion_period_headers() -> None:
    evidence = Evidence(
        evidence_id="e-series-context",
        document_id="doc",
        chunk_id="series-context",
        page=30,
        text="A wide table discloses paired customer concentration series and headers.",
    )
    chunk = DocumentChunk(
        document_id=evidence.document_id,
        chunk_id=evidence.chunk_id,
        page=evidence.page,
        text=evidence.text,
    )
    fact = ConcentrationFact(
        concentration_type="customer",
        period_end=date(2020, 12, 31),
        period_months=None,
        largest_counterparty_pct=Decimal("41.2"),
        top_five_pct=Decimal("44.6"),
        evidence_ids=[evidence.evidence_id],
        status=ExtractionStatus.NEEDS_REVIEW,
        issues=["latest_period_months_ambiguous"],
        metadata={
            "candidate_diagnostics": [
                {
                    "status": "needs_review",
                    "issues": ["latest_period_months_ambiguous"],
                    "period_end": "2020-12-31",
                    "period_months": None,
                    "evidence_ids": [evidence.evidence_id],
                    "raw_percentages": {
                        "largest": ["24.4%", "34.8%", "41.2%"],
                        "top_five": ["24.8%", "35.2%", "44.6%"],
                    },
                },
                {
                    "status": "needs_review",
                    "issues": ["incomplete_concentration_values"],
                    "period_end": "2020-12-31",
                    "period_months": 12,
                    "period_candidates": [
                        {"period_end": "2018-12-31", "period_months": 12},
                        {"period_end": "2019-12-31", "period_months": 12},
                        {"period_end": "2020-12-31", "period_months": 12},
                    ],
                    "evidence_ids": [evidence.evidence_id],
                    "raw_percentages": {"largest": [], "top_five": ["1.7%"]},
                },
            ]
        },
    )

    decision = V03FinancialRiskBuilder(load_v03_financial_policy()).build_concentration(
        fact,
        {evidence.evidence_id: evidence},
        {chunk.chunk_id: chunk},
    )

    assert decision.risk is not None
    assert decision.risk.verification_status == VerificationStatus.PENDING
    assert decision.risk.level == RiskLevel.MEDIUM
    assert decision.risk.calculation is not None
    assert decision.risk.calculation.inputs["period_months"] == 12
    assert decision.risk.metadata["decision_basis"] == (
        "track_record_companion_period_binding"
    )


def test_low_concentration_with_incomplete_companion_series_requires_review() -> None:
    evidence = Evidence(
        evidence_id="e-clean-series",
        document_id="doc",
        chunk_id="clean-series",
        page=30,
        text="Largest suppliers were 2.2%, 1.5%, 2.4%; top five were 8.8%, 6.8%, 7.4%.",
    )
    incomplete = Evidence(
        evidence_id="e-incomplete-series",
        document_id="doc",
        chunk_id="incomplete-series",
        page=31,
        text="A separate disclosed supplier series was 0.7% and 1.1%.",
    )
    fact = ConcentrationFact(
        concentration_type="supplier",
        period_end=date(2020, 12, 31),
        period_months=12,
        largest_counterparty_pct=Decimal("2.4"),
        top_five_pct=Decimal("7.4"),
        evidence_ids=[evidence.evidence_id],
        status=ExtractionStatus.EXTRACTED,
        metadata={
            "candidate_diagnostics": [
                {
                    "status": "extracted",
                    "issues": [],
                    "evidence_ids": [evidence.evidence_id],
                    "raw_percentages": {
                        "largest": ["2.2%", "1.5%", "2.4%"],
                        "top_five": ["8.8%", "6.8%", "7.4%"],
                    },
                },
                {
                    "status": "needs_review",
                    "issues": ["incomplete_concentration_values", "missing_period"],
                    "evidence_ids": [incomplete.evidence_id],
                    "raw_percentages": {
                        "largest": [],
                        "top_five": ["0.7%", "1.1%"],
                    },
                },
            ]
        },
    )
    chunks = {
        item.chunk_id: DocumentChunk(
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            page=item.page,
            text=item.text,
        )
        for item in (evidence, incomplete)
    }

    decision = V03FinancialRiskBuilder(
        load_v03_financial_policy()
    ).build_concentration(
        fact,
        {item.evidence_id: item for item in (evidence, incomplete)},
        chunks,
    )

    assert decision.risk is not None
    assert decision.risk.verification_status == VerificationStatus.PENDING
    assert decision.risk.calculation is None
    assert decision.risk.metadata["decision_basis"] == (
        "track_record_series_requires_review"
    )
    assert {item.evidence_id for item in decision.risk.evidence} == {
        evidence.evidence_id,
        incomplete.evidence_id,
    }


def test_invalid_concentration_relationship_needs_review() -> None:
    agent = v03_agent()

    risks = agent.analyze(
        IPOProfile(company_name="Demo"),
        [concentration_chunk("customer", "70", "60", page=30)],
    )

    risk = risk_by_code(risks, "customer_concentration")
    assert risk is not None
    assert risk.verification_status == VerificationStatus.PENDING
    assert risk.calculation is None
    assert risk.evidence
    assert risk.metadata["candidate_state"] == (
        "bounded_percentage_signal_requires_review"
    )
    assert risk.metadata["provisional_level"] is True
    diagnostic = diagnostic_by_code(agent, "customer_concentration")
    assert diagnostic.code == DiagnosticCode.RISK_GENERATED
    assert "largest_percentage_exceeds_top_five" in risk.metadata["extraction_issues"]


def test_concentration_without_parsed_percentage_remains_diagnostic_only() -> None:
    agent = v03_agent()

    risks = agent.analyze(
        IPOProfile(company_name="Demo"),
        [
            DocumentChunk(
                document_id="doc",
                chunk_id="customer-no-percentage",
                page=30,
                section="業務",
                text="截至2023年12月31日止年度，五大客戶資料未提供百分比。",
            )
        ],
    )

    assert risk_by_code(risks, "customer_concentration") is None
    assert diagnostic_by_code(agent, "customer_concentration").code in {
        DiagnosticCode.NEEDS_REVIEW,
        DiagnosticCode.EXTRACTION_FAILED,
    }


def test_negative_customer_concentration_disclosure_ignores_shareholding_percentage() -> None:
    agent = v03_agent()

    risks = agent.analyze(
        IPOProfile(company_name="Demo"),
        [
            DocumentChunk(
                document_id="doc",
                chunk_id="customer-negative-bound",
                page=31,
                section="業務",
                text=(
                    "本集團於往績記錄期並不依賴任何單一客戶，因此確定本集團"
                    "五大客戶並非切實可行。概無擁有本公司超過5.0%股本的股東"
                    "於客戶中擁有權益。"
                ),
            )
        ],
    )

    assert risk_by_code(risks, "customer_concentration") is None
    assert diagnostic_by_code(agent, "customer_concentration").code in {
        DiagnosticCode.NEEDS_REVIEW,
        DiagnosticCode.EXTRACTION_FAILED,
    }


def test_frozen_concentration_model_excludes_period_months_but_chain_retains_it() -> None:
    assert set(ConcentrationObservation.model_fields) == {
        "concentration_type",
        "period_end",
        "largest_counterparty_pct",
        "top_five_pct",
        "evidence_ids",
    }
    assert "period_months" not in ConcentrationObservation.model_fields

    agent = v03_agent()
    risk = risk_by_code(
        agent.analyze(
            IPOProfile(company_name="Demo"),
            [concentration_chunk("customer", "37.5", "68.0", page=30, months=6)],
        ),
        "customer_concentration",
    )

    assert risk is not None and risk.calculation is not None
    assert risk.calculation.inputs["period_months"] == 6
    assert risk.metadata["period_months"] == 6
    assert diagnostic_by_code(agent, "customer_concentration").metadata["period_months"] == 6


def test_policy_loaded_from_yaml_matches_frozen_boundaries() -> None:
    policy = load_v03_financial_policy()

    assert policy.version == "v03_contract_v1"
    assert policy.cash_runway_level(Decimal("2.999")) == RiskLevel.CRITICAL
    assert policy.cash_runway_level(Decimal("3")) == RiskLevel.HIGH
    assert policy.cash_runway_level(Decimal("6")) == RiskLevel.MEDIUM
    assert policy.cash_runway_level(Decimal("12")) == RiskLevel.LOW
    assert policy.loss_level(2) == RiskLevel.MEDIUM
    assert policy.loss_level(3) == RiskLevel.HIGH
    assert policy.revenue_level(Decimal("-20")) == RiskLevel.HIGH
    assert policy.revenue_level(Decimal("-0.0001")) == RiskLevel.MEDIUM
    assert policy.revenue_level(Decimal("0")) is None
    assert policy.concentration_level("customer", Decimal("50"), None) == RiskLevel.HIGH
    assert policy.concentration_level("supplier", None, Decimal("60")) == RiskLevel.MEDIUM


def test_agent_query_map_is_centralized_multilingual_and_company_agnostic() -> None:
    assert {"年內虧損", "年内亏损", "net loss"} <= set(
        FINANCIAL_EVIDENCE_QUERIES["continuous_loss"]
    )
    assert {"收入", "收益", "revenue"} <= set(
        FINANCIAL_EVIDENCE_QUERIES["revenue_growth"]
    )
    assert {"最大客戶", "最大客户", "largest customer"} <= set(
        FINANCIAL_EVIDENCE_QUERIES["customer_concentration"]
    )
    assert {"最大供應商", "最大供应商", "largest supplier"} <= set(
        FINANCIAL_EVIDENCE_QUERIES["supplier_concentration"]
    )
    assert not any(
        digit in query
        for queries in FINANCIAL_EVIDENCE_QUERIES.values()
        for query in queries
        for digit in ("1167", "1541", "8489", "2503", "9633", "2410")
    )


class SelectiveExplodingRetriever(KeywordDocumentRetriever):
    def retrieve(self, chunks, query, limit=3):
        if query in {
            "年內虧損",
            "年内亏损",
            "期內虧損",
            "net loss",
            "loss for the year",
            "年內溢利",
            "年╱期內溢利",
            "net profit",
            "profit for the year",
        }:
            raise RuntimeError("loss retrieval failed")
        return super().retrieve(chunks, query, limit)


def test_one_retrieval_family_failure_does_not_block_revenue() -> None:
    agent = v03_agent(retriever=SelectiveExplodingRetriever())
    chunks = [*loss_chunks(["(1)", "(2)"]), *revenue_chunks("100", "80")]

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "continuous_loss") is None
    assert risk_by_code(risks, "revenue_growth") is not None
    assert diagnostic_by_code(agent, "continuous_loss").code == DiagnosticCode.COMPONENT_FAILURE
    assert diagnostic_by_code(agent, "revenue_growth").code == DiagnosticCode.RISK_GENERATED


class SelectiveExplodingExtractor(V03FinancialFactExtractor):
    def extract_v03(self, *args, **kwargs):
        if kwargs.get("customer_concentration_candidates"):
            raise RuntimeError("customer extraction failed")
        return super().extract_v03(*args, **kwargs)


def test_one_extraction_family_failure_does_not_block_supplier() -> None:
    agent = v03_agent(extractor=SelectiveExplodingExtractor())
    chunks = [
        concentration_chunk("customer", "37.5", "68", page=30),
        concentration_chunk("supplier", "22.6", "68", page=40),
    ]

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "customer_concentration") is None
    assert risk_by_code(risks, "supplier_concentration") is not None
    assert diagnostic_by_code(agent, "customer_concentration").code == DiagnosticCode.COMPONENT_FAILURE


def failed_revenue_skill(*args, **kwargs) -> SkillResult:
    return SkillResult(
        skill_name="revenue_growth",
        skill_version="test",
        success=False,
        evidence_ids=["known"],
        error="forced_failure",
    )


def test_skill_failure_does_not_block_other_risks() -> None:
    policy = load_v03_financial_policy()
    builder = V03FinancialRiskBuilder(policy, revenue_growth_skill=failed_revenue_skill)
    agent = v03_agent(policy=policy, risk_builder=builder)
    chunks = [
        *loss_chunks(["(1)", "(2)"]),
        *revenue_chunks("100", "80"),
        concentration_chunk("supplier", "22.6", "68", page=40),
    ]

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "continuous_loss") is not None
    assert risk_by_code(risks, "revenue_growth") is None
    assert risk_by_code(risks, "supplier_concentration") is not None
    diagnostic = diagnostic_by_code(agent, "revenue_growth")
    assert diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert diagnostic.metadata["skill_error"] == "forced_failure"


class ExplodingCashRunwayAgent:
    last_diagnostics = None

    def analyze(self, profile, chunks, market=None):
        raise RuntimeError("cash failure")


def test_cash_runway_failure_does_not_block_v03_risks() -> None:
    agent = V03FinancialAgent(cash_runway_agent=ExplodingCashRunwayAgent())

    risks = agent.analyze(
        IPOProfile(company_name="Demo"), revenue_chunks("100", "80")
    )

    assert risk_by_code(risks, "revenue_growth") is not None
    assert diagnostic_by_code(agent, "cash_runway").code == DiagnosticCode.COMPONENT_FAILURE


def test_same_inputs_have_stable_risk_evidence_and_diagnostic_order() -> None:
    chunks = [
        *loss_chunks(["(1)", "(2)"]),
        *revenue_chunks("100", "80"),
        concentration_chunk("customer", "37.5", "68", page=30),
    ]
    agent = v03_agent()

    first = agent.analyze(IPOProfile(company_name="Demo"), chunks)
    first_diagnostics = list(agent.last_diagnostics)
    second = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert [item.risk_id for item in first] == [item.risk_id for item in second]
    assert [[e.evidence_id for e in item.evidence] for item in first] == [
        [e.evidence_id for e in item.evidence] for item in second
    ]
    assert [item.risk_code for item in first_diagnostics] == [
        item.risk_code for item in agent.last_diagnostics
    ]
    revenue = risk_by_code(first, "revenue_growth")
    assert revenue is not None and isinstance(revenue.calculation.result, str)


def test_unsupported_layout_and_conflict_diagnostics_are_distinct() -> None:
    unsupported = period_chunks(
        "revenue", 20, "收入 詳情載於附註", [("2023年12月31日", 12)]
    )
    agent = v03_agent()
    agent.analyze(IPOProfile(company_name="Demo"), unsupported)
    assert diagnostic_by_code(agent, "revenue_growth").code == DiagnosticCode.UNSUPPORTED_LAYOUT

    header = period_chunks(
        "first", 50, "收入 100", [("2023年12月31日", 12)]
    )[0]
    first = DocumentChunk(document_id="doc", chunk_id="first-row", page=51, text="收入 100")
    second = DocumentChunk(document_id="doc", chunk_id="second-row", page=51, text="收入 90")
    agent.analyze(IPOProfile(company_name="Demo"), [header, first, second])
    assert diagnostic_by_code(agent, "revenue_growth").code == DiagnosticCode.CONFLICTING_VALUES


class MisleadingRetriever:
    def retrieve(self, chunks, query, limit=3):
        if query != "收入":
            return []
        chunk = chunks[0]
        return [
            Evidence(
                evidence_id="misleading",
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                page=chunk.page,
                text=chunk.text,
            )
        ]


def test_retrieved_non_target_evidence_is_extraction_failed_not_no_risk() -> None:
    chunk = DocumentChunk(document_id="doc", chunk_id="other", page=1, text="無關披露")
    agent = v03_agent(retriever=MisleadingRetriever())

    agent.analyze(IPOProfile(company_name="Demo"), [chunk])

    assert diagnostic_by_code(agent, "revenue_growth").code == DiagnosticCode.EXTRACTION_FAILED


class MissingEvidenceReferenceExtractor(V03FinancialFactExtractor):
    def extract_v03(self, *args, **kwargs):
        result = super().extract_v03(*args, **kwargs)
        if not kwargs.get("revenue_candidates") or not result.revenues.observations:
            return result
        observations = [
            item.model_copy(update={"evidence_ids": ["missing-evidence"]})
            for item in result.revenues.observations
        ]
        revenues = result.revenues.model_copy(
            update={"observations": observations, "evidence_ids": ["missing-evidence"]}
        )
        return result.model_copy(update={"revenues": revenues})


def test_missing_evidence_reference_blocks_risk_without_blocking_other_family() -> None:
    agent = v03_agent(extractor=MissingEvidenceReferenceExtractor())
    chunks = [
        *revenue_chunks("100", "80"),
        concentration_chunk("supplier", "22.6", "68", page=40),
    ]

    risks = agent.analyze(IPOProfile(company_name="Demo"), chunks)

    assert risk_by_code(risks, "revenue_growth") is None
    assert risk_by_code(risks, "supplier_concentration") is not None
    diagnostic = diagnostic_by_code(agent, "revenue_growth")
    assert diagnostic.code == DiagnosticCode.NEEDS_REVIEW
    assert diagnostic.metadata["issue"] == "referenced_evidence_not_found"
