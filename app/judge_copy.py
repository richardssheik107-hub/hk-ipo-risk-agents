"""前端展示文案与简体中文本地化辅助。

本模块只负责展示，不修改 RiskItem、Evidence、Market-X、模型、Verifier 或运行语义。
招股书原文证据保持原样；除此之外，界面使用简体中文和必要的专有名词。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
import re
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

RISK_DISPLAY_NAMES: dict[str, str] = {
    "cash_runway": "现金可支撑期",
    "continuous_loss": "持续亏损",
    "revenue_growth": "收入增长",
    "customer_concentration": "客户集中度",
    "supplier_concentration": "供应商集中度",
    "redemption_rights": "特殊股东权利与赎回安排",
    "material_litigation_compliance": "重大诉讼与合规",
    "precommercial_product": "产品尚未商业化",
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

_RISK_LEVEL_LABELS = {
    "critical": "极高",
    "high": "高",
    "medium": "中",
    "low": "低",
    "unavailable": "暂不可用",
}

_VERIFICATION_ISSUE_LABELS = {
    "calculation_missing": "缺少可复算的确定性计算",
    "value_period_count_mismatch": "报告期与数值数量未能一一对应",
    "incomplete_concentration_values": "集中度数值提取不完整",
    "conflicting_values_for_same_period": "同一报告期出现相互冲突的候选数值",
    "holder_not_supported_by_evidence": "权利主体的精确名称或适用范围仍需逐句核对",
    "actual_matter_not_established": "该披露是否满足本风险类型的认定条件尚未完成验证",
    "closure_status_not_established": "事项是否已经结束尚未确认",
    "pending_status_not_supported_by_evidence": "持续或待处理状态尚未被当前证据支持",
    "manual_legal_judgment_required": "仍需要法律专业判断",
    "counterparty_or_regulator_not_identified": "相对方或主管机构尚未明确",
    "management_materiality_not_established": "管理层关于重大性的判断尚未完成交叉核验",
    "remediation_metadata_not_supported_by_evidence": "整改状态尚未被当前证据充分支持",
    "material_impact_not_supported_by_evidence": "重大影响判断尚未被当前证据充分支持",
    "period_value_reconciliation_required": "报告期与数值仍需重新对齐",
    "evidence_missing": "缺少完成核验所需的原文证据",
}

_CURRENCY_LABELS = {
    "CNY": "人民币",
    "HKD": "港元",
    "USD": "美元",
}

_UNIT_LABELS = {
    "thousand": "千元",
    "million": "百万元",
    "months": "个月",
    "percent": "%",
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
    "於": "于", "補": "补", "繳": "缴", "納": "纳", "僱": "雇", "罰": "罚",
    "監": "监", "請": "请", "緊": "紧", "適": "适", "決": "决", "絕": "绝",
    "攤": "摊", "績": "绩", "記": "记", "樓": "楼", "顧": "顾", "門": "门",
    "給": "给", "屬": "属", "幣": "币", "約": "约", "億": "亿", "條": "条",
    "滿": "满", "屆": "届", "觸": "触", "勞": "劳", "員": "员", "徑": "径",
    "許": "许", "須": "须", "轉": "转", "讓": "让", "達": "达", "聨": "联",
    "聞": "闻", "創": "创",
    "積": "积", "獲": "获", "償": "偿", "眾": "众", "歷": "历", "廠": "厂",
    "佔": "占", "況": "况", "視": "视", "護": "护", "訂": "订", "維": "维",
    "減": "减", "擔": "担", "繼": "继", "載": "载", "範": "范", "遷": "迁",
    "遞": "递", "計": "计", "內": "内", "猶": "犹", "滯": "滞", "強": "强",
    "執": "执", "響": "响", "訴": "诉", "暫": "暂", "問": "问", "穫": "获",
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


def _risk_metadata(risk: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = risk.get("metadata") or {}
    return metadata if isinstance(metadata, Mapping) else {}


def _compact_ui_fact(value: object, *, limit: int = 320) -> str:
    """Normalize an already-produced structured fact for reader copy.

    Evidence quotes never pass through this helper.  It is only used for LLM or
    deterministic structured fields that the workflow has already emitted.
    """

    text = (
        to_simplified_ui(value)
        .replace(";", "；")
        .replace(",", "，")
        .replace(":", "：")
        .replace("(", "（")
        .replace(")", "）")
        .strip()
    )
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*([，；。：])\s*", r"\1", text)
    text = re.sub(r"\s*（\s*", "（", text)
    text = re.sub(r"\s*）\s*", "）", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip("，；。") + "…"


def _decimal_text(value: object, *, places: int = 2, grouping: bool = False) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value or "")
    quantizer = Decimal(1).scaleb(-places)
    rounded = number.quantize(quantizer)
    rendered = format(rounded, ",f" if grouping else "f")
    return rendered.rstrip("0").rstrip(".") or "0"


def _evidence_pages(risk: Mapping[str, Any]) -> list[str]:
    pages: list[str] = []
    for item in risk.get("evidence") or []:
        if not isinstance(item, Mapping) or item.get("page") in (None, ""):
            continue
        page = str(item.get("page"))
        if page not in pages:
            pages.append(page)
    return sorted(
        pages,
        key=lambda page: (0, int(page)) if page.isdigit() else (1, page),
    )


def _page_basis(risk: Mapping[str, Any]) -> str:
    pages = _evidence_pages(risk)
    evidence_count = len(risk.get("evidence") or [])
    if not evidence_count:
        return "当前风险项没有附着可展示的招股书原文。"
    if len(pages) == 1:
        return f"本项关联 1 条招股书原文，位于第 {pages[0]} 页。"
    shown = "、".join(pages[:5])
    suffix = "等" if len(pages) > 5 else ""
    return f"本项关联 {evidence_count} 条招股书原文，分布在第 {shown} 页{suffix}。"


def _verification_issue_codes(risk: Mapping[str, Any]) -> list[str]:
    metadata = _risk_metadata(risk)
    codes: list[str] = []
    for key in (
        "extraction_issues",
        "fact_issues",
        "observation_issues",
        "builder_issues",
        "legal_verifier_issues",
        "verification_issues",
    ):
        values = metadata.get(key) or []
        if isinstance(values, str):
            values = [values]
        for value in values:
            code = str(value or "").strip()
            if code and code not in codes:
                codes.append(code)

    note = str(risk.get("verification_notes") or "").lower()
    if "calculation" in note and "missing" in note and "calculation_missing" not in codes:
        codes.append("calculation_missing")
    if "period/value reconciliation" in note and "period_value_reconciliation_required" not in codes:
        codes.append("period_value_reconciliation_required")
    if "evidence" in note and "missing" in note and "evidence_missing" not in codes:
        codes.append("evidence_missing")
    return codes


def _verification_issues_zh(risk: Mapping[str, Any], *, limit: int = 4) -> list[str]:
    labels: list[str] = []
    for code in _verification_issue_codes(risk):
        label = _VERIFICATION_ISSUE_LABELS.get(code)
        if label and label not in labels:
            labels.append(label)
        if len(labels) >= limit:
            break
    return labels


def _calculation_conclusion(risk: Mapping[str, Any]) -> str | None:
    calculation = risk.get("calculation")
    if not _calculation_is_safe(risk):
        return None
    assert isinstance(calculation, Mapping)
    code = str(risk.get("risk_code") or "")
    result = _decimal_text(calculation.get("result"), places=2)
    unit = _UNIT_LABELS.get(str(calculation.get("unit") or ""), str(calculation.get("unit") or ""))
    inputs = calculation.get("inputs") or {}
    if code == "cash_runway" and isinstance(inputs, Mapping):
        cash = _decimal_text(inputs.get("cash"), places=0, grouping=True)
        try:
            outflow_value: object = abs(Decimal(str(inputs.get("operating_cash_flow"))))
        except (InvalidOperation, TypeError, ValueError):
            outflow_value = ""
        outflow = _decimal_text(outflow_value, places=0, grouping=True) if outflow_value != "" else ""
        period = _decimal_text(inputs.get("period_months"), places=0)
        currency = _CURRENCY_LABELS.get(str(inputs.get("currency") or ""), str(inputs.get("currency") or ""))
        source_unit = _UNIT_LABELS.get(str(inputs.get("source_unit") or ""), str(inputs.get("source_unit") or ""))
        if cash and outflow and period:
            return (
                f"财务报表记录现金及现金等价物{currency} {cash} {source_unit}，{period} 个月经营活动净流出"
                f"{currency} {outflow} {source_unit}；按“现金 ÷ 月均经营净流出”复算，现金可支撑期约为 "
                f"{result} {unit}。该结论来自确定性计算，不是风险发生概率。"
            )
    return f"系统已按已记录的公式完成确定性复算，结果为 {result}{unit}；该结果不是概率。"


def _calculation_is_safe(risk: Mapping[str, Any]) -> bool:
    """Only expose a numeric calculation when its governed links are intact."""

    calculation = risk.get("calculation")
    if not isinstance(calculation, Mapping):
        return False
    if calculation.get("success") is not True or calculation.get("result") in (None, ""):
        return False
    calculation_ids = {
        str(item) for item in (calculation.get("evidence_ids") or []) if str(item)
    }
    risk_ids = {
        str(item.get("evidence_id"))
        for item in (risk.get("evidence") or [])
        if isinstance(item, Mapping) and item.get("evidence_id")
    }
    return bool(calculation_ids) and calculation_ids <= risk_ids


def risk_conclusion_zh(risk: Mapping[str, Any]) -> str:
    """把受治理的结构化事实投影为有内容的中文结论。

    这里不调用模型，也不把待复核字段写成已证实事实。页面刷新时只读取分析
    阶段已经生成并经过现有 Verifier/范围约束的字段。
    """

    code = str(risk.get("risk_code") or "")
    verification = str(risk.get("verification_status") or "unavailable").lower()
    metadata = _risk_metadata(risk)
    calculated = _calculation_conclusion(risk) if verification == "verified" else None
    if calculated:
        return calculated
    if code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        values = []
        if verification == "verified" and metadata.get("largest_counterparty_pct") not in (None, ""):
            values.append(f"最大{subject}占比约 {metadata['largest_counterparty_pct']}%")
        if verification == "verified" and metadata.get("top_five_pct") not in (None, ""):
            values.append(f"前五大{subject}合计占比约 {metadata['top_five_pct']}%")
        if values:
            return (
                "，".join(values)
                + f"。这些结构化数值提示{subject}依赖值得关注，但仍需结合报告期口径和验证状态阅读。"
            )
        issues = _verification_issues_zh(risk)
        issue_copy = "；".join(issues)
        pages = _evidence_pages(risk)
        location = f"系统已在招股书第 {'、'.join(pages[:5])} 页定位相关披露" if pages else "系统已形成相关披露候选"
        if issue_copy:
            return (
                f"{location}，内容涉及往绩记录期的{subject}构成、集中度或交易关系。"
                f"由于{issue_copy}，本次尚未完成口径一致的集中度复算，"
                "因此只能保留为待复核线索，不能据此判断集中程度或风险等级。"
            )
        return f"{location}；当前尚需把{subject}占比与对应报告期逐项对齐后，才能判断集中程度。"
    if code == "continuous_loss":
        count = metadata.get("latest_loss_period_count")
        return f"最新可比报告序列中已核验连续 {count} 个亏损期；该判断仍需结合各期损益和现金流理解经营压力。" if verification == "verified" and count not in (None, "") else "当前原文候选显示发行人可能存在持续亏损，但报告期与数值尚未形成可复核的连续序列，因此不能把候选直接写成已确认事实。"
    if code == "revenue_growth":
        growth = metadata.get("growth_pct_rounded") or metadata.get("growth_pct_exact")
        return f"最新两个可比报告期的收入变动已核验为约 {growth}%；该变化需结合收入基数、业务构成和报告期口径解释。" if verification == "verified" and growth not in (None, "") else "当前原文候选包含收入增长或下滑信号，但尚未形成口径一致的可比序列，现阶段只能作为待核对事项。"
    if code == "cash_runway":
        months = next((metadata.get(key) for key in ("runway_months", "cash_runway_months", "months_of_runway") if metadata.get(key) not in (None, "")), None)
        return f"按当前可核验数据估算，现金可支撑期约为 {months} 个月；仍需结合最新现金余额、经营现金流和融资安排持续观察。" if verification == "verified" and months is not None else "当前资料提示现金消耗压力，但缺少完成现金可支撑期复算所需的完整输入，暂不能形成确定性结论。"
    if code == "redemption_rights":
        holder = _compact_ui_fact(metadata.get("holder"), limit=90).rstrip("。；")
        termination = _compact_ui_fact(metadata.get("termination_event"), limit=220).rstrip("。；")
        restoration = _compact_ui_fact(metadata.get("restoration_condition"), limit=260).rstrip("。；")
        parts = []
        if holder:
            parts.append(f"招股书条款将相关权利人记为{holder}")
        if termination:
            parts.append(f"终止安排为：{termination}")
        if metadata.get("restoration_clause") is True and restoration:
            parts.append(f"同时存在恢复条件：{restoration}")
        if parts:
            return "；".join(parts) + "。如果相关权利按披露在上市后终止且未触发恢复条件，对上市后公众股东的直接影响应较为有限；但权利主体范围、终止时点和恢复条件仍需逐句核对。"
        return "招股书条款候选涉及特殊股东权利的终止或恢复安排；当前需要核对权利主体、触发条件和上市后的存续状态。"
    if code == "material_litigation_compliance":
        subject = _compact_ui_fact(metadata.get("subject"), limit=300)
        management = _compact_ui_fact(metadata.get("management_materiality"), limit=220)
        impact = _compact_ui_fact(metadata.get("potential_impact"), limit=240)
        parts = []
        if subject:
            parts.append(f"招股书披露：{subject}")
        if impact:
            parts.append(f"系统整理的潜在责任或缓释说明包括：{impact}")
        if management:
            parts.append(f"招股书同时记录管理层或法律顾问观点：{management}")
        if parts:
            return "；".join(parts) + "。这些披露能够说明事项及相关缓释观点，但事项是否持续、整改是否完成和重大性仍待复核。"
        return "当前原文候选涉及诉讼、监管或合规事项，但事项身份、进展和潜在责任尚未形成可验证的完整链条。"
    if code == "precommercial_product":
        product = _compact_ui_fact(metadata.get("product_name") or metadata.get("subject"), limit=120)
        fact_kind = "结构化事实" if verification == "verified" else "结构化候选"
        prefix = f"{fact_kind}显示{product}" if product else f"{fact_kind}显示核心产品"
        return prefix + "仍处于商业化前阶段，收入兑现取决于研发、审批、量产和市场接受度等后续里程碑。"

    pages = _evidence_pages(risk)
    if pages:
        return f"系统已在招股书第 {'、'.join(pages[:5])} 页定位与该事项相关的原文；当前结论应以这些原文和验证状态为边界。"
    return "该风险项尚未形成足够的可读结构化事实，当前不补写推测性结论。"


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


def risk_reasoning_annotation(risk: Mapping[str, Any]) -> dict[str, str]:
    """将既有风险字段投影为可审阅的“依据—影响—复核”解释。

    该函数不生成新风险，也不展示内部思维过程；它只说明已经产出的风险项
    为什么值得关注、当前验证到了哪一步，以及评审下一步应核对什么。
    """

    code = str(risk.get("risk_code") or "")
    verification = str(risk.get("verification_status") or "unavailable").lower()
    metadata = _risk_metadata(risk)
    page_copy = _page_basis(risk)
    calculation = risk.get("calculation")
    calculation_safe = _calculation_is_safe(risk)
    extraction_method = str(metadata.get("extraction_method") or "")
    if calculation_safe and verification == "verified":
        basis = page_copy + "相关财务输入已经过确定性公式复算，计算引用均能回到本风险项的原文证据，本项也已通过验证。"
    elif isinstance(calculation, Mapping):
        basis = page_copy + "上游已形成计算候选，但计算状态、证据关联或风险验证尚未全部满足，因此页面不把候选数值写成确定性结论。"
    elif extraction_method.startswith("llm_structured"):
        basis = page_copy + "系统先从原文整理候选事实，再检查各字段能否被同一组证据支持。"
    else:
        basis = page_copy + "结论只使用本次运行已经产出的结构化字段和验证状态，不根据页面展示补写新事实。"

    if verification == "verified":
        basis += "本项已通过当前验证规则。"
    elif verification in {"needs_review", "pending"}:
        basis += "本项尚未通过全部验证条件，因此保留为待复核，而不是已确认事实。"
    elif verification == "rejected":
        basis += "该候选未通过验证，不纳入面向评审的风险结论。"
    else:
        basis += "当前验证状态尚未完整形成。"

    if verification == "verified":
        boundary = (
            "已验证仅表示该风险在本次运行中获得了当前证据和规则的支持，"
            "不代表风险必然发生；仍需关注招股书之后的事项变化。"
        )
    elif verification in {"needs_review", "pending"}:
        issues = _verification_issues_zh(risk)
        if issues:
            boundary = "当前尚未闭合的环节包括：" + "；".join(issues) + "。"
        else:
            boundary = verifier_note_zh(risk.get("verification_notes")) or (
                "关键事实、计算依据或事项状态仍未完全闭合，因此当前只能作为待复核风险阅读。"
            )
    elif verification == "rejected":
        boundary = "该候选未通过当前验证规则，不应作为已确认风险引用。"
    else:
        boundary = verifier_note_zh(risk.get("verification_notes")) or (
            "验证状态尚未完整形成，当前结论不能作为已确认事实。"
        )
    impact = risk_reasoning(code)
    if code == "cash_runway" and calculation_safe and verification == "verified" and isinstance(calculation, Mapping):
        result = _decimal_text(calculation.get("result"), places=2)
        if result:
            impact = (
                f"按本次复算，现有现金约可覆盖 {result} 个月的当前经营净流出。"
                "缓冲期较短会提高公司对融资进度、回款改善和支出控制的敏感度。"
            )
    elif code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        impact = (
            f"该事项关系到发行人对少数{subject}的依赖程度。"
            f"在占比尚未完成报告期对齐前，不能断言集中度高低；一旦确认依赖集中，{subject}流失、议价或履约变化才可能形成实质影响。"
        )
    elif code == "redemption_rights" and metadata.get("impact_on_public_shareholders"):
        impact = (
            "结构化条款同时记录了对上市后公众股东影响的候选判断："
            + _compact_ui_fact(metadata.get("impact_on_public_shareholders"), limit=260)
            + "。该判断仍受权利主体和条款状态验证结果约束。"
        )
    elif code == "material_litigation_compliance" and metadata.get("potential_impact"):
        impact = (
            "结构化法律事实记录的候选影响为："
            + _compact_ui_fact(metadata.get("potential_impact"), limit=260)
            + "。当前仅用于说明需要核查的责任范围，不代表影响已经发生。"
        )

    review_focus = risk_review_focus(code)
    if code in {"customer_concentration", "supplier_concentration"} and _verification_issues_zh(risk):
        review_focus = "先把每个占比与对应报告期逐项对齐、排除客户与供应商交叉口径，再核查合同稳定性和替代能力。"
    elif code == "redemption_rights":
        review_focus = "逐句核对权利人、终止时点、恢复触发条件和上市后是否存续，并确认每个结构化字段都能回到同一组原文。"
    elif code == "material_litigation_compliance":
        review_focus = "核对事项身份、主管机构、当前状态、整改证据及管理层重大性判断，尤其区分“未受处罚”与“事项已经解决”。"

    return {
        "basis": basis,
        "impact": impact,
        "boundary": boundary,
        "review_focus": review_focus,
    }


def calculation_summary_zh(risk: Mapping[str, Any]) -> str:
    calculation = risk.get("calculation")
    if not _calculation_is_safe(risk) or not isinstance(calculation, Mapping):
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
        and str(risk.get("verification_status") or "").lower() != "rejected"
    )
    if not summary["total"]:
        return (
            "本次没有风险事项进入审阅范围。"
            "这只表示当前证据与验证规则未形成可供审阅的风险事项，不等同于发行人不存在风险。"
        )
    parts = [f"本次有 {summary['total']} 项风险事项进入审阅范围"]
    if summary["high_or_critical"]:
        parts.append(f"其中 {summary['high_or_critical']} 项为高或极高风险")
    if summary["needs_review"]:
        parts.append(f"{summary['needs_review']} 项仍需进一步复核")
    if summary["evidence_count"]:
        parts.append(f"已绑定 {summary['evidence_count']} 条原文证据")
    if summary["high_or_critical"]:
        guidance = "建议优先查看高或极高风险事项及其原文依据。"
    elif summary["needs_review"]:
        guidance = "建议优先查看待复核事项及其原文依据。"
    else:
        guidance = "建议结合原文依据逐项审阅。"
    return "，".join(parts) + "。" + guidance


def _valid_final_synthesis(value: object) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    scope_check = value.get("scope_check") or {}
    judgement = value.get("judgement")
    if (
        value.get("status") != "available"
        or value.get("outcome") != "accepted"
        or value.get("fail_closed") is not False
        or not isinstance(scope_check, Mapping)
        or scope_check.get("status") != "passed"
        or not isinstance(judgement, Mapping)
    ):
        return None
    return value


def trusted_final_synthesis(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the governed final synthesis only after all trust checks pass.

    Component diagnostics are the primary source.  The copy stored under the
    final result metadata is a compatibility fallback; if both exist and their
    judgements disagree, the reader view fails closed instead of choosing one.
    """

    diagnostics = payload.get("component_diagnostics") or {}
    primary_raw = (
        diagnostics.get("final_supervision_llm")
        if isinstance(diagnostics, Mapping)
        else None
    )
    final = payload.get("final_supervision") or {}
    final_metadata = final.get("metadata") or {} if isinstance(final, Mapping) else {}
    secondary_raw = (
        final_metadata.get("final_supervision_llm")
        if isinstance(final_metadata, Mapping)
        else None
    )

    if isinstance(primary_raw, Mapping) and primary_raw:
        primary = _valid_final_synthesis(primary_raw)
        if primary is None:
            return None
        secondary = _valid_final_synthesis(secondary_raw)
        if secondary is not None and secondary.get("judgement") != primary.get("judgement"):
            return None
        return primary
    return _valid_final_synthesis(secondary_raw)


def trusted_final_judgement(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    synthesis = trusted_final_synthesis(payload)
    judgement = synthesis.get("judgement") if synthesis is not None else None
    return judgement if isinstance(judgement, Mapping) else None


def _prioritized_reader_risks(
    payload: Mapping[str, Any], risks: list[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    """Use trusted LLM references for order, then a deterministic safe order."""

    judgement = trusted_final_judgement(payload)
    referenced_ids: list[str] = []
    if judgement is not None:
        for finding in judgement.get("key_findings") or []:
            if not isinstance(finding, Mapping):
                continue
            for risk_id in finding.get("risk_ids") or []:
                text = str(risk_id)
                if text and text not in referenced_ids:
                    referenced_ids.append(text)

    by_id = {str(risk.get("risk_id") or ""): risk for risk in risks}
    ordered = [by_id[risk_id] for risk_id in referenced_ids if risk_id in by_id]
    used = {str(risk.get("risk_id") or "") for risk in ordered}
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    verification_rank = {"verified": 0, "needs_review": 1, "pending": 2}
    remaining = [risk for risk in risks if str(risk.get("risk_id") or "") not in used]
    remaining.sort(
        key=lambda risk: (
            severity_rank.get(str(risk.get("level") or "").lower(), 9),
            verification_rank.get(
                str(risk.get("verification_status") or "").lower(), 9
            ),
            -len(risk.get("evidence") or []),
            str(risk.get("risk_code") or ""),
        )
    )
    return ordered + remaining


def supervisor_narrative_zh(payload: Mapping[str, Any]) -> str:
    """生成面向评审的长版综合结论，不复述原始技术载荷。"""

    risks = [
        risk
        for domain in (payload.get("domains") or {}).values()
        if isinstance(domain, Mapping)
        for risk in (domain.get("risks") or [])
        if isinstance(risk, Mapping)
        and str(risk.get("verification_status") or "").lower() != "rejected"
    ]
    summary = summarize_risks(risks)
    prediction = payload.get("prediction") or {}
    rule_level = _RISK_LEVEL_LABELS.get(
        str(prediction.get("risk_level") or "unavailable").lower(),
        "暂不可用",
    ) if isinstance(prediction, Mapping) else "暂不可用"
    synthesis = trusted_final_synthesis(payload)
    judgement = trusted_final_judgement(payload)
    raw_overall = (
        judgement.get("overall_risk") if isinstance(judgement, Mapping) else None
    )
    overall_level = _RISK_LEVEL_LABELS.get(
        str(raw_overall or "unavailable").lower(),
        "暂不可用",
    )
    if raw_overall:
        opening = (
            f"多通道综合审阅结论为{overall_level}风险，规则筛选参考为{rule_level}风险。"
            "综合结论同时考虑招股书风险、验证状态、市场环境、模型信号与跨通道分歧；"
            "当两者不同，应以综合审阅及其证据边界为准，不能用单一规则等级覆盖尚未解决的风险。"
        )
    else:
        opening = (
            "当前未形成通过范围检查的智能综合审阅。"
            f"规则筛选参考为{rule_level}风险，但它只用于初步排序，不能替代总体风险判断。"
        )
    paragraphs = [opening, supervisor_summary_zh(payload)]

    if risks:
        priority_rows: list[str] = []
        for risk in _prioritized_reader_risks(payload, risks)[:4]:
            code = str(risk.get("risk_code") or "")
            name = RISK_DISPLAY_NAMES.get(code, "其他风险事项")
            state = _STATUS_LABELS.get(
                str(risk.get("verification_status") or "unavailable").lower(),
                "状态不可用",
            )
            priority_rows.append(
                f"{name}（{state}）：{risk_conclusion_zh(risk)}"
            )
        paragraphs.append("招股书风险的具体依据如下：" + " ".join(priority_rows))

    if summary["needs_review"]:
        paragraphs.append(
            f"其中 {summary['needs_review']} 项仍处于待复核状态。"
            "这表示系统已经形成有依据的风险候选，但报告期口径、事项进展、影响程度或"
            "确定性计算仍有尚未闭合的环节；本结论既不把它们当作已证实事实，也不会因"
            "尚未验证而忽略。"
        )

    final = payload.get("final_supervision") or {}
    final_market = final.get("market_context") if isinstance(final, Mapping) else None
    market = final_market or payload.get("market_context") or {}
    observations = (
        (market.get("observations") or []) if isinstance(market, Mapping) else []
    )
    available_market = sum(
        1 for item in observations
        if isinstance(item, Mapping) and item.get("availability") == "available"
    )
    channel_states = {
        str(item.get("channel")): str(item.get("status") or "unavailable")
        for item in (final.get("channel_states") or [])
        if isinstance(item, Mapping)
    } if isinstance(final, Mapping) else {}
    if observations:
        market_copy = (
            f"市场方面，本次取得 {available_market}/{len(observations)} 项 Market-X 核心观测；"
            "未取得的项目保持缺失，不以 0 或推测值替代。"
        )
    else:
        market_copy = "市场方面，当前没有足够的上市前环境信息，不能据此判断外部环境为低风险。"
    if channel_states.get("model") == "available":
        model_copy = (
            "模型方面已形成辅助排序信号，但该信号未经概率校准，不能理解为风险发生概率"
            "或上市后收益预测。"
        )
    else:
        model_copy = "模型方面当前没有可核验的逐案信号；模型缺失同样不代表低风险。"
    provenance = market.get("provenance") or {} if isinstance(market, Mapping) else {}
    market_intelligence = (
        provenance.get("market_intelligence")
        if isinstance(provenance, Mapping)
        else None
    ) or (
        market.get("market_intelligence") if isinstance(market, Mapping) else None
    ) or payload.get("market_intelligence") or {}
    if isinstance(market_intelligence, Mapping):
        heat_payload = market_intelligence.get("ipo_heat") or {}
        regime_payload = market_intelligence.get("market_regime") or {}
        raw_heat = (
            heat_payload.get("ipo_heat")
            if isinstance(heat_payload, Mapping)
            else heat_payload
        )
        raw_regime = (
            regime_payload.get("market_regime")
            if isinstance(regime_payload, Mapping)
            else regime_payload
        )
        raw_liquidity = (
            regime_payload.get("liquidity_condition")
            if isinstance(regime_payload, Mapping)
            else None
        )
        heat_label = {
            "HOT": "偏热",
            "HIGH": "偏热",
            "WARM": "偏热",
            "NEUTRAL": "中性",
            "COOL": "偏冷",
            "COLD": "偏冷",
        }.get(str(raw_heat or "").upper())
        if heat_label:
            market_copy += f"近期新股发行热度判断为{heat_label}。"
        if str(raw_regime or "").upper() in {"INSUFFICIENT_DATA", "UNAVAILABLE"}:
            market_copy += "整体市场状态所需信息不足，暂不作方向性推断。"
        if str(raw_liquidity or "").upper() in {"INSUFFICIENT_DATA", "UNAVAILABLE"}:
            market_copy += "市场流动性状况暂无法可靠判断。"
    paragraphs.append(market_copy + model_copy)

    conflicts = (
        ((payload.get("component_diagnostics") or {}).get("conflict_detection") or {}).get("conflicts")
        or []
    )
    unsettled = sum(
        str(item.get("status") or "").lower() in {"partially_resolved", "unresolved"}
        for item in conflicts
        if isinstance(item, Mapping)
    )
    if unsettled:
        model_divergence = sum(
            "document_model_divergence" in str(item.get("conflict_id") or "")
            for item in conflicts
            if isinstance(item, Mapping)
            and str(item.get("status") or "").lower() in {"partially_resolved", "unresolved"}
        )
        divergence_copy = (
            f"其中 {model_divergence} 项是模型方向与招股书结论之间的分歧，"
            "该分歧不能靠模型分数覆盖原文判断；"
            if model_divergence
            else ""
        )
        paragraphs.append(
            f"跨通道审阅仍保留 {unsettled} 项部分解决或未解决的分歧。"
            + divergence_copy
            + "其余分歧主要涉及部分线索与核验结论不一致、数值口径未闭合或新证据仍需进一步判断。"
            "系统保留这些分歧，而不是强行合并为单一答案。"
        )

    unresolved_labels = {
        "continuous_loss": "持续亏损",
        "revenue_growth": "收入变化",
        "customer_concentration": "客户集中度",
        "supplier_concentration": "供应商集中度",
        "precommercial_product": "产品商业化状态",
    }
    formal_codes = {str(risk.get("risk_code") or "") for risk in risks}
    unresolved_clues: list[str] = []
    for item in conflicts:
        if not isinstance(item, Mapping):
            continue
        conflict_id = str(item.get("conflict_id") or "")
        if "unresolved_agent_claim" not in conflict_id:
            continue
        for code, label in unresolved_labels.items():
            if code in conflict_id and code not in formal_codes and label not in unresolved_clues:
                unresolved_clues.append(label)
    if unresolved_clues:
        paragraphs.append(
            "此外，系统还发现"
            + "、".join(unresolved_clues)
            + "方面的待核查线索，但现有数值存在冲突、报告期尚未对齐或结构化字段仍不完整，"
            "因此没有把这些线索列为面向评审的风险结论。"
        )

    focuses: list[str] = []
    for risk in risks:
        focus = risk_reasoning_annotation(risk)["review_focus"].rstrip("。；")
        if focus not in focuses:
            focuses.append(focus)
    if focuses:
        paragraphs.append("建议后续复核：" + "；".join(focuses[:3]) + "。")

    scope = synthesis.get("scope_check") if isinstance(synthesis, Mapping) else None
    if isinstance(scope, Mapping) and scope.get("status") == "passed":
        paragraphs.append(
            "综合结论只使用本次列示的招股书证据、已保存的市场信息和辅助信号，"
            "不新增未披露事实，也不把模型信号写成风险发生概率。"
        )

    return "\n\n".join(paragraphs)
