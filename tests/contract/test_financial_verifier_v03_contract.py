from inspect import signature

from pydantic import TypeAdapter

from ipo_risk.agents.base import RiskVerifier
from ipo_risk.agents.financial_verifier import V03FinancialVerifier
from ipo_risk.schemas import (
    Calculation,
    Evidence,
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationResult,
    VerificationStatus,
)


def valid_continuous_loss() -> RiskItem:
    first = Evidence(
        evidence_id="loss-1",
        document_id="doc",
        chunk_id="chunk-1",
        page=1,
        text="Loss for the year (100)",
    )
    second = Evidence(
        evidence_id="loss-2",
        document_id="doc",
        chunk_id="chunk-2",
        page=2,
        text="Loss for the year (200)",
    )
    observations = [
        {
            "period_end": "2022-12-31",
            "period_months": 12,
            "net_result": "-100",
            "currency": "CNY",
            "source_unit": "thousand",
            "evidence_ids": ["loss-1"],
        },
        {
            "period_end": "2023-12-31",
            "period_months": 12,
            "net_result": "-200",
            "currency": "CNY",
            "source_unit": "thousand",
            "evidence_ids": ["loss-2"],
        },
    ]
    return RiskItem(
        risk_id="stable-risk-id",
        risk_code="continuous_loss",
        category=RiskCategory.FINANCIAL,
        risk_type="Continuous losses",
        level=RiskLevel.MEDIUM,
        score=60,
        conclusion="The latest sequence contains 2 consecutive loss periods.",
        evidence=[first, second],
        calculation=Calculation(
            skill_name="continuous_loss",
            skill_version="1.0",
            inputs={"observations": observations},
            formula="count latest consecutive comparable net_result values below zero",
            result=2,
            unit="periods",
            evidence_ids=["loss-1", "loss-2"],
        ),
        agent_name="financial",
        metadata={
            "rule_version": "v03_contract_v1",
            "score_is_rule_based": True,
            "score_is_probability": False,
            "latest_loss_period_count": 2,
            "period_months": 12,
            "periods": ["2022-12-31", "2023-12-31"],
        },
    )


def test_v03_financial_verifier_matches_frozen_risk_verifier_signature() -> None:
    assert V03FinancialVerifier.name == "verifier"
    assert list(signature(RiskVerifier.verify).parameters) == [
        "self",
        "risks",
        "evidence_by_code",
    ]
    assert list(signature(V03FinancialVerifier.verify).parameters) == [
        "self",
        "risks",
        "evidence_by_code",
    ]


def test_v03_financial_verifier_returns_public_verification_result() -> None:
    risk = valid_continuous_loss()
    result = V03FinancialVerifier().verify([risk], {})
    assert isinstance(result, VerificationResult)
    assert set(VerificationResult.model_fields) == {
        "verified_risks",
        "pending_risks",
        "rejected_risks",
    }
    assert result.verified_risks[0].risk_id == risk.risk_id


def test_verification_result_round_trips_without_new_public_model() -> None:
    result = V03FinancialVerifier().verify([valid_continuous_loss()], {})
    restored = TypeAdapter(VerificationResult).validate_json(result.model_dump_json())
    assert restored == result


def test_non_financial_input_remains_unverified_and_appears_once() -> None:
    risk = valid_continuous_loss().model_copy(
        update={
            "risk_code": "redemption_rights",
            "category": RiskCategory.LEGAL,
            "agent_name": "legal",
        }
    )
    result = V03FinancialVerifier().verify([risk], {})
    assert result.verified_risks == []
    assert result.rejected_risks == []
    assert [item.risk_id for item in result.pending_risks] == [risk.risk_id]
    assert result.pending_risks[0].verification_status == VerificationStatus.PENDING
