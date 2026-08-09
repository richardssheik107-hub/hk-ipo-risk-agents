"""Small numeric regressions from draft financial annotations; no PDF access."""

from datetime import date
from decimal import Decimal

import pytest

from ipo_risk.agents.financial_builders import V03FinancialRiskBuilder
from ipo_risk.agents.financial_policy import load_v03_financial_policy
from ipo_risk.agents.financial_verifier import V03FinancialVerifier
from ipo_risk.domain.cash_runway import CashRunwayRiskBuilder
from ipo_risk.extraction import (
    ConcentrationFact,
    ExtractionStatus,
    FinancialExtractionResult,
    FinancialMetricValue,
    FinancialPeriodFact,
    FinancialPeriodSeriesResult,
)
from ipo_risk.schemas import DocumentChunk, Evidence, RiskItem, RiskLevel, VerificationStatus


def source(evidence_id: str, text: str) -> tuple[Evidence, DocumentChunk]:
    item = Evidence(
        evidence_id=evidence_id,
        document_id="golden-doc",
        chunk_id=f"chunk-{evidence_id}",
        page=1,
        text=text,
    )
    chunk = DocumentChunk(
        document_id="golden-doc",
        chunk_id=item.chunk_id,
        page=1,
        text=text,
    )
    return item, chunk


def verify(risk: RiskItem) -> RiskItem:
    result = V03FinancialVerifier().verify([risk], {})
    assert result.pending_risks == []
    assert result.rejected_risks == []
    assert len(result.verified_risks) == 1
    return result.verified_risks[0]


def loss_risk(values: list[str]) -> RiskItem:
    item, chunk = source("loss-gold", "年内亏损 " + " ".join(f"({abs(Decimal(value))})" for value in values))
    facts = [
        FinancialPeriodFact(
            metric_name="net_result",
            period_end=date(2021 + index, 12, 31),
            period_months=12,
            normalized_value=Decimal(value),
            currency="CNY",
            unit="thousand",
            evidence_ids=[item.evidence_id],
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            page=item.page,
            status=ExtractionStatus.EXTRACTED,
        )
        for index, value in enumerate(values)
    ]
    series = FinancialPeriodSeriesResult(
        metric_name="net_result",
        observations=facts,
        status=ExtractionStatus.EXTRACTED,
        evidence_ids=[item.evidence_id],
    )
    decision = V03FinancialRiskBuilder(load_v03_financial_policy()).build_continuous_loss(
        series, {item.evidence_id: item}, {chunk.chunk_id: chunk}
    )
    assert decision.risk is not None
    return decision.risk


def revenue_risk(previous: str, current: str) -> RiskItem:
    item, chunk = source("revenue-gold", f"收入 {previous} {current}")
    facts = [
        FinancialPeriodFact(
            metric_name="revenue",
            period_end=period_end,
            period_months=12,
            normalized_value=Decimal(value),
            currency="CNY",
            unit="thousand",
            evidence_ids=[item.evidence_id],
            document_id=item.document_id,
            chunk_id=item.chunk_id,
            page=item.page,
            status=ExtractionStatus.EXTRACTED,
        )
        for period_end, value in (
            (date(2021, 12, 31), previous),
            (date(2022, 12, 31), current),
        )
    ]
    series = FinancialPeriodSeriesResult(
        metric_name="revenue",
        observations=facts,
        status=ExtractionStatus.EXTRACTED,
        evidence_ids=[item.evidence_id],
    )
    decision = V03FinancialRiskBuilder(load_v03_financial_policy()).build_revenue_growth(
        series, {item.evidence_id: item}, {chunk.chunk_id: chunk}
    )
    assert decision.risk is not None
    return decision.risk


def concentration_risk(kind: str, largest: str, top_five: str) -> RiskItem:
    item, chunk = source(
        f"{kind}-gold", f"largest {kind} {largest}%; top five {top_five}%"
    )
    fact = ConcentrationFact(
        concentration_type=kind,
        period_end=date(2023, 12, 31),
        period_months=12,
        largest_counterparty_pct=Decimal(largest),
        top_five_pct=Decimal(top_five),
        evidence_ids=[item.evidence_id],
        document_id=item.document_id,
        chunk_id=item.chunk_id,
        page=item.page,
        status=ExtractionStatus.EXTRACTED,
    )
    decision = V03FinancialRiskBuilder(load_v03_financial_policy()).build_concentration(
        fact, {item.evidence_id: item}, {chunk.chunk_id: chunk}
    )
    assert decision.risk is not None
    return decision.risk


def cash_risk() -> RiskItem:
    cash, _ = source("cash-gold", "Cash and cash equivalents 77,208")
    flow, _ = source("flow-gold", "Operating cash flow (83,918)")
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=FinancialMetricValue(
            metric_name="cash_and_cash_equivalents",
            normalized_value=Decimal("77208"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            evidence_id=cash.evidence_id,
            document_id=cash.document_id,
            chunk_id=cash.chunk_id,
            page=cash.page,
            status=ExtractionStatus.EXTRACTED,
        ),
        operating_cash_flow=FinancialMetricValue(
            metric_name="operating_cash_flow",
            normalized_value=Decimal("-83918"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            period_months=3,
            evidence_id=flow.evidence_id,
            document_id=flow.document_id,
            chunk_id=flow.chunk_id,
            page=flow.page,
            status=ExtractionStatus.EXTRACTED,
        ),
    )
    built = CashRunwayRiskBuilder().build(
        extraction, {cash.evidence_id: cash, flow.evidence_id: flow}
    )
    assert built.risk_item is not None
    return built.risk_item.model_copy(
        update={"metadata": {**built.risk_item.metadata, "rule_version": "v03_contract_v1"}}
    )


def test_1167_two_comparable_annual_losses_verify_as_medium() -> None:
    risk = verify(loss_risk(["-155935", "-425817"]))
    assert risk.level == RiskLevel.MEDIUM
    assert risk.calculation.result == 2


@pytest.mark.parametrize(
    ("case_id", "previous", "current", "rounded", "level"),
    [
        ("1541.HK", "5067", "538", "-89.38", RiskLevel.HIGH),
        ("9633.HK", "9917234", "8663655", "-12.64", RiskLevel.MEDIUM),
        ("2410.HK", "44242", "0", "-100.00", RiskLevel.HIGH),
    ],
)
def test_draft_revenue_golden_values_verify(
    case_id: str, previous: str, current: str, rounded: str, level: RiskLevel
) -> None:
    risk = verify(revenue_risk(previous, current))
    assert case_id
    assert risk.level == level
    assert risk.metadata["growth_pct_rounded"] == rounded


@pytest.mark.parametrize(
    ("case_id", "kind", "largest", "top_five", "level"),
    [
        ("1541.HK", "customer", "43.6", "89.1", RiskLevel.HIGH),
        ("8489.HK", "customer", "37.5", "68.0", RiskLevel.MEDIUM),
        ("8489.HK", "supplier", "22.6", "68.0", RiskLevel.MEDIUM),
    ],
)
def test_draft_concentration_golden_values_verify(
    case_id: str, kind: str, largest: str, top_five: str, level: RiskLevel
) -> None:
    risk = verify(concentration_risk(kind, largest, top_five))
    assert case_id
    assert risk.level == level
    assert risk.metadata["largest_counterparty_pct"] == largest
    assert risk.metadata["top_five_pct"] == top_five


def test_2410_cash_runway_remains_2_76_months_and_verified() -> None:
    risk = verify(cash_risk())
    assert risk.verification_status == VerificationStatus.VERIFIED
    assert risk.level == RiskLevel.CRITICAL
    assert risk.calculation.result == "2.76"
    assert risk.metadata["runway_months_rounded"] == "2.76"
