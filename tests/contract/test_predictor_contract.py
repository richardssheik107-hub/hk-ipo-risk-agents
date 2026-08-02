from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.schemas import RiskCategory, RiskItem, RiskLevel

def test_predictor_returns_bounded_score():
    risk = RiskItem(risk_code="loss", category=RiskCategory.FINANCIAL, risk_type="Loss", level=RiskLevel.HIGH, score=80, conclusion="loss", agent_name="test")
    result = RuleBasedPredictor().predict([risk], None)
    assert result.target == "five_day_significant_decline_risk" and 0 <= result.risk_score <= 100
