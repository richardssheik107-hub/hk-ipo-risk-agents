from ipo_risk.schemas import RiskCategory, RiskItem, RiskLevel
from ipo_risk.workflows.state import append, reduce_risks

def test_reducers_append_logs_and_deduplicate_risks():
    risk = RiskItem(risk_code="loss", category=RiskCategory.FINANCIAL, risk_type="Loss", level=RiskLevel.HIGH, score=80, conclusion="x", agent_name="a")
    updated = risk.model_copy(update={"score": 82})
    assert append([1], [2]) == [1, 2]
    assert reduce_risks([risk], [updated]) == [updated]
