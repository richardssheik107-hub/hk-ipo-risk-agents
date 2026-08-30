"""Judge-facing Streamlit entrypoint.

This is an alternative presentation surface for final-day review. It reuses the
same governed IPOAnalysisService and result payload as the canonical frontend;
it does not change backend semantics.
"""

from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
import hashlib
import inspect
import json

import streamlit as st

from competition_ui import (
    apply_competition_theme,
    available_market_observation_count,
    channel_state_map,
    domain_label,
    domain_summary_rows,
    localize_market_observation_rows,
    market_degradation_summary,
    market_runtime_summary,
    render_case_header,
    render_channel_grid,
    render_modern_table,
    render_profile_grid,
    render_state_panel,
    risk_display_name,
    risk_inventory_rows,
    risk_level_label,
    status_label,
)
from competition_runtime_view import (
    RESOLUTION_LABELS,
    conflict_status_counts,
    trace_rows,
    traceability_metrics,
)
from evidence_viewer_compat import render_evidence_viewer
from ipo_risk.core.config import load_settings
from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.schemas import IPOAnalysisResult
from issuer_identity_ui import render_issuer_identity_inputs
from judge_copy import risk_reasoning, risk_review_focus, summarize_risks
from presenters import (
    build_analysis_request,
    markdown_report,
    result_payload,
    safe_download_stem,
    temporary_pdf,
    validate_pdf_upload,
)


SCENARIOS = {
    "比赛演示（离线，可复现）": "configs/v045_competition_offline.yaml",
    "AI 增强分析": "configs/v045_competition_ai.yaml",
}

RUNTIME_FINGERPRINT_SCHEMA = "ipo_frontend_runtime_fingerprint_v1"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "unreadable"


def _source_path(value: object) -> Path:
    return Path(inspect.getsourcefile(value) or inspect.getfile(value)).resolve()


def _runtime_fingerprint(config_path: str) -> dict[str, object]:
    resolved_config = Path(config_path)
    if not resolved_config.is_absolute():
        resolved_config = (REPO_ROOT / resolved_config).resolve()
    settings = load_settings(str(resolved_config))
    service_source = _source_path(IPOAnalysisService)
    config_source = _source_path(load_settings)
    expected_source_root = (REPO_ROOT / "src").resolve()
    material = {
        "schema_version": RUNTIME_FINGERPRINT_SCHEMA,
        "entrypoint": "judge",
        "config_path": resolved_config.relative_to(REPO_ROOT).as_posix(),
        "config_sha256": _sha256_file(resolved_config),
        "entrypoint_sha256": _sha256_file(Path(__file__).resolve()),
        "analysis_service_sha256": _sha256_file(service_source),
        "config_runtime_sha256": _sha256_file(config_source),
        "backend_source_root": str(service_source.parent),
        "settings_contract": {
            key: getattr(settings, key, None)
            for key in (
                "workflow_version",
                "runtime_mode",
                "llm_provider",
                "market_dynamic_context",
                "model_dynamic_runtime",
                "model_artifact_dir",
                "pr_f_run_dir",
            )
        },
    }
    return {
        "schema_version": RUNTIME_FINGERPRINT_SCHEMA,
        "entrypoint": "judge",
        "config_path": material["config_path"],
        "runtime_digest": hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source_matches_checkout": all(
            path.is_relative_to(expected_source_root)
            for path in (service_source, config_source)
        ),
    }


def _result_identity(result: IPOAnalysisResult) -> dict[str, str]:
    return {
        "analysis_id": str(result.analysis_id),
        "workflow_version": str(result.workflow_version),
        "stock_code": str(result.stock_code or ""),
    }


def _result_fingerprint(
    result: IPOAnalysisResult,
    runtime: dict[str, object],
    scenario: str,
) -> dict[str, object]:
    return {
        "schema_version": RUNTIME_FINGERPRINT_SCHEMA,
        "scenario": scenario,
        "config_path": runtime.get("config_path"),
        "runtime_digest": runtime.get("runtime_digest"),
        "result_identity": _result_identity(result),
    }


def _result_compatibility(
    result: IPOAnalysisResult,
    fingerprint: object,
) -> tuple[bool, str]:
    if not isinstance(fingerprint, dict) or fingerprint.get("schema_version") != RUNTIME_FINGERPRINT_SCHEMA:
        return False, "当前结果缺少可核验的运行指纹，已停止将它当作当前代码的分析结果。"
    if fingerprint.get("result_identity") != _result_identity(result):
        return False, "当前结果与运行指纹的案例身份不一致，已停止展示以避免串案。"
    config_path = str(fingerprint.get("config_path") or "")
    if not config_path:
        return False, "当前结果没有记录生成它的配置，已停止将它当作当前结果。"
    try:
        current = _runtime_fingerprint(config_path)
    except Exception as exc:
        return False, f"无法复核当前结果的运行配置：{exc}"
    if fingerprint.get("runtime_digest") != current.get("runtime_digest"):
        return False, "生成当前结果的代码或配置已变化；旧结果仍保留，但不再冒充本次运行结果。"
    return True, ""


def _analysis_failed(result: IPOAnalysisResult) -> bool:
    return str(getattr(result.status, "value", result.status)).lower() == "failed"


def _clear_judge_intake_state() -> None:
    for key in (
        "judge_company",
        "judge_code",
        "judge_listing",
        "judge_issuer_lookup",
        "judge_issuer_match_choice",
        "judge_issuer_match_applied",
        "judge_issuer_applied_case",
    ):
        st.session_state.pop(key, None)


def _clear_judge_result() -> None:
    for key in (
        "judge_result",
        "judge_result_fingerprint",
        "judge_result_scenario",
        "judge_result_config_path",
        "judge_prospectus_bytes",
    ):
        st.session_state.pop(key, None)


def _model_projection(
    payload: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object]]:
    final = payload.get("final_supervision") or {}
    raw = (
        final.get("model_prediction")
        if isinstance(final, dict)
        else None
    ) or payload.get("model_prediction") or {}
    if not isinstance(raw, dict):
        return None, {}
    if str(raw.get("status") or "").lower() != "available":
        return None, raw
    return raw, raw


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { --judge-teal:#0f766e; --judge-aqua:#14b8a6; --judge-purple:#7066d9; }
        .judge-hero {
          margin:.15rem 0 1.1rem;padding:1.25rem 1.4rem;border-radius:24px;
          border:1px solid rgba(15,118,110,.16);
          background:
            radial-gradient(circle at 90% 8%,rgba(184,167,255,.32),transparent 29%),
            linear-gradient(118deg,rgba(20,184,166,.16),rgba(255,255,255,.96) 50%,rgba(245,158,11,.10));
          box-shadow:0 16px 36px rgba(15,118,110,.10);
        }
        .judge-hero h1 {font-size:1.62rem!important;margin:0 0 .35rem!important;color:#143c3a;}
        .judge-hero p {margin:0;color:#526b69;line-height:1.75;font-size:.92rem;}
        .judge-values {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.7rem;margin:.7rem 0 1.15rem;}
        .judge-value {padding:.88rem 1rem;border-radius:16px;background:#fff;border:1px solid rgba(15,118,110,.14);box-shadow:0 7px 18px rgba(15,118,110,.055);}
        .judge-value b {display:block;color:#173f3d;margin-bottom:.22rem;}
        .judge-value span {font-size:.78rem;color:#637977;line-height:1.6;}
        .judge-summary {
          margin:.35rem 0 1rem;padding:1rem 1.15rem;border-radius:18px;color:#fff;
          background:linear-gradient(120deg,#0f766e,#0d9488 56%,#625fd1 128%);
          box-shadow:0 14px 30px rgba(13,148,136,.18);
        }
        .judge-summary-title {font-weight:820;font-size:1.22rem;}
        .judge-summary-copy {opacity:.9;font-size:.82rem;margin-top:.2rem;line-height:1.6;}
        .judge-kpis {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin-top:.8rem;}
        .judge-kpi {padding:.62rem .7rem;border-radius:12px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.17);}
        .judge-kpi strong {display:block;font-size:1.08rem;}
        .judge-kpi span {font-size:.7rem;opacity:.84;}
        .risk-card-title {display:flex;justify-content:space-between;gap:.6rem;align-items:flex-start;padding:.72rem .82rem;border-radius:13px;border-left:5px solid #64748b;background:#f8fafc;margin-bottom:.7rem;}
        .risk-card-title.high,.risk-card-title.critical {border-left-color:#e11d48;background:#fff1f2;}
        .risk-card-title.medium {border-left-color:#d97706;background:#fffbeb;}
        .risk-card-title.low {border-left-color:#0f766e;background:#f0fdfa;}
        .risk-card-name {font-weight:820;color:#183a38;}
        .risk-card-level {font-size:.76rem;font-weight:800;background:rgba(255,255,255,.86);padding:.3rem .55rem;border-radius:999px;white-space:nowrap;}
        .judge-story-grid {display:grid;grid-template-columns:1fr 1fr;gap:.65rem;margin:.5rem 0 .7rem;}
        .judge-story {padding:.78rem .86rem;border:1px solid #e1eceb;border-radius:13px;background:#f9fcfc;}
        .judge-story b {display:block;color:#315b58;font-size:.78rem;margin-bottom:.2rem;}
        .judge-story span {color:#425d5a;font-size:.81rem;line-height:1.65;}
        .trust-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;margin:.5rem 0 1rem;}
        .trust-grid div {padding:.6rem .7rem;text-align:center;border-radius:12px;background:#effcf9;border:1px solid rgba(13,148,136,.14);font-size:.74rem;color:#285653;font-weight:650;}
        @media (max-width:900px) {
          .judge-values,.judge-kpis,.trust-grid {grid-template-columns:1fr 1fr;}
          .judge-story-grid {grid-template-columns:1fr;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _hero() -> None:
    st.markdown(
        """
        <div class="judge-hero">
          <h1>港股 IPO 智能风险研判平台</h1>
          <p>招股书风险识别 · 原文证据定位 · 风险归因 · 多智能体交叉核验。<br>
          目标不是只给一个分数，而是让管理层知道“有什么风险、为什么、证据在哪里、下一步该核查什么”。</p>
        </div>
        <div class="judge-values">
          <div class="judge-value"><b>找风险</b><span>覆盖财务、法律合规与业务风险，优先呈现需要管理层关注的事项。</span></div>
          <div class="judge-value"><b>找证据</b><span>风险结论绑定真实招股书页码与 Evidence，可回到原文逐项复核。</span></div>
          <div class="judge-value"><b>讲原因</b><span>把结构化事实翻译为业务含义、判断依据和下一步复核重点。</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _all_risks(payload: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    domains = payload.get("domains") or {}
    for domain in ("financial", "legal", "business"):
        rows.extend((domains.get(domain) or {}).get("risks") or [])
    return rows


def _management_summary(payload: dict[str, object]) -> None:
    summary = summarize_risks(_all_risks(payload))
    highest = risk_level_label(summary["highest_level"])
    st.markdown(
        f"""
        <div class="judge-summary">
          <div class="judge-summary-title">综合风险研判：{escape(str(highest))}</div>
          <div class="judge-summary-copy">
            当前结论仅汇总本次运行已经生成的风险、验证状态和真实 Evidence；
            不把缺失信息补成“低风险”，也不静默抹平冲突。
          </div>
          <div class="judge-kpis">
            <div class="judge-kpi"><strong>{summary["total"]}</strong><span>正式风险项</span></div>
            <div class="judge-kpi"><strong>{summary["high_or_critical"]}</strong><span>高 / 极高风险</span></div>
            <div class="judge-kpi"><strong>{summary["needs_review"]}</strong><span>待进一步复核</span></div>
            <div class="judge-kpi"><strong>{summary["evidence_count"]}</strong><span>已绑定原文证据</span></div>
          </div>
        </div>
        <div class="trust-grid">
          <div>原文证据可回溯</div>
          <div>上市时点数据边界</div>
          <div>冲突不静默抹平</div>
          <div>支持专家人工复核</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "可信边界：市场与结果类数据遵循受治理的时点/冻结边界；不可用信息原样保留。"
    )


def _risk_card(risk: dict[str, object], *, expert: bool) -> None:
    code = str(risk.get("risk_code") or "Unavailable")
    level = str(risk.get("level") or "unavailable").lower()
    verification = str(risk.get("verification_status") or "unavailable")
    evidence = risk.get("evidence") or []
    calculation = risk.get("calculation")

    with st.container(border=True):
        st.markdown(
            "<div class='risk-card-title " + escape(level) + "'>"
            "<div><div class='risk-card-name'>" + escape(risk_display_name(code)) + "</div>"
            "<div style='font-size:.75rem;color:#647875;margin-top:.15rem'>"
            + escape(status_label(verification))
            + "</div></div>"
            "<div class='risk-card-level'>" + escape(risk_level_label(level)) + "风险</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("**一句话结论**")
        st.write(risk.get("conclusion") or "本次未生成风险结论。")
        st.markdown(
            "<div class='judge-story-grid'>"
            "<div class='judge-story'><b>为什么值得关注</b><span>"
            + escape(risk_reasoning(code))
            + "</span></div>"
            "<div class='judge-story'><b>建议进一步核查</b><span>"
            + escape(risk_review_focus(code))
            + "</span></div></div>",
            unsafe_allow_html=True,
        )

        basis: list[str] = []
        if evidence:
            basis.append(f"已绑定 {len(evidence)} 条招股书原文证据")
        if calculation:
            basis.append("存在确定性计算依据")
        if basis:
            st.markdown("**判断依据**")
            st.caption("；".join(basis) + "。")

        if evidence:
            st.markdown(f"**原文证据 · {len(evidence)} 条**")
            for idx, item in enumerate(evidence, start=1):
                page = item.get("page", "—")
                label = f"第 {page} 页 · 原文证据 {idx}"
                if expert:
                    label += f" · {item.get('evidence_id', '—')}"
                with st.expander(label):
                    st.write(item.get("text") or "该条 Evidence 暂无可展示原文。")
        else:
            render_state_panel(
                "尚未附着原文证据",
                verification,
                "当前没有关联 Evidence，因此该风险仍需谨慎解读和进一步复核。",
            )

        if calculation:
            with st.expander("计算依据"):
                st.json(calculation)
        if expert and risk.get("metadata"):
            with st.expander("技术审计：结构化事实 / metadata"):
                st.json(risk["metadata"])


def _run_analysis(
    *,
    config_path: str,
    company: str,
    code: str,
    listing: date,
    uploaded,
):
    if uploaded is None:
        raise ValueError("请先上传招股书 PDF。")
    content = uploaded.getvalue()
    validate_pdf_upload(uploaded.name, content)
    settings = load_settings(config_path)
    with temporary_pdf(content) as prospectus_path:
        request = build_analysis_request(
            company_name=company,
            stock_code=code,
            listing_date=listing,
            prospectus_path=prospectus_path,
            use_mock=False,
            workflow_version=settings.workflow_version,
        )
        with st.spinner("正在解析招股书、识别风险、绑定 Evidence，并形成综合研判……"):
            return IPOAnalysisService(settings=settings).analyze(request), content


def _render_overview(payload: dict[str, object]) -> None:
    profile = payload.get("profile") or {}
    _management_summary(payload)
    render_case_header(payload)
    render_channel_grid(payload)

    st.markdown("### 发行人信息")
    render_profile_grid(
        (
            ("公司", profile.get("company_name") or "不可用"),
            ("股票代码", profile.get("stock_code") or "不可用"),
            ("上市日期", profile.get("listing_date") or "不可用"),
            ("行业", profile.get("industry") or "不可用"),
            ("发行价", profile.get("issue_price") or "不可用"),
            ("发行规模", profile.get("issue_size") or "不可用"),
        )
    )

    left, right = st.columns((1, 1.35))
    with left:
        st.markdown("### 风险覆盖")
        render_modern_table(
            domain_summary_rows(payload),
            badge_columns={"领域": "domain", "状态": "status"},
            compact=True,
        )
    with right:
        st.markdown("### 风险清单")
        inventory = risk_inventory_rows(payload)
        if inventory:
            st.dataframe(inventory, hide_index=True, width="stretch")
        else:
            render_state_panel(
                "暂无正式风险项",
                "unavailable",
                "本次运行未产出正式风险项；界面不会用“低风险”替代未知状态。",
            )


def _render_risks(payload: dict[str, object], *, expert: bool) -> None:
    st.markdown("## 风险解释与原文证据")
    st.caption("先解释为什么值得关注，再回到招股书原文、计算依据和复核状态。")
    domains = payload.get("domains") or {}
    tabs = st.tabs([domain_label(x) for x in ("financial", "legal", "business")])
    for domain, tab in zip(("financial", "legal", "business"), tabs, strict=True):
        with tab:
            risks = (domains.get(domain) or {}).get("risks") or []
            if not risks:
                render_state_panel(
                    "该领域暂无正式风险项",
                    (domains.get(domain) or {}).get("status", "unavailable"),
                    "本次运行未在该领域识别到正式风险项。",
                )
            for risk in risks:
                _risk_card(risk, expert=expert)

    st.divider()
    render_evidence_viewer(
        payload,
        st.session_state.get("judge_prospectus_bytes"),
        None,
    )


def _render_market_model(payload: dict[str, object], *, expert: bool) -> None:
    st.markdown("## 市场与模型信号")
    st.caption("上市前市场环境按受治理时点展示；模型评分只在存在可核验结果时展示。")
    left, right = st.columns((1.18, 1))
    with left:
        market = payload.get("market_context") or {}
        available, total = available_market_observation_count(payload)
        st.markdown("### 上市前市场环境")
        st.markdown(
            f"**Market-X：{status_label(market.get('status', 'unavailable'))}** · "
            f"可用观测 {available}/{total if total else 0}"
        )
        degradation = market_degradation_summary(payload)
        if degradation:
            st.info(f"缺失观测及原因：{degradation}")
        rows = market_runtime_summary(payload)
        if rows:
            st.dataframe(rows, hide_index=True, width="stretch")
        observations = market.get("observations") or []
        if observations:
            st.dataframe(
                localize_market_observation_rows(observations),
                hide_index=True,
                width="stretch",
            )
        if expert:
            with st.expander("技术审计：Market-X provenance"):
                st.json(market.get("provenance") or {})

    with right:
        model, raw_model = _model_projection(payload)
        st.markdown("### 模型与规则信号")
        if model is not None:
            st.metric("模型评分", model.get("score", "不可用"))
            st.caption(
                f"评分语义：{model.get('score_semantics', '不可用')} · "
                f"校准状态：{model.get('calibration_status', '不可用')}"
            )
            drivers = model.get("drivers") or []
            if drivers:
                st.markdown("**主要驱动因素（SHAP）**")
                st.dataframe(drivers, hide_index=True, width="stretch")
        else:
            states = channel_state_map(payload)
            raw_status = str(raw_model.get("status") or states.get("model") or "unavailable")
            detail = "该 IPO 暂无可核验的冻结逐案例模型评分。"
            if expert and raw_model.get("reason"):
                detail += f" 技术原因：{raw_model['reason']}"
            render_state_panel(
                "冻结模型结果不可用",
                raw_status,
                detail,
            )
        prediction = payload.get("prediction") or {}
        col1, col2 = st.columns(2)
        col1.metric("规则评分", prediction.get("risk_score", "不可用"))
        col2.metric("风险等级", risk_level_label(prediction.get("risk_level")))
        st.caption("规则信号用于确定性风险排序，不是概率，也不是收益预测。")


def _render_reasoning_trace(payload: dict[str, object], *, expert: bool) -> None:
    st.markdown("## 结论形成过程")
    st.caption("风险事实识别 → 原文证据绑定 → 风险判断 → 交叉核验 → 定向复核 → 综合研判。")
    counts = conflict_status_counts(payload)
    if counts:
        cols = st.columns(len(counts))
        for col, (status, count) in zip(cols, sorted(counts.items()), strict=False):
            col.metric(RESOLUTION_LABELS.get(status, status), count)
        st.caption("未解决冲突会被明确保留，不会被模型静默覆盖。")
    else:
        render_state_panel(
            "未检出跨智能体冲突",
            "available",
            "本次运行没有记录跨智能体冲突；各风险项仍按自身 Evidence 与验证状态独立判断。",
        )

    if not expert:
        st.info("需要查看 Provider、Prompt、Evidence ID 与完整事件 sidecar 时，可在左侧开启“专家 / 技术审计模式”。")
        return

    metrics = traceability_metrics(payload)
    if metrics:
        st.markdown("### 技术审计：可追溯率")
        st.dataframe(metrics, hide_index=True, width="stretch")
    rows = trace_rows(payload)
    if rows:
        with st.expander(f"技术审计：完整事件轨迹 · {len(rows)}"):
            st.dataframe(rows, hide_index=True, width="stretch")
        with st.expander("原始 competition runtime sidecar"):
            st.json((payload.get("component_diagnostics") or {}).get("competition_runtime") or {})


def _render_report(payload: dict[str, object], result, *, expert: bool) -> None:
    st.markdown("## 专家复核与最终报告")
    st.caption("下载结果用于审阅与交付；人工判断不会静默覆盖机器原始结论。")
    stem = safe_download_stem(result.stock_code)
    left, right = st.columns(2)
    left.download_button(
        "下载 Markdown 报告",
        markdown_report(result),
        file_name=f"{stem}-risk-report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    right.download_button(
        "下载结构化 JSON",
        json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{stem}-risk-result.json",
        mime="application/json",
        use_container_width=True,
    )
    final = payload.get("final_supervision") or {}
    if final:
        st.markdown("### 综合研判")
        st.write(final.get("summary") or final.get("uncertainty_statement") or "综合研判结果已生成。")
        if final.get("uncertainty_statement"):
            st.warning(final["uncertainty_statement"])
    if expert:
        with st.expander("技术审计：完整结构化 payload"):
            st.json(payload)


st.set_page_config(
    page_title="港股 IPO 智能风险研判",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_competition_theme()
_inject_css()

st.sidebar.markdown("## 港股 IPO 风险研判")
st.sidebar.caption("证据驱动 · 可解释 · 可追溯")
expert_mode = st.sidebar.checkbox("专家 / 技术审计模式", value=False)
scenario = st.sidebar.selectbox("分析模式", list(SCENARIOS), index=0)
config_path = SCENARIOS[scenario]
st.sidebar.caption("市场与结果类数据遵循受治理的时点/冻结边界；不可用信息不会被填成 0。")

previous_scenario = st.session_state.get("_judge_runtime_scenario_seen")
if previous_scenario is not None and previous_scenario != scenario:
    _clear_judge_intake_state()
st.session_state["_judge_runtime_scenario_seen"] = scenario

current_runtime = _runtime_fingerprint(config_path)
if not current_runtime["source_matches_checkout"]:
    st.error(
        "前端加载的后端代码不属于当前项目目录。"
        "为避免新界面与旧运行时混用，系统已停止本次展示；"
        "请使用当前项目的 src 路径重新启动。"
    )
    st.stop()

_hero()

company, code, listing = render_issuer_identity_inputs(key_prefix="judge")
uploaded = st.file_uploader("上传招股书 PDF", type=["pdf"])
if st.button("开始风险研判", type="primary", use_container_width=True):
    try:
        new_result, new_prospectus_bytes = _run_analysis(
            config_path=config_path,
            company=company,
            code=code,
            listing=listing,
            uploaded=uploaded,
        )
    except Exception as exc:
        st.error(f"分析未完成，系统已安全停止：{exc}")
    else:
        if _analysis_failed(new_result):
            error_detail = next(
                (str(item.message) for item in new_result.errors if item.message),
                "运行返回了失败状态",
            )
            st.error(
                f"分析未完成：{error_detail}。"
                "上一份成功结果及其原文文件已保留，未被本次失败运行覆盖。"
            )
        else:
            completed_runtime = _runtime_fingerprint(config_path)
            result_fingerprint = _result_fingerprint(
                new_result,
                completed_runtime,
                scenario,
            )
            # Install the result, its PDF and its runtime identity as one bundle.
            # Nothing from the previous successful case is removed until the
            # replacement has completed and passed the failed-status boundary.
            _clear_judge_result()
            st.session_state["judge_result"] = new_result
            st.session_state["judge_result_fingerprint"] = result_fingerprint
            st.session_state["judge_result_scenario"] = scenario
            st.session_state["judge_result_config_path"] = config_path
            st.session_state["judge_prospectus_bytes"] = new_prospectus_bytes
            st.rerun()

stored_result = st.session_state.get("judge_result")
result = stored_result
if stored_result is not None:
    compatible, compatibility_notice = _result_compatibility(
        stored_result,
        st.session_state.get("judge_result_fingerprint"),
    )
    if not compatible:
        result = None
        st.warning(compatibility_notice)
    else:
        origin_scenario = (
            st.session_state.get("judge_result_fingerprint") or {}
        ).get("scenario")
        if origin_scenario not in {None, scenario}:
            st.info(
                f"当前案例由“{origin_scenario}”生成；已选的“{scenario}”"
                "只用于下一次新分析，不会改写当前结果。"
            )
if result is None:
    st.info("上传招股书后，系统将依次给出风险总览、风险解释与原文证据、市场与模型、结论形成过程和最终报告。")
else:
    if st.sidebar.button("清除当前结果"):
        _clear_judge_result()
        st.rerun()

    payload = result_payload(result)
    tabs = st.tabs(
        [
            "风险总览",
            "风险解释与证据",
            "市场与模型",
            "结论形成过程",
            "专家复核与报告",
        ]
    )
    with tabs[0]:
        _render_overview(payload)
    with tabs[1]:
        _render_risks(payload, expert=expert_mode)
    with tabs[2]:
        _render_market_model(payload, expert=expert_mode)
    with tabs[3]:
        _render_reasoning_trace(payload, expert=expert_mode)
    with tabs[4]:
        _render_report(payload, result, expert=expert_mode)
