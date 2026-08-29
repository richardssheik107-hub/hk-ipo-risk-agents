"""Competition-facing Streamlit presentation helpers.

The UI stays presentation-only: every rendered value is either static product copy
or derived from an already-produced result payload. No risk, Evidence, market
observation, model score, or completion claim is created by this module.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Iterable

import streamlit as st
import streamlit.components.v1 as components


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
    """Apply the presentation-only design system used by the Streamlit workspace."""

    st.markdown(
        """
        <style>
        :root {
          --ipo-background:#F2FBF8; --ipo-surface:#FFFFFF;
          --ipo-primary:#14B8A6; --ipo-secondary:#60D5C8;
          --ipo-lavender:#B8A7FF; --ipo-mist-purple:#D9CCFF;
          --ipo-success:#22C55E; --ipo-warning:#F59E0B; --ipo-danger:#EF4444;
          --ipo-bg:var(--ipo-background); --ipo-surface-alt:rgba(255,255,255,.68);
          --ipo-ink:#163B38; --ipo-muted:#607976; --ipo-line:rgba(20,184,166,.16);
          --ipo-navy:#163B38; --ipo-teal:var(--ipo-primary);
          --ipo-green:var(--ipo-success); --ipo-amber:var(--ipo-warning); --ipo-red:var(--ipo-danger);
          --ipo-radius:14px; --ipo-shadow:0 10px 28px rgba(20,184,166,.08);
          --motion-fast:160ms; --motion-standard:220ms; --motion-enter:420ms;
          --motion-slow:700ms; --motion-hero:1100ms; --ease-product:cubic-bezier(.2,.8,.2,1);
          --ipo-font:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Segoe UI","Helvetica Neue",Arial,sans-serif;
          --streamlit-header-height:3.75rem; --product-nav-height:66px;
          --section-scroll-offset:calc(var(--streamlit-header-height) + var(--product-nav-height) + 20px);
        }
        html,body,[class*="css"],button,input,textarea,select {font-family:var(--ipo-font);color:var(--ipo-ink);}
        [data-testid="stAppViewContainer"],[data-testid="stMain"],.main {background:var(--ipo-bg);}
        [data-testid="stMainBlockContainer"],.block-container {background:transparent;}
        [data-testid="stHeader"] {background:rgba(244,246,248,.92);}
        .block-container {max-width:1540px;padding-top:1.15rem;padding-bottom:4rem;}
        [data-testid="stSidebar"] {border-right:1px solid #d9e0e8;background:#eef2f6;}
        [data-testid="stSidebar"] .block-container {padding-top:1.2rem;padding-left:1.15rem;padding-right:1.15rem;}
        [data-testid="stSidebar"] h3 {color:var(--ipo-navy);font-size:.91rem;letter-spacing:.01em;margin-top:1.2rem;}
        .sidebar-brand {border-bottom:1px solid #d7dee7;padding:.15rem 0 1rem;margin-bottom:.75rem;}
        .sidebar-brand-title {font-weight:780;color:var(--ipo-navy);font-size:.98rem;}
        .sidebar-brand-copy {font-size:.72rem;color:var(--ipo-muted);margin-top:.18rem;letter-spacing:.02em;}
        .sidebar-section-label {font-size:.66rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#728096;margin:.9rem 0 .35rem;}
        .sidebar-config {border:1px solid #dbe2e9;border-radius:8px;background:rgba(255,255,255,.55);padding:.55rem .62rem;font-size:.7rem;color:#536173;line-height:1.42;overflow-wrap:anywhere;word-break:break-word;}
        .sidebar-note {border-left:3px solid #91a4b7;padding:.42rem .62rem;background:rgba(255,255,255,.45);font-size:.74rem;color:#536173;line-height:1.48;}
        div[data-testid="stForm"] {border:1px solid var(--ipo-line);border-radius:var(--ipo-radius);padding:1.1rem 1.2rem 1rem;background:var(--ipo-surface);box-shadow:var(--ipo-shadow);}
        div[data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--ipo-line)!important;border-radius:var(--ipo-radius)!important;background:var(--ipo-surface);box-shadow:0 4px 14px rgba(20,35,55,.035);}
        div[data-testid="stMetric"] {border:1px solid var(--ipo-line);border-radius:var(--ipo-radius);padding:.82rem .95rem;background:var(--ipo-surface);min-height:100px;box-shadow:0 3px 12px rgba(20,35,55,.035);}
        [data-testid="stMetricLabel"] {font-weight:650;color:var(--ipo-muted);font-size:.78rem;}
        [data-testid="stMetricValue"] {font-weight:760;color:var(--ipo-ink);font-size:1.42rem;line-height:1.25;white-space:normal;overflow-wrap:anywhere;}
        div[data-testid="stExpander"] {border:1px solid var(--ipo-line);border-radius:10px;overflow:hidden;background:var(--ipo-surface);}
        div[data-testid="stDataFrame"] {border:1px solid var(--ipo-line);border-radius:10px;overflow:hidden;background:var(--ipo-surface);}
        [data-testid="stAlert"] {border-radius:10px;border-width:1px;}
        hr {border-color:var(--ipo-line)!important;margin:1.4rem 0!important;}
        .stTabs [data-baseweb="tab-list"] {gap:.15rem;overflow-x:auto;padding:.28rem;background:#e9eef3;border:1px solid #dbe2e9;border-radius:10px;}
        .stTabs [data-baseweb="tab"] {border-radius:7px;padding:.56rem .78rem;font-size:.79rem;font-weight:670;color:#536173;white-space:nowrap;}
        .stTabs [aria-selected="true"] {background:var(--ipo-surface);color:var(--ipo-navy);box-shadow:0 1px 4px rgba(20,35,55,.12);}
        .stTabs [data-baseweb="tab-highlight"] {background-color:var(--ipo-teal)!important;}
        .stButton>button,.stDownloadButton>button {border-radius:8px;font-weight:680;min-height:2.55rem;border-color:#cbd5df;}
        .stButton>button[kind="primary"],button[kind^="primary"],[data-testid^="stBaseButton-primary"] {background:var(--ipo-teal)!important;border-color:var(--ipo-teal)!important;color:#fff!important;}
        .stButton>button[kind="primary"]:hover,button[kind^="primary"]:hover,[data-testid^="stBaseButton-primary"]:hover {background:#0b5360!important;border-color:#0b5360!important;}
        .ipo-hero {position:relative;border:1px solid var(--ipo-line);border-radius:14px;padding:1.2rem 1.4rem 1.15rem;margin-bottom:1rem;background:var(--ipo-surface);box-shadow:var(--ipo-shadow);overflow:hidden;}
        .ipo-hero:before {content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--ipo-teal);}
        .ipo-hero-row {display:flex;align-items:flex-start;justify-content:space-between;gap:1.4rem;flex-wrap:wrap;}
        .ipo-kicker {font-size:.68rem;font-weight:800;letter-spacing:.105em;color:var(--ipo-teal);text-transform:uppercase;}
        .ipo-title {font-size:clamp(1.55rem,2.4vw,2.2rem);font-weight:790;line-height:1.13;letter-spacing:-.025em;margin:.3rem 0 .34rem;color:var(--ipo-navy);}
        .ipo-subtitle {font-size:.86rem;color:var(--ipo-muted);max-width:980px;line-height:1.6;}
        .ipo-badge-row {display:flex;gap:.38rem;flex-wrap:wrap;margin-top:.72rem;}
        .ipo-badge,.status-chip,.risk-chip {display:inline-flex;align-items:center;gap:.32rem;border-radius:999px;border:1px solid #d2d9e1;padding:.24rem .58rem;font-size:.71rem;font-weight:700;line-height:1.2;background:#f6f8fa;color:#536173;white-space:normal;}
        .status-chip:before {content:"";width:6px;height:6px;border-radius:50%;background:#98a2b3;flex:0 0 6px;}
        .status-good {border-color:#a9dac4;background:#edf8f2;color:#11633f;}
        .status-good:before {background:var(--ipo-green);}
        .status-warn {border-color:#ecd09d;background:#fff8ea;color:#855006;}
        .status-warn:before {background:var(--ipo-amber);}
        .status-bad {border-color:#efb8bd;background:#fff1f2;color:#98202a;}
        .status-bad:before {background:var(--ipo-red);}
        .status-muted {border-color:#d7dde5;background:#f4f6f8;color:#667085;}
        .case-shell {display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;margin:1.15rem 0 .72rem;padding:1rem 1.15rem;background:var(--ipo-surface);border:1px solid var(--ipo-line);border-radius:var(--ipo-radius);box-shadow:0 4px 14px rgba(20,35,55,.035);}
        .case-name {font-size:1.42rem;font-weight:790;letter-spacing:-.018em;line-height:1.2;color:var(--ipo-navy);}
        .case-code {font-size:.9rem;color:var(--ipo-muted);font-weight:670;margin-left:.3rem;}
        .case-meta {font-size:.78rem;color:var(--ipo-muted);margin-top:.3rem;}
        .section-head {margin:1.18rem 0 .62rem;}
        .section-eyebrow {font-size:.65rem;font-weight:800;letter-spacing:.105em;color:var(--ipo-teal);text-transform:uppercase;margin:0 0 .2rem;}
        .section-title {font-size:1.08rem;font-weight:780;letter-spacing:-.01em;color:var(--ipo-navy);line-height:1.3;}
        .section-copy {font-size:.77rem;color:var(--ipo-muted);line-height:1.52;margin-top:.2rem;max-width:1020px;}
        .metric-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:.65rem;margin:.5rem 0 1rem;}
        .metric-card {min-width:0;border:1px solid var(--ipo-line);border-radius:var(--ipo-radius);padding:.82rem .9rem .76rem;background:var(--ipo-surface);box-shadow:0 3px 12px rgba(20,35,55,.035);}
        .metric-label {font-size:.69rem;font-weight:720;color:var(--ipo-muted);line-height:1.35;}
        .metric-value {font-size:1.32rem;font-weight:790;color:var(--ipo-navy);line-height:1.22;margin:.3rem 0 .18rem;overflow-wrap:anywhere;word-break:break-word;}
        .metric-context {font-size:.68rem;color:#778396;line-height:1.35;overflow-wrap:anywhere;}
        .channel-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin:.5rem 0 1.05rem;}
        .channel-card {position:relative;border:1px solid var(--ipo-line);border-radius:var(--ipo-radius);padding:.82rem .9rem .78rem;background:var(--ipo-surface);min-height:96px;overflow:hidden;}
        .channel-card:before {content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:#aeb8c4;}
        .channel-top {display:flex;align-items:center;justify-content:space-between;gap:.55rem;}
        .channel-name {font-size:.82rem;font-weight:780;color:var(--ipo-navy);}
        .channel-copy {font-size:.72rem;color:var(--ipo-muted);margin-top:.48rem;line-height:1.43;}
        .pipeline-grid {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:.72rem;margin:.6rem 0 1rem;}
        .pipeline-card {position:relative;border:1px solid var(--ipo-line);border-radius:10px;padding:.68rem .68rem .62rem;background:var(--ipo-surface);min-height:94px;}
        .pipeline-card:not(:last-child):after {content:"";position:absolute;top:45%;right:-.73rem;width:.73rem;border-top:1px solid #aeb9c5;}
        .pipeline-index {font-size:.62rem;color:#8490a0;font-weight:800;letter-spacing:.075em;}
        .pipeline-title {font-size:.74rem;font-weight:740;color:var(--ipo-navy);line-height:1.34;margin:.28rem 0 .44rem;overflow-wrap:anywhere;}
        .profile-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:1px;background:var(--ipo-line);border:1px solid var(--ipo-line);border-radius:10px;overflow:hidden;margin:.45rem 0 .95rem;}
        .profile-item {background:var(--ipo-surface);padding:.76rem .85rem;min-width:0;}
        .profile-label {font-size:.65rem;font-weight:720;color:#7a8696;margin-bottom:.24rem;}
        .profile-value {font-size:.82rem;font-weight:680;color:var(--ipo-ink);overflow-wrap:anywhere;}
        .state-panel {border:1px solid var(--ipo-line);border-left:4px solid #98a2b3;border-radius:10px;padding:.78rem .9rem;background:var(--ipo-surface-alt);margin:.45rem 0 .75rem;}
        .state-panel-title {font-size:.82rem;font-weight:760;color:var(--ipo-navy);}
        .state-panel-copy {font-size:.74rem;color:var(--ipo-muted);line-height:1.48;margin-top:.28rem;}
        .trace-list {display:grid;gap:.5rem;margin:.5rem 0 .8rem;}
        .trace-card {display:grid;grid-template-columns:42px minmax(130px,.8fr) minmax(180px,1.4fr) auto;gap:.65rem;align-items:center;border:1px solid var(--ipo-line);border-radius:10px;padding:.66rem .76rem;background:var(--ipo-surface);}
        .trace-index {font-size:.66rem;font-weight:800;color:#7b8797;}
        .trace-agent {font-size:.76rem;font-weight:740;color:var(--ipo-navy);overflow-wrap:anywhere;}
        .trace-action {font-size:.72rem;color:var(--ipo-muted);line-height:1.4;overflow-wrap:anywhere;}
        .empty-flow {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin:.75rem 0 .35rem;}
        .empty-step {border:1px solid var(--ipo-line);border-radius:10px;padding:.82rem .86rem;background:var(--ipo-surface);}
        .empty-step-no {font-size:.63rem;color:#8792a1;font-weight:800;letter-spacing:.08em;}
        .empty-step-title {font-size:.82rem;font-weight:760;color:var(--ipo-navy);margin:.25rem 0;}
        .empty-step-copy {font-size:.72rem;color:var(--ipo-muted);line-height:1.48;}
        .roadmap-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin:.7rem 0 1rem;}
        .roadmap-card {border:1px solid var(--ipo-line);border-radius:10px;padding:.9rem;background:var(--ipo-surface);min-height:150px;}
        .roadmap-code {font-size:.65rem;font-weight:800;letter-spacing:.08em;color:#7d8998;}
        .roadmap-title {font-size:.88rem;font-weight:760;color:var(--ipo-navy);margin:.28rem 0 .38rem;}
        .roadmap-copy {font-size:.73rem;color:var(--ipo-muted);line-height:1.5;}
        .roadmap-state {font-size:.65rem;font-weight:760;margin-top:.65rem;color:#7d8998;}
        /* Round two: structural cockpit layout. */
        header[data-testid="stHeader"] {height:3.75rem;background:rgba(244,247,250,.97);border-bottom:1px solid #dfe6ed;backdrop-filter:blur(8px);}
        [data-testid="stAppViewContainer"]>.main .block-container {padding-top:5rem!important;}
        [data-testid="stSidebar"] .block-container {padding-top:4.65rem!important;}
        .ipo-hero {min-height:168px;display:flex;align-items:center;border:0;border-radius:16px;padding:1.25rem 1.45rem;margin:0 0 1rem;background-color:#122b43;background-image:linear-gradient(115deg,rgba(15,100,113,.42),rgba(18,43,67,.1) 46%),linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:auto,28px 28px,28px 28px;box-shadow:0 16px 34px rgba(20,40,62,.16);}
        .ipo-hero:before {display:none;}
        .ipo-hero-row {width:100%;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(430px,.9fr);align-items:center;gap:1.4rem;}
        .ipo-kicker {color:#8ed3d5;font-size:.64rem;}
        .ipo-title {color:#fff;font-size:clamp(1.55rem,2.2vw,2.05rem);margin:.25rem 0 .32rem;}
        .ipo-subtitle {color:#c9d7e3;line-height:1.48;max-width:720px;}
        .command-health {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.45rem;}
        .health-item {min-width:0;border:1px solid rgba(218,233,242,.18);background:rgba(7,27,44,.34);border-radius:9px;padding:.62rem .68rem;}
        .health-label {font-size:.59rem;color:#9eb2c3;letter-spacing:.065em;text-transform:uppercase;}
        .health-value {display:flex;align-items:center;gap:.36rem;color:#fff;font-size:.72rem;font-weight:720;margin-top:.24rem;overflow-wrap:anywhere;}
        .health-dot,.pipeline-dot {width:7px;height:7px;border-radius:50%;background:#98a2b3;box-shadow:0 0 0 3px rgba(152,162,179,.14);flex:0 0 7px;}
        .tone-good .health-dot,.tone-good .pipeline-dot {background:var(--ipo-green);box-shadow:0 0 0 3px rgba(22,115,75,.15);}
        .tone-warn .health-dot,.tone-warn .pipeline-dot {background:var(--ipo-amber);box-shadow:0 0 0 3px rgba(168,100,8,.15);}
        .tone-bad .health-dot,.tone-bad .pipeline-dot {background:var(--ipo-red);box-shadow:0 0 0 3px rgba(180,35,45,.14);}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"] {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.24rem;padding:.32rem;background:#dfe6ed;border:1px solid #d4dde6;border-radius:13px;box-shadow:inset 0 1px 2px rgba(20,35,55,.04);}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"] {justify-content:center;border-radius:9px;padding:.66rem .55rem;font-size:.76rem;font-weight:710;color:#566577;transition:background-color .18s ease,color .18s ease,box-shadow .18s ease;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"]:hover {background:rgba(255,255,255,.55);color:var(--ipo-navy);}
        .stTabs:has([role="tab"]:nth-child(5)) [aria-selected="true"] {background:linear-gradient(135deg,#18324a,#0f6471)!important;color:#fff!important;box-shadow:0 5px 12px rgba(18,50,74,.2)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-highlight"],.stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-border"],.stTabs:has([role="tab"]:nth-child(5)) .react-aria-SelectionIndicator {display:none!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [role="tablist"] {display:grid!important;grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:.24rem!important;padding:.32rem!important;background:#dfe6ed!important;border:1px solid #d4dde6!important;border-radius:13px!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [role="tab"] {justify-content:center!important;border:0!important;border-radius:9px!important;background:transparent!important;color:#566577!important;transition:background-color .18s ease,color .18s ease,box-shadow .18s ease!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [role="tab"]:before,.stTabs:has([role="tab"]:nth-child(5)) [role="tab"]:after {display:none!important;content:none!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [role="tab"] p {color:inherit!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [role="tab"][aria-selected="true"] {background:linear-gradient(135deg,#18324a,#0f6471)!important;color:#fff!important;box-shadow:0 5px 12px rgba(18,50,74,.2)!important;}
        .section-eyebrow {display:none;}
        .section-head {margin:1.35rem 0 .66rem;padding-left:.72rem;border-left:3px solid #93a5b6;}
        .section-title {font-size:1.06rem;}
        .bento-shell {display:grid;grid-template-columns:minmax(0,1.62fr) minmax(330px,1fr);gap:.75rem;margin:.5rem 0 .75rem;}
        .assessment-panel {position:relative;overflow:hidden;border-radius:14px;padding:1.18rem 1.25rem;background:#17324a;color:#fff;min-height:205px;box-shadow:0 10px 24px rgba(20,48,71,.14);}
        .assessment-panel:after {content:"";position:absolute;width:210px;height:210px;border:48px solid rgba(49,151,153,.12);border-radius:50%;right:-80px;bottom:-115px;}
        .assessment-label {font-size:.66rem;color:#9fc3cf;font-weight:760;letter-spacing:.06em;}
        .assessment-status {font-size:1.46rem;font-weight:790;line-height:1.22;margin:.42rem 0;color:#fff;max-width:80%;}
        .assessment-risk {display:inline-flex;align-items:center;border:1px solid rgba(255,255,255,.2);border-radius:999px;padding:.28rem .62rem;font-size:.7rem;font-weight:740;background:rgba(255,255,255,.08);}
        .assessment-copy {position:relative;z-index:1;color:#cfdae3;font-size:.78rem;line-height:1.55;margin-top:.78rem;max-width:88%;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;}
        .health-panel {border:1px solid var(--ipo-line);border-radius:14px;background:#fff;padding:1rem;}
        .health-panel-title {font-size:.78rem;font-weight:780;color:var(--ipo-navy);margin-bottom:.55rem;}
        .channel-list {display:grid;gap:.18rem;}
        .channel-line {display:grid;grid-template-columns:96px auto;align-items:center;gap:.55rem;padding:.48rem .15rem;border-bottom:1px solid #edf1f4;}
        .channel-line:last-child {border-bottom:0;}
        .channel-line-name {font-size:.72rem;font-weight:710;color:#536173;}
        .channel-line .status-chip {justify-self:end;}
        .bento-kpis {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.58rem;margin:0 0 1rem;}
        .bento-kpi {border-top:3px solid #88a6b3;background:#fff;padding:.72rem .8rem;border-radius:4px 4px 10px 10px;box-shadow:0 4px 12px rgba(20,35,55,.045);min-width:0;}
        .bento-kpi-value {font-size:1.18rem;font-weight:790;color:var(--ipo-navy);overflow-wrap:anywhere;}
        .bento-kpi-label {font-size:.67rem;color:var(--ipo-muted);margin-top:.2rem;}
        .pipeline-grid {position:relative;display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:0;margin:.8rem 0 1rem;padding:.7rem .2rem .2rem;}
        .pipeline-grid:before {content:"";position:absolute;left:7%;right:7%;top:31px;border-top:2px solid #cbd5df;}
        .pipeline-card {position:relative;z-index:1;border:0;border-radius:0;padding:0 .4rem;background:transparent;min-height:108px;text-align:center;}
        .pipeline-card:not(:last-child):after {display:none;}
        .pipeline-node {width:42px;height:42px;margin:0 auto .52rem;display:grid;place-items:center;border-radius:50%;background:#fff;border:2px solid #aeb9c5;box-shadow:0 0 0 5px var(--ipo-bg);font-size:.68rem;font-weight:800;color:#526273;}
        .pipeline-card.tone-good .pipeline-node {border-color:var(--ipo-green);color:var(--ipo-green);}
        .pipeline-card.tone-warn .pipeline-node {border-color:var(--ipo-amber);color:var(--ipo-amber);}
        .pipeline-card.tone-bad .pipeline-node {border-color:var(--ipo-red);color:var(--ipo-red);}
        .pipeline-title {font-size:.69rem;margin:.2rem 0 .35rem;}
        .pipeline-status {display:flex;align-items:center;justify-content:center;gap:.32rem;font-size:.64rem;color:var(--ipo-muted);}
        .trace-flow {display:grid;grid-template-columns:repeat(6,minmax(0,1fr));margin:.5rem 0 1rem;border:1px solid var(--ipo-line);border-radius:13px;background:#fff;overflow:hidden;}
        .trace-flow-step {position:relative;padding:.8rem .65rem;text-align:center;font-size:.72rem;font-weight:720;color:var(--ipo-navy);}
        .trace-flow-step:not(:last-child):after {content:"→";position:absolute;right:-.25rem;color:#78909c;font-weight:800;}
        .trace-card {position:relative;margin-left:18px;border-left:3px solid #8aa5b1;grid-template-columns:42px minmax(130px,.8fr) minmax(180px,1.4fr) auto;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;}
        .trace-card:before {content:"";position:absolute;width:10px;height:10px;border-radius:50%;background:#5f8795;left:-25px;top:50%;transform:translateY(-50%);box-shadow:0 0 0 5px var(--ipo-bg);}
        .trace-card:hover {transform:translateY(-1px);border-color:#b8c8d4;box-shadow:0 7px 16px rgba(20,35,55,.07);}
        .intelligence-panel {border-top:4px solid #4c7184;background:#fff;border-radius:4px 4px 12px 12px;padding:.2rem .9rem .9rem;min-height:220px;}
        .audit-split {display:grid;grid-template-columns:minmax(330px,.85fr) minmax(0,1.35fr);gap:1rem;align-items:start;}
        @keyframes product-enter {from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        @keyframes workflow-line {from{transform:scaleX(0)}to{transform:scaleX(1)}}
        @keyframes ambient-drift {0%,100%{transform:translate3d(0,0,0)}50%{transform:translate3d(-8px,6px,0)}}
        @keyframes indeterminate-bar {0%{transform:translateX(-115%) scaleX(.34)}55%{transform:translateX(65%) scaleX(.52)}100%{transform:translateX(220%) scaleX(.28)}}
        @keyframes status-enter {from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}
        .landing-hero {position:relative;isolation:isolate;padding:.65rem 0 1.65rem;margin:0 0 .6rem;border-bottom:1px solid #d8e0e7;}
        .landing-hero:after {content:"";position:absolute;z-index:-1;width:420px;height:300px;right:-60px;top:-105px;background:radial-gradient(circle,rgba(15,100,113,.055),rgba(15,100,113,0) 69%);pointer-events:none;animation:ambient-drift 15s var(--ease-product) infinite;}
        .landing-product {font-size:.72rem;font-weight:720;color:var(--ipo-teal);letter-spacing:.035em;margin-bottom:1.15rem;}
        .landing-title {font-size:clamp(2.15rem,4vw,2.9rem);font-weight:760;line-height:1.08;letter-spacing:-.035em;color:#172b3d;margin:0;}
        .landing-subtitle {max-width:760px;font-size:1rem;line-height:1.65;color:#647281;margin:.72rem 0 1.35rem;}
        .landing-runtime {display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;font-size:.73rem;color:#687887;}
        .landing-runtime span {display:inline-flex;align-items:center;gap:.34rem;}
        .landing-runtime span:not(:last-child):after {content:"";width:1px;height:12px;background:#c9d2da;margin-left:.42rem;}
        .landing-runtime-dot {width:6px;height:6px;border-radius:50%;background:#91a0ac;}
        .landing-runtime-dot.ready {background:var(--ipo-teal);}
        .motion-enter {opacity:0;animation:product-enter var(--motion-enter) var(--ease-product) forwards;}
        .motion-title {animation-delay:40ms;}.motion-subtitle{animation-delay:100ms}.motion-runtime{animation-delay:160ms}
        .landing-intake-label {font-size:.72rem;font-weight:760;color:var(--ipo-teal);margin-bottom:.3rem;}
        .landing-intake-title {font-size:1.5rem;font-weight:750;letter-spacing:-.02em;color:#1c3042;margin:0 0 .3rem;}
        .landing-intake-copy {font-size:.82rem;color:#74808d;line-height:1.5;margin-bottom:.65rem;}
        div[data-testid="stForm"]:has(.landing-intake-title) {box-shadow:none;}
        div[data-testid="stForm"]:has(.landing-intake-title) {opacity:0;animation:product-enter var(--motion-enter) var(--ease-product) 220ms forwards;}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] {display:flex;justify-content:flex-end;margin-top:.6rem;}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button {width:168px;min-height:46px;transition:transform var(--motion-standard) var(--ease-product),box-shadow var(--motion-standard) var(--ease-product),background-color var(--motion-standard) var(--ease-product);}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button:hover {transform:translateY(-1px);box-shadow:0 7px 16px rgba(15,100,113,.15);}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button:active {transform:scale(.985);}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button p {display:flex;align-items:center;gap:.3rem;}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button p::after {content:"→";transition:transform var(--motion-standard) var(--ease-product);}
        div[data-testid="stForm"]:has(.landing-intake-title) div[data-testid="stFormSubmitButton"] button:hover p::after {transform:translateX(3px);}
        div[data-testid="stForm"]:has(.landing-intake-title) [data-testid="stFileUploaderDropzone"] {min-height:172px;border:1px dashed #aebbc6!important;background:#f7f9fa!important;display:flex;align-items:center;transition:border-color var(--motion-standard) var(--ease-product),background-color var(--motion-standard) var(--ease-product);}
        div[data-testid="stForm"]:has(.landing-intake-title) [data-testid="stFileUploaderDropzone"]:hover {border-color:#5d969c!important;background:#f1f7f7!important;}
        div[data-testid="stForm"]:has(.landing-intake-title) [data-testid="stFileUploaderDropzone"] svg {transition:transform var(--motion-standard) var(--ease-product),color var(--motion-standard) var(--ease-product);}
        div[data-testid="stForm"]:has(.landing-intake-title) [data-testid="stFileUploaderDropzone"]:hover svg {transform:translateY(-2px);color:var(--ipo-teal);}
        [data-testid="stFileUploaderFile"] {border:1px solid #b9d9cc;border-radius:9px;background:#f2f9f5;animation:status-enter var(--motion-enter) var(--ease-product) both;}
        [data-testid="stFileUploaderFile"]:after {content:"Ready";margin-left:auto;color:var(--ipo-green);font-size:.68rem;font-weight:760;}
        .stTextInput [data-baseweb="input"],.stDateInput [data-baseweb="input"],.stTextInput input,.stDateInput input {transition:border-color 170ms var(--ease-product),box-shadow 170ms var(--ease-product),background-color 170ms var(--ease-product);}
        .stTextInput [data-baseweb="input"]:hover,.stDateInput [data-baseweb="input"]:hover {border-color:#91a8b2;}
        .stTextInput [data-baseweb="input"]:focus-within,.stDateInput [data-baseweb="input"]:focus-within {border-color:#4f8e94!important;box-shadow:0 0 0 3px rgba(15,100,113,.11)!important;}
        .editorial-stepper {position:relative;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2rem;margin:1.1rem 0 .45rem;padding-top:.35rem;opacity:0;animation:product-enter var(--motion-enter) var(--ease-product) 300ms forwards;}
        .editorial-stepper:before {content:"";position:absolute;left:0;right:0;top:2.75rem;border-top:1px solid #bdc8d1;transform-origin:left center;animation:workflow-line var(--motion-slow) var(--ease-product) 420ms both;}
        .editorial-step {position:relative;min-width:0;padding-bottom:.7rem;transition:transform var(--motion-standard) var(--ease-product);}
        .editorial-step-no {position:relative;z-index:1;display:inline-block;background:var(--ipo-bg);padding-right:.7rem;font-size:1.65rem;font-weight:640;letter-spacing:-.035em;color:#84929e;opacity:0;animation:product-enter var(--motion-enter) var(--ease-product) forwards;transition:color var(--motion-standard) var(--ease-product);}
        .editorial-step:nth-child(1) .editorial-step-no{animation-delay:420ms}.editorial-step:nth-child(2) .editorial-step-no{animation-delay:480ms}.editorial-step:nth-child(3) .editorial-step-no{animation-delay:540ms}.editorial-step:nth-child(4) .editorial-step-no{animation-delay:600ms}
        .editorial-step-title {font-size:.9rem;font-weight:750;color:#203548;margin:1rem 0 .2rem;transition:color var(--motion-standard) var(--ease-product);}
        .editorial-step-copy {font-size:.72rem;line-height:1.48;color:#798591;max-width:210px;}
        .editorial-step:hover {transform:translateY(-2px);}
        .editorial-step:hover .editorial-step-no {color:var(--ipo-teal);}
        .editorial-step:hover .editorial-step-title {color:#102638;}
        .analysis-activity {border:1px solid #cbd9df;border-radius:10px;background:#f7fafb;padding:.75rem .85rem;margin:.55rem 0;}
        .analysis-activity-copy {display:flex;align-items:center;gap:.5rem;font-size:.76rem;font-weight:700;color:#294252;}
        .analysis-activity-copy:before {content:"";width:7px;height:7px;border-radius:50%;background:var(--ipo-teal);animation:status-enter 900ms var(--ease-product) infinite alternate;}
        .analysis-activity-track {height:3px;background:#dfe8eb;border-radius:999px;overflow:hidden;margin-top:.62rem;}
        .analysis-activity-bar {height:100%;width:46%;background:#2b7a82;border-radius:999px;animation:indeterminate-bar 1.35s var(--ease-product) infinite;transform-origin:center;}
        .case-shell.result-enter {animation:product-enter var(--motion-enter) var(--ease-product) 40ms both;}
        .bento-shell.result-enter {animation:product-enter var(--motion-enter) var(--ease-product) 100ms both;}
        .stTabs:has([role="tab"]:nth-child(5)) {animation:product-enter var(--motion-enter) var(--ease-product) 180ms both;}
        .status-chip {animation:status-enter var(--motion-standard) var(--ease-product) both;}
        html {scroll-behavior:smooth;scroll-padding-top:var(--section-scroll-offset);}
        div[data-testid="stElementContainer"]:has(.product-nav) {position:sticky;top:var(--streamlit-header-height);z-index:990;margin-bottom:.8rem;}
        .product-nav {height:var(--product-nav-height);display:flex;align-items:center;justify-content:space-between;gap:1.5rem;padding:0 1.15rem;background:rgba(255,255,255,.94);border:0;border-bottom:1px solid #dce3e8;border-radius:3px;backdrop-filter:blur(12px);box-shadow:none;transition:box-shadow var(--motion-standard) var(--ease-product),border-color var(--motion-standard) var(--ease-product);}
        .product-nav.nav-scrolled {border-bottom-color:#ccd7df;box-shadow:0 5px 14px rgba(26,44,60,.055);}
        .product-nav-brand {display:flex;align-items:center;text-decoration:none!important;white-space:nowrap;transition:opacity var(--motion-fast) var(--ease-product),transform var(--motion-fast) var(--ease-product);}
        .product-nav-brand:hover {opacity:.88;transform:translateY(-1px);}
        .product-nav-logo {display:block;height:34px;width:auto;max-width:190px;object-fit:contain;object-position:left center;}
        .product-nav-links {display:flex;align-items:stretch;gap:30px;height:100%;overflow-x:auto;scrollbar-width:none;}
        .product-nav-links::-webkit-scrollbar {display:none;}
        .product-nav-links a {position:relative;display:flex;align-items:center;font-size:.86rem;font-weight:610;color:#71808d;text-decoration:none!important;white-space:nowrap;transition:color var(--motion-standard) var(--ease-product);}
        .product-nav-links a:hover {color:#203a4d;}
        .product-nav-links a:after {content:"";position:absolute;left:8%;right:8%;bottom:0;height:4px;border-radius:999px;background:#16a6a1;transform:scaleX(0);transform-origin:left center;transition:transform var(--motion-standard) var(--ease-product);}
        .product-nav-links a.nav-active {color:#0f6471;font-weight:650;}
        .product-nav-links a.nav-active:after {transform:scaleX(1);}
        .st-key-case_workspace_shell {margin-top:1.35rem;padding:22px 24px 26px;background:rgba(255,255,255,.62);border:1px solid rgba(255,255,255,.82);border-radius:24px;box-shadow:0 10px 28px rgba(45,70,95,.07);}
        .result-breadcrumb {display:flex;align-items:center;gap:.62rem;min-width:0;margin:0 0 16px;font-size:13px;line-height:1.5;color:#81909d;}
        .result-breadcrumb a {color:#687b8b;text-decoration:none;transition:color var(--motion-fast) ease;}
        .result-breadcrumb a:hover {color:#183047;}
        .result-breadcrumb-separator {color:#a8b2bb;}
        .result-breadcrumb-current {min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:650;color:#304b5e;}
        .stTabs:has([role="tab"]:nth-child(5)) {margin-top:0;padding:0;background:transparent;border:0;border-radius:0;box-shadow:none;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"],.stTabs:has([role="tab"]:nth-child(5)) [role="tablist"] {gap:clamp(1rem,2.8vw,2.4rem);padding:6px;background:rgba(218,228,237,.72);border:0;border-radius:16px;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"],.stTabs:has([role="tab"]:nth-child(5)) [role="tab"] {min-width:0;padding:.72rem .05rem .68rem;border-radius:0;background:transparent;color:#71808d;font-size:.8rem;font-weight:650;}
        .stTabs:has([role="tab"]:nth-child(5)) [aria-selected="true"] {background:transparent;color:#183047;box-shadow:none;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-highlight"] {height:3px;background:#16a6a1!important;border-radius:3px 3px 0 0;}
        .st-key-risk_command_shell,.st-key-evidence_section_shell,.st-key-market_model_section_shell,.st-key-agent_trace_section_shell,.st-key-review_report_section_shell {margin-top:24px;padding:clamp(1.35rem,2.2vw,2rem);background:rgba(255,255,255,.58);border:1px solid rgba(255,255,255,.72);border-radius:28px;box-shadow:0 10px 30px rgba(45,70,95,.08);overflow:hidden;}
        .st-key-risk_command_shell div[data-testid="stVerticalBlockBorderWrapper"],.st-key-evidence_section_shell div[data-testid="stVerticalBlockBorderWrapper"],.st-key-market_model_section_shell div[data-testid="stVerticalBlockBorderWrapper"],.st-key-agent_trace_section_shell div[data-testid="stVerticalBlockBorderWrapper"],.st-key-review_report_section_shell div[data-testid="stVerticalBlockBorderWrapper"] {background:#fff;border:1px solid rgba(120,140,160,.16)!important;box-shadow:0 4px 14px rgba(45,70,95,.05)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) .channel-card,.stTabs:has([role="tab"]:nth-child(5)) .metric-card,.stTabs:has([role="tab"]:nth-child(5)) .profile-item {background:#fff;border-color:rgba(120,140,160,.16);box-shadow:0 4px 14px rgba(45,70,95,.05);}
        .landing-hero-v3 {position:relative;isolation:isolate;min-height:410px;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(420px,.9fr);align-items:center;gap:1.5rem;overflow:hidden;padding:2.25rem 2.45rem;border-radius:18px;background:radial-gradient(70% 100% at 84% 8%,rgba(38,210,202,.38) 0%,rgba(24,154,169,.2) 34%,rgba(13,101,137,.08) 54%,transparent 70%),radial-gradient(55% 80% at 68% 100%,rgba(31,132,174,.24) 0%,transparent 68%),linear-gradient(112deg,#032448 0%,#053b67 34%,#075b79 66%,#0b737b 100%);box-shadow:0 22px 44px rgba(17,45,65,.18);}
        .hero-static-bg,.hero-reading-overlay {position:absolute;inset:0;pointer-events:none;}
        .hero-static-bg {z-index:0;background-image:radial-gradient(70% 100% at 84% 8%,rgba(38,210,202,.38) 0%,rgba(24,154,169,.2) 34%,rgba(13,101,137,.08) 54%,transparent 70%),radial-gradient(55% 80% at 68% 100%,rgba(31,132,174,.24) 0%,transparent 68%),linear-gradient(112deg,#032448 0%,#053b67 34%,#075b79 66%,#0b737b 100%);background-size:cover;background-position:center right;background-repeat:no-repeat;}
        .hero-reading-overlay {z-index:3;background:linear-gradient(90deg,rgba(10,39,57,.94) 0%,rgba(10,39,57,.82) 34%,rgba(10,39,57,.56) 57%,rgba(10,39,57,.24) 100%);}
        .hero-v3-copy {position:relative;z-index:4;max-width:680px;}
        .hero-v3-label {font-size:.72rem;font-weight:550;letter-spacing:.045em;color:#8fd0d0;margin-bottom:1rem;}
        .hero-v3-title {font-size:clamp(2.35rem,4.4vw,3.65rem);line-height:1.15;letter-spacing:-.018em;font-weight:680;color:#fff!important;margin:0;}
        .hero-v3-subtitle {font-size:1.06rem;line-height:1.72;font-weight:400;color:#d4e1e8;max-width:620px;margin:1rem 0 .48rem;}
        .hero-v3-detail {font-size:.84rem;line-height:1.65;font-weight:400;color:#a9bdca;max-width:620px;}
        .hero-v3-actions {display:flex;align-items:center;gap:1rem;margin-top:1.35rem;}
        .hero-v3-cta {display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 1.05rem;border-radius:8px;background:#fff;color:#14354a!important;font-size:.78rem;font-weight:780;text-decoration:none!important;box-shadow:0 8px 20px rgba(4,24,38,.18);transition:transform var(--motion-standard) var(--ease-product),box-shadow var(--motion-standard) var(--ease-product);}
        .hero-v3-cta:hover {transform:translateY(-1px);box-shadow:0 11px 24px rgba(4,24,38,.24);}
        .hero-v3-meta {display:flex;align-items:center;gap:.8rem;flex-wrap:wrap;margin-top:1.25rem;color:#a9bfcc;font-size:.69rem;}
        .hero-v3-meta span {display:inline-flex;align-items:center;gap:.36rem;}
        .hero-v3-meta i {width:5px;height:5px;border-radius:50%;background:#76b9b6;}
        .risk-flow-visual {position:relative;z-index:4;min-width:0;width:100%;contain:layout paint;isolation:isolate;}
        .risk-flow-visual:before {content:"";position:absolute;inset:7% 1% 2%;border-radius:50%;background:radial-gradient(circle,rgba(31,190,187,.15) 0%,rgba(31,190,187,.055) 38%,transparent 70%);opacity:.7;pointer-events:none;}
        .risk-flow-visual svg {position:relative;display:block;width:100%;height:auto;max-height:386px;margin:0;overflow:hidden;}
        .risk-flow-visual text {font-family:var(--ipo-font);}
        .hero-canvas-bg {opacity:1;}
        .hero-prospectus,.hero-evidence,.hero-market,.hero-rule,.hero-risk,.hero-final {opacity:.96;transform-box:fill-box;transform-origin:center;will-change:transform,opacity;animation:hero-focus-cycle 12s cubic-bezier(.2,.8,.2,1) var(--focus-delay) infinite;}
        .hero-prospectus {--focus-delay:.8s;}
        .hero-evidence {--focus-delay:2.65s;}
        .hero-market {--focus-delay:4.5s;}
        .hero-rule {--focus-delay:6.35s;}
        .hero-risk {--focus-delay:8.2s;}
        .hero-final {--focus-delay:10.05s;animation-name:hero-final-focus-cycle;}
        .hero-evidence-sweep {transform-box:fill-box;transform-origin:left center;}
        .hero-connector {opacity:.32;will-change:opacity;animation:hero-connector-focus 12s ease-in-out var(--connector-delay) infinite;}
        .hero-connector-evidence {--connector-delay:2.65s;}
        .hero-connector-market {--connector-delay:4.5s;}
        .hero-connector-final {--connector-delay:10.05s;}
        .hero-market-line {opacity:.72;}
        .hero-audit-mark {opacity:1;}
        @keyframes hero-focus-cycle {0%,18%,100%{opacity:.96;transform:translate3d(0,0,0) scale(1)}4%,12%{opacity:1;transform:translate3d(0,-3px,0) scale(1.04)}}
        @keyframes hero-final-focus-cycle {0%,19%,100%{opacity:.96;transform:translate3d(0,0,0) scale(1)}4%,13%{opacity:1;transform:translate3d(0,-3px,0) scale(1.05)}}
        @keyframes hero-connector-focus {0%,18%,100%{opacity:.32}4%,12%{opacity:.72}}
        .product-nav,.landing-hero-v3,.landing-section-head,.capability-stack,.product-footer,.ipo-hero,.case-shell {font-family:var(--ipo-font);}
        .product-nav-links a {font-weight:550;letter-spacing:0;}
        .landing-section-title {font-weight:630;letter-spacing:-.018em;}
        .landing-section-copy,.capability-text,.footer-brand-copy {font-weight:400;line-height:1.72;}
        .capability-title {font-weight:620;letter-spacing:-.015em;}
        .sidebar-section-label,.section-eyebrow,.ipo-kicker {font-weight:600;letter-spacing:.055em;}
        .landing-section-anchor {scroll-margin-top:var(--section-scroll-offset);}
        .landing-section-head {display:grid;grid-template-columns:minmax(0,.42fr) minmax(0,.58fr);gap:2rem;align-items:end;margin:4.3rem 0 1.25rem;padding-top:.3rem;border-top:1px solid #dce3e8;}
        .landing-section-index {font-size:.67rem;font-weight:780;letter-spacing:.075em;color:#148081;padding-top:1.2rem;}
        .landing-section-title {font-size:clamp(1.65rem,2.5vw,2.25rem);font-weight:760;letter-spacing:-.03em;color:#172c3e;margin:.9rem 0 .3rem;}
        .landing-section-copy {font-size:.84rem;color:#71808c;line-height:1.6;max-width:650px;}
        .capability-stack {display:grid;gap:0;margin:.4rem 0 1rem;}
        .capability-band {display:grid;grid-template-columns:minmax(0,1fr) minmax(360px,.92fr);gap:4rem;align-items:center;padding:3.2rem 0;border-top:1px solid #dce3e8;}
        .capability-band.reverse .capability-copy {order:2}.capability-band.reverse .capability-visual {order:1}
        .capability-no {font-size:.67rem;font-weight:780;color:#148081;letter-spacing:.07em;}
        .capability-title {font-size:1.55rem;font-weight:750;letter-spacing:-.025em;color:#193044;margin:.55rem 0 .58rem;}
        .capability-text {font-size:.82rem;line-height:1.65;color:#6e7c89;max-width:590px;}
        .capability-list {display:grid;gap:.55rem;margin-top:1.15rem;}
        .capability-list div {display:flex;align-items:center;gap:.55rem;font-size:.75rem;font-weight:680;color:#42586a;}
        .capability-list div:before {content:"";width:17px;border-top:1px solid #5f969b;}
        .capability-visual {width:100%;max-width:640px;min-width:0;justify-self:center;margin:0;background:transparent;}
        .capability-image-frame {width:100%;overflow:hidden;border:1px solid rgba(38,65,82,.13);border-radius:22px;background:#eef2f5;box-shadow:0 10px 26px rgba(25,48,68,.065);transition:transform 220ms var(--ease-product),box-shadow 220ms var(--ease-product);}
        .capability-image-frame:hover {transform:translateY(-3px) scale(1.008);box-shadow:0 13px 29px rgba(25,48,68,.075);}
        .capability-image {display:block;width:100%;height:auto;max-width:100%;object-fit:contain;}
        .capability-caption {margin-top:8px;font-size:12px;line-height:1.45;color:#85909b;text-align:center;}
        .product-footer {margin:3.8rem -1rem -4rem;padding:56px 1rem 28px;background:#e9edf1;border-top:1px solid #d5dce3;color:#667789;}
        .product-footer-grid {display:grid;grid-template-columns:minmax(0,1.16fr) minmax(150px,.6fr) minmax(260px,1fr);gap:clamp(2rem,4vw,4.5rem);align-items:start;}
        .footer-brand-logo {display:block;width:auto;height:36px;max-width:210px;object-fit:contain;}
        .footer-brand-copy {max-width:410px;margin-top:1rem;font-size:14px;line-height:1.6;color:#667789;}
        .footer-column-title {margin:0 0 .9rem;font-size:13px;font-weight:650;line-height:1.4;color:#20384d;}
        .footer-product-links {display:grid;justify-items:start;gap:11px;}
        .footer-product-link {font-size:13px;line-height:1.45;color:#748291;text-decoration:none;transition:color var(--motion-fast) ease;}
        .footer-product-link:hover {color:#183047;}
        .footer-status-list {display:grid;gap:0;margin:0;}
        .footer-status-row {display:grid;grid-template-columns:minmax(86px,.48fr) minmax(0,1fr);align-items:center;min-height:30px;gap:.75rem;}
        .footer-status-row dt,.footer-status-row dd {margin:0;min-width:0;}
        .footer-status-label {display:flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;color:#526273;}
        .footer-status-value {font-size:12.5px;line-height:1.45;color:#8a96a3;overflow-wrap:anywhere;}
        .footer-status-dot {width:6px;height:6px;flex:0 0 6px;border-radius:50%;background:#98a4af;}
        .footer-lower {display:flex;align-items:flex-end;justify-content:space-between;gap:2rem;margin-top:40px;padding-top:22px;border-top:1px solid rgba(82,98,115,.18);}
        .footer-disclaimer {max-width:760px;font-size:12px;line-height:1.6;color:#8a96a3;}
        .footer-meta {flex:0 0 auto;font-size:11.5px;line-height:1.5;color:#9aa4ae;white-space:nowrap;}
        body.ipo-scrollspy-ready .section-reveal .landing-section-title,body.ipo-scrollspy-ready .section-reveal .landing-section-copy {opacity:0;transform:translateY(14px);transition:opacity 480ms var(--ease-product),transform 480ms var(--ease-product);}
        body.ipo-scrollspy-ready .section-reveal .landing-section-copy {transition-delay:60ms;}
        .section-reveal .landing-section-title:after {content:"";display:block;width:48px;height:3px;border-radius:999px;background:#16a6a1;margin-top:.62rem;transform:scaleX(0);transform-origin:left center;transition:transform 500ms var(--ease-product) 70ms;}
        body.ipo-scrollspy-ready .section-reveal.section-visible .landing-section-title,body.ipo-scrollspy-ready .section-reveal.section-visible .landing-section-copy {opacity:1;transform:translateY(0);}
        body.ipo-scrollspy-ready .section-reveal.section-visible .landing-section-title:after {transform:scaleX(1);}
        body.ipo-scrollspy-ready .scroll-content-target {opacity:0;transform:translateY(10px);transition:opacity 440ms var(--ease-product) 120ms,transform 440ms var(--ease-product) 120ms;}
        body.ipo-scrollspy-ready .scroll-content-target.content-visible {opacity:1;transform:translateY(0);}
        body.ipo-scrollspy-ready .capability-band.scroll-content-target {opacity:1;transform:none;transition:none;}
        body.ipo-scrollspy-ready .capability-band.scroll-content-target .capability-copy {opacity:0;transform:translateY(10px);transition:opacity 480ms var(--ease-product),transform 480ms var(--ease-product);}
        body.ipo-scrollspy-ready .capability-band.scroll-content-target .capability-visual {opacity:0;transform:translateY(14px) scale(.985);transition:opacity 520ms var(--ease-product) 80ms,transform 520ms var(--ease-product) 80ms;}
        body.ipo-scrollspy-ready .capability-band.scroll-content-target.content-visible .capability-copy,body.ipo-scrollspy-ready .capability-band.scroll-content-target.content-visible .capability-visual {opacity:1;transform:translateY(0) scale(1);}
        body.ipo-scrollspy-ready .product-footer.scroll-content-target {opacity:0;transform:translateY(8px);transition:opacity 380ms var(--ease-product),transform 380ms var(--ease-product);}
        body.ipo-scrollspy-ready .product-footer.scroll-content-target.content-visible {opacity:1;transform:translateY(0);}
        div[data-testid="stForm"]:has(.landing-intake-title),.editorial-stepper {animation:none;opacity:1;}
        /* Unified nine-colour product theme. */
        [data-testid="stHeader"],header[data-testid="stHeader"] {background:rgba(242,251,248,.92);border-bottom-color:rgba(20,184,166,.14);}
        [data-testid="stSidebar"] {background:color-mix(in srgb,var(--ipo-background) 82%,var(--ipo-secondary));border-right-color:rgba(20,184,166,.16);}
        .sidebar-brand {border-bottom-color:rgba(20,184,166,.16);}
        .sidebar-section-label {color:var(--ipo-primary);}
        .sidebar-config {border-color:rgba(20,184,166,.18);background:rgba(255,255,255,.72);color:var(--ipo-muted);}
        .sidebar-note {border-left-color:var(--ipo-lavender);background:rgba(255,255,255,.58);color:var(--ipo-muted);}
        div[data-testid="stForm"],div[data-testid="stVerticalBlockBorderWrapper"],div[data-testid="stMetric"],div[data-testid="stExpander"],div[data-testid="stDataFrame"],.metric-card,.channel-card,.profile-item,.empty-step,.roadmap-card,.health-panel,.trace-flow,.intelligence-panel {background:var(--ipo-surface);border-color:var(--ipo-line)!important;box-shadow:var(--ipo-shadow);}
        .stButton>button,.stDownloadButton>button {border-color:rgba(20,184,166,.28);background:var(--ipo-surface);color:var(--ipo-navy);}
        .stButton>button:hover,.stDownloadButton>button:hover {border-color:var(--ipo-secondary);color:var(--ipo-primary);}
        .stButton>button[kind="primary"],button[kind^="primary"],[data-testid^="stBaseButton-primary"] {background:var(--ipo-primary)!important;border-color:var(--ipo-primary)!important;color:#fff!important;box-shadow:0 8px 20px rgba(20,184,166,.2);}
        .stButton>button[kind="primary"]:hover,button[kind^="primary"]:hover,[data-testid^="stBaseButton-primary"]:hover {background:color-mix(in srgb,var(--ipo-primary) 86%,#163B38)!important;border-color:color-mix(in srgb,var(--ipo-primary) 86%,#163B38)!important;}
        .stTabs [data-baseweb="tab-list"] {background:color-mix(in srgb,var(--ipo-mist-purple) 36%,var(--ipo-surface));border-color:color-mix(in srgb,var(--ipo-lavender) 35%,transparent);}
        .stTabs [aria-selected="true"] {background:var(--ipo-surface);color:var(--ipo-primary);box-shadow:0 4px 12px rgba(184,167,255,.18);}
        .stTabs [data-baseweb="tab-highlight"] {background:var(--ipo-primary)!important;}
        .status-good {border-color:var(--ipo-success);background:color-mix(in srgb,var(--ipo-success) 10%,white);color:color-mix(in srgb,var(--ipo-success) 62%,#163B38);}
        .status-warn {border-color:var(--ipo-warning);background:color-mix(in srgb,var(--ipo-warning) 10%,white);color:color-mix(in srgb,var(--ipo-warning) 64%,#163B38);}
        .status-bad {border-color:var(--ipo-danger);background:color-mix(in srgb,var(--ipo-danger) 9%,white);color:color-mix(in srgb,var(--ipo-danger) 68%,#163B38);}
        .status-good:before,.tone-good .health-dot,.tone-good .pipeline-dot {background:var(--ipo-success);}
        .status-warn:before,.tone-warn .health-dot,.tone-warn .pipeline-dot {background:var(--ipo-warning);}
        .status-bad:before,.tone-bad .health-dot,.tone-bad .pipeline-dot {background:var(--ipo-danger);}
        .section-head {border-left-color:var(--ipo-secondary);}
        .channel-card:before,.bento-kpi {border-color:var(--ipo-secondary);}
        .pipeline-grid:before,.editorial-stepper:before {border-color:var(--ipo-mist-purple);}
        .pipeline-node {background:var(--ipo-surface);border-color:var(--ipo-lavender);box-shadow:0 0 0 5px var(--ipo-background);}
        .trace-flow-step:not(:last-child):after,.result-breadcrumb-separator {color:var(--ipo-lavender);}
        .trace-card {border-left-color:var(--ipo-lavender);}
        .trace-card:before {background:var(--ipo-secondary);box-shadow:0 0 0 5px var(--ipo-background);}
        .product-nav {background:rgba(255,255,255,.9);border-bottom-color:rgba(20,184,166,.16);}
        .product-nav.nav-scrolled {border-bottom-color:var(--ipo-secondary);box-shadow:0 7px 18px rgba(20,184,166,.09);}
        .product-nav-links a:hover,.product-nav-links a.nav-active {color:var(--ipo-primary);}
        .product-nav-links a:after {background:var(--ipo-primary);}
        .st-key-case_workspace_shell,.st-key-risk_command_shell,.st-key-evidence_section_shell,.st-key-market_model_section_shell,.st-key-agent_trace_section_shell,.st-key-review_report_section_shell {background:rgba(255,255,255,.68);border-color:rgba(255,255,255,.9);box-shadow:0 14px 34px rgba(20,184,166,.08);backdrop-filter:blur(12px);}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"],.stTabs:has([role="tab"]:nth-child(5)) [role="tablist"] {background:color-mix(in srgb,var(--ipo-mist-purple) 42%,rgba(255,255,255,.8))!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"],.stTabs:has([role="tab"]:nth-child(5)) [role="tab"] {color:var(--ipo-muted)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [aria-selected="true"] {color:var(--ipo-primary)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-highlight"] {background:var(--ipo-primary)!important;}
        .assessment-panel,.ipo-hero {background-color:var(--ipo-primary);background-image:radial-gradient(circle at 88% 10%,rgba(184,167,255,.34),transparent 43%),linear-gradient(125deg,var(--ipo-primary),color-mix(in srgb,var(--ipo-primary) 62%,var(--ipo-secondary)));box-shadow:0 16px 34px rgba(20,184,166,.2);}
        .assessment-panel:after {border-color:rgba(217,204,255,.26);}
        .assessment-label,.ipo-kicker {color:color-mix(in srgb,var(--ipo-mist-purple) 68%,white);}
        .bento-kpi {border-top-color:var(--ipo-secondary);}
        .intelligence-panel {border-top-color:var(--ipo-secondary);}
        .landing-hero-v3 {background:radial-gradient(65% 90% at 88% 8%,rgba(184,167,255,.48),transparent 62%),radial-gradient(50% 70% at 72% 100%,rgba(96,213,200,.44),transparent 70%),linear-gradient(118deg,var(--ipo-primary) 0%,color-mix(in srgb,var(--ipo-primary) 72%,#163B38) 58%,var(--ipo-secondary) 100%);box-shadow:0 22px 46px rgba(20,184,166,.2);}
        .hero-static-bg {background-color:var(--ipo-primary);}
        .hero-reading-overlay {background:linear-gradient(90deg,rgba(10,74,68,.92) 0%,rgba(10,74,68,.78) 42%,rgba(20,184,166,.22) 100%);}
        .hero-v3-label {color:var(--ipo-mist-purple);}
        .hero-v3-subtitle {color:rgba(255,255,255,.88);}
        .hero-v3-detail,.hero-v3-meta {color:rgba(255,255,255,.72);}
        .hero-v3-cta {background:var(--ipo-surface);color:var(--ipo-primary)!important;box-shadow:0 9px 22px rgba(20,184,166,.22);}
        .hero-v3-meta i {background:var(--ipo-lavender);}
        .landing-section-head,.capability-band {border-color:rgba(20,184,166,.16);}
        .landing-section-index,.capability-no {color:var(--ipo-primary);}
        .section-reveal .landing-section-title:after {background:var(--ipo-primary);}
        .capability-list div:before {border-color:var(--ipo-secondary);}
        .capability-image-frame {background:color-mix(in srgb,var(--ipo-mist-purple) 20%,var(--ipo-background));border-color:rgba(184,167,255,.24);box-shadow:0 12px 28px rgba(184,167,255,.12);}
        .product-footer {background:color-mix(in srgb,var(--ipo-background) 76%,var(--ipo-mist-purple));border-top-color:rgba(184,167,255,.28);}
        .footer-status-dot {background:var(--ipo-secondary);}
        .analysis-activity {border-color:rgba(20,184,166,.2);background:rgba(255,255,255,.74);}
        .analysis-activity-bar {background:var(--ipo-primary);}
        /* Lightweight fintech form controls across initial and rerun states. */
        .stTextInput [data-testid="stTextInputRootElement"],.stTextInput [data-baseweb="input"],.stDateInput [data-baseweb="input"] {background:rgba(255,255,255,.88)!important;border:1px solid rgba(20,184,166,.24)!important;border-radius:12px!important;box-shadow:0 2px 8px rgba(20,184,166,.035)!important;transition:background-color 170ms var(--ease-product),border-color 170ms var(--ease-product),box-shadow 170ms var(--ease-product);}
        .stTextInput input,.stDateInput input {background:transparent!important;color:var(--ipo-ink)!important;caret-color:var(--ipo-primary);-webkit-text-fill-color:var(--ipo-ink)!important;}
        .stTextInput input::placeholder,.stDateInput input::placeholder {color:#7F94A3!important;opacity:.78;}
        .stTextInput [data-testid="stTextInputRootElement"]:hover,.stTextInput [data-baseweb="input"]:hover,.stDateInput [data-baseweb="input"]:hover {background:rgba(255,255,255,.94)!important;border-color:rgba(96,213,200,.78)!important;}
        .stTextInput [data-testid="stTextInputRootElement"]:focus-within,.stTextInput [data-baseweb="input"]:focus-within,.stDateInput [data-baseweb="input"]:focus-within {background:rgba(255,255,255,.97)!important;border-color:var(--ipo-primary)!important;box-shadow:0 0 0 3px rgba(20,184,166,.12),0 5px 14px rgba(20,184,166,.06)!important;outline:none!important;}
        .stTextInput input:disabled,.stDateInput input:disabled {color:var(--ipo-muted)!important;-webkit-text-fill-color:var(--ipo-muted)!important;opacity:.72;}
        .stTextInput input:-webkit-autofill,.stDateInput input:-webkit-autofill {-webkit-box-shadow:0 0 0 1000px rgba(255,255,255,.97) inset!important;-webkit-text-fill-color:var(--ipo-ink)!important;}
        .st-key-analysis_intake_shell [data-testid="stFileUploaderDropzone"] {min-height:172px;border:1px dashed rgba(20,184,166,.34)!important;border-radius:14px;background:rgba(255,255,255,.84)!important;box-shadow:0 3px 12px rgba(20,184,166,.04);transition:background-color 170ms var(--ease-product),border-color 170ms var(--ease-product),box-shadow 170ms var(--ease-product);}
        .st-key-analysis_intake_shell [data-testid="stFileUploaderDropzone"]:hover {border-color:rgba(96,213,200,.9)!important;background:rgba(255,255,255,.94)!important;box-shadow:0 0 0 3px rgba(96,213,200,.08);}
        [data-testid="stFileUploaderDropzoneInstructions"],[data-testid="stFileUploaderDropzoneInstructions"] span {color:var(--ipo-muted)!important;}
        [data-testid="stFileUploaderDropzone"] button {background:rgba(255,255,255,.92)!important;border:1px solid rgba(20,184,166,.22)!important;color:var(--ipo-ink)!important;border-radius:10px!important;box-shadow:0 2px 7px rgba(20,184,166,.04)!important;}
        [data-testid="stFileUploaderDropzone"] button:hover {background:var(--ipo-surface)!important;border-color:rgba(96,213,200,.78)!important;color:var(--ipo-primary)!important;}
        [data-testid="stFileUploaderFile"] {display:flex;align-items:center;gap:.65rem;padding:.72rem .82rem;border:1px solid rgba(20,184,166,.22)!important;border-radius:12px!important;background:rgba(255,255,255,.9)!important;box-shadow:0 3px 10px rgba(20,184,166,.04)!important;}
        [data-testid="stFileUploaderFileName"] {color:var(--ipo-ink)!important;font-weight:650;}
        [data-testid="stFileUploaderFileData"] {color:var(--ipo-muted)!important;font-size:.75rem;}
        [data-testid="stFileUploaderFile"] button {color:var(--ipo-muted)!important;border-radius:9px!important;transition:color 160ms var(--ease-product),background-color 160ms var(--ease-product);}
        [data-testid="stFileUploaderFile"] button:hover {color:var(--ipo-danger)!important;background:rgba(239,68,68,.08)!important;}
        [data-testid="stFileUploaderFile"] button:hover svg {fill:var(--ipo-danger)!important;color:var(--ipo-danger)!important;}
        .st-key-analysis_intake_shell [data-testid="stFileUploaderDropzone"]:has([data-testid="stFileChips"]) {min-height:68px;padding:.62rem .7rem;background:rgba(255,255,255,.88)!important;border-style:solid!important;}
        [data-testid="stFileChips"] {width:100%;}
        [data-testid="stFileChip"] {display:flex;align-items:center;gap:.6rem;min-width:0;padding:.62rem .72rem;border:1px solid rgba(20,184,166,.22)!important;border-radius:12px!important;background:rgba(255,255,255,.94)!important;box-shadow:0 3px 10px rgba(20,184,166,.045)!important;}
        [data-testid="stFileChip"] svg {color:var(--ipo-primary);}
        [data-testid="stFileChipName"] {color:var(--ipo-ink)!important;font-weight:650;}
        [data-testid="stFileChipName"] + div {color:var(--ipo-muted)!important;font-size:.73rem;}
        [data-testid="stFileChipDeleteBtn"] button {background:transparent!important;border:0!important;color:var(--ipo-muted)!important;box-shadow:none!important;border-radius:9px!important;}
        [data-testid="stFileChipDeleteBtn"] button:hover {background:rgba(239,68,68,.08)!important;color:var(--ipo-danger)!important;}
        [data-testid="stFileChipDeleteBtn"] button:hover svg {fill:var(--ipo-danger)!important;color:var(--ipo-danger)!important;}
        [data-testid="stFileUploaderDropzone"] button[aria-label="Add files"] {background:rgba(255,255,255,.76)!important;border:1px solid rgba(20,184,166,.18)!important;color:var(--ipo-muted)!important;box-shadow:none!important;}
        [data-testid="stFileUploaderDropzone"] button[aria-label="Add files"]:hover {background:var(--ipo-surface)!important;border-color:rgba(96,213,200,.72)!important;color:var(--ipo-primary)!important;}
        /* One translucent support layer for the full new-analysis intake. */
        .st-key-analysis_intake_shell {position:relative;isolation:isolate;margin:.15rem 0 2.1rem;padding:clamp(1.15rem,2.4vw,2rem);border:1px solid rgba(255,255,255,.92);border-radius:30px;background:rgba(255,255,255,.68);box-shadow:0 18px 42px rgba(20,184,166,.09);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);}
        .st-key-analysis_intake_shell:before {content:"";position:absolute;z-index:-1;left:5%;right:5%;bottom:-12px;height:42%;border-radius:28px;background:linear-gradient(100deg,rgba(96,213,200,.16),rgba(217,204,255,.22));filter:blur(10px);}
        .st-key-analysis_intake_shell div[data-testid="stForm"] {padding:0;border:0;background:transparent;box-shadow:none;}
        .st-key-analysis_intake_shell div[data-testid="stFormSubmitButton"] {display:flex;justify-content:flex-end;margin-top:.75rem;}
        .st-key-analysis_intake_shell div[data-testid="stFormSubmitButton"] button {width:min(100%,180px);min-height:46px;}
        .st-key-analysis_intake_shell [data-testid="stFileUploaderDropzone"] {isolation:isolate;}
        .st-key-analysis_intake_shell [data-testid="stFileUploaderDropzone"] > span svg {color:var(--ipo-primary);}
        /* Result workspace accents remain subtle and inherit the governed nine-colour palette. */
        .st-key-case_workspace_shell {--workspace-accent:var(--ipo-primary);--workspace-tint:rgba(20,184,166,.055);}
        .st-key-case_workspace_shell:has([role="tab"]:nth-child(2)[aria-selected="true"]) {--workspace-accent:var(--ipo-secondary);--workspace-tint:rgba(96,213,200,.065);}
        .st-key-case_workspace_shell:has([role="tab"]:nth-child(3)[aria-selected="true"]) {--workspace-accent:var(--ipo-lavender);--workspace-tint:rgba(184,167,255,.07);}
        .st-key-case_workspace_shell:has([role="tab"]:nth-child(4)[aria-selected="true"]) {--workspace-accent:var(--ipo-mist-purple);--workspace-tint:rgba(217,204,255,.09);}
        .st-key-case_workspace_shell:has([role="tab"]:nth-child(5)[aria-selected="true"]) {--workspace-accent:var(--ipo-primary);--workspace-tint:rgba(20,184,166,.045);}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"],.stTabs:has([role="tab"]:nth-child(5)) [role="tablist"] {min-height:52px;padding:6px!important;border:1px solid color-mix(in srgb,var(--workspace-accent) 14%,transparent)!important;background:color-mix(in srgb,var(--ipo-mist-purple) 27%,rgba(255,255,255,.9))!important;border-radius:16px!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"],.stTabs:has([role="tab"]:nth-child(5)) [role="tab"] {min-height:40px;padding:.68rem .75rem!important;font-size:.81rem!important;font-weight:650!important;border-radius:11px!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [aria-selected="true"] {background:color-mix(in srgb,var(--workspace-accent) 14%,white)!important;color:color-mix(in srgb,var(--workspace-accent) 72%,#163B38)!important;box-shadow:0 4px 12px color-mix(in srgb,var(--workspace-accent) 15%,transparent)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-highlight"] {height:3px!important;background:var(--workspace-accent)!important;}
        .stTabs:has([role="tab"]:nth-child(5)) .react-aria-SelectionIndicator {height:3px!important;background:var(--workspace-accent)!important;border-radius:999px!important;}
        .st-key-risk_command_shell {--section-accent:var(--ipo-primary);--section-tint:rgba(20,184,166,.052);}
        .st-key-evidence_section_shell {--section-accent:var(--ipo-secondary);--section-tint:rgba(96,213,200,.062);}
        .st-key-market_model_section_shell {--section-accent:var(--ipo-lavender);--section-tint:rgba(184,167,255,.068);}
        .st-key-agent_trace_section_shell {--section-accent:var(--ipo-lavender);--section-tint:rgba(217,204,255,.09);}
        .st-key-review_report_section_shell {--section-accent:var(--ipo-primary);--section-tint:rgba(217,204,255,.06);}
        .st-key-risk_command_shell,.st-key-evidence_section_shell,.st-key-market_model_section_shell,.st-key-agent_trace_section_shell,.st-key-review_report_section_shell {position:relative;border-left:3px solid var(--section-accent)!important;background:linear-gradient(145deg,var(--section-tint),rgba(255,255,255,.74) 32%,rgba(255,255,255,.68))!important;box-shadow:0 14px 34px color-mix(in srgb,var(--section-accent) 8%,transparent)!important;}
        .st-key-risk_command_shell .section-head,.st-key-evidence_section_shell .section-head,.st-key-market_model_section_shell .section-head,.st-key-agent_trace_section_shell .section-head,.st-key-review_report_section_shell .section-head {border-left-color:var(--section-accent)!important;}
        .st-key-risk_command_shell .section-eyebrow,.st-key-evidence_section_shell .section-eyebrow,.st-key-market_model_section_shell .section-eyebrow,.st-key-agent_trace_section_shell .section-eyebrow,.st-key-review_report_section_shell .section-eyebrow {color:color-mix(in srgb,var(--section-accent) 72%,#163B38);}
        .st-key-risk_command_shell .metric-card,.st-key-evidence_section_shell .metric-card,.st-key-market_model_section_shell .metric-card,.st-key-agent_trace_section_shell .metric-card,.st-key-review_report_section_shell .metric-card {border-top:2px solid color-mix(in srgb,var(--section-accent) 68%,white)!important;}
        /* Evidence sub-tabs are a compact child navigation, not another workspace switcher. */
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs {margin:.35rem clamp(1.15rem,5vw,4.25rem) .4rem;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [data-baseweb="tab-list"],.st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [role="tablist"] {min-height:42px!important;gap:4px!important;padding:4px!important;border:1px solid rgba(96,213,200,.18)!important;border-radius:11px!important;background:rgba(96,213,200,.075)!important;box-shadow:none!important;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [data-baseweb="tab"],.st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [role="tab"] {min-height:32px!important;padding:.46rem .8rem!important;border-radius:8px!important;background:transparent!important;color:var(--ipo-muted)!important;font-size:.73rem!important;font-weight:610!important;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [aria-selected="true"] {background:rgba(255,255,255,.88)!important;color:color-mix(in srgb,var(--ipo-secondary) 72%,#163B38)!important;box-shadow:inset 0 0 0 1px rgba(96,213,200,.22)!important;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [data-baseweb="tab-highlight"] {height:2px!important;background:var(--ipo-secondary)!important;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs [role="tab"][data-testid="stTab"][data-selected="true"][aria-selected="true"] {background:rgba(255,255,255,.88)!important;background-image:none!important;color:color-mix(in srgb,var(--ipo-secondary) 72%,#163B38)!important;box-shadow:inset 0 0 0 1px rgba(96,213,200,.22)!important;}
        .st-key-case_workspace_shell .st-key-evidence_section_shell .stTabs .react-aria-SelectionIndicator {height:2px!important;background:var(--ipo-secondary)!important;border-radius:999px!important;}
        /* Preserve interactive Streamlit dataframes while replacing the Excel-like grid treatment. */
        [data-testid="stDataFrame"] {overflow:visible;border:0!important;border-radius:15px!important;background:transparent!important;box-shadow:none!important;}
        [data-testid="stDataFrameResizable"] {overflow:hidden!important;border:1px solid rgba(20,184,166,.13)!important;border-radius:14px!important;background:rgba(255,255,255,.92)!important;box-shadow:0 4px 14px rgba(20,184,166,.04)!important;}
        [data-testid="stDataFrame"] .stDataFrameGlideDataEditor {--gdg-accent-color:var(--section-accent,var(--workspace-accent,var(--ipo-primary)))!important;--gdg-accent-light:var(--section-tint,var(--workspace-tint,rgba(20,184,166,.06)))!important;--gdg-bg-cell:rgba(255,255,255,.96)!important;--gdg-bg-cell-medium:rgba(255,255,255,.96)!important;--gdg-bg-header:color-mix(in srgb,var(--section-accent,var(--workspace-accent,var(--ipo-primary))) 7%,white)!important;--gdg-bg-header-hovered:color-mix(in srgb,var(--section-accent,var(--workspace-accent,var(--ipo-primary))) 11%,white)!important;--gdg-bg-header-has-focus:color-mix(in srgb,var(--section-accent,var(--workspace-accent,var(--ipo-primary))) 11%,white)!important;--gdg-border-color:transparent!important;--gdg-horizontal-border-color:rgba(20,184,166,.1)!important;--gdg-text-header:#42586A!important;--gdg-header-font-style:650 13px!important;--gdg-base-font-style:400 13px!important;--gdg-cell-horizontal-padding:12px!important;--gdg-cell-vertical-padding:8px!important;--gdg-bg-bubble:rgba(217,204,255,.32)!important;--gdg-text-bubble:#42586A!important;}
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button {border-radius:8px!important;color:var(--ipo-muted)!important;}
        /* Small read-only summaries use semantic chips without changing source values or order. */
        .modern-table-shell {width:100%;overflow:auto;margin:.45rem 0 .95rem;border:1px solid rgba(20,184,166,.13);border-radius:14px;background:rgba(255,255,255,.92);box-shadow:0 4px 14px rgba(20,184,166,.04);}
        .modern-table-scroll {max-height:430px;}
        .modern-data-table {width:100%;border-collapse:separate;border-spacing:0;color:var(--ipo-ink);font-size:.79rem;line-height:1.45;}
        .modern-data-table th {position:sticky;top:0;z-index:1;padding:.68rem .78rem;background:color-mix(in srgb,var(--section-accent,var(--workspace-accent,var(--ipo-primary))) 7%,white);color:#42586A;font-size:.73rem;font-weight:650;text-align:left;white-space:nowrap;}
        .modern-data-table td {padding:.7rem .78rem;border:0;border-top:1px solid rgba(20,184,166,.09);background:transparent;vertical-align:middle;}
        .modern-data-table tbody tr:first-child td {border-top:0;}
        .modern-data-table tbody tr {transition:background-color 150ms var(--ease-product);}
        .modern-data-table tbody tr:hover {background:var(--section-tint,var(--workspace-tint,rgba(20,184,166,.055)));}
        .modern-table-compact .modern-data-table {table-layout:fixed;font-size:.7rem;}
        .modern-table-compact .modern-data-table th,.modern-table-compact .modern-data-table td {padding:.58rem .42rem;white-space:normal;overflow-wrap:anywhere;}
        .modern-table-compact .data-badge {padding:2px 6px;font-size:.67rem;}
        .data-badge {display:inline-flex;align-items:center;gap:.32rem;max-width:100%;padding:3px 8px;border:1px solid transparent;border-radius:999px;font-size:.73rem;font-weight:650;line-height:1.35;white-space:nowrap;}
        .data-badge:before {content:"";width:5px;height:5px;flex:0 0 5px;border-radius:50%;background:currentColor;opacity:.82;}
        .badge-success {color:color-mix(in srgb,var(--ipo-success) 68%,#163B38);background:color-mix(in srgb,var(--ipo-success) 9%,white);border-color:color-mix(in srgb,var(--ipo-success) 24%,transparent);}
        .badge-warning {color:color-mix(in srgb,var(--ipo-warning) 70%,#163B38);background:color-mix(in srgb,var(--ipo-warning) 10%,white);border-color:color-mix(in srgb,var(--ipo-warning) 25%,transparent);}
        .badge-danger {color:color-mix(in srgb,var(--ipo-danger) 72%,#163B38);background:color-mix(in srgb,var(--ipo-danger) 8%,white);border-color:color-mix(in srgb,var(--ipo-danger) 23%,transparent);}
        .badge-neutral {color:var(--ipo-muted);background:rgba(127,148,163,.08);border-color:rgba(127,148,163,.18);}
        .badge-category {color:color-mix(in srgb,var(--ipo-lavender) 64%,#304B5E);background:rgba(217,204,255,.3);border-color:rgba(184,167,255,.2);}
        .badge-domain-financial {color:color-mix(in srgb,var(--ipo-primary) 70%,#163B38);background:rgba(20,184,166,.09);border-color:rgba(20,184,166,.2);}
        .badge-domain-legal {color:color-mix(in srgb,var(--ipo-lavender) 68%,#304B5E);background:rgba(217,204,255,.31);border-color:rgba(184,167,255,.22);}
        .badge-domain-business {color:color-mix(in srgb,var(--ipo-secondary) 70%,#163B38);background:rgba(96,213,200,.1);border-color:rgba(96,213,200,.22);}
        /* IPO facts behave as a profile matrix, not a cell-by-cell spreadsheet. */
        .profile-grid {gap:0!important;padding:4px;background:rgba(255,255,255,.72)!important;border:1px solid rgba(20,184,166,.12)!important;border-radius:14px!important;box-shadow:0 4px 14px rgba(20,184,166,.035);}
        .profile-item {position:relative;background:transparent!important;border:0!important;border-radius:10px!important;box-shadow:none!important;padding:.82rem .9rem!important;}
        .profile-item:after {content:"";position:absolute;left:.9rem;right:.9rem;bottom:0;border-bottom:1px solid rgba(20,184,166,.075);}
        .profile-label {color:#7F94A3!important;font-size:.64rem!important;font-weight:620!important;letter-spacing:.02em;}
        .profile-value {color:var(--ipo-ink)!important;font-weight:680!important;}
        @media(max-width:1200px){.landing-hero-v3{grid-template-columns:minmax(0,1.05fr) minmax(360px,.85fr);padding:2rem}.capability-band{gap:2.5rem}.ipo-hero-row{grid-template-columns:1fr}.ipo-hero{min-height:185px}.bento-shell{grid-template-columns:minmax(0,1.35fr) minmax(285px,1fr)}.pipeline-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem}.pipeline-grid:before{display:none}.pipeline-card{background:#fff;border:1px solid var(--ipo-line);border-radius:10px;padding:.6rem}.trace-card{grid-template-columns:38px minmax(120px,.7fr) minmax(160px,1.3fr) auto;}}
        @media(max-width:900px){.product-nav-links{gap:20px}.product-nav-links a{font-size:.78rem}.landing-hero-v3{grid-template-columns:1fr;min-height:auto}.risk-flow-visual{max-width:620px;margin:0 auto}.risk-flow-visual svg{width:100%;margin-left:0}.landing-section-head,.capability-band{grid-template-columns:1fr;gap:1.3rem}.capability-band.reverse .capability-copy,.capability-band.reverse .capability-visual{order:initial}.product-footer-grid{grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr)}.footer-system{grid-column:1/-1;max-width:620px}.command-health{grid-template-columns:repeat(2,minmax(0,1fr))}.stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"],.stTabs:has([role="tab"]:nth-child(5)) [role="tablist"]{display:flex!important;overflow-x:auto}.stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab"],.stTabs:has([role="tab"]:nth-child(5)) [role="tab"]{min-width:max-content}.bento-shell,.audit-split{grid-template-columns:1fr}.bento-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.trace-flow{grid-template-columns:repeat(3,1fr)}.trace-flow-step:nth-child(3):after{display:none}.channel-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.roadmap-grid{grid-template-columns:repeat(2,minmax(0,1fr));}.editorial-stepper{grid-template-columns:repeat(2,1fr);gap:1.25rem}.editorial-stepper:before{display:none}.block-container{padding-left:1rem;padding-right:1rem}.trace-card{grid-template-columns:34px 1fr auto}.trace-action{grid-column:2/4}.stTabs [data-baseweb="tab"]{font-size:.74rem;padding:.5rem .6rem}}
        @media(max-width:620px){div[data-testid="stElementContainer"]:has(.product-nav){top:var(--streamlit-header-height)}.product-nav{padding:0 .7rem}.product-nav-logo{height:30px;max-width:150px}.product-nav-links{max-width:66%;gap:17px}.product-nav-links a{font-size:.73rem}.landing-hero-v3{padding:1.5rem 1.15rem;border-radius:14px}.hero-v3-title{font-size:2.25rem}.risk-flow-visual{margin-top:.5rem}.capability-image-frame{border-radius:18px}.product-footer{padding-top:44px}.product-footer-grid{grid-template-columns:1fr;gap:2rem}.footer-system{grid-column:auto;max-width:none}.footer-lower{align-items:flex-start;flex-direction:column;gap:1rem;margin-top:34px}.metric-grid,.channel-grid,.pipeline-grid,.profile-grid,.empty-flow,.roadmap-grid,.bento-kpis{grid-template-columns:1fr;}.ipo-hero{padding:1rem;min-height:auto}.command-health{grid-template-columns:1fr 1fr}.case-shell{align-items:flex-start}.trace-flow{grid-template-columns:1fr}.trace-flow-step:after{display:none!important}.trace-card{grid-template-columns:30px 1fr}.trace-action{grid-column:2}.trace-card .status-chip{grid-column:2;justify-self:start}}
        @media(max-width:900px){.st-key-case_workspace_shell{padding:20px;border-radius:22px}.st-key-risk_command_shell,.st-key-evidence_section_shell,.st-key-market_model_section_shell,.st-key-agent_trace_section_shell,.st-key-review_report_section_shell{padding:1.25rem;border-radius:22px}}
        @media(max-width:620px){.st-key-case_workspace_shell{padding:16px;border-radius:18px}.stTabs:has([role="tab"]:nth-child(5)) [data-baseweb="tab-list"],.stTabs:has([role="tab"]:nth-child(5)) [role="tablist"]{border-radius:14px;padding:5px}.st-key-risk_command_shell,.st-key-evidence_section_shell,.st-key-market_model_section_shell,.st-key-agent_trace_section_shell,.st-key-review_report_section_shell{margin-top:18px;padding:1rem;border-radius:18px}}
        @media(max-width:620px){.st-key-analysis_intake_shell{padding:1rem;border-radius:22px}.st-key-analysis_intake_shell:before{left:8%;right:8%;bottom:-8px}.st-key-analysis_intake_shell div[data-testid="stFormSubmitButton"] button{width:100%}}
        @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}.hero-prospectus,.hero-evidence,.hero-market,.hero-rule,.hero-risk,.hero-final,.hero-connector{animation:none!important;transform:none!important;opacity:.96!important}.motion-enter,.editorial-stepper,.editorial-step-no,.result-enter,.section-reveal .landing-section-title,.section-reveal .landing-section-copy,.scroll-content-target,.capability-band .capability-copy,.capability-band .capability-visual,.product-footer{opacity:1!important;transform:none!important}.section-reveal .landing-section-title:after,.product-nav-links a.nav-active:after{transform:scaleX(1)!important}}
        </style>
        """,
        unsafe_allow_html=True,
    )


@lru_cache(maxsize=4)
def _asset_png_data_uri(relative_path: str) -> str:
    """Return a bundled PNG as an embeddable, rerun-stable URI."""

    asset_path = Path(__file__).resolve().parent / "assets" / relative_path
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _hero_static_background_style() -> str:
    """Use the formal Hero background when present, otherwise keep the CSS fallback."""

    relative_path = "hero/hero_aurora_bg.png"
    asset_path = Path(__file__).resolve().parent / "assets" / relative_path
    if not asset_path.is_file():
        return ""
    return f" style=\"background-image:url('{_asset_png_data_uri(relative_path)}')\""


def render_product_navigation(*, result_mode: bool = False) -> None:
    """Render page-level section navigation below the Streamlit header."""

    if result_mode:
        links_html = (
            "<a class='nav-active' aria-current='location' href='#result-overview'>首页</a>"
            "<a href='#new-analysis'>新建分析</a>"
            "<a href='#case-workspace'>案例工作台</a>"
        )
        brand_target = "#result-overview"
    else:
        links_html = (
            "<a class='nav-active' aria-current='location' data-section='overview' href='#overview'>概览</a>"
            "<a data-section='new-analysis' href='#new-analysis'>新建分析</a>"
            "<a data-section='workflow' href='#workflow'>研究流程</a>"
            "<a data-section='capabilities' href='#capabilities'>核心能力</a>"
            "<a data-section='runtime' href='#runtime'>运行环境</a>"
        )
        brand_target = "#overview"
    st.markdown(
        "<nav class='product-nav' aria-label='产品导航'>"
        f"<a class='product-nav-brand' href='{brand_target}' aria-label='返回首页'>"
        f"<img class='product-nav-logo' src='{_asset_png_data_uri('ipo_risk_logo.png')}' alt='IPO Risk'></a>"
        "<div class='product-nav-links'>"
        f"{links_html}</div></nav>",
        unsafe_allow_html=True,
    )


def render_navigation_behavior() -> None:
    """Attach idempotent, browser-local navigation and reveal behaviour."""

    components.html(
        """
        <script>
        (() => {
          const root = window.parent;
          const doc = root.document;
          const previous = root.__ipoRiskNavigation;
          if (previous && previous.destroy) previous.destroy();

          const ids = ["overview", "new-analysis", "workflow", "capabilities", "runtime"];
          const nav = doc.querySelector(".product-nav");
          const scroller = doc.querySelector('[data-testid="stMain"]') || root;
          const navLinks = [...doc.querySelectorAll(".product-nav [data-section]")];
          const scrollLinks = [...doc.querySelectorAll(".product-nav [data-section], .product-footer [data-section]")];
          const sections = ids.map((id) => doc.getElementById(id)).filter(Boolean);
          if (!nav || sections.length !== ids.length) return;

          const reduced = root.matchMedia("(prefers-reduced-motion: reduce)").matches;
          const clickHandlers = [];
          let frame = 0;

          const activate = (id) => {
            navLinks.forEach((link) => {
              const active = link.dataset.section === id;
              link.classList.toggle("nav-active", active);
              if (active) link.setAttribute("aria-current", "location");
              else link.removeAttribute("aria-current");
            });
          };

          scrollLinks.forEach((link) => {
            const handler = (event) => {
              const target = doc.getElementById(link.dataset.section);
              if (!target) return;
              event.preventDefault();
              target.scrollIntoView({behavior: reduced ? "auto" : "smooth", block: "start"});
              root.history.replaceState(null, "", `#${link.dataset.section}`);
            };
            link.addEventListener("click", handler);
            clickHandlers.push([link, handler]);
          });

          const syncActiveSection = () => {
            frame = 0;
            const scrollTop = scroller === root ? root.scrollY : scroller.scrollTop;
            const clientHeight = scroller === root ? root.innerHeight : scroller.clientHeight;
            const scrollHeight = scroller === root ? doc.documentElement.scrollHeight : scroller.scrollHeight;
            const scrollerTop = scroller === root ? 0 : scroller.getBoundingClientRect().top;
            nav.classList.toggle("nav-scrolled", scrollTop > 12);
            if (scrollTop < 80) {
              activate("overview");
              return;
            }
            if (clientHeight + scrollTop >= scrollHeight - 24) {
              activate("runtime");
              return;
            }
            const readingLine = scrollerTop + clientHeight * 0.34;
            let active = sections[0].id;
            sections.forEach((section) => {
              if (section.getBoundingClientRect().top <= readingLine) active = section.id;
            });
            activate(active);
          };
          const onScroll = () => {
            if (!frame) frame = root.requestAnimationFrame(syncActiveSection);
          };
          scroller.addEventListener("scroll", onScroll, {passive: true});

          const sectionObserver = new root.IntersectionObserver((entries) => {
            const scrollerTop = scroller === root ? 0 : scroller.getBoundingClientRect().top;
            const clientHeight = scroller === root ? root.innerHeight : scroller.clientHeight;
            const readingLine = scrollerTop + clientHeight * 0.34;
            const visible = entries.filter((entry) => entry.isIntersecting).sort(
              (a, b) => Math.abs(a.boundingClientRect.top - readingLine) - Math.abs(b.boundingClientRect.top - readingLine)
            );
            if (visible[0]) activate(visible[0].target.id);
          }, {root: scroller === root ? null : scroller, rootMargin: "-28% 0px -58% 0px", threshold: 0});
          sections.forEach((section) => sectionObserver.observe(section));

          const headings = [...doc.querySelectorAll(".section-reveal")];
          const content = [
            ...doc.querySelectorAll('div[data-testid="stForm"]:has(.landing-intake-title)'),
            ...doc.querySelectorAll(".editorial-stepper, .capability-band, .product-footer")
          ];
          content.forEach((element) => element.classList.add("scroll-content-target"));
          const revealObserver = new root.IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) return;
              entry.target.classList.add(
                entry.target.classList.contains("section-reveal") ? "section-visible" : "content-visible"
              );
              revealObserver.unobserve(entry.target);
            });
          }, {root: null, rootMargin: "0px 0px -18% 0px", threshold: 0.12});
          headings.forEach((element) => revealObserver.observe(element));
          content.forEach((element) => revealObserver.observe(element));

          doc.body.classList.add("ipo-scrollspy-ready");
          syncActiveSection();
          root.__ipoRiskNavigation = {
            destroy() {
              scroller.removeEventListener("scroll", onScroll);
              if (frame) root.cancelAnimationFrame(frame);
              sectionObserver.disconnect();
              revealObserver.disconnect();
              clickHandlers.forEach(([link, handler]) => link.removeEventListener("click", handler));
            }
          };
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def render_product_header(payload: dict[str, Any] | None = None, *, runtime_label: str = "待运行") -> None:
    """Render the product landing hero or compact result command header."""

    if payload is None:
        st.markdown(
            "<section id='overview' class='landing-hero-v3 landing-section-anchor'>"
            f"<div class='hero-static-bg'{_hero_static_background_style()}></div>"
            "<div class='hero-reading-overlay' aria-hidden='true'></div>"
            "<div class='hero-v3-copy'>"
            "<div class='hero-v3-label'>IPO Risk Review</div>"
            "<h1 class='hero-v3-title'>港股 IPO 风险分析</h1>"
            "<div class='hero-v3-subtitle'>从招股书证据到最终审阅，构建可追溯、可核验的 IPO 风险研究链。</div>"
            "<div class='hero-v3-detail'>统一连接 Prospectus、Evidence、Risk、Market Signal 与 Final Review。</div>"
            "<div class='hero-v3-actions'><a class='hero-v3-cta' href='#new-analysis'>开始一次 IPO 分析 →</a></div>"
            "<div class='hero-v3-meta'><span><i></i>Evidence traceable</span>"
            "<span><i></i>Fail-closed</span><span><i></i>Human review</span></div>"
            "</div>"
            "<div class='risk-flow-visual' aria-hidden='true'>"
            "<svg viewBox='0 0 640 430' role='img'>"
            "<defs>"
            "<linearGradient id='heroPaper' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#FFFFFF'/><stop offset='.7' stop-color='#F2FBF8'/><stop offset='1' stop-color='#D9CCFF'/></linearGradient>"
            "<linearGradient id='heroGlass' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#14B8A6'/><stop offset='1' stop-color='#60D5C8'/></linearGradient>"
            "<linearGradient id='heroFinal' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#14B8A6'/><stop offset='.58' stop-color='#60D5C8'/><stop offset='1' stop-color='#B8A7FF'/></linearGradient>"
            "<linearGradient id='heroEvidenceFill' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#D9CCFF'/><stop offset='1' stop-color='#F59E0B'/></linearGradient>"
            "<radialGradient id='heroAmbient' cx='55%' cy='48%' r='62%'><stop offset='0' stop-color='#60D5C8' stop-opacity='.28'/><stop offset='.55' stop-color='#B8A7FF' stop-opacity='.09'/><stop offset='1' stop-color='#14B8A6' stop-opacity='0'/></radialGradient>"
            "<pattern id='heroDots' width='22' height='22' patternUnits='userSpaceOnUse'><circle cx='2' cy='2' r='1.1' fill='#D9CCFF' opacity='.3'/></pattern>"
            "<clipPath id='marketClip'><rect x='430' y='104' width='126' height='42' rx='6'/></clipPath>"
            "</defs>"
            "<g class='hero-canvas-bg'><ellipse cx='330' cy='215' rx='286' ry='190' fill='url(#heroAmbient)'/><rect x='54' y='26' width='540' height='360' rx='40' fill='url(#heroDots)' opacity='.34'/><ellipse cx='325' cy='214' rx='238' ry='155' fill='none' stroke='#8bc9c7' stroke-opacity='.12'/><ellipse cx='325' cy='214' rx='184' ry='118' fill='none' stroke='#8bc9c7' stroke-opacity='.13' stroke-dasharray='4 10'/><path d='M72 108C150 48 247 35 341 52M470 369c66-27 102-75 112-132' fill='none' stroke='#a9d8d6' stroke-opacity='.12' stroke-width='1.2'/><circle cx='92' cy='106' r='3' fill='#77c9c4'/><circle cx='570' cy='236' r='3' fill='#d8b15a'/><circle cx='477' cy='368' r='2.5' fill='#77c9c4'/></g>"
            "<g fill='none' stroke='#B8A7FF' stroke-width='1.5' stroke-linecap='round'><path class='hero-connector hero-connector-evidence' d='M276 167C218 168 190 224 166 278'/><path class='hero-connector hero-connector-market' d='M407 125C431 111 446 98 466 90'/><path class='hero-connector hero-connector-final' d='M405 244C466 246 495 264 504 288'/></g>"
            "<g class='hero-doc-stack hero-prospectus'>"
            "<rect x='167' y='52' width='260' height='322' rx='18' fill='#c7dce0' opacity='.28' transform='rotate(-5 297 213)'/><rect x='180' y='44' width='260' height='324' rx='18' fill='#dce9eb' opacity='.52' transform='rotate(2.5 310 206)'/>"
            "<rect x='164' y='38' width='270' height='330' rx='20' fill='url(#heroPaper)' stroke='#bcd2d7' stroke-width='1.2'/><path d='M382 38h32c11 0 20 9 20 20v31z' fill='#d7e7e9'/><path d='M382 38v31c0 11 9 20 20 20h32' fill='#edf4f5' stroke='#c3d7db'/>"
            "<rect x='164' y='38' width='38' height='330' rx='20' fill='#163d52'/><rect x='164' y='66' width='38' height='282' fill='#163d52'/><circle cx='183' cy='68' r='8' fill='#2a8790'/><path d='M179 68l3 3 6-7' fill='none' stroke='#d8f1ef' stroke-width='1.8'/><rect x='176' y='111' width='14' height='17' rx='3' fill='#eef6f5' opacity='.88'/><rect x='176' y='153' width='14' height='3' rx='1.5' fill='#84c8c4'/><rect x='176' y='164' width='14' height='3' rx='1.5' fill='#84c8c4' opacity='.65'/><circle cx='183' cy='216' r='7' fill='none' stroke='#8fc8c6'/><path d='M179 216h8M183 212v8' stroke='#8fc8c6'/><rect x='176' y='268' width='14' height='14' rx='4' fill='#d8b15a' opacity='.85'/><circle cx='183' cy='329' r='5' fill='#8fc8c6'/>"
            "<text x='224' y='68' fill='#203f52' font-size='12' font-weight='750' letter-spacing='.8'>PROSPECTUS</text><text x='224' y='85' fill='#7b8d98' font-size='7.5' font-weight='650'>IPO FILING · RESEARCH COPY</text><rect x='348' y='57' width='57' height='18' rx='9' fill='#e4f1f0'/><circle cx='360' cy='66' r='3' fill='#249a95'/><text x='368' y='69' fill='#397078' font-size='6.5' font-weight='700'>SOURCE</text>"
            "<rect x='224' y='111' width='142' height='8' rx='4' fill='#b8c9cf'/><rect x='224' y='130' width='176' height='5' rx='2.5' fill='#d2dde1'/><rect x='224' y='143' width='148' height='5' rx='2.5' fill='#dce5e8'/><rect x='224' y='189' width='170' height='5' rx='2.5' fill='#d3dee2'/><rect x='224' y='202' width='132' height='5' rx='2.5' fill='#dce5e8'/><rect x='224' y='248' width='174' height='5' rx='2.5' fill='#d3dee2'/><rect x='224' y='261' width='151' height='5' rx='2.5' fill='#dce5e8'/><rect x='224' y='307' width='154' height='5' rx='2.5' fill='#d3dee2'/><rect x='224' y='320' width='112' height='5' rx='2.5' fill='#dce5e8'/>"
            "<rect x='218' y='158' width='188' height='22' rx='5' fill='#f4dfae' opacity='.86'/><rect x='224' y='165' width='134' height='4' rx='2' fill='#bb9140' opacity='.65'/><rect x='218' y='217' width='168' height='22' rx='5' fill='#d9eeee'/><rect x='224' y='224' width='116' height='4' rx='2' fill='#4c9997' opacity='.58'/><text x='377' y='351' fill='#82939c' font-size='7' font-weight='650'>156 / 423</text>"
            "</g>"
            "<g class='hero-evidence'><rect x='88' y='135' width='206' height='76' rx='14' fill='#f8fbfb' stroke='#b9d7d8'/><rect x='88' y='135' width='5' height='76' rx='2.5' fill='#d8b15a'/><text x='108' y='157' fill='#8b6a27' font-size='7.5' font-weight='650' letter-spacing='.4'>EVIDENCE · SOURCE LINKED</text><rect class='hero-evidence-sweep' x='108' y='169' width='158' height='11' rx='4' fill='url(#heroEvidenceFill)'/><rect x='108' y='187' width='128' height='4' rx='2' fill='#cad8dd'/><circle cx='272' cy='174' r='7' fill='#fff7e6' stroke='#d2a64c'/><path d='M269 174l2 2 4-5' fill='none' stroke='#a8791d' stroke-width='1.4'/></g>"
            "<g class='hero-market'><rect x='404' y='56' width='184' height='108' rx='17' fill='url(#heroGlass)' stroke='#4c7c89'/><text x='426' y='80' fill='#b9d8da' font-size='8' font-weight='650' letter-spacing='.4'>MARKET SIGNAL</text><text x='426' y='94' fill='#739aa5' font-size='6.5' font-weight='500'>CONTEXT LAYER</text><g clip-path='url(#marketClip)'><path d='M430 140L447 132L463 136L480 116L497 124L515 105L535 113L556 90V148H430Z' fill='#3ba9ab' opacity='.14'/><path class='hero-market-line' d='M430 140L447 132L463 136L480 116L497 124L515 105L535 113L556 90' fill='none' stroke='#75d0cb' stroke-width='2'/></g><line x1='430' y1='148' x2='562' y2='148' stroke='#557987' stroke-opacity='.55'/><circle cx='568' cy='76' r='4' fill='#d8b15a'/></g>"
            "<g class='hero-risk'><rect x='38' y='268' width='204' height='116' rx='18' fill='#f7fafb' stroke='#b7d0d5'/><text x='60' y='292' fill='#25495b' font-size='8' font-weight='650' letter-spacing='.4'>RISK REVIEW</text><circle cx='211' cy='288' r='8' fill='#e7f2f1'/><path d='M207 288l3 3 6-7' fill='none' stroke='#238d89' stroke-width='1.5'/><text x='60' y='319' fill='#607783' font-size='7'>FINANCIAL</text><rect x='119' y='313' width='90' height='7' rx='3.5' fill='#d8e4e7'/><rect x='119' y='313' width='54' height='7' rx='3.5' fill='#73bbb8'/><text x='60' y='342' fill='#607783' font-size='7'>LEGAL</text><rect x='119' y='336' width='90' height='7' rx='3.5' fill='#d8e4e7'/><rect x='119' y='336' width='66' height='7' rx='3.5' fill='#d8b15a'/><text x='60' y='365' fill='#607783' font-size='7'>BUSINESS</text><rect x='119' y='359' width='90' height='7' rx='3.5' fill='#d8e4e7'/><rect x='119' y='359' width='44' height='7' rx='3.5' fill='#5c9fa3'/></g>"
            "<g class='hero-rule'><rect x='430' y='178' width='145' height='58' rx='15' fill='#173f52' stroke='#527f8b'/><path d='M448 194l8-4 8 4v7c0 6-4 10-8 12-4-2-8-6-8-12z' fill='#74c5c1' opacity='.9'/><path d='M452 201l3 3 5-7' fill='none' stroke='#103c4e' stroke-width='1.5'/><text x='474' y='199' fill='#c5dfdf' font-size='7.5' font-weight='650'>RULE / GOVERNANCE</text><text x='474' y='214' fill='#789ca6' font-size='6.5'>Policy checks retained</text></g>"
            "<g class='hero-final'><rect x='368' y='248' width='238' height='142' rx='21' fill='url(#heroFinal)' stroke='#8bc9c5' stroke-width='1.2'/><circle cx='398' cy='280' r='15' fill='#d8f1ee'/><g class='hero-audit-mark'><path d='M391 280l5 5 10-12' fill='none' stroke='#176b75' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'/></g><text x='423' y='275' fill='#ffffff' font-size='10.5' font-weight='650' letter-spacing='.3'>FINAL REVIEW</text><text x='423' y='290' fill='#9ed0cf' font-size='7'>GOVERNED SUMMARY</text><line x1='390' y1='307' x2='581' y2='307' stroke='#92c3c3' stroke-opacity='.32'/><circle cx='397' cy='326' r='3.5' fill='#84d0cb'/><text x='409' y='329' fill='#d4e9e8' font-size='7.5'>Evidence linked</text><rect x='510' y='321' width='66' height='12' rx='6' fill='#2e7d83'/><text x='522' y='329.5' fill='#c7e6e4' font-size='6'>TRACEABLE</text><circle cx='397' cy='350' r='3.5' fill='#d8b15a'/><text x='409' y='353' fill='#d4e9e8' font-size='7.5'>Limits retained</text><rect x='510' y='345' width='66' height='12' rx='6' fill='#2e7d83'/><text x='524' y='353.5' fill='#c7e6e4' font-size='6'>REVIEWED</text><path d='M577 370h-76' stroke='#86b8b9' stroke-width='1.2'/><circle cx='584' cy='370' r='4' fill='#d8b15a'/></g>"
            "</svg></div></section>",
            unsafe_allow_html=True,
        )
        return

    states = channel_state_map(payload or {})
    diagnostics = (payload or {}).get("component_diagnostics") or {}
    llm_state = (diagnostics.get("final_supervision_llm") or {}).get("status") or "unavailable"
    runtime_state = (payload or {}).get("runtime_completion_status") or (payload or {}).get("status") or "pending"
    indicators = (
        ("Runtime", runtime_state, runtime_label),
        ("LLM", llm_state, status_label(llm_state) if payload else "待分析"),
        ("Market-X", states.get("market", "unavailable"), status_label(states.get("market")) if payload else "待分析"),
        ("Model", states.get("model", "unavailable"), status_label(states.get("model")) if payload else "待分析"),
    )
    health_html = "".join(
        "<div class='health-item'><div class='health-label'>"
        f"{escape(label)}</div><div class='health-value {_status_tone(state).replace('status-', 'tone-')}'>"
        f"<span class='health-dot'></span>{escape(str(value))}</div></div>"
        for label, state, value in indicators
    )
    st.markdown(
        "<div id='result-overview' class='ipo-hero landing-section-anchor'><div class='ipo-hero-row'><div>"
        "<div class='ipo-kicker'>HK IPO Risk Intelligence</div>"
        "<div class='ipo-title'>港股 IPO 风险分析工作台</div>"
        "<div class='ipo-subtitle'>Evidence-driven Multi-Agent IPO Risk Intelligence · "
        "招股书风险、证据链、市场信号与治理结论汇聚于同一审计工作台。</div>"
        "</div><div class='command-health'>"
        f"{health_html}</div></div></div>",
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    st.markdown(
        "<section id='workflow' class='landing-section-head landing-section-anchor section-reveal'>"
        "<div class='landing-section-index'>02 · RESEARCH WORKFLOW</div>"
        "<div><div class='landing-section-title'>研究流程</div>"
        "<div class='landing-section-copy'>从招股书输入到最终审阅，四个阶段保持证据、状态与限制可追溯。</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )
    steps = (
        ("01", "招股书解析", "上传真实招股书并建立可追溯的文档来源。"),
        ("02", "风险与 Evidence", "识别财务、法律与业务风险，并绑定原文证据。"),
        ("03", "市场与模型", "接入可用的 Market-X、规则信号与冻结模型结果。"),
        ("04", "审阅与报告", "保留冲突与不确定性，形成可审计的最终报告。"),
    )
    cards = []
    for number, title, copy in steps:
        cards.append(
            "<div class='editorial-step'>"
            f"<div class='editorial-step-no'>{escape(number)}</div>"
            f"<div class='editorial-step-title'>{escape(title)}</div>"
            f"<div class='editorial-step-copy'>{escape(copy)}</div>"
            "</div>"
        )
    st.markdown("<div class='editorial-stepper'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_product_capabilities() -> None:
    """Render truthful product capabilities with decorative, data-free visuals."""

    evidence_image = _asset_png_data_uri("capabilities/capability_evidence_review.png")
    fusion_image = _asset_png_data_uri("capabilities/capability_cross_channel_fusion.png")
    review_image = _asset_png_data_uri("capabilities/capability_human_review_report.png")
    st.markdown(
        "<section id='capabilities' class='landing-section-head landing-section-anchor section-reveal'>"
        "<div class='landing-section-index'>03 · PRODUCT CAPABILITIES</div>"
        "<div><div class='landing-section-title'>核心能力</div>"
        "<div class='landing-section-copy'>所有能力均对应当前系统已有的受治理输出；右侧视觉为无数据的界面抽象，不代表分析结论。</div></div>"
        "</section>"
        "<div class='capability-stack'>"
        "<section class='capability-band'><div class='capability-copy'><div class='capability-no'>01 / 02</div>"
        "<div class='capability-title'>证据驱动的多领域风险审阅</div>"
        "<div class='capability-text'>Financial、Legal 与 Business 风险从招股书 Evidence 出发，保留原文、PDF 页码、Calculation 与 Verifier 状态。</div>"
        "<div class='capability-list'><div>Evidence traceability</div><div>Financial / Legal / Business</div></div></div>"
        f"<figure class='capability-visual'><div class='capability-image-frame'><img class='capability-image' src='{evidence_image}' alt='证据驱动的多领域风险审阅示意图'></div>"
        "<figcaption class='capability-caption'>界面示意 · 不代表当前案例分析结果</figcaption></figure></section>"
        "<section class='capability-band reverse'><div class='capability-copy'><div class='capability-no'>03</div>"
        "<div class='capability-title'>跨通道风险融合</div><div class='capability-text'>Document、Market、Rule 与 Model 通道按真实可用状态进入综合审阅；不可用、部分可用与失败不会被界面掩盖。</div>"
        "<div class='capability-list'><div>Governed channel status</div><div>Conflict-aware synthesis</div></div></div>"
        f"<figure class='capability-visual'><div class='capability-image-frame'><img class='capability-image' src='{fusion_image}' alt='跨通道风险融合示意图'></div>"
        "<figcaption class='capability-caption'>界面示意 · 不代表当前案例分析结果</figcaption></figure></section>"
        "<section class='capability-band'><div class='capability-copy'><div class='capability-no'>04 / 05</div>"
        "<div class='capability-title'>人工复核与结构化报告</div><div class='capability-text'>机器结论与人工决定并列保留，最终输出可下载的 Markdown 研究报告与结构化 JSON 审计结果。</div>"
        "<div class='capability-list'><div>Human Review sidecar</div><div>Final Report / Downloads</div></div></div>"
        f"<figure class='capability-visual'><div class='capability-image-frame'><img class='capability-image' src='{review_image}' alt='人工复核与结构化报告示意图'></div>"
        "<figcaption class='capability-caption'>界面示意 · 不代表当前案例分析结果</figcaption></figure></section>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_landing_runtime(runtime_label: str) -> None:
    """Close the landing page with quiet product and real runtime metadata."""

    llm_status = "待运行确认" if "AI" in runtime_label else "当前模式未启用"
    logo_uri = _asset_png_data_uri("ipo_risk_logo.png")
    st.markdown(
        "<footer id='runtime' class='product-footer landing-section-anchor'>"
        "<div class='product-footer-grid'>"
        "<div class='footer-brand'>"
        f"<a data-section='overview' href='#overview' aria-label='返回概览'><img class='footer-brand-logo' src='{logo_uri}' alt='IPO Risk'></a>"
        "<div class='footer-brand-copy'>从招股书证据到最终审阅，构建可追溯、可核验的 IPO 风险研究链。</div>"
        "</div>"
        "<nav class='footer-product' aria-label='页尾产品导航'><div class='footer-column-title'>产品</div>"
        "<div class='footer-product-links'>"
        "<a class='footer-product-link' data-section='overview' href='#overview'>概览</a>"
        "<a class='footer-product-link' data-section='new-analysis' href='#new-analysis'>新建分析</a>"
        "<a class='footer-product-link' data-section='workflow' href='#workflow'>研究流程</a>"
        "<a class='footer-product-link' data-section='capabilities' href='#capabilities'>核心能力</a>"
        "</div></nav>"
        "<div class='footer-system'><div class='footer-column-title'>系统状态</div>"
        "<dl class='footer-status-list'>"
        f"<div class='footer-status-row'><dt class='footer-status-label'><i class='footer-status-dot'></i>Runtime</dt><dd class='footer-status-value'>{escape(runtime_label)}</dd></div>"
        f"<div class='footer-status-row'><dt class='footer-status-label'><i class='footer-status-dot'></i>LLM</dt><dd class='footer-status-value'>{escape(llm_status)}</dd></div>"
        "<div class='footer-status-row'><dt class='footer-status-label'><i class='footer-status-dot'></i>Market-X</dt><dd class='footer-status-value'>等待案例运行</dd></div>"
        "<div class='footer-status-row'><dt class='footer-status-label'><i class='footer-status-dot'></i>Model</dt><dd class='footer-status-value'>等待案例运行</dd></div>"
        "</dl></div></div>"
        "<div class='footer-lower'><div class='footer-disclaimer'>"
        "<div>本工具用于 IPO 风险研究与审阅，不构成投资、证券、法律或交易建议。</div>"
        "<div>分析结果受当前 Evidence、Market、Model 与运行配置的可用性限制。</div>"
        "</div><div class='footer-meta'>IPO Risk Review · v0.4.5</div></div>"
        "</footer>",
        unsafe_allow_html=True,
    )


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


def status_badge(value: object, *, label: object | None = None) -> str:
    """Return a safe, text-labelled semantic status badge."""

    text = status_label(value) if label is None else str(label)
    return f"<span class='status-chip {_status_tone(value)}'>{escape(text)}</span>"


def section_header(title: str, copy: str = "", eyebrow: str = "") -> None:
    """Render a compact section heading without introducing business semantics."""

    eyebrow_html = f"<div class='section-eyebrow'>{escape(eyebrow)}</div>" if eyebrow else ""
    copy_html = f"<div class='section-copy'>{escape(copy)}</div>" if copy else ""
    st.markdown(
        "<div class='section-head'>"
        f"{eyebrow_html}<div class='section-title'>{escape(title)}</div>{copy_html}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_metric_grid(cards: Iterable[tuple[object, object, object]]) -> None:
    """Render non-truncating KPI cards from already-computed label/value/context triples."""

    html = []
    for label, value, context in cards:
        html.append(
            "<div class='metric-card'>"
            f"<div class='metric-label'>{escape(str(label))}</div>"
            f"<div class='metric-value'>{escape(str(value))}</div>"
            f"<div class='metric-context'>{escape(str(context))}</div>"
            "</div>"
        )
    st.markdown("<div class='metric-grid'>" + "".join(html) + "</div>", unsafe_allow_html=True)


def render_state_panel(title: str, status: object, copy: str) -> None:
    """Render an honest empty/partial/unavailable state with its reason visible."""

    st.markdown(
        "<div class='state-panel'><div style='display:flex;justify-content:space-between;"
        "align-items:center;gap:.65rem;flex-wrap:wrap'>"
        f"<div class='state-panel-title'>{escape(title)}</div>{status_badge(status)}"
        f"</div><div class='state-panel-copy'>{escape(copy)}</div></div>",
        unsafe_allow_html=True,
    )


def _table_badge_tone(value: object, kind: str) -> str:
    """Map an existing display value to presentation-only badge colours."""

    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if kind == "domain":
        if normalized in {"财务风险", "financial"}:
            return "badge-domain-financial"
        if normalized in {"法律与合规", "legal"}:
            return "badge-domain-legal"
        return "badge-domain-business"
    if kind == "risk":
        if normalized in {"low", "低"}:
            return "badge-success"
        if normalized in {"medium", "中"}:
            return "badge-warning"
        if normalized in {"high", "critical", "高", "严重"}:
            return "badge-danger"
        return "badge-neutral"
    if kind == "status":
        if normalized in {
            "available", "completed", "verified", "matched", "resolved", "accepted",
            "可用", "已完成", "已验证", "已匹配", "已解决", "已执行", "接受（accept）",
        }:
            return "badge-success"
        if normalized in {
            "partial", "partially_resolved", "needs_review", "pending", "rechecking",
            "部分可用", "部分解决", "待复核", "待处理", "复核中", "需继续跟进（needs_follow_up）",
        }:
            return "badge-warning"
        if normalized in {"failed", "rejected", "unresolved", "error", "失败", "已驳回", "未解决", "驳回（reject）"}:
            return "badge-danger"
        return "badge-neutral"
    return "badge-category"


def _table_badge(value: object, kind: str) -> str:
    text = "" if value is None else str(value)
    return f"<span class='data-badge {_table_badge_tone(value, kind)}'>{escape(text)}</span>"


def render_modern_table(
    rows: Iterable[dict[str, object]],
    *,
    badge_columns: dict[str, str] | None = None,
    compact: bool = False,
) -> None:
    """Render a compact read-only table without changing row values or order."""

    data = [dict(row) for row in rows]
    if not data:
        return
    columns: list[str] = []
    for row in data:
        for key in row:
            if key not in columns:
                columns.append(key)
    badges = badge_columns or {}
    header = "".join(f"<th scope='col'>{escape(str(column))}</th>" for column in columns)
    body_rows = []
    for row in data:
        cells = []
        for column in columns:
            value = row.get(column, "")
            content = _table_badge(value, badges[column]) if column in badges else escape("" if value is None else str(value))
            cells.append(f"<td>{content}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    scroll_class = " modern-table-scroll" if len(data) > 8 else ""
    compact_class = " modern-table-compact" if compact else ""
    st.markdown(
        f"<div class='modern-table-shell{scroll_class}{compact_class}'><table class='modern-data-table'>"
        f"<thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_profile_grid(items: Iterable[tuple[object, object]]) -> None:
    """Render compact label/value facts without altering their values."""

    cards = []
    for label, value in items:
        label_text = str(label)
        if label_text == "匹配状态":
            rendered_value = _table_badge(value, "status")
        elif label_text == "证券类别" and str(value).lower() not in {"", "unavailable"}:
            rendered_value = _table_badge(value, "category")
        else:
            rendered_value = escape(str(value))
        cards.append(
            "<div class='profile-item'>"
            f"<div class='profile-label'>{escape(label_text)}</div>"
            f"<div class='profile-value'>{rendered_value}</div>"
            "</div>"
        )
    st.markdown("<div class='profile-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_trace_timeline(rows: Iterable[dict[str, object]]) -> None:
    """Render the existing trace rows as a compact audit timeline."""

    cards = []
    for row in rows:
        status = row.get("状态") or "unavailable"
        agent = row.get("Agent") or row.get("类型") or "未标识 Agent"
        action = row.get("动作") or row.get("无 Evidence 原因") or "未记录动作说明"
        cards.append(
            "<div class='trace-card'>"
            f"<div class='trace-index'>{escape(str(row.get('#', ''))).zfill(2)}</div>"
            f"<div class='trace-agent'>{escape(str(agent))}</div>"
            f"<div class='trace-action'>{escape(str(action))}</div>"
            f"{status_badge(status, label=status)}"
            "</div>"
        )
    st.markdown("<div class='trace-list'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_case_breadcrumb(payload: dict[str, Any]) -> None:
    """Render the result workspace hierarchy without changing case state."""

    profile = payload.get("profile") or {}
    company = escape(str(profile.get("company_name") or "不可用"))
    stock_code = escape(str(profile.get("stock_code") or "不可用"))
    st.markdown(
        "<nav id='case-workspace' class='result-breadcrumb landing-section-anchor' aria-label='面包屑导航'>"
        "<a href='#result-overview'>IPO Risk Review</a><span class='result-breadcrumb-separator'>›</span>"
        "<span>IPO 分析</span><span class='result-breadcrumb-separator'>›</span>"
        f"<span class='result-breadcrumb-current' aria-current='page'>{company} · {stock_code}</span></nav>",
        unsafe_allow_html=True,
    )


def render_case_header(payload: dict[str, Any]) -> None:
    profile = payload.get("profile") or {}
    company = escape(str(profile.get("company_name") or "不可用"))
    stock_code = escape(str(profile.get("stock_code") or "不可用"))
    listing_date = escape(str(profile.get("listing_date") or "不可用"))
    industry = escape(str(profile.get("industry") or "不可用"))
    raw_status = payload.get("runtime_completion_status") or payload.get("status") or "unavailable"
    st.markdown(
        "<div class='case-shell result-enter'><div>"
        f"<div class='case-name'>{company}<span class='case-code'>{stock_code}</span></div>"
        f"<div class='case-meta'>行业 · {industry}&nbsp;&nbsp;&nbsp;上市日期 · {listing_date}</div>"
        "</div>"
        f"{status_badge(raw_status)}"
        "</div>",
        unsafe_allow_html=True,
    )


def render_executive_snapshot(payload: dict[str, Any]) -> None:
    prediction = payload.get("prediction") or {}
    counts = payload.get("risk_status_counts") or {}
    states = channel_state_map(payload)
    available_market, total_market = available_market_observation_count(payload)
    final = payload.get("final_supervision") or {}
    view = executive_supervisor_view(payload)
    assessment_status = view["title"] if final else "综合判断不可用"
    assessment_copy = view["body"] if final else "本次运行没有可展示的 Supervisor 综合结论。"
    rule_level = risk_level_label(prediction.get("risk_level"))
    channel_rows = "".join(
        "<div class='channel-line'>"
        f"<div class='channel-line-name'>{escape(_CHANNEL_LABELS[channel])}</div>"
        f"{status_badge(states.get(channel, 'unavailable'))}</div>"
        for channel in ("document", "market", "model", "rule")
    )
    st.markdown(
        "<div class='bento-shell result-enter'>"
        "<div class='assessment-panel'><div class='assessment-label'>OVERALL ASSESSMENT</div>"
        f"<div class='assessment-status'>{escape(assessment_status)}</div>"
        f"<div class='assessment-risk'>规则风险等级 · {escape(rule_level)}</div>"
        f"<div class='assessment-copy'>{escape(str(assessment_copy))}</div></div>"
        "<div class='health-panel'><div class='health-panel-title'>Run / Channel Health</div>"
        f"<div class='channel-list'>{channel_rows}</div></div></div>",
        unsafe_allow_html=True,
    )
    kpis = (
        (counts.get("verified", 0), "Verified Risks"),
        (evidence_reference_count(payload), "Evidence"),
        (sum(view["conflict_counts"].values()), "Conflicts"),
        (prediction.get("risk_score", "不可用"), "Rule Score"),
    )
    st.markdown(
        "<div class='bento-kpis'>"
        + "".join(
            "<div class='bento-kpi'>"
            f"<div class='bento-kpi-value'>{escape(str(value))}</div>"
            f"<div class='bento-kpi-label'>{escape(label)}</div></div>"
            for value, label in kpis
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    if total_market:
        st.caption(f"Market-X 可用观测 {available_market}/{total_market}。")
    if final and view["mode"] == "deterministic_fallback" and view["llm_status"] == "unavailable":
        render_state_panel(
            "LLM Final Supervisor 不可用",
            "unavailable",
            f"{view['llm_reason'] or '未说明原因'}。当前展示确定性 Document Supervisor 汇总。",
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
            f"{status_badge(raw_status)}"
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
        tone = _status_tone(raw_status).replace("status-", "tone-")
        cards.append(
            f"<div class='pipeline-card {tone}' title='{escape(stage_summary_zh(stage), quote=True)}'>"
            f"<div class='pipeline-node'>{escape(ordinal.zfill(2))}</div>"
            f"<div class='pipeline-title'>{escape(stage_title_zh(stage))}</div>"
            "<div class='pipeline-status'><span class='pipeline-dot'></span>"
            f"{escape(status_label(raw_status))}</div></div>"
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
