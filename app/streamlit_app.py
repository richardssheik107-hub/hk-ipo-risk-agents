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
    channel_state_map,
    domain_label,
    domain_summary_rows,
    localize_market_observation_rows,
    render_case_header,
    render_case_breadcrumb,
    render_channel_grid,
    render_empty_state,
    executive_supervisor_view,
    render_executive_snapshot,
    render_metric_grid,
    render_pipeline_strip,
    render_product_capabilities,
    render_profile_grid,
    render_product_header,
    render_product_navigation,
    render_navigation_behavior,
    render_landing_runtime,
    render_state_panel,
    render_trace_timeline,
    report_section_title,
    risk_display_name,
    risk_inventory_rows,
    risk_level_label,
    stage_notice_zh,
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


def _display_value(value: object) -> str:
    return "不可用" if value in (None, "", {}) else str(value)


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


def _render_replay_banner(provenance: dict) -> None:
    """State, above everything, that this is a recording rather than a run."""

    st.warning(
        f"**回放模式** · {provenance.get('statement')}\n\n"
        f"- 来源案例 `{provenance.get('case_id')}` · 分析标识 `{provenance.get('analysis_id') or '—'}`\n"
        f"- 运行配置 `{provenance.get('config') or '—'}` · 代码版本 "
        f"`{provenance.get('code_base_sha') or '—'}`"
        + ("（工作树有未提交改动）" if provenance.get("code_base_dirty") else "")
        + "\n"
        f"- 招股书 SHA-256 `{provenance.get('prospectus_sha256') or '—'}`"
    )


def _render_replay_picker() -> None:
    """The sidebar entry into the offline bundle, or why there is none."""

    bundle = _demo_bundle_dir()
    st.sidebar.markdown(
        "<div class='sidebar-section-label'>Demo replay</div>", unsafe_allow_html=True
    )
    cases = available_recorded_cases(bundle)
    if not cases:
        st.sidebar.caption(
            f"未找到演示备份（{bundle}）。先运行 scripts/build_v045_demo_bundle.py 生成，"
            f"或用 {DEMO_BUNDLE_ENV} 指定目录。"
        )
        return
    labels = {path.name: path for path in cases}
    chosen = st.sidebar.selectbox("已记录运行", list(labels), key="replay_case_choice")
    if st.sidebar.button("载入回放", width="stretch"):
        try:
            _load_replay(labels[chosen])
        except (FileNotFoundError, ValueError) as exc:
            st.sidebar.error(f"该记录无法回放：{exc}")
        else:
            st.rerun()
    st.sidebar.caption("回放不联网、不调用模型、不需要 PDF；界面顶部会标明这是已记录运行。")


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
):
    settings = load_settings(config_path)
    if scenario == SCENARIO_PREDICTOR_FAILURE:
        settings = replace(settings, predictor="fault")

    if needs_pdf:
        if uploaded is None:
            raise ValueError("Please upload a prospectus PDF.")
        content = uploaded.getvalue()
        validate_pdf_upload(uploaded.name, content)
        # Kept only in this session, so the Evidence Viewer can render the very
        # pages the parser cited. It is never written to disk by the UI.
        st.session_state["prospectus_bytes"] = content
        with temporary_pdf(content) as prospectus_path:
            request = build_analysis_request(
                company_name=company,
                stock_code=code,
                listing_date=listing,
                prospectus_path=prospectus_path,
                use_mock=False,
                workflow_version=settings.workflow_version,
            )
            activity = _analysis_activity("正在分析招股书并建立 Evidence 链")
            try:
                with st.spinner("正在解析招股书、运行各 Agent、接入可用通道，并由 Final Supervisor 汇总结果……"):
                    return IPOAnalysisService(settings=settings).analyze(request)
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
            return IPOAnalysisService(settings=settings).analyze(request)
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


def _render_risk(risk: dict[str, object]) -> None:
    risk_code = str(risk.get("risk_code", "Unavailable"))
    level = str(risk.get("level", "Unavailable"))
    verification = str(risk.get("verification_status", "Unavailable"))
    score = _display_value(risk.get("score"))

    with st.container(border=True):
        st.markdown(
            "<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:.7rem;"
            "flex-wrap:wrap;margin-bottom:.25rem'>"
            f"<div><div class='section-title'>{escape(risk_display_name(risk_code))}</div></div>"
            f"<span class='risk-chip'>{escape(risk_code)}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='display:flex;gap:.4rem;flex-wrap:wrap;margin:-.2rem 0 .7rem 0'>"
            f"<span class='risk-chip {_risk_level_tone(level)}'>风险等级：{escape(risk_level_label(level))}</span>"
            f"<span class='risk-chip {_verification_tone(verification)}'>{escape(status_label(verification))}</span>"
            f"<span class='risk-chip'>规则评分 {escape(score)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("**结论**")
        st.write(risk.get("conclusion") or "本次未生成风险结论。")

        notes = risk.get("verification_notes")
        if notes:
            st.caption(f"Verifier 复核说明 · {notes}")
        if risk.get("category") in {"legal", "business"}:
            st.caption(
                "当前 v0.3 文档策略下，Legal / Business 的风险等级仍属于暂定结果；确定性规则不会自动将其提升为 high / critical。"
            )

        evidence_items = risk.get("evidence") or []
        if evidence_items:
            st.markdown(f"**Evidence · {len(evidence_items)} 条**")
            for evidence in evidence_items:
                evidence_id = _display_value(evidence.get("evidence_id"))
                page = _display_value(evidence.get("page"))
                with st.expander(f"{evidence_id} · PDF 第 {page} 页", expanded=False):
                    st.write(evidence.get("text") or "该条 Evidence 暂无可展示的原文。")
        else:
            render_state_panel(
                "Evidence 未附着",
                verification,
                "当前没有关联 Evidence，因此该风险不能视为已完成验证。",
            )

        calculation = risk.get("calculation")
        if calculation:
            with st.expander("确定性 Calculation", expanded=False):
                st.json(calculation)

        if risk.get("metadata"):
            with st.expander("结构化事实 / metadata", expanded=False):
                st.json(risk["metadata"])


def _render_sidebar_status(payload: dict[str, object], stages) -> None:
    profile = payload.get("profile") or {}
    st.sidebar.markdown("<div class='sidebar-section-label'>Current case</div>", unsafe_allow_html=True)
    st.sidebar.markdown(
        f"**{_display_value(profile.get('stock_code'))}** · {_display_value(profile.get('company_name'))}"
    )
    completion = payload.get("runtime_completion_status") or payload.get("status")
    st.sidebar.caption(f"运行结果 · {status_label(completion)}")
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        gate = f" · {stage.blocking_gate}" if stage.blocking_gate else ""
        st.sidebar.caption(f"{stage.ordinal}. {stage_title_zh(stage)} · {status_label(raw_status)}{gate}")


def _render_overview(payload: dict[str, object], stages) -> None:
    profile = payload["profile"]

    section_header("IPO Profile", "发行资料、数据来源与案例匹配状态。", "Case facts")
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
        section_header("Risk Coverage", "Financial / Legal / Business 覆盖。", "Coverage")
        st.dataframe(domain_summary_rows(payload), hide_index=True, width="stretch")
    with right:
        section_header("Risk Inventory", "正式风险项与 Evidence 数量。", "Inventory")
        inventory = risk_inventory_rows(payload)
        if inventory:
            st.dataframe(inventory, hide_index=True, width="stretch")
        else:
            render_state_panel("暂无正式风险项", "unavailable", "本次运行未产出正式风险项；界面不会用低风险或 0 替代未知状态。")

    section_header("七阶段运行链路", "从招股书解析到最终报告的受治理处理链。", "Pipeline")
    render_pipeline_strip(stages)
    st.caption("规则评分仅用于确定性风险排序，不代表发生概率、股价走势，也不构成投资或法律建议。")


def _render_risks_and_evidence(payload: dict[str, object]) -> None:
    section_header(
        "风险与 Evidence",
        "风险结论、验证状态与规则评分优先；Evidence、Calculation、metadata 和诊断仍可逐层核验。",
        "Document intelligence",
    )
    domain_tabs = st.tabs([domain_label(domain) for domain in DOMAINS])
    for domain, tab in zip(DOMAINS, domain_tabs, strict=True):
        with tab:
            domain_data = payload["domains"][domain]
            counts = domain_data["status_counts"]
            render_metric_grid(
                (
                    ("风险项", domain_data["risk_count"], domain_label(domain)),
                    ("已验证", counts.get("verified", 0), "Verified"),
                    ("待复核", counts.get("needs_review", 0), "Needs review"),
                    ("待处理 / 已驳回", counts.get("pending", 0) + counts.get("rejected", 0), "Pending / Rejected"),
                )
            )
            if not domain_data["risks"]:
                render_state_panel("该领域暂无正式风险项", domain_data.get("status", "unavailable"), "本次运行未在该领域识别到正式风险项。")
            for risk in domain_data["risks"]:
                _render_risk(risk)
            if domain_data["diagnostics"]:
                with st.expander("Agent 诊断信息", expanded=False):
                    st.json(domain_data["diagnostics"])


def _render_market_and_model(payload: dict[str, object], stages_by_id: dict[str, object]) -> None:
    section_header(
        "市场与模型信号",
        "Market-X 缺失值原样保留；仅在存在冻结且可核验的逐案例 runtime handoff 时展示模型评分。",
        "Market & model intelligence",
    )

    left, right = st.columns((1.22, 1))
    with left:
        with st.container(border=True):
            section_header("市场情报", "Point-in-time 市场环境与来源追溯。")
            market = payload.get("market_context") or {}
            available, total = available_market_observation_count(payload)
            raw_status = market.get("status", "unavailable")
            st.markdown(
                f"**Market-X**  ·  {status_label(raw_status)}  ·  "
                f"可用观测 {available}/{total if total else 0}"
            )
            observations = market.get("observations") or []
            if observations:
                st.dataframe(localize_market_observation_rows(observations), hide_index=True, width="stretch")
            else:
                render_state_panel("Market-X 观测不可用", raw_status, "本次分析没有可展示的 Market-X 观测；具体来源与缺失原因可在下方 provenance 中核验。")
            with st.expander("Market-X 数据来源 / provenance", expanded=False):
                st.json(market.get("provenance", {}))

    with right:
        with st.container(border=True):
            final = payload.get("final_supervision") or {}
            states = channel_state_map(payload)
            model = final.get("model_prediction")
            section_header("模型 / 规则情报", "冻结模型信号与确定性规则信号对照。")
            if model:
                st.metric("模型评分", model.get("score", "不可用"))
                if model.get("alert") is not None:
                    st.metric("V2 风险初筛告警", "是" if model["alert"] else "否")
                    st.caption(f"告警策略：{model.get('alert_policy', '不可用')}")
                st.caption(
                    f"评分语义：{model.get('score_semantics', '不可用')} · 校准状态：{model.get('calibration_status', '不可用')}"
                )
                drivers = model.get("drivers") or []
                if drivers:
                    st.markdown("**主要驱动因素（SHAP）**")
                    st.dataframe(drivers, hide_index=True, width="stretch")
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
                st.warning(uncertainty)

    notices = []
    for stage_id in ("market_features", "prediction", "explainability"):
        stage = stages_by_id.get(stage_id)
        if stage is not None:
            notice = stage_notice_zh(stage)
            if notice:
                notices.append((stage_title_zh(stage), notice))
    if notices:
        with st.expander("当前通道限制", expanded=False):
            for title, notice in notices:
                st.markdown(f"**{title}**")
                st.markdown(notice)


def _render_supervisor_and_report(payload: dict[str, object], result, stages_by_id: dict[str, object]) -> None:
    section_header(
        "Final Supervisor 与最终报告",
        "机器结论、受治理的不确定性与可下载审计成果保持一致。",
        "Audit & research report",
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

    section_header("完整分析报告（13 节）", "按标准报告结构逐节审阅，结构化 metadata 保留在对应章节。", "Report workspace")
    for section in sorted(payload["report_sections"], key=lambda item: item["order"]):
        expanded = section["order"] in {1, 2, 9}
        title = report_section_title(section["order"], section["title"])
        with st.expander(f"{section['order']}. {title}", expanded=expanded):
            st.write(section["summary"])
            if section.get("metadata"):
                with st.expander("结构化 section metadata", expanded=False):
                    st.json(section["metadata"])

    stage = stages_by_id.get("final_report")
    if stage is not None:
        notice = stage_notice_zh(stage)
        if notice:
            st.info(notice)


def _render_system(payload: dict[str, object], stages) -> None:
    section_header(
        "系统信息、追溯与诊断",
        "工程状态与风险结论分层展示；底层配置、错误和运行日志保持可审计。",
        "Diagnostics",
    )

    stage_rows = []
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        stage_rows.append(
            {
                "阶段": stage.ordinal,
                "名称": stage_title_zh(stage),
                "状态": status_label(raw_status),
                "阻塞 Gate": stage.blocking_gate or "",
                "说明": stage_summary_zh(stage),
            }
        )
    st.markdown("#### Pipeline 状态")
    st.dataframe(stage_rows, hide_index=True, width="stretch")

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
    st.dataframe(component_rows, hide_index=True, width="stretch")

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
        st.write(verdict.get("overall_risk_rationale") or "未给出依据。")

        findings = verdict.get("key_findings") or []
        st.markdown(f"**关键发现 · {len(findings)}**")
        for finding in findings:
            st.markdown(
                f"- {finding.get('statement', '')}  \n"
                f"  <span class='risk-chip'>risk {len(finding.get('risk_ids') or [])}</span> "
                f"<span class='risk-chip'>evidence {len(finding.get('evidence_ids') or [])}</span>",
                unsafe_allow_html=True,
            )

        assessments = verdict.get("conflict_assessments") or []
        if assessments:
            with st.expander(f"冲突评述 · {len(assessments)}", expanded=False):
                for item in assessments:
                    st.markdown(f"- `{item.get('conflict_id', '')}` — {item.get('assessment', '')}")

        uncertainties = verdict.get("uncertainties") or []
        if uncertainties:
            st.markdown("**不确定性**")
            for item in uncertainties:
                st.markdown(f"- {item}")

        targets = verdict.get("recheck_targets") or []
        if targets:
            st.markdown("**建议的定向复核对象**")
            for item in targets:
                st.markdown(f"- `{item.get('target', '')}` — {item.get('reason', '')}")

        st.markdown("**最终说明**")
        st.write(verdict.get("final_explanation") or "未给出最终说明。")


def _render_command_center(payload: dict[str, object], stages) -> None:
    section_header("风险指挥中心", "综合判断、通道健康、冲突、案例画像与运行链路。")
    render_executive_snapshot(payload)

    counts = conflict_status_counts(payload)
    if counts:
        section_header("Competition Conflict 状态", "Resolved / Partial / Unresolved 冲突概览。", "Conflict summary")
        render_metric_grid(
            (RESOLUTION_LABELS.get(status, status), count, "Competition conflict")
            for status, count in sorted(counts.items())
        )
        st.caption("冲突明细与定向复核结论见「Agent 协作轨迹」工作区。")

    _render_overview(payload, stages)


def _render_agent_trace(payload: dict[str, object], stages) -> None:
    section_header(
        "Agent 协作轨迹",
        "Agent → Evidence → Risk → Conflict → Re-check → Supervisor；完整 Provider、Prompt、Evidence 与 Calculation 仍可审计。",
        "Traceability",
    )

    st.markdown(
        "<div class='trace-flow'>"
        "<div class='trace-flow-step'>Agent</div><div class='trace-flow-step'>Evidence</div>"
        "<div class='trace-flow-step'>Risk</div><div class='trace-flow-step'>Conflict</div>"
        "<div class='trace-flow-step'>Re-check</div><div class='trace-flow-step'>Supervisor</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    metrics = traceability_metrics(payload)
    if metrics:
        section_header("可追溯率", "每项比例均来自本次 trace sidecar。", "Audit metrics")
        st.dataframe(metrics, hide_index=True, width="stretch")
        unresolved = (traceability(payload) or {}).get("unresolved_evidence_ids") or []
        if unresolved:
            st.warning(f"有 {len(unresolved)} 个被引用的 Evidence ID 无法回溯到本次运行的 Evidence 集合。")
            st.json(unresolved)
    else:
        render_state_panel("Agent Trace 不可用", "unavailable", "当前运行模式没有生成 Agent Trace sidecar。")

    conflicts_table = conflict_rows(payload)
    section_header("跨 Agent 冲突与定向复核", "冲突、参与方、复核状态与保留结论。", "Conflict & re-check")
    if conflicts_table:
        st.dataframe(conflicts_table, hide_index=True, width="stretch")
        outcomes = recheck_outcomes(payload)
        with st.expander(f"定向复核执行明细 · {len(outcomes)}", expanded=False):
            st.json(outcomes)
    else:
        render_state_panel("未检出跨 Agent 冲突", "available", "本次运行未记录跨 Agent 冲突；这不改变各风险项自身的验证状态。")

    rows = trace_rows(payload)
    section_header(f"完整事件轨迹 · {len(rows)}", "按 sidecar 原始顺序呈现，紧凑视图下方保留完整字段表。", "Event timeline")
    if rows:
        render_trace_timeline(rows)
        with st.expander("完整事件字段表", expanded=False):
            st.dataframe(rows, hide_index=True, width="stretch")
        with st.expander("原始 trace sidecar（competition_runtime_v1）", expanded=False):
            st.json((payload.get("component_diagnostics") or {}).get("competition_runtime", {}))
    else:
        render_state_panel("事件轨迹不可用", "unavailable", "本次运行没有可展示的 trace 事件。")

    st.divider()
    _render_system(payload, stages)


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


st.set_page_config(
    page_title="港股 IPO 风险分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_competition_theme()

st.sidebar.markdown(
    "<div class='sidebar-brand'><div class='sidebar-brand-title'>IPO Risk Intelligence</div>"
    "<div class='sidebar-brand-copy'>Evidence-driven audit workspace</div></div>",
    unsafe_allow_html=True,
)
scenario_names = list(SCENARIOS)
default_scenario = scenario_names.index(SCENARIO_COMPETITION_OFFLINE)
st.sidebar.markdown("<div class='sidebar-section-label'>Runtime scenario</div>", unsafe_allow_html=True)
scenario = st.sidebar.selectbox(
    "运行模式",
    scenario_names,
    index=default_scenario,
    key="runtime_scenario",
    on_change=_clear_result,
)
config_path, needs_pdf = SCENARIOS[scenario]

has_existing_result = st.session_state.get("analysis_result") is not None
render_product_navigation(result_mode=has_existing_result)
header_slot = st.container()

st.sidebar.markdown("<div class='sidebar-section-label'>Configuration</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='sidebar-config'>{escape(config_path)}</div>", unsafe_allow_html=True)
st.sidebar.markdown(
    "<div class='sidebar-note'>离线模式不调用外部模型；AI 模式仅从环境变量读取凭证。"
    "外部服务不可用时，系统将按既定语义安全降级。</div>",
    unsafe_allow_html=True,
)
st.sidebar.caption("当前正式 Gate · PR-H 完整受治理 E2E 集成")
clear_result_slot = st.sidebar.empty()
_render_replay_picker()

if not has_existing_result:
    st.markdown(
        "<section id='new-analysis' class='landing-section-head landing-section-anchor section-reveal'>"
        "<div class='landing-section-index'>01 · NEW IPO ANALYSIS</div>"
        "<div><div class='landing-section-title'>开始一次 IPO 研究</div>"
        "<div class='landing-section-copy'>填写发行人信息并上传招股书。系统只基于本次提交启动受治理分析。</div></div>"
        "</section>",
        unsafe_allow_html=True,
    )
    identity_col, upload_col = st.columns((0.4, 0.6), gap="large")
    with identity_col:
        st.markdown("<div class='landing-intake-label'>IPO Identity</div>", unsafe_allow_html=True)
        st.markdown("<div class='landing-intake-title'>发行人信息</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='landing-intake-copy'>输入公司名称、股票代码、case id 或上市日期即可从官方 catalog 自动匹配；匹配后仍可手工修改。</div>",
            unsafe_allow_html=True,
        )
        company, code, listing = render_issuer_identity_inputs(key_prefix="analysis")
    with upload_col:
        st.markdown("<div class='landing-intake-label'>Prospectus</div>", unsafe_allow_html=True)
        st.markdown("<div class='landing-intake-title'>上传招股书</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='landing-intake-copy'>PDF 将在当前分析生命周期内用于解析、Evidence 定位与原页复核。</div>",
            unsafe_allow_html=True,
        )
        with st.form("analysis"):
            uploaded = st.file_uploader("招股书 PDF", type=["pdf"]) if needs_pdf else None
            submitted = st.form_submit_button("开始分析", type="primary")
else:
    st.markdown("<div id='new-analysis' class='landing-section-anchor'></div>", unsafe_allow_html=True)
    section_header("Analysis Setup", "输入任一发行人身份线索即可匹配官方 catalog，也可手工填写新 IPO。")
    company, code, listing = render_issuer_identity_inputs(key_prefix="analysis")
    with st.form("analysis"):
        uploaded = st.file_uploader("招股书 PDF", type=["pdf"]) if needs_pdf else None
        submitted = st.form_submit_button("开始分析", type="primary", width="stretch")

if submitted:
    try:
        result = _run_analysis(
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
        st.session_state["analysis_result"] = result
        st.session_state["analysis_scenario"] = scenario
        # Repaint immediately into the dense result workbench; the governed
        # result and PDF session payload stay unchanged.
        st.rerun()

result = st.session_state.get("analysis_result")
replay_provenance = st.session_state.get("replay_provenance")
header_payload = result_payload(result) if result is not None else None
with header_slot:
    render_product_header(
        header_payload,
        runtime_label=SCENARIO_REPLAY if replay_provenance else scenario,
    )
    if replay_provenance:
        _render_replay_banner(replay_provenance)
if result is not None:
    if clear_result_slot.button("清除当前结果", width="stretch"):
        _clear_result()
        st.rerun()
if result is None:
    render_empty_state()
    render_product_capabilities()
    render_landing_runtime(scenario)
    render_navigation_behavior()
else:
    payload = result_payload(result)
    stages = resolve_stages(payload)
    stages_by_id = {stage.stage_id: stage for stage in stages}

    _render_sidebar_status(payload, stages)
    with st.container(key="case_workspace_shell"):
        render_case_breadcrumb(payload)
        # Five workspaces, one job each: decide, verify, contextualise, audit, sign off.
        workspace_tabs = st.tabs(
            [
                "案例概览",
                "Evidence",
                "市场与模型",
                "Agent 协作",
                "人机复核与最终报告",
            ]
        )

        with workspace_tabs[0]:
            render_case_header(payload)
            render_channel_grid(payload)
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
            with st.container(key="agent_trace_section_shell"):
                _render_agent_trace(payload, stages)

        with workspace_tabs[4]:
            with st.container(key="review_report_section_shell"):
                _render_review_and_report(payload, result, stages_by_id)
