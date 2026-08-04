from datetime import date
from decimal import Decimal

from pydantic import TypeAdapter

from ipo_risk.domain.cash_runway import CashRunwayRiskBuilder
from ipo_risk.domain.cash_runway_verifier import (
    CashRunwayRiskVerifier,
    CashRunwayVerificationResult,
    CashRunwayVerificationStatus,
)
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.schemas import Evidence


def valid_case():
    cash_evidence = Evidence(
        evidence_id="cash-e", document_id="doc", chunk_id="cash", page=1, text="77,208"
    )
    cash_flow_evidence = Evidence(
        evidence_id="ocf-e", document_id="doc", chunk_id="ocf", page=2, text="(83,918)"
    )
    extraction = FinancialExtractionResult(
        cash_and_cash_equivalents=FinancialMetricValue(
            metric_name="cash_and_cash_equivalents",
            normalized_value=Decimal("77208"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            evidence_id="cash-e",
            document_id="doc",
            chunk_id="cash",
            page=1,
            status=ExtractionStatus.EXTRACTED,
        ),
        operating_cash_flow=FinancialMetricValue(
            metric_name="operating_cash_flow",
            normalized_value=Decimal("-83918"),
            currency="CNY",
            unit="thousand",
            period_end=date(2024, 3, 31),
            period_months=3,
            evidence_id="ocf-e",
            document_id="doc",
            chunk_id="ocf",
            page=2,
            status=ExtractionStatus.EXTRACTED,
        ),
    )
    evidence = {"cash-e": cash_evidence, "ocf-e": cash_flow_evidence}
    built = CashRunwayRiskBuilder().build(extraction, evidence)
    assert built.risk_item is not None
    return built.risk_item, evidence


def test_verifier_returns_stable_pydantic_result() -> None:
    risk, evidence = valid_case()
    result = CashRunwayRiskVerifier().verify(risk, evidence)
    assert isinstance(result, CashRunwayVerificationResult)
    assert result.status == CashRunwayVerificationStatus.VERIFIED
    assert result.verified_risk is not None


def test_verification_result_round_trips_through_json() -> None:
    risk, evidence = valid_case()
    result = CashRunwayRiskVerifier().verify(risk, evidence)
    restored = TypeAdapter(CashRunwayVerificationResult).validate_json(
        result.model_dump_json()
    )
    assert restored == result


def test_verification_collection_defaults_are_not_shared() -> None:
    risk, _ = valid_case()
    first = CashRunwayVerificationResult(
        status=CashRunwayVerificationStatus.NEEDS_REVIEW,
        reviewed_risk=risk,
    )
    second = CashRunwayVerificationResult(
        status=CashRunwayVerificationStatus.NEEDS_REVIEW,
        reviewed_risk=risk,
    )
    first.issues.append("x")
    first.checks["x"] = False
    assert second.issues == []
    assert second.checks == {}
