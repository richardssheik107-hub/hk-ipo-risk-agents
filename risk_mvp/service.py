"""总控决策层：融合三类风险，并输出可追溯的最小报告。"""

from .agents import financial_agent, governance_agent, market_agent
from .contracts import RiskReport


def evaluate(case: dict) -> RiskReport:
    financial, fin_evidence = financial_agent(case)
    governance, gov_evidence = governance_agent(case)
    market, market_evidence = market_agent(case)
    # 可替换接口：后期由 4 号接入时间序列模型或校准模型。
    probability = round(min(0.95, 0.05 + 0.40 * financial / 100 + 0.25 * governance / 100 + 0.35 * market / 100), 3)
    level = "高" if probability >= 0.60 else "中" if probability >= 0.35 else "低"
    evidence = fin_evidence + gov_evidence + market_evidence
    return RiskReport(
        company_id=case["company_id"],
        company_name=case["company_name"],
        as_of_date=case["as_of_date"],
        fundamental_score=financial,
        governance_score=governance,
        market_score=market,
        risk_probability_5d=probability,
        risk_level=level,
        review_required=level == "高" or any(item.confidence < 0.85 for item in evidence),
        evidence=evidence,
        assumptions=["全部输入均为模拟数据", "风险概率仅用于演示，不构成投资建议", "所有证据页码均为模拟定位"],
    )
