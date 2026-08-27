"""Competition-facing Streamlit presentation helpers.

The UI stays presentation-only: every rendered value is either static product copy
or derived from an already-produced result payload. No risk, Evidence, market
observation, model score, or completion claim is created by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Iterable

import streamlit as st


@dataclass(frozen=True)
class FutureModule:
    code: str
    title: str
    purpose: str


FUTURE_MODULES = (
    FutureModule(
        "CH-1",
        "多周期结果验证",
        "在已冻结的 5D 基线之外，补充受治理的 1D / 20D / 60D 上市后结果，用同一口径比较不同时间尺度。",
    ),
    FutureModule(
        "CH-2",
        "Document 风险能力评测",
        "按风险类别评估 Precision / Recall / F1 / Evidence Recall，再针对性改进 Agent 与 Retriever。",
    ),
    FutureModule(
        "CH-3",
        "Market 情绪与新股环境",
        "在严格 PIT 约束下加入 IPO 热度、近期新股表现、流动性及可比市场环境。",
    ),
    FutureModule(
        "CH-4",
        "多 Agent 冲突仲裁",
        "识别跨 Agent / 跨通道冲突，重新核对 Evidence，并保留无法可靠消解的不确定性。",
    ),
    FutureModule(
        "CH-5",
        "Evidence 可视化复核",
        "增加 PDF 页面 / bbox 高亮、证据截图和人工复核记录，让风险结论可以直接回到原文。",
    ),
    FutureModule(
        "CH-6",
        "比赛版最终评估",
        "统一完成指标评估、真实案例矩阵、演示材料与提交版本冻结。",
    ),
)


_CHANNEL_COPY = {
    "document": "招股书风险识别与 Evidence 证据链",
    "market": "上市前 Market-X 与 PIT 市场环境",
    "model": "冻结的逐案例模型结果",
    "rule": "确定性风险优先级信号",
}

_CHANNEL_LABELS = {
    "document": "招股书",
    "market": "Market-X",
    "model": "模型",
    "rule": "规则",
}

_DOMAIN_LABELS = {
    "financial": "财务风险",
    "legal": "法律与合规",
    "business": "业务风险",
}

_RISK_LABELS = {
    "cash_runway": "现金可支撑期",
    "continuous_loss": "持续亏损",
    "revenue_growth": "收入增长",
    "customer_concentration": "客户集中度",
    "supplier_concentration": "供应商集中度",
    "redemption_rights": "特殊股东权利 / 赎回安排",
    "material_litigation_compliance": "重大诉讼与合规",
    "precommercial_product": "产品尚未商业化",
}

_STATUS_LABELS = {
    "available": "可用",
    "partial": "部分可用",
    "pending_gate": "待 Gate",
    "completed": "已完成",
    "completed_with_real_llm": "真实 LLM 完成",
    "completed_with_partial_llm": "部分 LLM 完成",
    "completed_with_deterministic_fallback": "确定性降级完成",
    "degraded": "已降级",
    "verified": "已验证",
    "needs_review": "待复核",
    "pending": "待处理",
    "rejected": "已驳回",
    "failed": "失败",
    "error": "错误",
    "disabled": "未启用",
    "unavailable": "不可用",
    "no_risk_emitted": "未识别到风险",
}

_RISK_LEVEL_LABELS = {
    "critical": "极高",
    "high": "高",
    "medium": "中",
    "low": "低",
}

_STAGE_TITLES = {
    "document_analysis": "招股书分析",
    "document_features": "Document-X 风险特征",
    "market_features": "Market-X 市场特征",
    "prediction": "风险预测",
    "explainability": "Evidence / 可解释性",
    "final_supervisor": "Final Supervisor",
    "final_report": "最终风险报告",
}

_STAGE_SUMMARIES = {
    ("document_analysis", "available"): "v0.3 Document Intelligence 已可用，包括 PDF 解析、检索以及 Financial / Legal / Business Agents。",
    ("document_features", "partial"): "Document-X 特征规范已冻结，但当前 checkout 不包含 PR-A 物化运行生成的逐 IPO 100 维特征文件。",
    ("market_features", "available"): "当前案例已经接入受治理的上市前 Market-X，并按 PIT 口径提供可用市场观测。",
    ("market_features", "partial"): "PR-B Market-X Core 已冻结，但当前运行环境尚未向 Market 通道提供该案例的受治理投影。",
    ("prediction", "available"): "该案例已有冻结模型评分；评分仍是未校准的模型信号，不代表概率。",
    ("prediction", "partial"): "确定性规则评分与 PR-F 整体模型证据可用；逐案例模型评分只有在 hash 绑定的 PR-F runtime handoff 存在时才展示。",
    ("explainability", "available"): "Document Evidence / Calculation 与冻结模型的逐案例解释信息均可用。",
    ("explainability", "partial"): "Evidence 原文、PDF 页码和确定性 Calculation 已可用；逐案例 SHAP 驱动因素仍依赖本地 PR-F runtime handoff。",
    ("final_supervisor", "available"): "Document、Market、Model 与 Rule 通道已进入 Final Supervisor；冲突会被保留并明确展示，而不是被静默抹平。",
    ("final_supervisor", "partial"): "Document Supervisor 可用，但当前配置尚未启用跨通道 Final Supervisor。",
    ("final_report", "partial"): "v0.4 报告链路已可运行；PR-H 仍需完成 3–5 个真实 IPO 的完整 E2E 案例矩阵后才能正式冻结。",
}

_STAGE_LIMITATIONS = {
    "document_features": "当前缺少 PR-A 本地运行产生的逐案例 Document-X 特征文件。这是运行资产缺失，不代表 PR-A Gate 未完成。",
    "market_features": "当前配置没有提供该案例的受治理 Market-X runtime 投影；PR-B 本身并不是阻塞 Gate。",
    "prediction": "当前场景缺少逐案例 PR-F runtime 资产；PR-F 本身已经 COMPLETE / FROZEN，因此不会重新训练或重跑替代。",
    "explainability": "当前 runtime 没有逐案例模型解释文件，因此不展示 SHAP / top drivers；PR-F 本身不是阻塞 Gate。",
    "final_supervisor": "当前所选配置未启用跨通道 Final Supervisor。",
    "final_report": "PR-H 的真实案例 E2E 矩阵与最终 freeze 尚未完成。",
}

_STAGE_UNBLOCKED = {
    "document_features": ("该 IPO 的 100 维 Document-X 特征", "特征与快照的 provenance hash"),
    "market_features": ("带 PIT provenance 的历史新股环境", "逐特征可用状态与缺失原因", "仅在权威来源存在时展示行业 / 成交额特征"),
    "prediction": ("冻结的逐案例模型评分及其 score semantics", "模型版本与冻结结果 identity"),
    "explainability": ("与冻结模型结果绑定的逐 IPO SHAP / top drivers", "冻结资产支持时的 Document 与 Market 贡献信息"),
    "final_report": ("招股书页码 → Evidence → 风险 → Market-X → 模型驱动 → 结论的完整链路", "3–5 个真实 IPO E2E 演示案例", "可复现的运行 provenance 与演示资产"),
}

_REPORT_TITLES = {
    1: "IPO 基本信息",
    2: "系统运行与风险摘要",
    3: "财务风险",
    4: "法律与合规风险",
    5: "业务风险",
    6: "Document Supervisor 汇总",
    7: "市场环境",
    8: "模型信号与不确定性",
    9: "Final Supervisor 综合结论",
    10: "Evidence 索引",
    11: "Calculation 索引",
    12: "待人工复核",
    13: "方法、局限与治理",
}


def status_label(value: object) -> str:
    normalized = str(value or "unavailable").lower()
    return _STATUS_LABELS.get(normalized, str(value or "不可用"))


def risk_level_label(value: object) -> str:
    normalized = str(value or "").lower()
    return _RISK_LEVEL_LABELS.get(normalized, str(value or "不可用"))


def risk_display_name(code: object) -> str:
    text = str(code or "Unavailable")
    return _RISK_LABELS.get(text, text)


def domain_label(domain: object) -> str:
    text = str(domain or "")
    return _DOMAIN_LABELS.get(text, text)


def stage_title_zh(stage: object) -> str:
    stage_id = str(getattr(stage, "stage_id", ""))
    return _STAGE_TITLES.get(stage_id, str(getattr(stage, "title", "阶段")))


def stage_summary_zh(stage: object) -> str:
    stage_id = str(getattr(stage, "stage_id", ""))
    status_obj = getattr(stage, "status", "unavailable")
    status = str(getattr(status_obj, "value", status_obj))
    return _STAGE_SUMMARIES.get((stage_id, status), str(getattr(stage, "summary", "")))


def stage_notice_zh(stage: object) -> str | None:
    status_obj = getattr(stage, "status", "available")
    status = str(getattr(status_obj, "value", status_obj))
    if status == "available":
        return None
    stage_id = str(getattr(stage, "stage_id", ""))
    reason = _STAGE_LIMITATIONS.get(stage_id)
    if not reason:
        return None
    gate = getattr(stage, "blocking_gate", None)
    prefix = f"当前限制 · {gate}" if gate else "当前限制"
    return f"**{prefix}**\n\n{reason}"


def stage_unblocked_items_zh(stage: object) -> tuple[str, ...]:
    return _STAGE_UNBLOCKED.get(str(getattr(stage, "stage_id", "")), ())


def report_section_title(order: object, fallback: object) -> str:
    try:
        key = int(order)
    except (TypeError, ValueError):
        return str(fallback)
    return _REPORT_TITLES.get(key, str(fallback))


def localize_market_observation_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Localize common presentation keys while keeping technical feature names intact."""

    key_map = {
        "feature": "指标",
        "feature_name": "指标",
        "name": "指标",
        "value": "数值",
        "availability": "可用状态",
        "missing_reason": "缺失原因",
        "as_of": "截至时点",
        "as_of_date": "截至日期",
        "source": "来源",
        "window": "统计窗口",
        "unit": "单位",
    }
    output: list[dict[str, object]] = []
    for row in rows:
        localized: dict[str, object] = {}
        for key, value in row.items():
            display_key = key_map.get(str(key), str(key))
            if str(key) == "availability":
                value = status_label(value)
            localized[display_key] = value
        output.append(localized)
    return output


def apply_competition_theme() -> None:
    """Apply an app-like, neutral workspace theme without changing behavior."""

    st.markdown(
        """
        <style>
        .block-container {max-width:1480px;padding-top:1rem;padding-bottom:3.5rem;}
        [data-testid="stAppViewContainer"] {background:radial-gradient(circle at 92% 0%,rgba(37,99,235,.075),transparent 22rem),radial-gradient(circle at 12% 18%,rgba(15,118,110,.055),transparent 26rem);}
        [data-testid="stSidebar"] {border-right:1px solid rgba(128,128,128,.16);background:rgba(128,128,128,.025);}
        [data-testid="stSidebar"] .block-container {padding-top:1rem;}
        div[data-testid="stForm"] {border:1px solid rgba(128,128,128,.18);border-radius:18px;padding:1rem 1.05rem .85rem;background:rgba(128,128,128,.035);box-shadow:0 10px 34px rgba(15,23,42,.035);}
        div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.18);border-radius:16px;padding:.85rem 1rem;background:rgba(128,128,128,.035);min-height:104px;}
        [data-testid="stMetricLabel"] {font-weight:650;letter-spacing:.01em;}
        [data-testid="stMetricValue"] {font-weight:760;}
        div[data-testid="stExpander"] {border:1px solid rgba(128,128,128,.16);border-radius:14px;overflow:hidden;background:rgba(128,128,128,.018);}
        div[data-testid="stDataFrame"] {border:1px solid rgba(128,128,128,.14);border-radius:14px;overflow:hidden;}
        .stTabs [data-baseweb="tab-list"] {gap:.35rem;overflow-x:auto;padding-bottom:.15rem;}
        .stTabs [data-baseweb="tab"] {border-radius:10px;padding:.55rem .9rem;font-weight:620;}
        .stTabs [aria-selected="true"] {background:rgba(37,99,235,.09);}
        .stButton>button,.stDownloadButton>button {border-radius:10px;font-weight:650;}
        .ipo-hero {border:1px solid rgba(128,128,128,.18);border-radius:22px;padding:1.35rem 1.5rem 1.25rem;margin-bottom:.9rem;background:linear-gradient(135deg,rgba(37,99,235,.105),rgba(15,118,110,.055) 58%,rgba(128,128,128,.02));box-shadow:0 18px 50px rgba(15,23,42,.045);}
        .ipo-hero-row {display:flex;align-items:flex-start;justify-content:space-between;gap:1.5rem;flex-wrap:wrap;}
        .ipo-kicker {font-size:.73rem;font-weight:800;letter-spacing:.1em;opacity:.68;}
        .ipo-title {font-size:clamp(1.8rem,3vw,2.65rem);font-weight:790;line-height:1.08;letter-spacing:-.025em;margin:.28rem 0 .48rem;}
        .ipo-subtitle {font-size:.98rem;opacity:.76;max-width:960px;line-height:1.68;}
        .ipo-badge-row {display:flex;gap:.38rem;flex-wrap:wrap;margin-top:.85rem;}
        .ipo-badge,.status-chip,.risk-chip {display:inline-flex;align-items:center;gap:.28rem;border-radius:999px;border:1px solid rgba(128,128,128,.2);padding:.24rem .56rem;font-size:.75rem;font-weight:680;line-height:1.2;background:rgba(128,128,128,.045);}
        .status-good {border-color:rgba(5,150,105,.28);background:rgba(5,150,105,.08);}
        .status-warn {border-color:rgba(217,119,6,.3);background:rgba(217,119,6,.09);}
        .status-bad {border-color:rgba(220,38,38,.28);background:rgba(220,38,38,.08);}
        .status-muted {opacity:.74;}
        .case-shell {display:flex;align-items:flex-end;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:1.2rem 0 .8rem;}
        .case-name {font-size:1.6rem;font-weight:770;letter-spacing:-.015em;line-height:1.15;}
        .case-meta {font-size:.86rem;opacity:.7;margin-top:.28rem;}
        .section-eyebrow {font-size:.72rem;font-weight:800;letter-spacing:.08em;opacity:.62;margin:.15rem 0 .35rem;}
        .channel-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin:.55rem 0 .9rem;}
        .channel-card {border:1px solid rgba(128,128,128,.17);border-radius:15px;padding:.8rem .9rem;background:rgba(128,128,128,.03);min-height:92px;}
        .channel-top {display:flex;align-items:center;justify-content:space-between;gap:.5rem;}
        .channel-name {font-size:.84rem;font-weight:760;}
        .channel-copy {font-size:.76rem;opacity:.64;margin-top:.42rem;line-height:1.38;}
        .pipeline-grid {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:.48rem;margin:.55rem 0 1.05rem;}
        .pipeline-card {border:1px solid rgba(128,128,128,.15);border-radius:12px;padding:.62rem .68rem;background:rgba(128,128,128,.025);min-height:78px;}
        .pipeline-index {font-size:.68rem;opacity:.55;font-weight:760;letter-spacing:.04em;}
        .pipeline-title {font-size:.76rem;font-weight:720;line-height:1.28;margin:.2rem 0 .35rem;}
        .empty-flow {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin:1rem 0 .4rem;}
        .empty-step {border:1px solid rgba(128,128,128,.16);border-radius:15px;padding:.9rem;background:rgba(128,128,128,.025);}
        .empty-step-no {font-size:.7rem;opacity:.55;font-weight:800;}
        .empty-step-title {font-size:.91rem;font-weight:750;margin:.22rem 0;}
        .empty-step-copy {font-size:.77rem;opacity:.68;line-height:1.5;}
        .roadmap-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.72rem;margin:.7rem 0 1rem;}
        .roadmap-card {border:1px solid rgba(128,128,128,.16);border-radius:15px;padding:.9rem;background:rgba(128,128,128,.026);min-height:150px;}
        .roadmap-code {font-size:.72rem;font-weight:800;letter-spacing:.08em;opacity:.58;}
        .roadmap-title {font-size:.95rem;font-weight:760;margin:.28rem 0 .38rem;}
        .roadmap-copy {font-size:.78rem;opacity:.67;line-height:1.5;}
        .roadmap-state {font-size:.68rem;font-weight:760;margin-top:.65rem;opacity:.58;}
        @media(max-width:1050px){.channel-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.pipeline-grid{grid-template-columns:repeat(4,minmax(0,1fr));}.roadmap-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
        @media(max-width:720px){.channel-grid,.pipeline-grid,.empty-flow,.roadmap-grid{grid-template-columns:1fr;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_product_header() -> None:
    st.markdown(
        """
        <div class="ipo-hero"><div class="ipo-hero-row"><div>
          <div class="ipo-kicker">港股 IPO 风险智能分析</div>
          <div class="ipo-title">港股 IPO 风险分析工作台</div>
          <div class="ipo-subtitle">
            围绕招股书风险、Evidence 证据链、确定性 Calculation、上市前 Market-X、模型信号与 Final Supervisor，
            将关键结论、依据和不确定性放在同一工作台中。任何缺失通道都会明确标记，不用模拟结果补位。
          </div>
          <div class="ipo-badge-row">
            <span class="ipo-badge">v0.4 治理版</span>
            <span class="ipo-badge">Evidence 可追溯</span>
            <span class="ipo-badge">审计优先</span>
            <span class="ipo-badge">Fail-closed</span>
          </div>
        </div></div></div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown("<div class='section-eyebrow'>分析流程</div>", unsafe_allow_html=True)
    steps = (
        ("01", "上传招股书", "上传真实招股书，并绑定公司、股票代码和上市日期。"),
        ("02", "识别文档风险", "Financial / Legal / Business Agents 从招股书中提取有 Evidence 支持的风险。"),
        ("03", "接入市场与模型", "在可用时接入受治理的 Market-X、确定性规则信号和冻结模型结果。"),
        ("04", "Final Supervisor 汇总", "综合各通道信息，保留冲突和不确定性，生成可审计的最终报告。"),
    )
    cards = []
    for number, title, copy in steps:
        cards.append(
            "<div class='empty-step'>"
            f"<div class='empty-step-no'>{escape(number)}</div>"
            f"<div class='empty-step-title'>{escape(title)}</div>"
            f"<div class='empty-step-copy'>{escape(copy)}</div>"
            "</div>"
        )
    st.markdown("<div class='empty-flow'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption("完成上方信息并运行分析后进入案例工作区。未运行真实案例前，不展示模拟指标。")


def channel_state_map(payload: dict[str, Any]) -> dict[str, str]:
    final = payload.get("final_supervision") or {}
    states = final.get("channel_states") or []
    return {str(item.get("channel")): str(item.get("status", "unavailable")) for item in states}


def executive_supervisor_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Project the correct competition-level summary without recomputing backend facts.

    ``FinalSupervisionResult.summary`` is the frozen Document Supervisor summary.
    Competition conflicts and the optional LLM judgement are separate governed
    outputs.  Keeping them separate prevents a document-level ``0 unresolved``
    message from being presented as the competition-wide conflict count.
    """

    final = payload.get("final_supervision") or {}
    diagnostics = payload.get("component_diagnostics") or {}
    synthesis = diagnostics.get("final_supervision_llm") or {}
    detected = (diagnostics.get("conflict_detection") or {}).get("conflicts") or []
    conflict_counts: dict[str, int] = {}
    for conflict in detected:
        status = str(conflict.get("status") or "unknown")
        conflict_counts[status] = conflict_counts.get(status, 0) + 1

    llm_judgement = synthesis.get("judgement") if synthesis.get("status") == "available" else None
    if isinstance(llm_judgement, dict):
        body = (
            llm_judgement.get("final_explanation")
            or llm_judgement.get("overall_risk_rationale")
            or final.get("summary")
            or "本次运行未生成综合结论。"
        )
        return {
            "title": "LLM Final Supervisor 综合判断",
            "body": body,
            "mode": "llm",
            "llm_status": "available",
            "llm_reason": synthesis.get("reason") or "",
            "conflict_counts": conflict_counts,
        }

    return {
        "title": "确定性 Document Supervisor 汇总",
        "body": final.get("summary") or "本次运行未生成文档汇总结论。",
        "mode": "deterministic_fallback",
        "llm_status": synthesis.get("status") or "not_configured",
        "llm_reason": synthesis.get("reason") or "",
        "conflict_counts": conflict_counts,
    }


def evidence_reference_count(payload: dict[str, Any]) -> int:
    return sum(len(risk.get("evidence") or []) for risk in payload.get("verified_risks") or [])


def available_market_observation_count(payload: dict[str, Any]) -> tuple[int, int]:
    observations = (payload.get("market_context") or {}).get("observations") or []
    available = sum(1 for item in observations if item.get("availability") == "available")
    return available, len(observations)


def risk_inventory_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for domain in ("financial", "legal", "business"):
        domain_payload = (payload.get("domains") or {}).get(domain) or {}
        for risk in domain_payload.get("risks") or []:
            code = risk.get("risk_code", "Unavailable")
            rows.append(
                {
                    "领域": domain_label(domain),
                    "风险项": risk_display_name(code),
                    "风险代码": code,
                    "等级": risk_level_label(risk.get("level")),
                    "规则评分": risk.get("score", "Unavailable"),
                    "验证状态": status_label(risk.get("verification_status")),
                    "Evidence": len(risk.get("evidence") or []),
                }
            )
    return rows


def domain_summary_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for domain in ("financial", "legal", "business"):
        item = (payload.get("domains") or {}).get(domain) or {}
        counts = item.get("status_counts") or {}
        rows.append(
            {
                "领域": domain_label(domain),
                "风险项": item.get("risk_count", 0),
                "已验证": counts.get("verified", 0),
                "待复核": counts.get("needs_review", 0),
                "状态": status_label(item.get("status", "unavailable")),
            }
        )
    return rows


def _status_tone(status: object) -> str:
    normalized = str(status or "unavailable").lower()
    if normalized in {"available", "completed", "completed_with_real_llm", "verified"}:
        return "status-good"
    if normalized in {
        "partial",
        "completed_with_partial_llm",
        "completed_with_deterministic_fallback",
        "degraded",
        "needs_review",
        "pending",
        "pending_gate",
    }:
        return "status-warn"
    if normalized in {"failed", "rejected", "error"}:
        return "status-bad"
    return "status-muted"


def render_case_header(payload: dict[str, Any]) -> None:
    profile = payload.get("profile") or {}
    company = escape(str(profile.get("company_name") or "不可用"))
    stock_code = escape(str(profile.get("stock_code") or "不可用"))
    listing_date = escape(str(profile.get("listing_date") or "不可用"))
    industry = escape(str(profile.get("industry") or "不可用"))
    raw_status = payload.get("runtime_completion_status") or payload.get("status") or "unavailable"
    st.markdown(
        "<div class='case-shell'><div>"
        f"<div class='case-name'>{company} <span style='opacity:.5;font-weight:620'>· {stock_code}</span></div>"
        f"<div class='case-meta'>上市日期 {listing_date} · {industry}</div>"
        "</div>"
        f"<span class='status-chip {_status_tone(raw_status)}'>{escape(status_label(raw_status))}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_executive_snapshot(payload: dict[str, Any]) -> None:
    prediction = payload.get("prediction") or {}
    counts = payload.get("risk_status_counts") or {}
    states = channel_state_map(payload)
    available_market, total_market = available_market_observation_count(payload)

    st.markdown("<div class='section-eyebrow'>核心结果</div>", unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("规则风险信号", prediction.get("risk_score", "不可用"), risk_level_label(prediction.get("risk_level")))
    cols[1].metric("已验证风险", counts.get("verified", 0))
    cols[2].metric("Evidence 数量", evidence_reference_count(payload))
    cols[3].metric("Market-X 覆盖", f"{available_market}/{total_market}" if total_market else status_label(states.get("market")))
    cols[4].metric("模型通道", status_label(states.get("model")))

    final = payload.get("final_supervision") or {}
    if final:
        view = executive_supervisor_view(payload)
        with st.container(border=True):
            st.markdown(f"**{view['title']}**")
            st.write(view["body"])
            conflict_counts = view["conflict_counts"]
            if conflict_counts:
                st.caption(
                    "Competition Conflict · "
                    f"已解决 {conflict_counts.get('resolved', 0)} · "
                    f"部分解决 {conflict_counts.get('partially_resolved', 0)} · "
                    f"未解决 {conflict_counts.get('unresolved', 0)}"
                )
            if view["mode"] == "deterministic_fallback" and view["llm_status"] == "unavailable":
                st.warning(
                    "LLM Final Supervisor 当前不可用："
                    f"{view['llm_reason'] or '未说明原因'}。"
                    "上方为确定性 Document Supervisor 汇总；Competition Conflict 状态单独列示，不用旧文档摘要替代。"
                )
            uncertainty = final.get("uncertainty_statement")
            if uncertainty:
                st.caption(uncertainty)


def render_channel_grid(payload: dict[str, Any]) -> None:
    states = channel_state_map(payload)
    cards: list[str] = []
    for channel in ("document", "market", "model", "rule"):
        raw_status = states.get(channel, "unavailable")
        cards.append(
            "<div class='channel-card'><div class='channel-top'>"
            f"<div class='channel-name'>{escape(_CHANNEL_LABELS[channel])}</div>"
            f"<span class='status-chip {_status_tone(raw_status)}'>{escape(status_label(raw_status))}</span>"
            "</div>"
            f"<div class='channel-copy'>{escape(_CHANNEL_COPY[channel])}</div>"
            "</div>"
        )
    st.markdown("<div class='channel-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_pipeline_strip(stages: Iterable[object]) -> None:
    cards: list[str] = []
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        ordinal = str(getattr(stage, "ordinal", ""))
        cards.append(
            f"<div class='pipeline-card' title='{escape(stage_summary_zh(stage), quote=True)}'>"
            f"<div class='pipeline-index'>阶段 {escape(ordinal)}</div>"
            f"<div class='pipeline-title'>{escape(stage_title_zh(stage))}</div>"
            f"<span class='status-chip {_status_tone(raw_status)}'>{escape(status_label(raw_status))}</span>"
            "</div>"
        )
    st.markdown("<div class='pipeline-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def roadmap_rows() -> list[dict[str, str]]:
    return [
        {"阶段": item.code, "模块": item.title, "状态": "v0.4.3 后启动", "目标": item.purpose}
        for item in FUTURE_MODULES
    ]


def render_competition_roadmap() -> None:
    st.markdown("### 比赛强化路线")
    st.caption("以下内容是 v0.4.3 之后的正式强化计划。相关实现落地前，这里不会提前展示任何指标或模拟结果。")
    cards: list[str] = []
    for item in FUTURE_MODULES:
        cards.append(
            "<div class='roadmap-card'>"
            f"<div class='roadmap-code'>{escape(item.code)}</div>"
            f"<div class='roadmap-title'>{escape(item.title)}</div>"
            f"<div class='roadmap-copy'>{escape(item.purpose)}</div>"
            "<div class='roadmap-state'>v0.4.3 后启动</div>"
            "</div>"
        )
    st.markdown("<div class='roadmap-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
