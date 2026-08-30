"""Judge-facing presentation copy for the final-day frontend.

This module is presentation-only. It does not alter RiskItem, Evidence,
Market-X, model, verifier, or runtime semantics.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


RISK_REASONING: dict[str, str] = {
    "cash_runway": (
        "现金可支撑期偏短意味着公司对后续经营现金流改善、再融资或外部资金补充更敏感；"
        "一旦融资节奏或经营回款不及预期，流动性压力可能较快显现。"
    ),
    "continuous_loss": (
        "持续亏损会持续消耗资本与现金储备，并提高公司对融资、收入增长和成本控制的依赖；"
        "若亏损趋势延续，财务韧性会进一步下降。"
    ),
    "revenue_growth": (
        "收入增长乏力或波动较大时，通常意味着商业化、客户拓展或需求稳定性仍需验证，"
        "也会削弱公司通过经营增长覆盖成本的能力。"
    ),
    "customer_concentration": (
        "收入对少数核心客户依赖较高时，主要客户的订单变化、议价或流失都可能对收入和"
        "利润造成较大影响，因此需要重点关注客户关系的稳定性。"
    ),
    "supplier_concentration": (
        "采购对少数供应商依赖较高时，关键供应商的价格、产能、交付或合作关系变化可能"
        "影响成本和经营连续性，需要核查替代供应能力。"
    ),
    "redemption_rights": (
        "特殊股东权利、赎回或恢复安排可能影响资本结构、现金安排和其他股东权益；"
        "若相关权利仍存续或触发条件复杂，需要持续关注其终止、恢复和结算机制。"
    ),
    "material_litigation_compliance": (
        "重大诉讼、监管或合规事项可能带来罚款、赔偿、业务限制和声誉影响；"
        "风险判断应以招股书披露的事项、进展与管理层说明为依据。"
    ),
    "precommercial_product": (
        "核心产品尚未商业化意味着收入实现仍依赖研发、审批、量产和市场接受度等后续环节，"
        "商业兑现存在时间和执行不确定性。"
    ),
}

RISK_REVIEW_FOCUS: dict[str, str] = {
    "cash_runway": "复核现金余额、经营现金流、未来十二个月资金需求、融资计划及到期负债。",
    "continuous_loss": "复核亏损成因、毛利率和费用趋势，以及管理层给出的扭亏或资金安排。",
    "revenue_growth": "复核收入变化原因、在手订单、客户拓展和核心业务的持续性。",
    "customer_concentration": "复核主要客户合同期限、续约、议价能力、客户流失风险及新客户拓展。",
    "supplier_concentration": "复核核心供应商合同、替代供应来源、采购议价能力和关键原材料保障。",
    "redemption_rights": "复核赎回权终止/恢复条件、结算安排、上市前后的权利状态及潜在现金影响。",
    "material_litigation_compliance": "复核案件/监管事项进展、潜在责任、整改措施和管理层对财务影响的判断。",
    "precommercial_product": "复核研发/注册进度、商业化里程碑、预计上市时间、渠道和收入转化假设。",
}


def risk_reasoning(risk_code: object) -> str:
    code = str(risk_code or "")
    return RISK_REASONING.get(
        code,
        "该风险项已由系统依据受治理的结构化事实和原文证据形成。"
        "建议结合下方证据、计算依据和复核状态理解其业务含义。",
    )


def risk_review_focus(risk_code: object) -> str:
    code = str(risk_code or "")
    return RISK_REVIEW_FOCUS.get(
        code,
        "复核关键事实、对应招股书原文、事项时点以及可能影响风险判断的后续变化。",
    )


def highest_risk_level(risks: Iterable[Mapping[str, Any]]) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    best = "unavailable"
    best_rank = 0
    for risk in risks:
        level = str(risk.get("level") or "").lower()
        rank = order.get(level, 0)
        if rank > best_rank:
            best = level
            best_rank = rank
    return best


def summarize_risks(risks: Iterable[Mapping[str, Any]]) -> dict[str, int | str]:
    rows = list(risks)
    return {
        "total": len(rows),
        "high_or_critical": sum(
            str(row.get("level") or "").lower() in {"critical", "high"} for row in rows
        ),
        "medium": sum(str(row.get("level") or "").lower() == "medium" for row in rows),
        "verified": sum(
            str(row.get("verification_status") or "").lower() == "verified"
            for row in rows
        ),
        "needs_review": sum(
            str(row.get("verification_status") or "").lower()
            in {"needs_review", "pending"}
            for row in rows
        ),
        "evidence_count": sum(len(row.get("evidence") or []) for row in rows),
        "highest_level": highest_risk_level(rows),
    }
