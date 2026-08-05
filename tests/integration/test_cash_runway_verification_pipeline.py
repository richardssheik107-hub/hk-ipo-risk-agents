from datetime import date
from decimal import Decimal

from ipo_risk.agents.rules import RuleVerifier
from ipo_risk.domain.cash_runway import CashRunwayRiskBuilder
from ipo_risk.extraction import ExtractionStatus, FinancialExtractionResult, FinancialMetricValue
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.schemas import Evidence, RiskLevel, VerificationStatus


def test_builder_verifier_predictor_pipeline_scores_only_verified_cash_runway() -> None:
    cash_evidence = Evidence(
        evidence_id="cash-e",
        document_id="doc",
        chunk_id="cash",
        page=10,
        text="Cash at period end: 77 208",
    )
    cash_flow_evidence = Evidence(
        evidence_id="ocf-e",
        document_id="doc",
        chunk_id="ocf",
        page=11,
        text="Operating cash flow: （83,918）",
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
            page=10,
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
            page=11,
            status=ExtractionStatus.EXTRACTED,
        ),
    )
    evidence = {"cash-e": cash_evidence, "ocf-e": cash_flow_evidence}
    built = CashRunwayRiskBuilder().build(extraction, evidence)
    assert built.risk_item is not None

    verification = RuleVerifier().verify(
        [built.risk_item], {"cash_runway": list(evidence.values())}
    )
    assert len(verification.verified_risks) == 1
    assert verification.pending_risks == []
    verified = verification.verified_risks[0]
    assert verified.verification_status == VerificationStatus.VERIFIED

    prediction = RuleBasedPredictor().predict(
        verification.verified_risks + verification.pending_risks, None
    )
    assert prediction.risk_score == 90
    assert prediction.risk_level == RiskLevel.CRITICAL
    assert prediction.probabilities == {}
    assert prediction.metadata["used_verified_risk_ids"] == [verified.risk_id]
    assert prediction.metadata["score_is_probability"] is False
