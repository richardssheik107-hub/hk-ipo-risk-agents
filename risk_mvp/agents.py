"""可替换的规则型 Agent；正式版可逐个替换为检索、模型或人工复核。"""

from .contracts import Evidence


def financial_agent(case: dict) -> tuple[float, list[Evidence]]:
    score = 0.0
    evidence = []
    if case["cash_runway_months"] < 12:
        score += 35
        evidence.append(_e(case, "FIN-01", 102, "现金可支撑期不足12个月", "财务", 5, 0.95, "财务穿透"))
    if case["top_customer_ratio"] > 0.4:
        score += 20
        evidence.append(_e(case, "FIN-02", 156, "前五大客户集中度偏高", "财务", 4, 0.90, "财务穿透"))
    if case["revenue_growth"] < 0:
        score += 15
        evidence.append(_e(case, "FIN-03", 98, "收入同比下滑", "财务", 3, 0.88, "财务穿透"))
    return min(score, 100), evidence


def governance_agent(case: dict) -> tuple[float, list[Evidence]]:
    score = 0.0
    evidence = []
    if case["related_party_ratio"] > 0.15:
        score += 30
        evidence.append(_e(case, "GOV-01", 189, "关联交易占比超过15%", "治理", 4, 0.90, "法务合规"))
    if case["has_redemption_right"]:
        score += 25
        evidence.append(_e(case, "GOV-02", 211, "存在优先股赎回或对赌安排", "治理", 4, 0.92, "法务合规"))
    if case["litigation_count"] > 0:
        score += min(case["litigation_count"] * 10, 30)
        evidence.append(_e(case, "GOV-03", 225, "披露未决诉讼或监管事项", "治理", 3, 0.82, "法务合规"))
    return min(score, 100), evidence


def market_agent(case: dict) -> tuple[float, list[Evidence]]:
    score = 0.0
    evidence = []
    if case["market_volatility"] > 0.25:
        score += 25
        evidence.append(_e(case, "MKT-01", 1, "发行窗口市场波动偏高", "市场", 4, 0.85, "市场量化"))
    if case["subscription_multiple"] < 1.2:
        score += 30
        evidence.append(_e(case, "MKT-02", 1, "模拟认购倍数偏低", "市场", 5, 0.80, "市场量化"))
    if case["sector_return_20d"] < -0.08:
        score += 20
        evidence.append(_e(case, "MKT-03", 1, "所属板块近20日表现较弱", "市场", 3, 0.90, "市场量化"))
    return min(score, 100), evidence


def _e(case: dict, suffix: str, page: int, claim: str, risk_type: str, severity: int, confidence: float, owner: str) -> Evidence:
    return Evidence(f"{case['company_id']}-{suffix}", "模拟招股书/模拟市场数据", page, claim, risk_type, severity, confidence, owner)
