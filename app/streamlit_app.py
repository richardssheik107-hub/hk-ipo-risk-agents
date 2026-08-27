"""Streamlit presentation layer; it only calls IPOAnalysisService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from html import escape
import json

import streamlit as st

from competition_ui import (
    apply_competition_theme,
    available_market_observation_count,
    channel_state_map,
    domain_label,
    domain_summary_rows,
    localize_market_observation_rows,
    render_case_header,
    render_channel_grid,
    render_empty_state,
    executive_supervisor_view,
    render_executive_snapshot,
    render_pipeline_strip,
    render_product_header,
    report_section_title,
    risk_display_name,
    risk_inventory_rows,
    risk_level_label,
    stage_notice_zh,
    stage_summary_zh,
    stage_title_zh,
    stage_unblocked_items_zh,
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
from evidence_viewer import render_evidence_viewer
from human_review_ui import render_human_review
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
from ipo_risk.core.config import load_settings
from ipo_risk.services.human_review_service import HumanReviewService
from ipo_risk.services.analysis_service import IPOAnalysisService


SCENARIO_COMPETITION_OFFLINE = "v0.4.5 比赛版（离线）"
SCENARIO_COMPETITION_AI = "v0.4.5 比赛版（AI）"
SCENARIO_PREDICTOR_FAILURE = "预测器故障降级演示"
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


def _friendly_error(message: str) -> str:
    known = {
        "Please upload a prospectus PDF.": "请先上传招股书 PDF。",
        "Only .pdf files are accepted.": "仅支持 PDF 文件。",
        "The uploaded PDF is empty.": "上传的 PDF 为空，请重新选择文件。",
        "The uploaded PDF exceeds the 200 MB size limit.": "上传的 PDF 超过 200 MB 限制。",
        "The uploaded file does not have a valid PDF header.": "上传文件不是有效的 PDF。",
    }
    return known.get(message, message)


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
            with st.spinner("正在解析招股书、运行各 Agent、接入可用通道，并由 Final Supervisor 汇总结果……"):
                return IPOAnalysisService(settings=settings).analyze(request)

    request = build_analysis_request(
        company_name=company,
        stock_code=code,
        listing_date=listing,
        prospectus_path="mock://prospectus",
        use_mock=True,
        workflow_version=settings.workflow_version,
    )
    with st.spinner("正在运行分析……"):
        return IPOAnalysisService(settings=settings).analyze(request)


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
        st.markdown(f"#### {risk_display_name(risk_code)}")
        st.markdown(
            "<div style='display:flex;gap:.4rem;flex-wrap:wrap;margin:-.2rem 0 .7rem 0'>"
            f"<span class='risk-chip {_risk_level_tone(level)}'>风险等级：{escape(risk_level_label(level))}</span>"
            f"<span class='risk-chip {_verification_tone(verification)}'>{escape(status_label(verification))}</span>"
            f"<span class='risk-chip'>规则评分 {escape(score)}</span>"
            f"<span class='risk-chip'>{escape(risk_code)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
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
            st.info("当前没有关联 Evidence，因此该风险不能视为已完成验证。")

        calculation = risk.get("calculation")
        if calculation:
            with st.expander("确定性 Calculation", expanded=False):
                st.json(calculation)

        if risk.get("metadata"):
            with st.expander("结构化事实 / metadata", expanded=False):
                st.json(risk["metadata"])


def _render_sidebar_status(payload: dict[str, object], stages) -> None:
    profile = payload.get("profile") or {}
    st.sidebar.markdown("### 当前案例")
    st.sidebar.markdown(
        f"**{_display_value(profile.get('stock_code'))}** · {_display_value(profile.get('company_name'))}"
    )
    completion = payload.get("runtime_completion_status") or payload.get("status")
    st.sidebar.caption(f"运行结果 · {status_label(completion)}")
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        raw_status = getattr(status_obj, "value", status_obj)
        icon = {"available": "🟢", "partial": "🟡", "pending_gate": "⚪"}.get(str(raw_status), "⚪")
        gate = f" · {stage.blocking_gate}" if stage.blocking_gate else ""
        st.sidebar.caption(f"{icon} {stage.ordinal}. {stage_title_zh(stage)} · {status_label(raw_status)}{gate}")


def _render_overview(payload: dict[str, object], stages) -> None:
    profile = payload["profile"]

    st.markdown("### IPO 基本信息")
    with st.container(border=True):
        first, second, third, fourth = st.columns((1.35, 1, 1, 1))
        first.markdown(f"**公司**  \n{_display_value(profile.get('company_name'))}")
        second.markdown(f"**股票代码**  \n{_display_value(profile.get('stock_code'))}")
        third.markdown(f"**上市日期**  \n{_display_value(profile.get('listing_date'))}")
        fourth.markdown(f"**行业**  \n{_display_value(profile.get('industry'))}")
        st.divider()
        details = st.columns(5)
        details[0].markdown(f"**发行价**  \n{_display_value(profile.get('issue_price'))}")
        details[1].markdown(f"**发行规模**  \n{_display_value(profile.get('issue_size'))}")
        details[2].markdown(f"**证券类别**  \n{_display_value(profile.get('security_category'))}")
        details[3].markdown(f"**IPO 数据来源**  \n{_display_value(profile.get('source'))}")
        details[4].markdown(f"**匹配状态**  \n{_display_value(profile.get('match_status'))}")

    left, right = st.columns((1.05, 1.45))
    with left:
        st.markdown("### 风险领域覆盖")
        st.dataframe(domain_summary_rows(payload), hide_index=True, use_container_width=True)
    with right:
        st.markdown("### 风险清单")
        inventory = risk_inventory_rows(payload)
        if inventory:
            st.dataframe(inventory, hide_index=True, use_container_width=True)
        else:
            st.info("本次运行未产出正式风险项。")

    st.markdown("### 运行链路")
    render_pipeline_strip(stages)
    st.caption("规则评分仅用于确定性风险排序，不代表发生概率、股价走势，也不构成投资或法律建议。")


def _render_risks_and_evidence(payload: dict[str, object]) -> None:
    st.markdown("### 风险与 Evidence")
    st.caption("先阅读风险结论；需要核验时，再展开 Evidence、Calculation 和 metadata 查看原始依据。")
    domain_tabs = st.tabs([domain_label(domain) for domain in DOMAINS])
    for domain, tab in zip(DOMAINS, domain_tabs, strict=True):
        with tab:
            domain_data = payload["domains"][domain]
            counts = domain_data["status_counts"]
            top = st.columns(4)
            top[0].metric("风险项", domain_data["risk_count"])
            top[1].metric("已验证", counts.get("verified", 0))
            top[2].metric("待复核", counts.get("needs_review", 0))
            top[3].metric("待处理 / 已驳回", counts.get("pending", 0) + counts.get("rejected", 0))
            if not domain_data["risks"]:
                st.info("该领域本次未识别到正式风险项。")
            for risk in domain_data["risks"]:
                _render_risk(risk)
            if domain_data["diagnostics"]:
                with st.expander("Agent 诊断信息", expanded=False):
                    st.json(domain_data["diagnostics"])


def _render_market_and_model(payload: dict[str, object], stages_by_id: dict[str, object]) -> None:
    st.markdown("### 市场与模型信号")
    st.caption("Market-X 的缺失值会原样保留；只有存在冻结且可核验的逐案例 runtime handoff 时，才展示模型评分。")

    left, right = st.columns((1.22, 1))
    with left:
        st.markdown("#### 上市前 Market-X")
        market = payload.get("market_context") or {}
        available, total = available_market_observation_count(payload)
        raw_status = market.get("status", "unavailable")
        top = st.columns(2)
        top[0].metric("通道状态", status_label(raw_status))
        top[1].metric("可用观测", f"{available}/{total}" if total else "0/0")
        observations = market.get("observations") or []
        if observations:
            st.dataframe(localize_market_observation_rows(observations), hide_index=True, use_container_width=True)
        else:
            st.info("本次分析没有可展示的 Market-X 观测。")
        with st.expander("Market-X 数据来源 / provenance", expanded=False):
            st.json(market.get("provenance", {}))

    with right:
        final = payload.get("final_supervision") or {}
        states = channel_state_map(payload)
        model = final.get("model_prediction")
        st.markdown("#### 冻结模型信号")
        if model:
            st.metric("模型评分", model.get("score", "不可用"))
            st.caption(
                f"评分语义：{model.get('score_semantics', '不可用')} · 校准状态：{model.get('calibration_status', '不可用')}"
            )
            drivers = model.get("drivers") or []
            if drivers:
                st.markdown("**主要驱动因素（SHAP）**")
                st.dataframe(drivers, hide_index=True, use_container_width=True)
        else:
            st.info(
                f"模型通道当前为“{status_label(states.get('model'))}”。该 IPO 暂无可核验的冻结逐案例模型评分，因此不展示模型结果。"
            )

        st.markdown("#### 确定性规则信号")
        prediction = payload.get("prediction") or {}
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
    st.markdown("### Final Supervisor 与最终报告")

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

    st.markdown("### 完整分析报告（13 节）")
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
    st.markdown("### 系统信息、追溯与诊断")
    st.caption("工程信息与风险结论分开展示，正常演示时无需展开这里的底层细节。")

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
    st.dataframe(stage_rows, hide_index=True, use_container_width=True)

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
    st.dataframe(component_rows, hide_index=True, use_container_width=True)

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
    st.markdown("### 风险指挥中心")
    st.caption("一屏看清：通道状态、综合判断、风险清单与本次运行链路。")
    _render_supervisor_judgement(payload)

    counts = conflict_status_counts(payload)
    if counts:
        st.markdown("#### Competition Conflict 状态")
        chips = st.columns(len(counts))
        for column, (status, count) in zip(chips, sorted(counts.items()), strict=True):
            column.metric(RESOLUTION_LABELS.get(status, status), count)
        st.caption("冲突明细与定向复核结论见「Agent 协作轨迹」工作区。")

    _render_overview(payload, stages)


def _render_agent_trace(payload: dict[str, object], stages) -> None:
    st.markdown("### Agent 协作轨迹")
    st.caption(
        "每一步都记录 Agent、工具 / Skill、Provider、Prompt 版本、Evidence 与 Calculation；"
        "没有 Evidence 的步骤必须写明原因，可追溯率因此是被度量出来的，而不是宣称的。"
    )

    metrics = traceability_metrics(payload)
    if metrics:
        st.markdown("#### 可追溯率")
        st.dataframe(metrics, hide_index=True, use_container_width=True)
        unresolved = (traceability(payload) or {}).get("unresolved_evidence_ids") or []
        if unresolved:
            st.warning(f"有 {len(unresolved)} 个被引用的 Evidence ID 无法回溯到本次运行的 Evidence 集合。")
            st.json(unresolved)
    else:
        st.info("当前运行模式没有生成 Agent Trace sidecar。")

    conflicts_table = conflict_rows(payload)
    st.markdown("#### 跨 Agent 冲突与定向复核")
    if conflicts_table:
        st.dataframe(conflicts_table, hide_index=True, use_container_width=True)
        outcomes = recheck_outcomes(payload)
        with st.expander(f"定向复核执行明细 · {len(outcomes)}", expanded=False):
            st.json(outcomes)
    else:
        st.info("本次运行没有检出跨 Agent 冲突。")

    rows = trace_rows(payload)
    st.markdown(f"#### 完整事件轨迹 · {len(rows)}")
    if rows:
        st.dataframe(rows, hide_index=True, use_container_width=True)
        with st.expander("原始 trace sidecar（competition_runtime_v1）", expanded=False):
            st.json((payload.get("component_diagnostics") or {}).get("competition_runtime", {}))
    else:
        st.info("本次运行没有可展示的 trace 事件。")

    st.divider()
    _render_system(payload, stages)


def _render_review_and_report(payload: dict[str, object], result, stages_by_id) -> None:
    render_human_review(
        payload,
        analysis_id=result.analysis_id,
        case_id=str((payload.get("profile") or {}).get("stock_code") or result.stock_code or "unknown_case"),
        run_id=result.request_id,
        service=HumanReviewService(),
    )
    st.divider()
    _render_supervisor_and_report(payload, result, stages_by_id)


st.set_page_config(
    page_title="港股 IPO 风险分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_competition_theme()
render_product_header()

scenario_names = list(SCENARIOS)
default_scenario = scenario_names.index(SCENARIO_COMPETITION_OFFLINE)
scenario = st.sidebar.selectbox(
    "运行模式",
    scenario_names,
    index=default_scenario,
    key="runtime_scenario",
    on_change=_clear_result,
)
config_path, needs_pdf = SCENARIOS[scenario]

st.sidebar.markdown("### 运行说明")
st.sidebar.caption(f"配置文件 · `{config_path}`")
st.sidebar.caption("离线模式不会调用外部模型；AI 模式仅从环境变量读取凭证，外部服务不可用时会安全降级。")
st.sidebar.caption("当前正式 Gate · PR-H 完整受治理 E2E 集成。")
if "analysis_result" in st.session_state:
    if st.sidebar.button("清除当前结果", use_container_width=True):
        _clear_result()
        st.rerun()

st.markdown("<div class='section-eyebrow'>分析招股书</div>", unsafe_allow_html=True)
with st.form("analysis"):
    first, second, third = st.columns((1.4, 1, 1))
    with first:
        company = st.text_input("公司名称", "Demo Biotech")
    with second:
        code = st.text_input("股票代码", "9999.HK")
    with third:
        listing = st.date_input("上市日期", date.today())
    uploaded = st.file_uploader("招股书 PDF", type=["pdf"]) if needs_pdf else None
    submitted = st.form_submit_button("开始分析", type="primary", use_container_width=True)

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
        st.session_state["analysis_result"] = result
        st.session_state["analysis_scenario"] = scenario

result = st.session_state.get("analysis_result")
if result is None:
    render_empty_state()
else:
    payload = result_payload(result)
    stages = resolve_stages(payload)
    stages_by_id = {stage.stage_id: stage for stage in stages}

    _render_sidebar_status(payload, stages)
    render_case_header(payload)
    render_executive_snapshot(payload)

    st.markdown("<div class='section-eyebrow'>通道状态</div>", unsafe_allow_html=True)
    render_channel_grid(payload)

    # Five workspaces, one job each: decide, verify, contextualise, audit, sign off.
    workspace_tabs = st.tabs(
        [
            "风险指挥中心",
            "Evidence 与 AI 分析",
            "市场与模型",
            "Agent 协作轨迹",
            "人机复核与最终报告",
        ]
    )

    with workspace_tabs[0]:
        _render_command_center(payload, stages)

    with workspace_tabs[1]:
        _render_risks_and_evidence(payload)
        st.divider()
        render_evidence_viewer(payload, st.session_state.get("prospectus_bytes"))

    with workspace_tabs[2]:
        _render_market_and_model(payload, stages_by_id)

    with workspace_tabs[3]:
        _render_agent_trace(payload, stages)

    with workspace_tabs[4]:
        _render_review_and_report(payload, result, stages_by_id)
