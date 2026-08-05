import pytest

from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.schemas import (
    RiskCategory,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


def risk(status: VerificationStatus, *, score: float = 90, code: str = "cash_runway") -> RiskItem:
    return RiskItem(
        risk_id=f"{status.value}-{code}",
        risk_code=code,
        category=RiskCategory.FINANCIAL,
        risk_type=code,
        level=RiskLevel.CRITICAL,
        score=score,
        conclusion="Deterministic verified risk",
        agent_name="financial",
        verification_status=status,
    )


def test_verified_cash_runway_is_the_only_scored_risk() -> None:
    verified = risk(VerificationStatus.VERIFIED)
    pending = risk(VerificationStatus.PENDING, score=10, code="pending")
    prediction = RuleBasedPredictor().predict([verified, pending], None)
    assert prediction.risk_score == 90
    assert prediction.risk_level == RiskLevel.CRITICAL
    assert [factor.feature_name for factor in prediction.top_factors] == ["cash_runway"]
    assert prediction.metadata["used_verified_risk_ids"] == [verified.risk_id]
    assert prediction.metadata["excluded_pending_risk_ids"] == [pending.risk_id]


@pytest.mark.parametrize(
    "status",
    [
        VerificationStatus.PENDING,
        VerificationStatus.NEEDS_REVIEW,
        VerificationStatus.REJECTED,
    ],
)
def test_untrusted_status_never_affects_score(status: VerificationStatus) -> None:
    excluded = risk(status, score=100)
    prediction = RuleBasedPredictor().predict([excluded], None)
    assert prediction.risk_score == 0
    assert prediction.risk_level == RiskLevel.LOW
    assert prediction.top_factors == []
    assert excluded.risk_id not in prediction.metadata["used_verified_risk_ids"]


def test_prediction_is_explicitly_non_probability_rule_v2() -> None:
    prediction = RuleBasedPredictor().predict([risk(VerificationStatus.VERIFIED)], None)
    assert prediction.model_name == "RuleBasedPredictor"
    assert prediction.model_version == "rule_v2"
    assert prediction.target == "five_day_significant_decline_risk"
    assert prediction.probabilities == {}
    assert prediction.metadata["scoring_mode"] == "deterministic_rule"
    assert prediction.metadata["score_is_probability"] is False
    assert "not a calibrated probability" in prediction.explanation


def test_verified_risk_without_market_is_degraded_but_keeps_score() -> None:
    prediction = RuleBasedPredictor().predict(
        [risk(VerificationStatus.VERIFIED)], None
    )
    assert prediction.risk_score == 90
    assert prediction.risk_level == RiskLevel.CRITICAL
    assert prediction.metadata["degraded_mode"] is True
    assert prediction.metadata["degradation_reasons"] == [
        "market_sentiment_score_missing"
    ]


def test_no_trusted_feature_enters_degraded_mode() -> None:
    prediction = RuleBasedPredictor().predict([], None)
    assert prediction.risk_score == 0
    assert prediction.risk_level == RiskLevel.LOW
    assert prediction.metadata["degraded_mode"] is True
    assert set(prediction.metadata["missing_features"]) == {
        "verified_risks",
        "market_sentiment_score",
    }


def test_predictor_does_not_mutate_inputs_and_is_deterministic() -> None:
    item = risk(VerificationStatus.VERIFIED)
    before = item.model_dump()
    predictor = RuleBasedPredictor()
    first = predictor.predict([item], None)
    second = predictor.predict([item], None)
    assert first.model_dump(exclude={"created_at"}) == second.model_dump(
        exclude={"created_at"}
    )
    assert item.model_dump() == before
