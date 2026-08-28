from datetime import date
from decimal import Decimal

from pydantic import TypeAdapter

from ipo_risk.domain.cash_runway import (
    CashRunwayBuildResult,
    CashRunwayBuildStatus,
    CashRunwayRiskBuilder,
)
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import Calculation, Evidence, RiskItem


def inputs() -> tuple[FinancialExtractionResult, dict[str, Evidence]]:
    cash = FinancialMetricValue(
        metric_name="cash_and_cash_equivalents",
        normalized_value=Decimal("77208"),
        currency="CNY",
        unit="thousand",
        period_end=date(2024, 3, 31),
        evidence_id="cash-e",
        document_id="doc",
        chunk_id="cash-chunk",
        page=1,
        status=ExtractionStatus.EXTRACTED,
        extraction_method="page_text_rule",
    )
    cash_flow = FinancialMetricValue(
        metric_name="operating_cash_flow",
        normalized_value=Decimal("-83918"),
        currency="CNY",
        unit="thousand",
        period_end=date(2024, 3, 31),
        period_months=3,
        evidence_id="ocf-e",
        document_id="doc",
        chunk_id="ocf-chunk",
        page=2,
        status=ExtractionStatus.EXTRACTED,
        extraction_method="page_text_rule",
    )
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=cash,
        operating_cash_flow=cash_flow,
    )
    evidence = {
        "cash-e": Evidence(
            evidence_id="cash-e",
            document_id="doc",
            chunk_id="cash-chunk",
            page=1,
            text="cash",
        ),
        "ocf-e": Evidence(
            evidence_id="ocf-e",
            document_id="doc",
            chunk_id="ocf-chunk",
            page=2,
            text="cash flow",
        ),
    }
    return extraction, evidence


def test_builder_returns_typed_public_calculation_and_risk_item() -> None:
    extraction, evidence = inputs()
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert isinstance(result, CashRunwayBuildResult)
    assert isinstance(result.calculation, Calculation)
    assert isinstance(result.risk_item, RiskItem)


def test_build_result_round_trips_through_pydantic_json() -> None:
    extraction, evidence = inputs()
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    restored = TypeAdapter(CashRunwayBuildResult).validate_json(result.model_dump_json())
    assert restored == result
    assert restored.status == CashRunwayBuildStatus.BUILT


def test_calculation_inputs_are_json_safe_decimal_strings() -> None:
    extraction, evidence = inputs()
    result = CashRunwayRiskBuilder().build(extraction, evidence)
    assert result.calculation is not None
    assert result.calculation.inputs["cash"] == "77208"
    assert result.calculation.inputs["operating_cash_flow"] == "-83918"
    assert Decimal(result.calculation.inputs["monthly_burn"]) > 0
    assert result.calculation.result == str(
        Decimal("77208") * Decimal("3") / Decimal("83918")
    )
    assert result.risk_item is not None
    assert result.risk_item.metadata["runway_months_rounded"] == "2.76"


def test_result_collection_defaults_are_not_shared() -> None:
    first = CashRunwayBuildResult(status=CashRunwayBuildStatus.NEEDS_REVIEW)
    second = CashRunwayBuildResult(status=CashRunwayBuildStatus.NEEDS_REVIEW)
    first.issues.append("x")
    first.metadata["x"] = 1
    assert second.issues == []
    assert second.metadata == {}
