"""前端展示文案与简体中文本地化辅助。

本模块只负责展示，不修改 RiskItem、Evidence、Market-X、模型、Verifier 或运行语义。
招股书原文证据保持原样；除此之外，界面使用简体中文和必要的专有名词。
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

_STATUS_LABELS = {
    "available": "可用", "partial": "部分可用", "pending_gate": "待完善",
    "completed": "已完成", "completed_with_real_llm": "已完成",
    "completed_with_partial_llm": "部分完成",
    "completed_with_deterministic_fallback": "已安全降级",
    "degraded": "已降级", "verified": "已验证", "needs_review": "待复核",
    "pending": "待处理", "rejected": "已驳回", "failed": "未完成",
    "error": "异常", "disabled": "未启用", "unavailable": "暂不可用",
    "unavailable_error": "暂不可用", "no_risk_emitted": "未识别到正式风险",
    "resolved": "已解决", "partial_resolved": "部分解决", "unresolved": "待复核",
}

# 仅用于非证据展示字段。原文 Evidence 不得经过此转换。
_TRAD_TO_SIMP = str.maketrans({
    "風": "风", "險": "险", "證": "证", "據": "据", "結": "结", "構": "构",
    "財": "财", "務": "务", "業": "业", "發": "发", "佈": "布", "現": "现",
    "關": "关", "聯": "联", "審": "审", "閱": "阅", "錄": "录", "報": "报",
    "價": "价", "規": "规", "則": "则", "數": "数", "類": "类", "別": "别",
    "項": "项", "狀": "状", "態": "态", "處": "处", "應": "应", "對": "对",
    "與": "与", "為": "为", "時": "时", "間": "间", "點": "点", "從": "从",
    "來": "来", "這": "这", "個": "个", "體": "体", "說": "说", "進": "进",
    "過": "过", "還": "还", "會": "会", "將": "将", "開": "开", "啟": "启",
    "終": "终", "續": "续", "測": "测", "試": "试", "驗": "验", "線": "线",
    "網": "网", "頁": "页", "號": "号", "碼": "码", "權": "权", "義": "义",
    "協": "协", "議": "议", "專": "专", "簡": "简", "稱": "称", "產": "产",
    "資": "资", "負": "负", "責": "责", "帳": "账", "戶": "户", "餘": "余",
    "額": "额", "營": "营", "運": "运", "經": "经", "動": "动", "損": "损",
    "虧": "亏", "潤": "润", "長": "长", "該": "该", "讀": "读", "寫": "写",
    "層": "层", "級": "级", "復": "复", "識": "识", "選": "选", "擇": "择",
    "顯": "显", "擊": "击", "導": "导", "覽": "览", "區": "区", "塊": "块",
    "連": "连", "變": "变", "廣": "广", "東": "东", "華": "华", "國": "国",
    "際": "际", "萬": "万", "龍": "龙", "醫": "医", "藥": "药", "電": "电",
    "氣": "气", "機": "机", "實": "实", "貿": "贸", "鏈": "链", "購": "购",
    "買": "买", "銷": "销", "準": "准", "確": "确", "認": "认", "預": "预",
    "輸": "输", "無": "无", "僅": "仅", "並": "并", "異": "异", "較": "较",
    "優": "优", "劣": "劣", "總": "总", "獨": "独", "嚴": "严", "謹": "谨",
    "邊": "边", "凍": "冻", "曆": "历", "當": "当", "後": "后", "衝": "冲",
    "歸": "归", "灣": "湾", "臺": "台", "啲": "些", "冊": "册", "圖": "图",
})


def to_simplified_ui(value: object) -> str:
    """将非证据展示值转换为简体字形。"""

    return str(value or "").translate(_TRAD_TO_SIMP)


def judge_status_label(value: object) -> str:
    return _STATUS_LABELS.get(str(value or "unavailable").lower(), "暂不可用")


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


def risk_conclusion_zh(risk: Mapping[str, Any]) -> str:
    """根据结构化字段生成中文结论，不复述后端英文正文。"""

    code = str(risk.get("risk_code") or "")
    metadata = risk.get("metadata") or {}
    if not isinstance(metadata, Mapping):
        metadata = {}
    if code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        values = []
        if metadata.get("largest_counterparty_pct") not in (None, ""):
            values.append(f"最大{subject}占比约 {metadata['largest_counterparty_pct']}%")
        if metadata.get("top_five_pct") not in (None, ""):
            values.append(f"前五大{subject}合计占比约 {metadata['top_five_pct']}%")
        return ("，".join(values) + "，系统据此识别到集中度风险。") if values else f"系统识别到{subject}集中度风险，建议结合原文证据核查集中程度及持续性。"
    if code == "continuous_loss":
        count = metadata.get("latest_loss_period_count")
        return f"最新可比报告序列中存在连续 {count} 个亏损期，系统据此识别到持续亏损风险。" if count not in (None, "") else "系统识别到持续亏损风险，建议结合可比报告期和原文证据核查亏损持续性。"
    if code == "revenue_growth":
        growth = metadata.get("growth_pct_rounded") or metadata.get("growth_pct_exact")
        return f"最新两个可比报告期的收入变动约为 {growth}%，系统据此识别到收入增长风险。" if growth not in (None, "") else "系统识别到收入增长或收入下滑风险，建议结合可比报告期核查变化原因。"
    if code == "cash_runway":
        months = next((metadata.get(key) for key in ("runway_months", "cash_runway_months", "months_of_runway") if metadata.get(key) not in (None, "")), None)
        return f"按当前可核验数据估算，现金可支撑期约为 {months} 个月，需要关注流动性安排。" if months is not None else "系统识别到现金可支撑期风险，需要结合现金余额、经营现金流和融资计划进一步复核。"
    if code == "redemption_rights":
        return "招股书披露了需要关注的特殊股东权利或赎回安排，建议核查其终止、恢复及潜在资金影响。"
    if code == "material_litigation_compliance":
        return "招股书披露了需要关注的诉讼、监管或合规事项，建议结合事项进展和潜在责任进一步复核。"
    if code == "precommercial_product":
        return "核心产品仍处于商业化前阶段，收入兑现依赖后续研发、审批、量产和市场接受度。"
    return "系统已形成该风险项，建议结合下方原文证据和复核状态进行判断。"


def verifier_note_zh(note: object) -> str:
    text = str(note or "").strip().lower()
    if not text:
        return ""
    if "calculation" in text and "missing" in text:
        return "当前缺少可核验的计算依据，因此该风险仍需进一步复核。"
    if "period/value reconciliation" in text or "period value reconciliation" in text:
        return "当前证据中的报告期与数值仍需进一步对齐，完成后才能进入最终验证。"
    if "evidence" in text and "missing" in text:
        return "当前缺少足够的原文证据支撑，因此该风险仍需进一步复核。"
    if "not found" in text:
        return "当前未找到完成验证所需的关键依据。"
    return "当前风险尚未完成最终验证，建议结合原文证据与计算依据进一步复核。"


def calculation_summary_zh(risk: Mapping[str, Any]) -> str:
    calculation = risk.get("calculation")
    if not isinstance(calculation, Mapping):
        return "暂无可展示的确定性计算依据。"
    result, unit = calculation.get("result"), calculation.get("unit")
    if result not in (None, ""):
        suffix = {"percent": "%", "periods": "个报告期", "months": "个月"}.get(str(unit or ""), "")
        return f"系统已完成确定性计算，结果为 {result}{suffix}。"
    return "系统已完成确定性计算，详细输入和公式可在技术审计区查看。"


def supervisor_summary_zh(payload: Mapping[str, Any]) -> str:
    summary = summarize_risks(
        risk
        for domain in (payload.get("domains") or {}).values()
        if isinstance(domain, Mapping)
        for risk in (domain.get("risks") or [])
        if isinstance(risk, Mapping)
    )
    parts = [f"本次共识别 {summary['total']} 项正式风险"]
    if summary["high_or_critical"]:
        parts.append(f"其中 {summary['high_or_critical']} 项为高或极高风险")
    if summary["needs_review"]:
        parts.append(f"{summary['needs_review']} 项仍需进一步复核")
    if summary["evidence_count"]:
        parts.append(f"已绑定 {summary['evidence_count']} 条原文证据")
    return "，".join(parts) + "。建议优先查看高风险事项及其原文依据。"
