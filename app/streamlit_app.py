"""Streamlit presentation layer; it only calls IPOAnalysisService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from html import escape
from pathlib import Path
import json
import os

import streamlit as st

from competition_ui import (
    apply_competition_theme,
    available_market_observation_count,
    market_degradation_summary,
    market_runtime_summary,
    reader_market_model_summary,
    channel_state_map,
    domain_label,
    domain_summary_rows,
    localize_market_observation_rows,
    render_case_header,
    render_case_breadcrumb,
    render_empty_state,
    executive_supervisor_view,
    render_executive_snapshot,
    render_metric_grid,
    render_pipeline_strip,
    render_product_capabilities,
    render_profile_grid,
    render_product_header,
    render_product_navigation,
    reader_markdown_report,
    render_landing_runtime,
    render_modern_table,
    render_state_panel,
    render_trace_timeline,
    report_section_title,
    report_section_summary_zh,
    risk_display_name,
    risk_inventory_rows,
    risk_level_label,
    stage_notice_zh,
    stage_status_label,
    stage_summary_zh,
    stage_title_zh,
    stage_unblocked_items_zh,
    section_header,
    status_label,
)
from competition_runtime_view import (
    RESOLUTION_LABELS,
    conflict_rows,
    conflict_status_counts,
    judgement,
    recheck_outcomes,
    supervision_synthesis,
    trace_rows,
    traceability,
    traceability_metrics,
)
from evidence_viewer_compat import render_evidence_viewer
from human_review_ui import render_human_review
from issuer_identity_ui import render_issuer_identity_inputs
from judge_copy import (
    risk_conclusion_zh,
    risk_reasoning_annotation,
    supervisor_summary_zh,
    to_simplified_ui,
    verifier_note_zh,
)
from ipo_risk.runtime.demo_replay import (
    available_recorded_cases,
    load_recorded_case,
    replay_screenshots,
)
from ipo_risk.runtime.review_projection import resolve_identity
from pipeline_stages import resolve_stages
from presenters import (
    DOMAINS,
    build_analysis_request,
    markdown_report,
    result_payload,
    safe_download_stem,
    temporary_pdf,
    validate_pdf_upload,
)
from ipo_risk.schemas import IPOAnalysisResult
from ipo_risk.core.config import load_settings
from ipo_risk.services.human_review_service import HumanReviewService
from ipo_risk.services.analysis_service import IPOAnalysisService


# Where the offline demonstration bundle is looked for. A bundle is a recorded
# run copied by scripts/build_v045_demo_bundle.py; replaying it needs no network,
# no provider credentials and no prospectus PDF.
DEMO_BUNDLE_ENV = "IPO_RISK_DEMO_BUNDLE"
DEFAULT_DEMO_BUNDLE = Path("reports/v045_demo_bundle")

SCENARIO_COMPETITION_OFFLINE = "v0.4.5 比赛版（离线）"
SCENARIO_COMPETITION_AI = "v0.4.5 比赛版（AI）"
SCENARIO_PREDICTOR_FAILURE = "预测器故障降级演示"
SCENARIO_REPLAY = "已记录运行回放"
SCENARIO_V04_OFFLINE = "v0.4 离线模式 + Final Supervisor"
SCENARIO_V04_OFFLINE_TABLE = "v0.4 离线模式（表格）+ Final Supervisor"
SCENARIO_V04_AI_TABLE = "v0.4 AI 模式（表格）+ Final Supervisor"
DEFAULT_ANALYSIS_SCENARIO = SCENARIO_COMPETITION_AI

SCENARIOS = {
    SCENARIO_COMPETITION_OFFLINE: ("configs/v045_competition_offline.yaml", True),
    SCENARIO_COMPETITION_AI: ("configs/v045_competition_ai.yaml", True),
    "Mock 架构演示": ("configs/mock.yaml", False),
    "v0.2 真实现金可支撑期切片": ("configs/real_pdf.yaml", True),
    "v0.3 增强版（离线）": ("configs/v03_offline.yaml", True),
    "v0.3 增强版（离线 + 表格）": ("configs/v03_offline_table.yaml", True),
    "v0.3 增强版（AI）": ("configs/v03_ai.yaml", True),
    "v0.3 增强版（AI + 表格）": ("configs/v03_ai_table.yaml", True),
    SCENARIO_V04_OFFLINE: ("configs/v04_offline.yaml", True),
    SCENARIO_V04_OFFLINE_TABLE: ("configs/v04_offline_table.yaml", True),
    "v0.4 AI 模式 + Final Supervisor": ("configs/v04_ai.yaml", True),
    SCENARIO_V04_AI_TABLE: ("configs/v04_ai_table.yaml", True),
    SCENARIO_PREDICTOR_FAILURE: ("configs/mock.yaml", False),
}

MARKET_FEATURE_LABELS = {
    "ipo_count_30d": "近 30 日前序 IPO 数量",
    "ipo_count_60d": "近 60 日前序 IPO 数量",
    "log_prior_ipo_funds_raised_30d": "近 30 日前序 IPO 募资规模",
    "log_prior_ipo_funds_raised_60d": "近 60 日前序 IPO 募资规模",
    "prior_ipo_funds_raised_30d_sample_count": "近 30 日募资规模样本数",
    "prior_ipo_funds_raised_60d_sample_count": "近 60 日募资规模样本数",
    "recent_ipo_break_rate": "近期 IPO 首日破发率",
    "recent_ipo_return_5d": "近期 IPO 上市后 5 日平均回报",
    "recent_ipo_1d_sample_count": "近期 IPO 首日表现样本数",
    "recent_ipo_5d_sample_count": "近期 IPO 五日表现样本数",
    "same_industry_ipo_count_180d": "近 180 日同业 IPO 数量",
    "same_industry_recent_break_rate": "近期同业 IPO 首日破发率",
    "same_industry_recent_return_5d": "近期同业 IPO 上市后 5 日平均回报",
    "same_industry_recent_1d_sample_count": "近期同业 IPO 首日表现样本数",
    "same_industry_recent_5d_sample_count": "近期同业 IPO 五日表现样本数",
}

MARKET_UNIT_LABELS = {
    "count": "个",
    "ratio": "比例",
    "log_currency": "对数金额",
}


def _display_value(value: object) -> str:
    if value in (None, "", {}):
        return "不可用"
    text = str(value)
    labels = {
        "Unavailable": "不可用", "unavailable": "不可用",
        "catalog": "官方目录", "matched": "已匹配", "unmatched": "未匹配",
        "unknown": "未知", "available": "可用", "partial": "部分可用",
    }
    return labels.get(text, to_simplified_ui(text))


def _display_score(value: object, *, exact: bool = False) -> str:
    if value in (None, ""):
        return "不可用"
    if exact:
        return str(value)
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return _display_value(value)


def _market_feature_label(value: object) -> str:
    technical_name = str(value or "").removeprefix("market_core__")
    return MARKET_FEATURE_LABELS.get(technical_name, _display_value(technical_name))


def _front_market_observation_rows(
    observations: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Project Market-X observations into reader language without source internals."""

    rows: list[dict[str, object]] = []
    for observation in localize_market_observation_rows(
        observations, include_reason_codes=False
    ):
        value = observation.get("数值")
        if isinstance(value, float):
            value = str(int(value)) if value.is_integer() else f"{value:.3f}".rstrip("0").rstrip(".")
        elif value is not None:
            value = str(value)
        rows.append(
            {
                "指标": _market_feature_label(observation.get("指标")),
                "数值": "不可用" if value is None else value,
                "单位": MARKET_UNIT_LABELS.get(
                    str(observation.get("单位") or ""),
                    _display_value(observation.get("单位")),
                ),
                "状态": observation.get("可用状态") or "不可用",
                "说明": observation.get("缺失原因") or "已取得上市前可核验数据",
            }
        )
    return rows


def _model_driver_rows(drivers: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for driver in drivers[:5]:
        feature = driver.get("feature") or driver.get("feature_name") or driver.get("name") or "未命名特征"
        contribution = driver.get("shap_value")
        if contribution is None:
            contribution = driver.get("contribution")
        try:
            numeric_contribution = float(contribution)
            if numeric_contribution > 0:
                direction = "推高风险"
            elif numeric_contribution < 0:
                direction = "降低风险"
            else:
                direction = "影响中性"
        except (TypeError, ValueError):
            direction = _display_value(driver.get("direction"))
        rows.append({"影响因素": _market_feature_label(feature), "影响方向": direction})
    return rows


def _clear_result() -> None:
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("analysis_scenario", None)
    st.session_state.pop("prospectus_bytes", None)
    # A replay must never outlive the result it belongs to: a stale replay
    # banner on a live run, or stale screenshots under a new run, would both
    # misattribute what is on screen.
    st.session_state.pop("replay_provenance", None)
    st.session_state.pop("replay_screenshots", None)


def _demo_bundle_dir() -> Path:
    configured = os.getenv(DEMO_BUNDLE_ENV)
    return Path(configured) if configured else DEFAULT_DEMO_BUNDLE


def _load_replay(case_dir: Path) -> None:
    """Put one recorded case on screen, labelled as the recording it is."""

    matrix_path = case_dir.parent / "summary.json"
    matrix = {}
    if matrix_path.is_file():
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            matrix = {}
    case = load_recorded_case(case_dir, matrix)
    _clear_result()
    # Validated through the same schema the service produces, so every workspace
    # reads a recorded run exactly as it reads a live one.
    st.session_state["analysis_result"] = IPOAnalysisResult.model_validate(case.result)
    st.session_state["analysis_scenario"] = SCENARIO_REPLAY
    st.session_state["replay_provenance"] = case.provenance
    st.session_state["replay_screenshots"] = replay_screenshots(case)


def _render_replay_banner(provenance: dict, *, expert: bool = False) -> None:
    """State, above everything, that this is a recording rather than a run."""

    if not expert:
        st.warning(
            "**回放模式** · 这是一次已记录运行的回放，不是正在进行的实时分析。"
            "页面中的风险、证据和通道状态均来自该次记录。"
        )
        return
    st.warning(
        f"**回放模式** · {provenance.get('statement')}\n\n"
        f"- 来源案例 `{provenance.get('case_id')}` · 分析标识 `{provenance.get('analysis_id') or '—'}`\n"
        f"- 运行配置 `{provenance.get('config') or '—'}` · 代码版本 "
        f"`{provenance.get('code_base_sha') or '—'}`"
        + ("（工作树有未提交改动）" if provenance.get("code_base_dirty") else "")
        + "\n"
        f"- 招股书 SHA-256 `{provenance.get('prospectus_sha256') or '—'}`"
    )


def _render_replay_picker(container=None) -> None:
    """Render the governed replay controls inside the technical backend."""

    container = container or st
    bundle = _demo_bundle_dir()
    container.markdown("#### 演示回放")
    cases = available_recorded_cases(bundle)
    if not cases:
        container.caption(
            f"未找到演示备份（{bundle}）。先运行 scripts/build_v045_demo_bundle.py 生成，"
            f"或用 {DEMO_BUNDLE_ENV} 指定目录。"
        )
        return
    labels = {path.name: path for path in cases}
    chosen = container.selectbox("已记录运行", list(labels), key="replay_case_choice")
    if container.button("载入回放", width="stretch", key="backend_load_replay"):
        try:
            _load_replay(labels[chosen])
        except (FileNotFoundError, ValueError) as exc:
            container.error(f"该记录无法回放：{exc}")
        else:
            st.session_state["_pending_product_view"] = "case"
            st.rerun()
    container.caption("回放不联网、不调用模型、不需要 PDF；载入后会返回案例工作台。")


def _friendly_error(message: str) -> str:
    known = {
        "Please upload a prospectus PDF.": "请先上传招股书 PDF。",
        "Only .pdf files are accepted.": "仅支持 PDF 文件。",
        "The uploaded PDF is empty.": "上传的 PDF 为空，请重新选择文件。",
        "The uploaded PDF exceeds the 200 MB size limit.": "上传的 PDF 超过 200 MB 限制。",
        "The uploaded file does not have a valid PDF header.": "上传文件不是有效的 PDF。",
    }
    return known.get(message, message)


def _analysis_activity(message: str):
    """Render a presentation-only indeterminate activity state."""

    slot = st.empty()
    slot.markdown(
        "<div class='analysis-activity'>"
        f"<div class='analysis-activity-copy'>{escape(message)}</div>"
        "<div class='analysis-activity-track'><div class='analysis-activity-bar'></div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    return slot


def _run_analysis(
    *,
    scenario: str,
    config_path: str,
    needs_pdf: bool,
    company: str,
    code: str,
    listing: date,
    uploaded,
) -> tuple[IPOAnalysisResult, bytes | None]:
    settings = load_settings(config_path)
    if scenario == SCENARIO_PREDICTOR_FAILURE:
        settings = replace(settings, predictor="fault")

    if needs_pdf:
        if uploaded is None:
            raise ValueError("Please upload a prospectus PDF.")
        content = uploaded.getvalue()
        validate_pdf_upload(uploaded.name, content)
        with temporary_pdf(content) as prospectus_path:
            request = build_analysis_request(
                company_name=company,
                stock_code=code,
                listing_date=listing,
                prospectus_path=prospectus_path,
                use_mock=False,
                workflow_version=settings.workflow_version,
            )
            activity = _analysis_activity("正在分析招股书并建立原文证据链")
            try:
                with st.spinner("正在解析招股书、运行各分析模块、接入可用通道并汇总结果……"):
                    result = IPOAnalysisService(settings=settings).analyze(request)
                return result, content
            finally:
                activity.empty()

    request = build_analysis_request(
        company_name=company,
        stock_code=code,
        listing_date=listing,
        prospectus_path="mock://prospectus",
        use_mock=True,
        workflow_version=settings.workflow_version,
    )
    activity = _analysis_activity("正在运行分析并汇总研究结果")
    try:
        with st.spinner("正在运行分析……"):
            result = IPOAnalysisService(settings=settings).analyze(request)
        return result, None
    finally:
        activity.empty()


def _risk_level_tone(level: object) -> str:
    normalized = str(level or "").lower()
    if normalized in {"critical", "high"}:
        return "status-bad"
    if normalized == "medium":
        return "status-warn"
    return "status-muted"


def _verification_tone(status: object) -> str:
    normalized = str(status or "").lower()
    if normalized == "verified":
        return "status-good"
    if normalized in {"needs_review", "pending"}:
        return "status-warn"
    if normalized == "rejected":
        return "status-bad"
    return "status-muted"


def _render_risk(risk: dict[str, object], *, expert: bool = False) -> None:
    risk_code = str(risk.get("risk_code", "Unavailable"))
    level = str(risk.get("level", "Unavailable"))
    verification = str(risk.get("verification_status", "Unavailable"))
    score = _display_value(risk.get("score"))

    with st.container(border=True):
        code_html = f"<span class='risk-chip'>{escape(risk_code)}</span>" if expert else ""
        st.markdown(
            "<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:.7rem;"
            "flex-wrap:wrap;margin-bottom:.25rem'>"
            f"<div><div class='section-title'>{escape(risk_display_name(risk_code))}</div></div>"
            f"{code_html}</div>",
            unsafe_allow_html=True,
        )
        score_html = f"<span class='risk-chip'>规则评分 {escape(score)}</span>" if expert else ""
        st.markdown(
            "<div style='display:flex;gap:.4rem;flex-wrap:wrap;margin:-.2rem 0 .7rem 0'>"
            f"<span class='risk-chip {_risk_level_tone(level)}'>风险等级：{escape(risk_level_label(level))}</span>"
            f"<span class='risk-chip {_verification_tone(verification)}'>{escape(status_label(verification))}</span>"
            f"{score_html}"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**结论**")
        st.write(risk_conclusion_zh(risk))

        if not expert:
            annotation = risk_reasoning_annotation(risk)
            st.markdown("**推理注释**")
            st.markdown(
                "<div class='reasoning-note'>"
                f"<div><span>形成依据</span>{escape(annotation['basis'])}</div>"
                f"<div><span>风险影响</span>{escape(annotation['impact'])}</div>"
                f"<div><span>判断边界</span>{escape(annotation['boundary'] or '当前没有额外验证限制。')}</div>"
                f"<div><span>复核重点</span>{escape(annotation['review_focus'])}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        notes = risk.get("verification_notes")
        if notes:
            st.caption(f"复核说明 · {verifier_note_zh(notes)}")
        if risk.get("category") in {"legal", "business"}:
            if expert:
                st.caption(
                    "当前 v0.3 文档策略下，法律与业务风险等级仍属于暂定结果；"
                    "确定性规则不会自动将其提升为高或极高。"
                )
            else:
                st.caption(
                    "法律与业务事项需要结合条款语境和后续进展审阅；"
                    "当前等级不会因单一规则自动上调。"
                )

        evidence_items = risk.get("evidence") or []
        if evidence_items:
            st.markdown(f"**原文证据 · {len(evidence_items)} 条**")
            for index, evidence in enumerate(evidence_items, start=1):
                evidence_id = _display_value(evidence.get("evidence_id"))
                page = _display_value(evidence.get("page"))
                label = f"证据 {index} · 招股书第 {page} 页"
                if expert:
                    label = f"{evidence_id} · PDF 第 {page} 页"
                with st.expander(label, expanded=False):
                    st.write(evidence.get("text") or "该条证据暂无可展示的原文。")
        else:
            render_state_panel(
                "原文证据未附着",
                verification,
                "当前没有关联原文证据，因此该风险不能视为已完成验证。",
            )

        calculation = risk.get("calculation")
        if expert and calculation:
            with st.expander("确定性 Calculation", expanded=False):
                st.json(calculation)

        if expert and risk.get("metadata"):
            with st.expander("结构化事实 / metadata", expanded=False):
                st.json(risk["metadata"])


def _render_sidebar_status(payload: dict[str, object], stages) -> None:
    profile = payload.get("profile") or {}
    st.sidebar.markdown("<div class='sidebar-section-label'>当前案例</div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        f"**{_display_value(profile.get('stock_code'))}** · {_display_value(profile.get('company_name'))}"
    )
    completion = payload.get("runtime_completion_status") or payload.get("status")
    st.sidebar.caption(f"运行结果 · {status_label(completion)}")
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        gate = f" · {stage.blocking_gate}" if stage.blocking_gate else ""
        st.sidebar.caption(f"{stage.ordinal}. {stage_title_zh(stage)} · {stage_status_label(stage)}{gate}")


def _render_overview(payload: dict[str, object], stages) -> None:
    profile = payload["profile"]

    section_header("IPO 概览", "发行资料、数据来源与案例匹配状态。", "案例信息")
    render_profile_grid(
        (
            ("公司", _display_value(profile.get("company_name"))),
            ("股票代码", _display_value(profile.get("stock_code"))),
            ("上市日期", _display_value(profile.get("listing_date"))),
            ("行业", _display_value(profile.get("industry"))),
            ("发行价", _display_value(profile.get("issue_price"))),
            ("发行规模", _display_value(profile.get("issue_size"))),
            ("证券类别", _display_value(profile.get("security_category"))),
            ("IPO 数据来源", _display_value(profile.get("source"))),
            ("匹配状态", _display_value(profile.get("match_status"))),
        )
    )

    left, right = st.columns((1.05, 1.45))
    with left:
        section_header("风险覆盖", "财务、法律与业务风险覆盖情况。", "覆盖情况")
        render_modern_table(
            domain_summary_rows(payload),
            badge_columns={"领域": "domain", "状态": "status"},
            compact=True,
        )
    with right:
        section_header("风险清单", "正式风险项与原文证据数量。", "风险清单")
        inventory = [
            {
                "领域": row.get("领域"),
                "风险项": row.get("风险项"),
                "等级": row.get("等级"),
                "验证状态": row.get("验证状态"),
                "原文证据": row.get("Evidence"),
            }
            for row in risk_inventory_rows(payload)
            if row.get("验证状态") != "已驳回"
        ]
        if inventory:
            st.dataframe(inventory, hide_index=True, width="stretch")
        else:
            render_state_panel("暂无正式风险项", "unavailable", "本次运行未产出正式风险项；界面不会用低风险或 0 替代未知状态。")

    section_header("七阶段运行链路", "从招股书解析到最终报告的受治理处理链。", "处理流程")
    render_pipeline_strip(stages)
    st.caption("风险等级用于提示审阅优先级，不代表发生概率、股价走势，也不构成投资或法律建议。")


def _render_risks_and_evidence(payload: dict[str, object], *, expert: bool = False) -> None:
    section_header(
        "风险与原文证据",
        "风险结论、验证状态与原文证据优先；技术字段和诊断信息集中放在后台。",
        "招股书风险分析",
    )
    domain_tabs = st.tabs([domain_label(domain) for domain in DOMAINS])
    for domain, tab in zip(DOMAINS, domain_tabs, strict=True):
        with tab:
            domain_data = payload["domains"][domain]
            counts = domain_data["status_counts"]
            visible_risks = [
                risk
                for risk in domain_data["risks"]
                if expert
                or str(risk.get("verification_status") or "").lower() != "rejected"
            ]
            if expert:
                metrics = (
                    ("风险项", domain_data["risk_count"], domain_label(domain)),
                    ("已验证", counts.get("verified", 0), "已完成验证"),
                    ("待复核", counts.get("needs_review", 0), "需要复核"),
                    ("待处理 / 已驳回", counts.get("pending", 0) + counts.get("rejected", 0), "其他状态"),
                )
            else:
                metrics = (
                    ("关注事项", len(visible_risks), domain_label(domain)),
                    ("已验证", counts.get("verified", 0), "已有证据支持"),
                    ("待复核", counts.get("needs_review", 0) + counts.get("pending", 0), "仍需审阅"),
                    (
                        "原文证据",
                        sum(len(risk.get("evidence") or []) for risk in visible_risks),
                        "可回到原文核验",
                    ),
                )
            render_metric_grid(metrics)
            if not visible_risks:
                render_state_panel("该领域暂无正式风险项", domain_data.get("status", "unavailable"), "本次运行未在该领域识别到正式风险项。")
            for risk in visible_risks:
                _render_risk(risk, expert=expert)
            if expert and domain_data["diagnostics"]:
                with st.expander("Agent 诊断信息", expanded=False):
                    st.json(domain_data["diagnostics"])


def _render_reader_market_and_model(payload: dict[str, object]) -> None:
    """Render only the conclusions a research reviewer needs on the case page."""

    signals = reader_market_model_summary(payload)
    section_header(
        "市场与模型解读",
        "把上市前市场环境与模型信号转化为可阅读结论；逐项指标和影响因素集中放在后台。",
        "辅助判断",
    )
    market_col, model_col = st.columns(2, gap="large", vertical_alignment="top")
    with market_col:
        with st.container(border=True):
            section_header("市场环境结论", "说明发行时点的外部环境，不替代招股书基本面。")
            st.markdown(f"#### {signals['market_title']}")
            st.write(signals["market_body"])
            st.info(signals["market_coverage"])
    with model_col:
        with st.container(border=True):
            section_header("模型使用说明", "只说明模型能否辅助审阅以及应如何理解。")
            st.markdown(f"#### {signals['model_title']}")
            st.write(signals["model_body"])
            st.info("模型信号只用于审阅排序，不构成投资、交易或收益预测。")

    with st.container(border=True):
        section_header("评审阅读建议", "先证据、后信号，避免把技术分数当成事实结论。")
        st.write(signals["review_guidance"])


def _render_market_and_model(
    payload: dict[str, object], stages_by_id: dict[str, object], *, expert: bool = False
) -> None:
    if not expert:
        _render_reader_market_and_model(payload)
        return

    section_header(
        "市场与模型信号",
        "展示上市前市场环境、模型信号及其适用边界；缺失信息不会被补成 0。",
        "市场与模型分析",
    )

    left, right = st.columns((1.22, 1))
    with left:
        with st.container(border=True):
            section_header("市场情报", "上市前市场环境与关键观测。")
            market = payload.get("market_context") or {}
            available, total = available_market_observation_count(payload)
            raw_status = market.get("status", "unavailable")
            runtime_rows = market_runtime_summary(payload)
            runtime_path = next(
                (str(row["取值"]) for row in runtime_rows if row["项目"] == "运行路径"),
                "",
            )
            st.markdown(
                f"**Market-X**  ·  {status_label(raw_status)}  ·  "
                f"可用观测 {available}/{total if total else 0}"
                + (f"  ·  {runtime_path}" if expert and runtime_path else "")
            )
            degradation = market_degradation_summary(payload, include_codes=expert)
            if degradation:
                # "Unavailable" alone reads as a broken pipeline. A governed data
                # boundary is a different fact and has to say so in words, or the
                # honest degradation is only honest to whoever wrote it.
                st.info(f"未取得的观测及原因：{degradation}")
            if expert and runtime_rows:
                # A frozen artifact read and a point-in-time recomputation both
                # render as "available"; which one produced these numbers is the
                # first thing a reader of a never-seen prospectus needs.
                st.dataframe(runtime_rows, hide_index=True, width="stretch")
            observations = market.get("observations") or []
            if observations:
                observation_rows = (
                    localize_market_observation_rows(observations)
                    if expert
                    else _front_market_observation_rows(observations)
                )
                st.dataframe(observation_rows, hide_index=True, width="stretch")
            else:
                empty_copy = (
                    "本次分析没有可展示的 Market-X 观测；具体来源与缺失原因可在下方追溯信息中核验。"
                    if expert
                    else "本次分析没有可展示的市场观测；具体技术原因可在后台的数据审计中查看。"
                )
                render_state_panel("Market-X 观测不可用", raw_status, empty_copy)
            if expert:
                with st.expander("Market-X 数据来源与追溯信息", expanded=False):
                    st.json(market.get("provenance", {}))

    with right:
        with st.container(border=True):
            final = payload.get("final_supervision") or {}
            states = channel_state_map(payload)
            model = final.get("model_prediction")
            section_header("模型 / 规则情报", "冻结模型信号与确定性规则信号对照。")
            if model:
                st.metric("模型评分", _display_score(model.get("score"), exact=expert))
                if model.get("alert") is not None:
                    st.metric("V2 风险初筛告警", "是" if model["alert"] else "否")
                    if expert:
                        st.caption(f"告警策略：{model.get('alert_policy', '不可用')}")
                st.caption("模型评分未经概率校准，只用于风险排序，不能理解为事件发生概率。")
                drivers = model.get("drivers") or []
                if drivers:
                    st.markdown("**主要驱动因素（SHAP）**")
                    st.dataframe(
                        drivers if expert else _model_driver_rows(drivers),
                        hide_index=True,
                        width="stretch",
                    )
            else:
                render_state_panel(
                    "冻结模型结果不可用",
                    states.get("model"),
                    f"该 IPO 暂无可核验的冻结逐案例模型评分；当前通道状态为“{status_label(states.get('model'))}”。",
                )

            prediction = payload.get("prediction") or {}
            st.markdown("**确定性规则信号**")
            rule_cols = st.columns(2)
            rule_cols[0].metric("规则评分", prediction.get("risk_score", "不可用"))
            rule_cols[1].metric("风险等级", risk_level_label(prediction.get("risk_level")))
            st.caption("规则信号用于确定性风险排序，不是概率，也不是收益预测。")

            uncertainty = final.get("uncertainty_statement")
            if uncertainty:
                if expert:
                    st.warning(uncertainty)
                else:
                    st.warning("当前模型结论仍受样本规模与校准状态限制，应与招股书风险和市场环境一并判断。")

    notices = []
    if expert:
        for stage_id in ("market_features", "prediction", "explainability"):
            stage = stages_by_id.get(stage_id)
            if stage is not None:
                notice = stage_notice_zh(stage)
                if notice:
                    notices.append((stage_title_zh(stage), notice))
    if expert and notices:
        with st.expander("当前通道限制", expanded=False):
            for title, notice in notices:
                st.markdown(f"**{title}**")
                st.markdown(notice)


def _render_supervisor_and_report(payload: dict[str, object], result, stages_by_id: dict[str, object]) -> None:
    section_header(
        "Final Supervisor 与最终报告",
        "机器结论、受治理的不确定性与可下载审计成果保持一致。",
        "审计与研究报告",
    )

    stem = safe_download_stem(result.stock_code)
    first, second = st.columns(2)
    first.download_button(
        "下载 Markdown 报告",
        markdown_report(result),
        file_name=f"{stem}-risk-report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    second.download_button(
        "下载结构化 JSON",
        json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{stem}-risk-result.json",
        mime="application/json",
        use_container_width=True,
    )

    final = payload.get("final_supervision") or {}
    if final:
        view = executive_supervisor_view(payload)
        with st.container(border=True):
            st.markdown(f"#### {view['title']}")
            st.write(view["body"])
            uncertainty = final.get("uncertainty_statement")
            if uncertainty:
                st.warning(uncertainty)

            # These are the Document Supervisor's own retained conflicts (PR-G
            # semantics).  The cross-agent Competition conflict layer is a
            # different, larger set and is not summarised by this count.
            conflicts = final.get("conflicts") or []
            if conflicts:
                with st.expander(f"Document Supervisor 保留冲突 · {len(conflicts)}", expanded=False):
                    st.json(conflicts)
            else:
                st.caption(
                    "Document Supervisor 未保留文档内冲突；跨 Agent 的 Competition Conflict "
                    "见「Agent 协作轨迹」工作区。"
                )
    else:
        st.info("当前工作流没有可用的 Final Supervisor 输出。")

    supervision = payload.get("supervision") or {}
    if supervision:
        with st.expander("Document Supervisor 详情", expanded=False):
            st.write(supervision.get("summary", "暂无摘要"))
            st.markdown("**重复风险归并**")
            st.json(supervision.get("duplicate_groups", []))
            st.markdown("**冲突与语义对齐**")
            st.json(supervision.get("conflicts", []))
            st.markdown("**组合发现**")
            st.json(supervision.get("composite_findings", []))
            st.markdown("**规则评分组成**")
            st.json(supervision.get("metadata", {}).get("rule_score_components", []))

    section_header("完整分析报告（13 节）", "按标准报告结构逐节审阅，结构化字段保留在对应章节。", "报告工作区")
    for section in sorted(payload["report_sections"], key=lambda item: item["order"]):
        expanded = section["order"] in {1, 2, 9}
        title = report_section_title(section["order"], section["title"])
        with st.expander(f"{section['order']}. {title}", expanded=expanded):
            st.write(report_section_summary_zh(payload, section))
            if section.get("metadata"):
                with st.expander("章节结构化字段", expanded=False):
                    st.json(section["metadata"])

    stage = stages_by_id.get("final_report")
    if stage is not None:
        notice = stage_notice_zh(stage)
        if notice:
            st.info(notice)


def _render_front_report(payload: dict[str, object], result) -> None:
    """Render the reader-facing conclusion without engineering audit payloads."""

    section_header(
        "综合结论与研究报告",
        "聚焦风险结论、市场与模型边界以及需要继续复核的事项。",
        "最终报告",
    )
    view = executive_supervisor_view(payload, reader=True)
    signals = reader_market_model_summary(payload)
    with st.container(border=True):
        st.markdown(f"#### {view['title']}")
        st.write(view["body"])
        unresolved = view.get("conflict_counts", {}).get("unresolved", 0)
        if unresolved:
            st.warning(f"仍有 {unresolved} 项跨通道冲突没有解决，建议结合相关原文证据继续复核。")
        else:
            st.caption("当前没有未解决的跨通道冲突。")

    stem = safe_download_stem(result.stock_code)
    st.download_button(
        "下载可阅读报告",
        reader_markdown_report(payload),
        file_name=f"{stem}-risk-report.md",
        mime="text/markdown",
        use_container_width=True,
    )

    section_header("报告正文", "按业务主题展开；结构化字段、索引和原始 JSON 可在后台查看。")
    visible_orders = {1, 3, 4, 5, 7, 8, 9, 12, 13}
    reader_titles = {8: "模型信号与不确定性", 9: "综合结论"}
    for section in sorted(payload.get("report_sections") or [], key=lambda item: item["order"]):
        if section.get("order") not in visible_orders:
            continue
        order = section["order"]
        title = reader_titles.get(order, report_section_title(order, section["title"]))
        with st.expander(title, expanded=section["order"] == 1):
            if order == 7:
                st.markdown(f"**{signals['market_title']}**")
                st.write(signals["market_body"])
                st.info(signals["market_coverage"])
            elif order == 8:
                st.markdown(f"**{signals['model_title']}**")
                st.write(signals["model_body"])
                st.caption("具体模型分数、版本和影响因素可在后台的数据审计中核验。")
            elif order == 9:
                st.write(view["body"])
            else:
                st.write(report_section_summary_zh(payload, section))


def _render_system(payload: dict[str, object], stages) -> None:
    section_header(
        "系统信息、追溯与诊断",
        "工程状态与风险结论分层展示；底层配置、错误和运行日志保持可审计。",
        "系统诊断",
    )

    stage_rows = []
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        stage_rows.append(
            {
                "阶段": stage.ordinal,
                "名称": stage_title_zh(stage),
                "状态": stage_status_label(stage),
                "阻塞 Gate": stage.blocking_gate or "",
                "说明": stage_summary_zh(stage),
            }
        )
    st.markdown("#### Pipeline 状态")
    render_modern_table(stage_rows, badge_columns={"状态": "status"})

    with st.expander("阶段限制与待补输出", expanded=False):
        any_notice = False
        for stage in stages:
            notice = stage_notice_zh(stage)
            if notice:
                any_notice = True
                st.markdown(f"**{stage.ordinal}. {stage_title_zh(stage)}**")
                st.markdown(notice)
                items = stage_unblocked_items_zh(stage)
                if items:
                    st.markdown("补齐对应运行资产后可展示：")
                    for item in items:
                        st.markdown(f"- {item}")
        if not any_notice:
            st.write("本次运行没有阶段限制说明。")

    st.markdown("#### 组件状态")
    component_rows = []
    for item in payload["component_statuses"]:
        component_rows.append(
            {
                "组件": item.get("component", ""),
                "模式": item.get("mode", ""),
                "状态": status_label(item.get("status")),
            }
        )
    render_modern_table(
        component_rows,
        badge_columns={"模式": "category", "状态": "status"},
    )

    with st.expander("配置与治理信息", expanded=False):
        st.json(
            {
                "configuration": payload["configuration"],
                "component_modes": payload["component_modes"],
                "governance": payload["governance"],
            }
        )

    errors = payload.get("errors") or []
    if errors:
        with st.expander(f"结构化错误 · {len(errors)}", expanded=False):
            st.json(errors)
    else:
        st.success("本次运行没有记录结构化 workflow error。")

    with st.expander("Agent 运行日志", expanded=False):
        st.json(payload.get("agent_logs") or [])



def _render_supervisor_judgement(payload: dict[str, object]) -> None:
    """Render the LLM Final Supervisor judgement, or state honestly why there is none."""

    synthesis = supervision_synthesis(payload)
    verdict = judgement(payload)
    with st.container(border=True):
        st.markdown("#### LLM Final Supervisor 综合判断")
        if not synthesis:
            st.info("当前运行模式没有启用 LLM Final Supervisor，只有确定性汇总结论。")
            return
        floor = synthesis.get("deterministic_severity_floor")
        if verdict is None:
            st.warning(f"LLM 综合判断不可用：{synthesis.get('reason', '未说明原因')}")
            if floor:
                st.caption(
                    f"确定性风险下限仍为 **{risk_level_label(floor)}**，"
                    "由已验证文档风险直接决定。"
                )
            return

        overall = verdict.get("overall_risk")
        head = st.columns(3)
        head[0].metric("综合风险判断", risk_level_label(overall))
        head[1].metric("确定性风险下限", risk_level_label(floor))
        head[2].metric("是否建议继续复核", "是" if verdict.get("recheck_required") else "否")
        st.caption(
            "LLM 只能在确定性下限之上做解释与升级，不能下调已验证的文档风险，"
            "也不能引入未提供的 risk_id / evidence_id 或任何概率表述。"
        )
        st.markdown("**判断依据**")
        st.write(supervisor_summary_zh(payload))

        findings = verdict.get("key_findings") or []
        st.markdown(f"**关键发现 · {len(findings)}**")
        for index, finding in enumerate(findings, start=1):
            st.markdown(
                f"- 关键发现 {index}：关联 {len(finding.get('risk_ids') or [])} 项风险、"
                f"{len(finding.get('evidence_ids') or [])} 条原文证据。"
            )

        assessments = verdict.get("conflict_assessments") or []
        if assessments:
            with st.expander(f"冲突评述 · {len(assessments)}", expanded=False):
                for item in assessments:
                    st.markdown(f"- `{item.get('conflict_id', '')}` — 该冲突已保留，需结合相关通道结果复核。")

        uncertainties = verdict.get("uncertainties") or []
        if uncertainties:
            st.markdown("**不确定性**")
            for _item in uncertainties:
                st.markdown("- 当前结论仍受证据完整性、通道可用性或待复核事项限制。")

        targets = verdict.get("recheck_targets") or []
        if targets:
            st.markdown("**建议的定向复核对象**")
            for item in targets:
                st.markdown(f"- `{item.get('target', '')}` — 建议对该对象进行定向复核。")

        st.markdown("**最终说明**")
        st.write(supervisor_summary_zh(payload))


def _render_command_center(payload: dict[str, object], stages) -> None:
    section_header("风险指挥中心", "综合判断、通道健康、冲突、案例画像与运行链路。")
    render_executive_snapshot(payload)

    counts = conflict_status_counts(payload)
    if counts:
        section_header("跨通道冲突状态", "已解决、部分解决和待复核的冲突概览。", "冲突摘要")
        render_metric_grid(
            (RESOLUTION_LABELS.get(status, status), count, "跨通道冲突")
            for status, count in sorted(counts.items())
        )
        st.caption("冲突明细与定向复核结论见后台的「轨迹与冲突」。")

    _render_overview(payload, stages)


def _render_agent_trace(payload: dict[str, object], stages) -> None:
    section_header(
        "智能体协作轨迹",
        "智能体 → 原文证据 → 风险 → 冲突 → 重新核验 → 综合审阅；完整的模型提供方、提示词、证据与计算仍可审计。",
        "追溯链路",
    )

    st.markdown(
        "<div class='trace-flow'>"
        "<div class='trace-flow-step'>智能体</div><div class='trace-flow-step'>原文证据</div>"
        "<div class='trace-flow-step'>风险</div><div class='trace-flow-step'>冲突</div>"
        "<div class='trace-flow-step'>重新核验</div><div class='trace-flow-step'>综合审阅</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    metrics = traceability_metrics(payload)
    if metrics:
        section_header("可追溯率", "每项比例均来自本次运行轨迹。", "审计指标")
        st.dataframe(metrics, hide_index=True, width="stretch")
        unresolved = (traceability(payload) or {}).get("unresolved_evidence_ids") or []
        if unresolved:
            st.warning(f"有 {len(unresolved)} 个被引用的 Evidence ID 无法回溯到本次运行的 Evidence 集合。")
            st.json(unresolved)
    else:
        render_state_panel("Agent Trace 不可用", "unavailable", "当前运行模式没有生成 Agent Trace sidecar。")

    conflicts_table = conflict_rows(payload)
    section_header("跨智能体冲突与定向复核", "冲突、参与方、复核状态与保留结论。", "冲突与重新核验")
    if conflicts_table:
        render_modern_table(
            conflicts_table,
            badge_columns={"状态": "status", "定向复核": "status"},
        )
        outcomes = recheck_outcomes(payload)
        with st.expander(f"定向复核执行明细 · {len(outcomes)}", expanded=False):
            st.json(outcomes)
    else:
        render_state_panel("未检出跨 Agent 冲突", "available", "本次运行未记录跨 Agent 冲突；这不改变各风险项自身的验证状态。")

    rows = trace_rows(payload)
    section_header(f"完整事件轨迹 · {len(rows)}", "按运行记录原始顺序呈现，紧凑视图下方保留完整字段表。", "事件时间线")
    if rows:
        render_trace_timeline(rows)
        with st.expander("完整事件字段表", expanded=False):
            st.dataframe(rows, hide_index=True, width="stretch")
        with st.expander("原始 trace sidecar（competition_runtime_v1）", expanded=False):
            st.json((payload.get("component_diagnostics") or {}).get("competition_runtime", {}))
    else:
        render_state_panel("事件轨迹不可用", "unavailable", "本次运行没有可展示的 trace 事件。")

def _render_review_and_report(payload: dict[str, object], result, stages_by_id) -> None:
    section_header("审计工作区", "人工复核与机器最终报告并列，结论互不覆盖。")
    # Resolved through the shared projection so a decision recorded here is filed
    # under the same case_id/run_id the review API uses, and the two surfaces stay
    # joinable.
    _review_case_id, _review_run_id = resolve_identity(payload)
    review_col, report_col = st.columns((0.88, 1.32), gap="large")
    with review_col:
        render_human_review(
            payload,
            analysis_id=result.analysis_id,
            case_id=_review_case_id,
            run_id=_review_run_id,
            service=HumanReviewService(),
        )
    with report_col:
        _render_supervisor_and_report(payload, result, stages_by_id)


def _render_backend_workspace(
    *,
    payload: dict[str, object] | None,
    result,
    stages: list[object],
    stages_by_id: dict[str, object],
) -> None:
    """Collect engineering, governance and review surfaces away from the reader UI."""

    section_header(
        "系统后台",
        "集中管理运行方式、回放、技术审计、智能体轨迹和结构化产物；这里的信息不会改写业务结论。",
        "管理与审计",
    )
    st.info("案例工作台面向研究阅读；本后台面向系统维护、审计复现和内部复核。")

    run_tab, data_tab, trace_tab, review_tab, system_tab = st.tabs(
        ["运行与回放", "数据审计", "轨迹与冲突", "复核与产物", "系统诊断"]
    )

    with run_tab:
        section_header("运行方式", "选择后续新分析使用的运行配置；不会改写当前已生成的案例结果。")
        scenario_names = list(SCENARIOS)
        selected = st.selectbox(
            "运行模式",
            scenario_names,
            key="runtime_scenario",
        )
        selected_config, selected_needs_pdf = SCENARIOS[selected]
        render_profile_grid(
            (
                ("配置文件", selected_config),
                ("需要上传招股书", "是" if selected_needs_pdf else "否"),
                ("外部模型", "启用" if "AI" in selected else "不启用"),
            )
        )
        st.caption("外部服务不可用时，系统仍按正式运行合同安全降级，不会伪造通道结果。")
        replay_provenance = st.session_state.get("replay_provenance")
        if replay_provenance:
            _render_replay_banner(replay_provenance, expert=True)
        st.divider()
        _render_replay_picker(st)
        if result is not None:
            st.divider()
            if st.button("清除当前案例结果", key="backend_clear_result"):
                _clear_result()
                st.session_state["_pending_product_view"] = "new"
                st.rerun()

    with data_tab:
        if payload is None:
            render_state_panel("暂无案例数据", "unavailable", "载入回放或完成一次分析后，可在这里查看技术字段与来源追溯。")
        else:
            _render_risks_and_evidence(payload, expert=True)
            st.divider()
            render_evidence_viewer(
                payload,
                st.session_state.get("prospectus_bytes"),
                st.session_state.get("replay_screenshots"),
                expert=True,
            )
            st.divider()
            _render_market_and_model(payload, stages_by_id, expert=True)

    with trace_tab:
        if payload is None:
            render_state_panel("暂无运行轨迹", "unavailable", "当前还没有可供审计的案例运行记录。")
        else:
            _render_agent_trace(payload, stages)

    with review_tab:
        if payload is None or result is None:
            render_state_panel("暂无复核对象", "unavailable", "载入案例后，可在这里进行人工复核并下载结构化产物。")
        else:
            _render_review_and_report(payload, result, stages_by_id)

    with system_tab:
        if payload is None:
            render_state_panel("暂无系统诊断", "unavailable", "运行或载入案例后，可查看组件状态、治理配置和日志。")
        else:
            _render_system(payload, stages)


def _render_analysis_intake(*, needs_pdf: bool) -> tuple[bool, str, str, date, object | None]:
    st.markdown(
        "<section id='new-analysis' class='landing-section-head landing-section-anchor section-reveal section-visible'>"
        "<div class='landing-section-index'>01 · 新股分析</div>"
        "<div><div class='landing-section-title'>开始一次 IPO 研究</div>"
        "<div class='landing-section-copy'>填写发行人信息并上传招股书。系统只基于本次提交启动受治理分析。</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )
    with st.container(key="analysis_intake_shell"):
        identity_col, upload_col = st.columns(
            (1, 1), gap="large", vertical_alignment="top"
        )
        with identity_col:
            st.markdown("<div class='landing-intake-label'>IPO 身份信息</div>", unsafe_allow_html=True)
            st.markdown("<div class='landing-intake-title'>发行人信息</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='landing-intake-copy'>输入公司名称、股票代码、案例编号或上市日期即可从官方目录自动匹配；匹配后仍可手工修改。</div>",
                unsafe_allow_html=True,
            )
            company, code, listing = render_issuer_identity_inputs(key_prefix="analysis")
        with upload_col:
            st.markdown("<div class='landing-intake-label'>招股书</div>", unsafe_allow_html=True)
            st.markdown("<div class='landing-intake-title'>上传招股书</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='landing-intake-copy'>PDF 仅在本次分析期间用于解析、证据定位与原页核验。</div>",
                unsafe_allow_html=True,
            )
            with st.form("analysis"):
                if needs_pdf:
                    uploaded = st.file_uploader("招股书 PDF", type=["pdf"])
                else:
                    uploaded = None
                    st.markdown(
                        "<div class='intake-no-upload'>当前运行模式使用内置演示材料，"
                        "无需上传招股书。</div>",
                        unsafe_allow_html=True,
                    )
                submitted = st.form_submit_button("开始分析", type="primary", width="stretch")
    return submitted, company, code, listing, uploaded


st.set_page_config(
    page_title="港股 IPO 风险分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_competition_theme()

scenario = st.session_state.get("runtime_scenario", DEFAULT_ANALYSIS_SCENARIO)
if scenario not in SCENARIOS:
    scenario = DEFAULT_ANALYSIS_SCENARIO
st.session_state["runtime_scenario"] = scenario
config_path, needs_pdf = SCENARIOS[scenario]

result = st.session_state.get("analysis_result")
replay_provenance = st.session_state.get("replay_provenance")
payload = result_payload(result) if result is not None else None
stages = resolve_stages(payload) if payload is not None else []
stages_by_id = {stage.stage_id: stage for stage in stages}
active_view = render_product_navigation(result_mode=result is not None)

if active_view == "home":
    render_product_header(None, runtime_label=scenario)
    st.markdown("<div id='new-analysis' class='landing-section-anchor'></div>", unsafe_allow_html=True)
    if st.button("开始一次 IPO 分析", type="primary", key="home_start_analysis"):
        st.session_state["_pending_product_view"] = "new"
        st.rerun()
    if payload is not None:
        profile = payload.get("profile") or {}
        with st.container(border=True):
            st.markdown("#### 当前案例")
            st.write(
                f"{_display_value(profile.get('company_name'))} · "
                f"{_display_value(profile.get('stock_code'))}"
            )
            if st.button("继续查看当前案例", key="home_continue_case"):
                st.session_state["_pending_product_view"] = "case"
                st.rerun()
    render_empty_state()
    render_product_capabilities()
    render_landing_runtime(scenario)

elif active_view == "new":
    submitted, company, code, listing, uploaded = _render_analysis_intake(needs_pdf=needs_pdf)
    if submitted:
        try:
            new_result, new_prospectus_bytes = _run_analysis(
                scenario=scenario,
                config_path=config_path,
                needs_pdf=needs_pdf,
                company=company,
                code=code,
                listing=listing,
                uploaded=uploaded,
            )
        except ValueError as exc:
            st.error(_friendly_error(str(exc)))
        except Exception as exc:  # UI boundary: fail visibly instead of blanking the app.
            st.error(f"分析未完成，系统已安全停止：{exc}")
        else:
            # A fresh run replaces any replay outright; a leftover replay banner or
            # its screenshots would describe a different run than the one on screen.
            st.session_state.pop("replay_provenance", None)
            st.session_state.pop("replay_screenshots", None)
            if new_prospectus_bytes is None:
                st.session_state.pop("prospectus_bytes", None)
            else:
                st.session_state["prospectus_bytes"] = new_prospectus_bytes
            st.session_state["analysis_result"] = new_result
            st.session_state["analysis_scenario"] = scenario
            st.session_state["_pending_product_view"] = "case"
            st.rerun()

elif active_view == "case":
    if payload is None or result is None:
        section_header("案例工作台", "完成一次新分析或从后台载入回放后，可在这里查看研究结果。")
        render_state_panel("暂无当前案例", "unavailable", "当前还没有可展示的分析结果。")
        if st.button("前往新建分析", type="primary", key="empty_case_start"):
            st.session_state["_pending_product_view"] = "new"
            st.rerun()
        st.stop()
    else:
        if replay_provenance:
            _render_replay_banner(replay_provenance, expert=False)
    with st.container(key="case_workspace_shell"):
        render_case_breadcrumb(payload)
        # Reader workspaces contain only decision-facing content. Engineering,
        # provenance and review controls are conditionally rendered in Backend.
        workspace_tabs = st.tabs(
            [
                "案例概览",
                "原文证据",
                "市场与模型",
                "综合结论与报告",
            ]
        )

        with workspace_tabs[0]:
            render_case_header(payload)
            with st.container(key="risk_command_shell"):
                _render_command_center(payload, stages)

        with workspace_tabs[1]:
            with st.container(key="evidence_section_shell"):
                _render_risks_and_evidence(payload)
                st.divider()
                render_evidence_viewer(
                    payload,
                    st.session_state.get("prospectus_bytes"),
                    st.session_state.get("replay_screenshots"),
                )

        with workspace_tabs[2]:
            with st.container(key="market_model_section_shell"):
                _render_market_and_model(payload, stages_by_id)

        with workspace_tabs[3]:
            with st.container(key="review_report_section_shell"):
                _render_front_report(payload, result)

elif active_view == "backend":
    with st.container(key="backend_page_shell"):
        _render_backend_workspace(
            payload=payload,
            result=result,
            stages=stages,
            stages_by_id=stages_by_id,
        )
