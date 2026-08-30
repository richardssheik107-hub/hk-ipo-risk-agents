"""前端展示文案与简体中文本地化辅助。

本模块只负责展示，不修改 RiskItem、Evidence、Market-X、模型、Verifier 或运行语义。
招股书原文证据保持原样；除此之外，界面使用简体中文和必要的专有名词。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
from typing import Any


RISK_REASONING: dict[str, str] = {
    "cash_runway": (
        "现金可支撑期把期末现金与同口径经营现金消耗联系起来，反映公司在当前消耗速度下"
        "能够承受多长时间的经营压力。支撑期越短，公司对回款改善、支出控制和后续融资时点"
        "越敏感；但它只是基于已披露期间的静态测算，不是未来现金余额预测。"
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
        "客户集中度反映收入是否依赖少数交易对手。若复核确认少数客户长期贡献较高，"
        "核心客户的订单缩减、续约失败、价格谈判或回款变化可能较快传导至收入、利润和"
        "经营现金流；判断时还需区分同一控制下客户以及不同报告期的统计口径。"
    ),
    "supplier_concentration": (
        "供应商集中度反映采购和生产是否依赖少数交易对手。若复核确认关键投入长期集中，"
        "供应商提价、产能收缩、质量或交付异常可能传导至成本、生产进度和履约能力；"
        "实际影响取决于替代来源、切换周期、认证要求和合同约束。"
    ),
    "redemption_rights": (
        "特殊股东权利需要同时看终止与恢复条款，不能仅凭“已经终止”或“曾经存在”单独下结论。"
        "若权利只在上市失败等条件下恢复，成功上市后的直接影响通常受到约束；若恢复条件被触发，"
        "赎回、撤资或反摊薄安排仍可能影响上市前现金、股权结构及其他股东权益。"
    ),
    "material_litigation_compliance": (
        "诉讼与合规分析需要把已披露事项、可能承担的责任、当前进展以及管理层或法律顾问的"
        "缓释观点分开阅读。未受处罚、风险较低或不构成重大不利影响的观点可以降低担忧，"
        "但不等同于义务已经消失、整改已经完成或未来不会产生现金及经营影响。"
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
    "unavailable_error": "运行异常", "no_risk_emitted": "未识别到正式风险",
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
    "聞": "闻", "創": "创", "敗": "败", "薦": "荐",
    "積": "积", "獲": "获", "賠": "赔", "償": "偿", "眾": "众", "歷": "历", "廠": "厂",
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


_MODEL_ERROR_STATUSES = frozenset({"error", "failed", "unavailable_error"})
_MODEL_KNOWN_STATUSES = frozenset({
    "available",
    "partial",
    "pending_gate",
    "degraded",
    "disabled",
    "unavailable",
    *_MODEL_ERROR_STATUSES,
})


@dataclass(frozen=True)
class ModelChannelProjection:
    """One conservative presentation view of the governed model channel.

    ``FinalSupervisionResult.channel_states`` is the channel-level authority,
    while its nested model prediction is the preferred result payload. Older
    persisted results may carry only the top-level prediction, so that remains
    a compatibility fallback. A channel can be shown as available only when
    both its state and a usable score-bearing prediction agree.
    """

    status: str
    prediction: Mapping[str, Any] | None
    reason: str = ""
    source: str = "none"
    consistency_issue: str = ""

    @property
    def is_available(self) -> bool:
        return self.status == "available"

    @property
    def is_error(self) -> bool:
        return self.status == "unavailable_error"


def model_channel_projection(payload: Mapping[str, Any]) -> ModelChannelProjection:
    """Resolve model payload, channel state and fallbacks exactly once.

    The function never repairs backend data. Contradictory ``available``
    claims fail closed to ``unavailable_error`` so no frontend surface can turn
    a missing or failed model result into a green model signal.
    """

    final = payload.get("final_supervision") or {}
    if not isinstance(final, Mapping):
        final = {}

    channel_status = ""
    channel_reason = ""
    for item in final.get("channel_states") or []:
        if not isinstance(item, Mapping) or str(item.get("channel") or "") != "model":
            continue
        channel_status = str(item.get("status") or "unavailable").strip().lower()
        channel_reason = str(item.get("reason") or "")

    candidates = (
        ("final_supervision.model_prediction", final.get("model_prediction")),
        ("model_prediction", payload.get("model_prediction")),
        ("model", payload.get("model")),
    )
    source = "none"
    prediction: Mapping[str, Any] | None = None
    for candidate_source, candidate in candidates:
        if isinstance(candidate, Mapping) and candidate:
            source = candidate_source
            prediction = candidate
            break

    prediction_status = "unavailable"
    prediction_reason = ""
    if prediction is not None:
        prediction_status = str(prediction.get("status") or "available").strip().lower()
        prediction_reason = str(prediction.get("reason") or "")

    if channel_status in _MODEL_ERROR_STATUSES or prediction_status in _MODEL_ERROR_STATUSES:
        return ModelChannelProjection(
            status="unavailable_error",
            prediction=prediction,
            reason=prediction_reason or channel_reason,
            source=source,
        )

    unknown = next(
        (
            status
            for status in (channel_status, prediction_status)
            if status and status not in _MODEL_KNOWN_STATUSES
        ),
        "",
    )
    if unknown:
        return ModelChannelProjection(
            status="unavailable_error",
            prediction=prediction,
            reason=prediction_reason or channel_reason,
            source=source,
            consistency_issue=f"unknown model status: {unknown}",
        )

    if channel_status and channel_status != "available":
        return ModelChannelProjection(
            status=channel_status,
            prediction=prediction,
            reason=channel_reason or prediction_reason,
            source=source,
        )

    if channel_status == "available" and prediction is None:
        return ModelChannelProjection(
            status="unavailable_error",
            prediction=None,
            reason=channel_reason,
            source=source,
            consistency_issue="model channel is available but prediction payload is missing",
        )

    if prediction_status == "available" and prediction is not None and prediction.get("score") is None:
        return ModelChannelProjection(
            status="unavailable_error",
            prediction=prediction,
            reason=prediction_reason or channel_reason,
            source=source,
            consistency_issue="available model prediction has no score",
        )

    return ModelChannelProjection(
        status=prediction_status,
        prediction=prediction,
        reason=prediction_reason or channel_reason,
        source=source,
    )


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


def _evidence_text(risk: Mapping[str, Any]) -> str:
    """Return raw Evidence text for presence checks only.

    The text is never rendered through this helper, translated, or paraphrased as
    a quotation.  It only lets reader copy state which disclosure dimensions are
    actually present in the persisted Evidence attached to this risk.
    """

    return "\n".join(
        str(item.get("text") or "")
        for item in (risk.get("evidence") or [])
        if isinstance(item, Mapping) and item.get("text")
    )


def _contains_any(text: str, values: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(value.lower() in lowered for value in values)


def _concentration_evidence_dimensions(
    risk: Mapping[str, Any], *, subject: str
) -> list[str]:
    """Describe, without extracting new numbers, what the bound Evidence covers."""

    text = _evidence_text(risk)
    if not text:
        return []
    is_customer = subject == "客户"
    dimensions: list[str] = []
    party_terms = (
        ("五大客戶", "五大客户", "主要客戶", "主要客户", "largest customer", "top five customers")
        if is_customer
        else ("五大供應商", "五大供应商", "主要供應商", "主要供应商", "largest supplier", "top five suppliers")
    )
    if _contains_any(text, party_terms):
        dimensions.append(f"主要及前五大{subject}")
    share_terms = (
        ("佔總收入", "占总收入", "收入百分比", "% of total revenue")
        if is_customer
        else ("佔採購", "占采购", "採購額百分比", "采购额百分比", "% of total purchases")
    )
    if _contains_any(text, share_terms):
        dimensions.append("交易金额及占比")
    if _contains_any(
        text,
        (
            "開始業務關係",
            "开始业务关系",
            "業務關係的年份",
            "业务关系的年份",
            "business relationship",
            "合約",
            "合同",
        ),
    ):
        dimensions.append("合作关系或合作年限")
    if _contains_any(
        text,
        (
            "同一實體最終控制",
            "同一实体最终控制",
            "共同控制",
            "common control",
            "ultimately controlled",
        ),
    ):
        dimensions.append("同一控制下交易对手的合并口径")
    if _contains_any(
        text,
        (
            "客戶兼供應商",
            "客户兼供应商",
            "客戶及供應商重疊",
            "客户及供应商重叠",
            "客戶與供應商重疊",
            "客户与供应商重叠",
            "同時為我們的客戶及供應商",
            "同时为我们的客户及供应商",
            "既是我們的客戶亦是我們的供應商",
            "既是我们的客户也是我们的供应商",
            "亦為我們的供應商",
            "亦为我们的供应商",
            "同時為我們的供應商",
            "同时为我们的供应商",
            "供應商－客戶",
            "供应商－客户",
            "供應商-客戶",
            "供应商-客户",
            "客戶－供應商",
            "客户－供应商",
            "both a customer and a supplier",
        ),
    ):
        dimensions.append("同一交易对手兼具客户与供应商身份")
    if _contains_any(
        text,
        (
            "推廣服務",
            "推广服务",
            "營銷服務",
            "营销服务",
            "promotion service",
            "marketing service",
        ),
    ):
        dimensions.append("推广或营销服务交易")
    if _contains_any(text, ("ODM", "OEM", "原設計製造", "原设计制造", "代工生產", "代工生产")):
        dimensions.append("ODM/OEM 业务或生产分工")
    return dimensions


def _has_readable_chinese(value: object) -> bool:
    text = str(value or "")
    han_count = len(re.findall(r"[\u3400-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    return han_count >= 4 and latin_count <= max(24, han_count * 3)


def _legal_evidence_topics(risk: Mapping[str, Any]) -> list[str]:
    text = _evidence_text(risk)
    topics: list[str] = []
    specific_topic_terms = (
        (
            "社会保险及住房公积金缴纳",
            ("社會保險", "社会保险", "住房公積金", "住房公积金", "social insurance", "housing provident fund"),
        ),
        (
            "土地使用权或物业权属",
            ("土地使用權", "土地使用权", "房屋所有權", "房屋所有权", "物業權屬", "物业权属", "land use right"),
        ),
        (
            "行政许可或业务资质",
            ("行政許可", "行政许可", "牌照", "許可證", "许可证", "license", "permit"),
        ),
        (
            "环境合规",
            ("環境保護", "环境保护", "環保", "环保", "排污", "environmental compliance"),
        ),
    )
    for label, terms in specific_topic_terms:
        if _contains_any(text, terms):
            topics.append(label)
    # Full prospectus pages often mention litigation incidentally in a nearby
    # paragraph.  Use it as the topic only when no more specific governed
    # compliance subject is present on this Evidence item.
    if not topics and _contains_any(text, ("訴訟", "诉讼", "仲裁", "litigation", "arbitration")):
        topics.append("诉讼或仲裁")
    return topics


def _legal_evidence_consequence(risk: Mapping[str, Any]) -> str:
    text = _evidence_text(risk)
    consequences: list[str] = []
    consequence_terms = (
        ("补缴", ("補繳", "补缴", "make up", "underpayment")),
        ("滞纳金", ("滯納金", "滞纳金", "late-payment surcharge")),
        ("罚款或行政处罚", ("罰款", "罚款", "行政處罰", "行政处罚", "fine", "penalty")),
        ("赔偿", ("賠償", "赔偿", "compensation", "indemnif")),
        ("法院强制执行", ("強制執行", "强制执行", "court-enforced")),
        ("拆除或恢复原状", ("拆除", "恢復原狀", "恢复原状", "demolish", "restore")),
        ("资产使用或业务限制", ("停止使用", "業務限制", "业务限制", "use restriction", "business restriction")),
    )
    for label, terms in consequence_terms:
        if _contains_any(text, terms):
            consequences.append(label)
    if not consequences:
        return ""
    return "原文涉及的条件性后果包括" + "、".join(consequences[:5])


def _legal_evidence_mitigation(risk: Mapping[str, Any]) -> str:
    text = _evidence_text(risk)
    mitigations: list[str] = []
    if _contains_any(text, ("未受到任何行政處罰", "未受到任何行政处罚", "無行政處罰", "无行政处罚", "no penalty")):
        mitigations.append("截至披露时点未受相关行政处罚")
    if _contains_any(text, ("不构成重大不利", "不會造成重大不利", "不会造成重大不利", "重大不利影響", "重大不利影响")):
        mitigations.append("原文包含管理层关于重大不利影响的判断")
    if _contains_any(text, ("風險較低", "风险较低", "low risk", "remote risk")):
        mitigations.append("原文包含法律顾问或专业意见的低风险判断")
    return "、".join(mitigations)


def _legal_reader_facts(risk: Mapping[str, Any]) -> tuple[str, str, str]:
    """Prefer concise Chinese Evidence cues over long English structured prose."""

    metadata = _risk_metadata(risk)
    topics = _legal_evidence_topics(risk)
    topic_copy = "、".join(topics)
    raw_subject = metadata.get("subject")
    subject = (
        _compact_ui_fact(raw_subject, limit=300)
        if _has_readable_chinese(raw_subject)
        else (f"{topic_copy}相关事项" if topic_copy else "")
    )
    raw_impact = metadata.get("potential_impact")
    impact = (
        _compact_ui_fact(raw_impact, limit=240)
        if _has_readable_chinese(raw_impact)
        else _legal_evidence_consequence(risk)
    )
    raw_management = metadata.get("management_materiality")
    management = (
        _compact_ui_fact(raw_management, limit=220)
        if _has_readable_chinese(raw_management)
        else _legal_evidence_mitigation(risk)
    )
    return subject, impact, management


def _rights_type_zh(value: object) -> str:
    labels = {
        "redemption_right": "赎回或撤资权",
        "anti_dilution_right": "反摊薄权",
        "liquidation_preference": "清算优先权",
    }
    raw = str(value or "").strip()
    return labels.get(raw.lower(), _compact_ui_fact(raw.replace("_", " "), limit=60))


def _risk_interpretation_zh(risk: Mapping[str, Any]) -> str:
    """Explain what the persisted facts mean without creating a new finding."""

    code = str(risk.get("risk_code") or "")
    verification = str(risk.get("verification_status") or "unavailable").lower()
    metadata = _risk_metadata(risk)
    if code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        dimensions = _concentration_evidence_dimensions(risk, subject=subject)
        covered = (
            "、".join(dimensions)
            if dimensions
            else f"往绩记录期的{subject}构成、交易关系和占比口径"
        )
        overlap_copy = ""
        if "同一交易对手兼具客户与供应商身份" in dimensions:
            service_side = (
                "采购或推广服务端"
                if "推广或营销服务交易" in dimensions
                else "供应端"
            )
            overlap_copy = (
                f"证据还提示同一交易对手可能同时出现在销售端和{service_side}；这种关系重叠会影响"
                "交易对手归并及交易实质判断，但本身不等于集中度已经较高。"
            )
        mechanism = (
            "这些字段共同用于判断收入是否实质依赖少数客户，以及这种依赖在不同报告期是否持续。"
            "客户兼供应商、同一控制下主体或 ODM/OEM 分工若确有披露，还会影响交易对手如何归并，"
            "不能把单张表中的名称或比例直接当成最终集中度。"
            if subject == "客户"
            else "这些字段共同用于判断采购与生产是否实质依赖少数供应商，以及这种依赖在不同报告期"
            "是否持续。同一控制下主体、客户兼供应商或 ODM/OEM 分工若确有披露，还会影响交易对手"
            "如何归并，不能把单张表中的名称或比例直接当成最终集中度。"
        )
        return (
            f"原文证据实际覆盖{covered}。{overlap_copy}{mechanism}"
            + (
                "当前数值与报告期尚未完成一致性复算，因此这里形成的是有明确证据入口的风险线索，"
                "不是“集中度已经较高”的事实判断。"
                if verification != "verified"
                else "当前结构化数值已经通过验证，但仍需结合交易关系稳定性判断其业务重要性。"
            )
        )
    if code == "cash_runway":
        calculation = risk.get("calculation")
        if _calculation_is_safe(risk) and isinstance(calculation, Mapping):
            inputs = calculation.get("inputs") or {}
            period = (
                _decimal_text(inputs.get("period_months"), places=0)
                if isinstance(inputs, Mapping)
                else ""
            )
            period_copy = f"{period} 个月" if period else "同一披露期间"
            level = str(risk.get("level") or "").lower()
            significance = (
                "从流动性压力角度看，这段缓冲偏短，"
                if level in {"critical", "high"}
                else "这段缓冲用于衡量公司应对经营消耗的时间窗口，"
            )
            return (
                f"两条财务证据分别提供期末现金与{period_copy}经营活动现金净流量，确定性公式把现金"
                f"除以月均经营净流出，得到在当前消耗速度下的现金缓冲。{significance}"
                "从而形成对经营改善或新资金到位时间的敏感性分析；它没有预测未来"
                "收入、融资或支出变化。"
            )
        return (
            "原文候选涉及现金余额与经营现金消耗，但当前输入或证据关联不足以完成同口径复算。"
            "现金消耗只有在金额、期间和单位对齐后，才能转化为可解释的流动性缓冲指标。"
        )
    if code == "redemption_rights":
        right_type = _rights_type_zh(metadata.get("right_type")) or "特殊股东权利"
        has_termination = bool(metadata.get("termination_event"))
        has_restoration = metadata.get("restoration_clause") is True
        clause_shape = (
            "原文结构化字段同时覆盖权利终止与条件恢复"
            if has_termination and has_restoration
            else "原文结构化字段覆盖特殊权利的状态或触发条件"
        )
        return (
            f"{clause_shape}，识别的权利类型为{right_type}。因此分析重点不是简单判断权利“有”或“无”，"
            "而是判断在上市申请、成功上市或上市失败等不同情形下，权利是否仍可生效。只有权利"
            "主体、终止时点和恢复条件逐句对应后，才能进一步判断潜在影响偏向现金退出、股权摊薄"
            "还是仅属于上市前历史安排。"
        )
    if code == "material_litigation_compliance":
        subject, impact, management = _legal_reader_facts(risk)
        subject = subject[:180].rstrip("。；")
        impact = impact[:180].rstrip("。；")
        management = management[:160].rstrip("。；")
        facts: list[str] = []
        if subject:
            facts.append(f"结构化提取将事项概括为：{subject}")
        if impact:
            facts.append(f"结构化字段记录的可能后果为：{impact}")
        if management:
            facts.append(f"同时记录管理层或法律顾问的缓释观点：{management}")
        fact_copy = "；".join(facts) if facts else "原文涉及一项诉讼、监管或合规事项"
        return (
            fact_copy
            + "。这些信息之所以形成风险线索，是因为已披露义务或瑕疵在被追究、整改未完成或业务"
            "依赖相关资产时，可能转化为现金支出、资产使用限制或经营扰动；缓释观点可以用于判断"
            "影响程度，但不能替代对事项状态、整改证据和主管机构意见的核验。"
        )
    if code == "continuous_loss":
        return (
            "原文事实用于判断多个可比报告期是否连续亏损。连续亏损本身说明经营产生的利润尚不足以"
            "覆盖成本费用，进一步的风险含义取决于亏损趋势、毛利率、费用结构和现金消耗是否同步恶化。"
        )
    if code == "revenue_growth":
        return (
            "原文事实用于比较口径一致的相邻报告期收入。收入变化只有结合基数、业务构成、客户与"
            "一次性因素，才能说明需求或商业化能力；单一增长率不能独立证明经营质量改善或恶化。"
        )
    if code == "precommercial_product":
        product = _compact_ui_fact(metadata.get("product_name") or metadata.get("subject"), limit=100)
        subject = product or "核心产品"
        return (
            f"结构化事实将{subject}识别为尚未进入稳定商业化阶段，因此收入实现仍取决于研发、审批、"
            "量产和市场接受度等后续环节。该线索说明的是兑现路径尚未闭合，不等同于产品必然失败。"
        )
    return (
        "原文证据为该事项提供了可追溯的审阅入口；风险线索来自已落盘结构化字段之间的关系，"
        "而不是页面根据关键词补写的新事实。"
    )


def evidence_item_interpretation_zh(
    risk: Mapping[str, Any], evidence: Mapping[str, Any]
) -> str:
    """Explain the role of one Evidence item without rewriting its source text.

    This helper performs presence checks against only ``evidence['text']``.  It
    never parses an unverified percentage or amount into a reader-facing fact;
    the original Evidence remains the sole quotation shown by the viewer.
    """

    fallback = "本页提供相关原文入口，需与其他证据合并判断。"
    if not isinstance(evidence, Mapping) or not str(evidence.get("text") or "").strip():
        return fallback
    scoped_risk = dict(risk)
    scoped_risk["evidence"] = [evidence]
    text = str(evidence.get("text") or "")
    code = str(risk.get("risk_code") or "")

    if code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        dimensions = _concentration_evidence_dimensions(scoped_risk, subject=subject)
        notes: list[str] = []
        if any(
            dimension in dimensions
            for dimension in (f"主要及前五大{subject}", "交易金额及占比")
        ):
            notes.append(
                f"本页包含{subject}构成、交易金额或占比表述，是核对集中度口径与报告期的直接入口"
            )
        if "同一控制下交易对手的合并口径" in dimensions:
            notes.append("本页提示若干交易对手受同一实体控制，复核时应先按经济实质判断是否需要合并归组")
        if "同一交易对手兼具客户与供应商身份" in dimensions:
            service_side = (
                "采购或推广服务端"
                if "推广或营销服务交易" in dimensions
                else "供应端"
            )
            notes.append(
                f"本页提示同一交易对手可能同时出现在销售端和{service_side}，这种角色重叠会影响交易实质与归并口径"
            )
        if "ODM/OEM 业务或生产分工" in dimensions:
            notes.append("本页涉及 ODM/OEM 业务或生产分工，需要结合替代供应能力理解交易依赖")
        if notes:
            return "；".join(notes) + "。本页不单独证明集中度高低，也不据此提取未经验证的具体占比。"
        return fallback

    if code == "material_litigation_compliance":
        topics = _legal_evidence_topics(scoped_risk)
        consequence = _legal_evidence_consequence(scoped_risk)
        mitigation = _legal_evidence_mitigation(scoped_risk)
        notes = []
        if "社会保险及住房公积金缴纳" in topics:
            notes.append("本页说明社会保险或住房公积金缴纳义务及相关合规事项")
        if "土地使用权或物业权属" in topics:
            notes.append("本页说明土地使用权或物业权属瑕疵及其处理状态")
        if consequence:
            notes.append(consequence)
        if _contains_any(text, ("產量", "产量", "產能", "产能", "production volume", "capacity")):
            notes.append("本页还提供相关产量或产能信息，可作为衡量经营影响范围的缓释线索")
        if mitigation:
            notes.append(mitigation)
        if notes:
            return (
                "；".join(notes)
                + "。这些内容构成事项、条件性后果与缓释依据的一部分，但本页不能单独证明事项已经解决或影响必然发生。"
            )
        return fallback

    if code == "redemption_rights":
        has_termination = _contains_any(
            text,
            ("終止", "终止", "失效", "不再生效", "terminate", "cease to have effect"),
        )
        has_restoration = _contains_any(
            text,
            ("恢復", "恢复", "自動恢復", "自动恢复", "restore", "revive"),
        )
        if has_termination and has_restoration:
            return (
                "本页同时包含特殊权利的终止安排与条件恢复安排，说明权利状态取决于上市进程或其他"
                "触发条件，不能只看“终止”一词判断其法律效果；仍需与权利主体和其他条款合并核对。"
            )
        if has_termination:
            return "本页提供特殊权利终止时点或失效安排，需要与恢复条款合并判断上市后是否仍可能生效。"
        if has_restoration:
            return "本页提供特殊权利恢复条件，需要与原权利内容及终止时点合并判断潜在现金或股权影响。"
        return fallback

    if code == "cash_runway":
        has_cash = _contains_any(
            text,
            (
                "現金及現金等價物",
                "现金及现金等价物",
                "現金及銀行結餘",
                "现金及银行结余",
                "cash and cash equivalents",
                "cash and bank balances",
            ),
        )
        has_operating_flow = _contains_any(
            text,
            (
                "經營活動現金流",
                "经营活动现金流",
                "經營活動所用現金",
                "经营活动所用现金",
                "operating cash flow",
                "cash used in operating activities",
            ),
        )
        if has_cash and has_operating_flow:
            return (
                "本页同时提供现金余额与经营活动现金流口径，是现金支撑期复算的输入来源之一；"
                "具体结果仍须使用已验证的期间、单位和证据关联完成确定性计算。"
            )
        if has_cash:
            return "本页提供披露时点的现金余额口径，是现金支撑期计算的分子输入，需与同期间经营现金净流出合并复算。"
        if has_operating_flow:
            return "本页提供经营活动现金流口径，是估算现金消耗速度的输入，需与同期间现金余额和期间长度合并复算。"
        return fallback

    return fallback


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
    """Only expose a numeric calculation after both governance and verification."""

    calculation = risk.get("calculation")
    if not isinstance(calculation, Mapping):
        return False
    if str(risk.get("verification_status") or "").lower() != "verified":
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
        if code == "cash_runway":
            level = str(risk.get("level") or "").lower()
            significance = (
                "从流动性审阅角度看，这一现金缓冲偏短，公司对经营回款改善、支出节奏和外部资金"
                "到位时间更为敏感。"
                if level in {"critical", "high"}
                else "该结果用于衡量公司应对当前经营消耗的时间窗口。"
            )
            return (
                calculated
                + " "
                + significance
                + "该测算没有纳入披露期后的融资、回款或支出"
                "变化，因此应作为流动性压力测试阅读，而不是对未来资金耗尽时点的预测。"
            )
        return calculated
    if code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        dimensions = _concentration_evidence_dimensions(risk, subject=subject)
        dimensions_copy = (
            "原文覆盖的判断维度包括" + "、".join(dimensions) + "。"
            if dimensions
            else "当前证据用于核对交易对手构成、交易占比和报告期口径。"
        )
        values = []
        if verification == "verified" and metadata.get("largest_counterparty_pct") not in (None, ""):
            values.append(f"最大{subject}占比约 {metadata['largest_counterparty_pct']}%")
        if verification == "verified" and metadata.get("top_five_pct") not in (None, ""):
            values.append(f"前五大{subject}合计占比约 {metadata['top_five_pct']}%")
        if values:
            return (
                "，".join(values)
                + f"。{dimensions_copy}这些结构化数值提供了衡量{subject}依赖程度的依据，但集中度本身不是损失结论；"
                + (
                    "还需要判断核心客户的订单、续约、议价和回款变化能否被其他客户承接。"
                    if subject == "客户"
                    else "还需要判断关键供应商的价格、产能、质量或交付变化能否由替代来源承接。"
                )
            )
        issues = _verification_issues_zh(risk)
        issue_copy = "；".join(issues)
        pages = _evidence_pages(risk)
        location = f"招股书第 {'、'.join(pages[:5])} 页包含相关披露" if pages else "当前已形成相关披露候选"
        mechanism = (
            "若逐期复核后确认收入持续依赖少数客户，订单缩减、续约失败、议价或回款变化才可能"
            "较快传导至收入、利润和经营现金流。"
            if subject == "客户"
            else "若逐期复核后确认采购持续依赖少数供应商，提价、停供、质量或交付异常才可能"
            "传导至成本、生产进度和履约能力。"
        )
        if issue_copy:
            return (
                f"{location}，内容涉及往绩记录期的{subject}构成、集中度或交易关系。"
                f"{dimensions_copy}由于{issue_copy}，本次尚未完成口径一致的集中度复算，"
                f"因此只能保留为待复核线索，不能据此判断集中程度或风险等级。{mechanism}"
            )
        return (
            f"{location}；{dimensions_copy}当前尚需把{subject}占比与对应报告期逐项对齐后，"
            f"才能判断集中程度。{mechanism}"
        )
    if code == "continuous_loss":
        count = metadata.get("latest_loss_period_count")
        return f"最新可比报告序列中已核验连续 {count} 个亏损期；该判断仍需结合各期损益和现金流理解经营压力。" if verification == "verified" and count not in (None, "") else "当前原文候选显示发行人可能存在持续亏损，但报告期与数值尚未形成可复核的连续序列，因此不能把候选直接写成已确认事实。"
    if code == "revenue_growth":
        growth = metadata.get("growth_pct_rounded") or metadata.get("growth_pct_exact")
        return f"最新两个可比报告期的收入变动已核验为约 {growth}%；该变化需结合收入基数、业务构成和报告期口径解释。" if verification == "verified" and growth not in (None, "") else "当前原文候选包含收入增长或下滑信号，但尚未形成口径一致的可比序列，现阶段只能作为待核对事项。"
    if code == "cash_runway":
        months = next((metadata.get(key) for key in ("runway_months", "cash_runway_months", "months_of_runway") if metadata.get(key) not in (None, "")), None)
        return (
            f"按当前可核验数据估算，现金可支撑期约为 {months} 个月。该指标把披露时点现金与"
            "当前经营净流出相比较，用于观察流动性缓冲，并不预测未来资金耗尽时点；仍需结合"
            "最新现金余额、经营现金流、融资安排和支出计划持续观察。"
            if verification == "verified" and months is not None
            else "当前资料提示现金消耗压力，但缺少完成现金可支撑期复算所需的完整输入，暂不能形成"
            "确定性结论。只有把同口径现金余额、经营净流出和期间长度对齐后，才能判断当前消耗速度"
            "是否会使公司对融资时点或经营回款更为敏感。"
        )
    if code == "redemption_rights":
        right_type = _rights_type_zh(metadata.get("right_type"))
        holder = _compact_ui_fact(metadata.get("holder"), limit=90).rstrip("。；")
        termination = _compact_ui_fact(metadata.get("termination_event"), limit=220).rstrip("。；")
        restoration = _compact_ui_fact(metadata.get("restoration_condition"), limit=260).rstrip("。；")
        parts = []
        if right_type:
            parts.append(f"结构化条款将相关权利识别为{right_type}")
        if holder:
            parts.append(f"候选权利人记为{holder}")
        if termination:
            parts.append(f"终止安排为：{termination}")
        if metadata.get("restoration_clause") is True and restoration:
            parts.append(f"同时存在恢复条件：{restoration}")
        if parts:
            return (
                "；".join(parts)
                + "。这组条款呈现的是“终止后在特定情形下恢复”的条件结构，而不是权利无条件持续存在。"
                "若成功上市时相关权利已经终止且没有触发恢复条件，上市后对公众股东的直接影响通常"
                "受到约束；若上市失败等恢复条件被触发，相关安排仍可能影响上市前现金、股权结构或"
                "其他股东权益。权利主体范围、终止时点和恢复条件仍需逐句核对。"
            )
        return (
            "招股书条款候选涉及特殊股东权利的终止或恢复安排。这里需要同时回答权利由谁持有、"
            "何时终止、何种情形下恢复以及上市后是否仍存续，才能判断其可能产生现金影响还是股权"
            "摊薄影响；当前证据链尚不足以确认这些条件。"
        )
    if code == "material_litigation_compliance":
        subject, impact, management = _legal_reader_facts(risk)
        parts = []
        if subject:
            parts.append(f"结合已关联原文，结构化分析将事项概括为：{subject}")
        if impact:
            parts.append(f"原文所对应的潜在责任或后果包括：{impact}")
        if management:
            parts.append(f"结构化字段同时记录管理层或法律顾问观点：{management}")
        if parts:
            return (
                "；".join(parts)
                + "。这组信息形成了“原文事项候选—可能责任—缓释观点”的分析链。潜在风险并不等同于"
                "处罚已经发生，而是相关义务若被主管机构追究或整改未完成，可能转化为补缴、罚款、"
                "赔偿、资产处置或经营限制；管理层的重大性判断属于缓释依据，不能单独证明事项已经"
                "解决。事项是否持续、整改是否完成和重大性仍待复核。"
            )
        return (
            "当前原文候选涉及诉讼、监管或合规事项，但事项身份、进展和潜在责任尚未形成可验证的"
            "完整链条。只有把事项本身、法定或合同后果、当前处理状态和管理层缓释依据相互对应，"
            "才能判断它主要构成一次性现金影响、持续经营约束还是披露层面的待核问题。"
        )
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
    interpretation = _risk_interpretation_zh(risk)
    if calculation_safe and verification == "verified":
        basis = page_copy + "相关财务输入已经过确定性公式复算，计算所用数据都能回到这些原文。"
    elif isinstance(calculation, Mapping):
        basis = page_copy + "目前已有计算候选，但计算状态、证据关联或风险验证尚未全部满足，因此不把候选数值写成确定性结论。"
    elif extraction_method.startswith("llm_structured"):
        basis = page_copy + "分析先从这些原文归纳候选事项，再核对主体、时点、责任和状态能否相互印证。"
    else:
        basis = page_copy + "分析只引用这些已经关联的原文，不根据页面上的关键词补写新事实。"

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
    if code == "cash_runway" and verification == "verified":
        boundary = (
            "已验证仅表示输入关联和公式结果通过了当前规则。现金可支撑期只反映披露时点现金与"
            "已披露期间经营净流出的静态关系，没有纳入后续融资、收入回款、资本开支或成本变化；"
            "它不表示未来流动性事件必然发生，更不是风险发生概率。"
        )
    elif code in {"customer_concentration", "supplier_concentration"} and verification in {
        "needs_review",
        "pending",
    }:
        issues = _verification_issues_zh(risk)
        issue_copy = "；".join(issues) if issues else "报告期、交易对手归并口径和占比仍需逐项对齐"
        boundary = (
            f"当前仍未完全闭合的环节包括：{issue_copy}。在这些环节闭合前，不能判断集中度高低，"
            "也不能把潜在的订单、议价、交付或替代风险写成已经发生的经营影响。"
        )
    elif code == "redemption_rights" and verification in {"needs_review", "pending"}:
        issues = _verification_issues_zh(risk)
        issue_copy = "；".join(issues) if issues else "权利主体、终止时点和恢复条件仍需核对"
        boundary = (
            f"当前仍未完全闭合的环节包括：{issue_copy}。因此只能说明条款可能形成条件性权利，"
            "不能断言权利在上市后仍存续、恢复条件已经触发或公众股东已经受到影响。"
        )
    elif code == "material_litigation_compliance" and verification in {
        "needs_review",
        "pending",
    }:
        issues = _verification_issues_zh(risk)
        issue_copy = "；".join(issues) if issues else "事项身份、状态、整改和重大性仍需核对"
        boundary = (
            f"当前仍未完全闭合的环节包括：{issue_copy}。招股书中的“未受处罚”、管理层重大性判断或"
            "法律顾问风险意见均属于缓释依据，不能单独推出事项已经结束、整改已经完成或不会产生影响。"
        )
    impact = risk_reasoning(code)
    if code == "cash_runway" and calculation_safe and verification == "verified" and isinstance(calculation, Mapping):
        result = _decimal_text(calculation.get("result"), places=2)
        if result:
            level = str(risk.get("level") or "").lower()
            significance = (
                "较短的现金缓冲会提高公司对融资进度、回款改善和支出控制的敏感度。"
                if level in {"critical", "high"}
                else "该结果用于衡量公司对融资进度、回款改善和支出控制的敏感度。"
            )
            impact = (
                f"按本次复算，现有现金约可覆盖 {result} 个月的当前经营净流出。"
                + significance
            )
    elif code in {"customer_concentration", "supplier_concentration"}:
        subject = "客户" if code.startswith("customer") else "供应商"
        impact = (
            f"该事项关系到发行人对少数{subject}的依赖程度。"
            f"在占比尚未完成报告期对齐前，不能断言集中度高低；一旦确认依赖集中，{subject}流失、议价或履约变化才可能形成实质影响。"
        )
    elif code == "redemption_rights" and _has_readable_chinese(
        metadata.get("impact_on_public_shareholders")
    ):
        impact = (
            "结构化条款同时记录了对上市后公众股东影响的候选判断："
            + _compact_ui_fact(
                metadata.get("impact_on_public_shareholders"), limit=260
            ).rstrip("。；")
            + "。该判断仍受权利主体和条款状态验证结果约束。"
        )
    elif code == "material_litigation_compliance":
        _, candidate_impact, _ = _legal_reader_facts(risk)
        if candidate_impact:
            impact = (
                "结构化候选及其原文线索指向的责任范围包括："
                + candidate_impact.rstrip("。；")
                + "。当前仅用于解释潜在影响如何传导，不代表责任或影响已经发生。"
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
        "interpretation": interpretation,
        "impact": impact,
        "boundary": boundary,
        "review_focus": review_focus,
    }


def calculation_summary_zh(risk: Mapping[str, Any]) -> str:
    calculation = risk.get("calculation")
    if not _calculation_is_safe(risk) or not isinstance(calculation, Mapping):
        if isinstance(calculation, Mapping) and str(
            risk.get("verification_status") or ""
        ).lower() != "verified":
            return "上游已形成计算候选，但本风险项尚未通过验证，因此不展示候选结果。"
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
    model_projection = model_channel_projection(payload)
    if observations:
        market_copy = (
            f"市场方面，本次取得 {available_market}/{len(observations)} 项 Market-X 核心观测；"
            "未取得的项目保持缺失，不以 0 或推测值替代。"
        )
    else:
        market_copy = "市场方面，当前没有足够的上市前环境信息，不能据此判断外部环境为低风险。"
    if model_projection.is_available:
        model_copy = (
            "模型方面已形成辅助排序信号，但该信号未经概率校准，不能理解为风险发生概率"
            "或上市后收益预测。"
        )
    elif model_projection.is_error:
        model_copy = (
            "模型通道本次运行异常，当前没有可核验的逐案信号；异常原因保留在后台，"
            "且模型异常不代表低风险。"
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
