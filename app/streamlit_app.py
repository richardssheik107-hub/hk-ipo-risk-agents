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
    domain_summary_rows,
    render_case_header,
    render_channel_grid,
    render_competition_roadmap,
    render_empty_state,
    render_executive_snapshot,
    render_pipeline_strip,
    render_product_header,
    risk_inventory_rows,
)
from pipeline_stages import StageStatus, pending_notice, resolve_stages
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
from ipo_risk.services.analysis_service import IPOAnalysisService


SCENARIOS = {
    "Mock architecture demo": ("configs/mock.yaml", False),
    "v0.2 real cash-runway slice": ("configs/real_pdf.yaml", True),
    "v0.3 enhanced offline": ("configs/v03_offline.yaml", True),
    "v0.3 enhanced offline + tables": ("configs/v03_offline_table.yaml", True),
    "v0.3 enhanced AI": ("configs/v03_ai.yaml", True),
    "v0.3 enhanced AI + tables": ("configs/v03_ai_table.yaml", True),
    "v0.4 offline + Final Supervisor": ("configs/v04_offline.yaml", True),
    "v0.4 AI + Final Supervisor": ("configs/v04_ai.yaml", True),
    "Predictor failure degradation": ("configs/mock.yaml", False),
}

RISK_TITLES = {
    "cash_runway": "Cash runway / 现金跑道",
    "continuous_loss": "Continuous loss / 持续亏损",
    "revenue_growth": "Revenue growth / 收入增长",
    "customer_concentration": "Customer concentration / 客户集中度",
    "supplier_concentration": "Supplier concentration / 供应商集中度",
    "redemption_rights": "Special shareholder rights / 特殊股东权利",
    "material_litigation_compliance": "Material litigation and compliance / 重大诉讼与合规",
    "precommercial_product": "Pre-commercial product / 未商业化及核心产品依赖",
}

_STAGE_BADGES = {
    StageStatus.AVAILABLE: "🟢 Available",
    StageStatus.PARTIAL: "🟡 Partial",
    StageStatus.PENDING_GATE: "⚪ Not available",
}

_DOMAIN_TITLES = {
    "financial": "Financial",
    "legal": "Legal & Compliance",
    "business": "Business",
}


def _display_value(value: object) -> str:
    return "Unavailable" if value in (None, "", {}) else str(value)


def _clear_result() -> None:
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("analysis_scenario", None)


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
    if scenario == "Predictor failure degradation":
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
            with st.spinner(
                "Running governed analysis… parsing the prospectus, executing Agents, "
                "attaching available channels and supervising the final result."
            ):
                return IPOAnalysisService(settings=settings).analyze(request)

    request = build_analysis_request(
        company_name=company,
        stock_code=code,
        listing_date=listing,
        prospectus_path="mock://prospectus",
        use_mock=True,
        workflow_version=settings.workflow_version,
    )
    with st.spinner("Running analysis…"):
        return IPOAnalysisService(settings=settings).analyze(request)


def _risk_level_tone(level: object) -> str:
    normalized = str(level or "").lower()
    if normalized in {"critical", "high"}:
        return "status-bad"
    if normalized in {"medium"}:
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
    title = RISK_TITLES.get(risk_code, risk_code)
    level = str(risk.get("level", "Unavailable"))
    verification = str(risk.get("verification_status", "Unavailable"))
    score = _display_value(risk.get("score"))

    with st.container(border=True):
        st.markdown(f"#### {title}")
        st.markdown(
            "<div style='display:flex;gap:.4rem;flex-wrap:wrap;margin:-.2rem 0 .7rem 0'>"
            f"<span class='risk-chip {_risk_level_tone(level)}'>{escape(level.upper())}</span>"
            f"<span class='risk-chip {_verification_tone(verification)}'>{escape(verification.replace('_', ' ').upper())}</span>"
            f"<span class='risk-chip'>RULE SCORE {escape(score)}</span>"
            f"<span class='risk-chip'>{escape(risk_code)}</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.write(risk.get("conclusion") or "No conclusion was produced.")

        notes = risk.get("verification_notes")
        if notes:
            st.caption(f"Verifier · {notes}")
        if risk.get("category") in {"legal", "business"}:
            st.caption(
                "Severity is provisional in the current v0.3 document policy; deterministic policy does not auto-escalate Legal/Business to high or critical."
            )

        evidence_items = risk.get("evidence") or []
        if evidence_items:
            st.markdown(f"**Evidence · {len(evidence_items)} reference(s)**")
            for evidence in evidence_items:
                evidence_id = _display_value(evidence.get("evidence_id"))
                page = _display_value(evidence.get("page"))
                with st.expander(f"{evidence_id} · PDF page {page}", expanded=False):
                    st.write(evidence.get("text") or "No Evidence text is available.")
        else:
            st.info("No Evidence is attached; this item cannot be treated as verified.")

        calculation = risk.get("calculation")
        if calculation:
            with st.expander("Deterministic Calculation", expanded=False):
                st.json(calculation)

        if risk.get("metadata"):
            with st.expander("Structured facts / metadata", expanded=False):
                st.json(risk["metadata"])


def _render_sidebar_status(payload: dict[str, object], stages) -> None:
    profile = payload.get("profile") or {}
    st.sidebar.markdown("### Current analysis")
    st.sidebar.markdown(
        f"**{_display_value(profile.get('stock_code'))}** · {_display_value(profile.get('company_name'))}"
    )
    for stage in stages:
        suffix = f" · {stage.blocking_gate}" if stage.blocking_gate else ""
        st.sidebar.caption(f"{_STAGE_BADGES[stage.status]} {stage.ordinal}. {stage.title}{suffix}")


def _render_overview(payload: dict[str, object], stages) -> None:
    profile = payload["profile"]

    st.markdown("### Case profile")
    with st.container(border=True):
        first, second, third, fourth = st.columns((1.35, 1, 1, 1))
        first.markdown(f"**Company**  \n{_display_value(profile.get('company_name'))}")
        second.markdown(f"**Stock code**  \n{_display_value(profile.get('stock_code'))}")
        third.markdown(f"**Listing date**  \n{_display_value(profile.get('listing_date'))}")
        fourth.markdown(f"**Industry**  \n{_display_value(profile.get('industry'))}")
        st.divider()
        details = st.columns(5)
        details[0].markdown(f"**Issue price**  \n{_display_value(profile.get('issue_price'))}")
        details[1].markdown(f"**Issue size**  \n{_display_value(profile.get('issue_size'))}")
        details[2].markdown(f"**Security**  \n{_display_value(profile.get('security_category'))}")
        details[3].markdown(f"**IPO source**  \n{_display_value(profile.get('source'))}")
        details[4].markdown(f"**Match status**  \n{_display_value(profile.get('match_status'))}")

    left, right = st.columns((1.05, 1.45))
    with left:
        st.markdown("### Domain coverage")
        st.dataframe(domain_summary_rows(payload), hide_index=True, use_container_width=True)
    with right:
        st.markdown("### Risk inventory")
        inventory = risk_inventory_rows(payload)
        if inventory:
            st.dataframe(inventory, hide_index=True, use_container_width=True)
        else:
            st.info("No risk item was emitted for this run.")

    st.markdown("### Governed pipeline")
    render_pipeline_strip(stages)
    st.caption(
        "Rule scores are deterministic prioritization signals—not probabilities, stock-return forecasts, or investment/legal advice."
    )


def _render_risks_and_evidence(payload: dict[str, object]) -> None:
    st.markdown("### Risk & Evidence workspace")
    st.caption("Read the conclusion first; open Evidence, Calculation and metadata only when you need to audit the finding.")
    domain_tabs = st.tabs([_DOMAIN_TITLES[domain] for domain in DOMAINS])
    for domain, tab in zip(DOMAINS, domain_tabs, strict=True):
        with tab:
            domain_data = payload["domains"][domain]
            counts = domain_data["status_counts"]
            top = st.columns(4)
            top[0].metric("Risk items", domain_data["risk_count"])
            top[1].metric("Verified", counts.get("verified", 0))
            top[2].metric("Needs review", counts.get("needs_review", 0))
            top[3].metric("Pending / rejected", counts.get("pending", 0) + counts.get("rejected", 0))
            if not domain_data["risks"]:
                st.info("No risk item was produced for this domain.")
            for risk in domain_data["risks"]:
                _render_risk(risk)
            if domain_data["diagnostics"]:
                with st.expander("Agent diagnostics", expanded=False):
                    st.json(domain_data["diagnostics"])


def _render_market_and_model(payload: dict[str, object], stages_by_id: dict[str, object]) -> None:
    st.markdown("### Market & model signals")
    st.caption("Market missingness stays explicit. Model scores appear only when the frozen per-case runtime handoff is available.")

    left, right = st.columns((1.22, 1))
    with left:
        st.markdown("#### Governed Market-X context")
        market = payload.get("market_context") or {}
        available, total = available_market_observation_count(payload)
        status = market.get("status", "unavailable")
        top = st.columns(2)
        top[0].metric("Channel status", str(status).upper())
        top[1].metric("Available observations", f"{available}/{total}" if total else "0/0")
        observations = market.get("observations") or []
        if observations:
            st.dataframe(observations, hide_index=True, use_container_width=True)
        else:
            st.info("No market observation is reported for this run.")
        with st.expander("Market provenance", expanded=False):
            st.json(market.get("provenance", {}))

    with right:
        final = payload.get("final_supervision") or {}
        states = channel_state_map(payload)
        model = final.get("model_prediction")
        st.markdown("#### Frozen model signal")
        if model:
            st.metric("Model score", model.get("score", "Unavailable"))
            st.caption(
                f"Semantics: {model.get('score_semantics', 'Unavailable')} · calibration: {model.get('calibration_status', 'Unavailable')}"
            )
            drivers = model.get("drivers") or []
            if drivers:
                st.markdown("**Top drivers**")
                st.dataframe(drivers, hide_index=True, use_container_width=True)
        else:
            st.info(
                f"Model channel: {states.get('model', 'unavailable').upper()}. No per-case frozen model score is rendered for this IPO."
            )

        st.markdown("#### Deterministic rule signal")
        prediction = payload.get("prediction") or {}
        rule_cols = st.columns(2)
        rule_cols[0].metric("Rule score", prediction.get("risk_score", "Unavailable"))
        rule_cols[1].metric("Rule level", prediction.get("risk_level", "Unavailable"))
        st.caption("The rule signal is deterministic prioritization, not a probability or return forecast.")

        uncertainty = final.get("uncertainty_statement")
        if uncertainty:
            st.warning(uncertainty)

    notices = []
    for stage_id in ("market_features", "prediction", "explainability"):
        stage = stages_by_id.get(stage_id)
        if stage is not None:
            notice = pending_notice(stage)
            if notice:
                notices.append((stage.title, notice))
    if notices:
        with st.expander("Channel limitations", expanded=False):
            for title, notice in notices:
                st.markdown(f"**{title}**")
                st.write(notice)


def _render_supervisor_and_report(payload: dict[str, object], result, stages_by_id: dict[str, object]) -> None:
    st.markdown("### Supervisor & final report")

    stem = safe_download_stem(result.stock_code)
    first, second = st.columns(2)
    first.download_button(
        "Download Markdown report",
        markdown_report(result),
        file_name=f"{stem}-risk-report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    second.download_button(
        "Download structured JSON",
        json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{stem}-risk-result.json",
        mime="application/json",
        use_container_width=True,
    )

    final = payload.get("final_supervision") or {}
    if final:
        with st.container(border=True):
            st.markdown("#### Final Supervisor")
            st.write(final.get("summary") or "No synthesis summary was produced.")
            render_channel_grid(payload)
            uncertainty = final.get("uncertainty_statement")
            if uncertainty:
                st.warning(uncertainty)

            conflicts = final.get("conflicts") or []
            if conflicts:
                with st.expander(f"Preserved conflicts · {len(conflicts)}", expanded=False):
                    st.json(conflicts)
            else:
                st.caption("No preserved cross-channel conflict is reported for this run.")
    else:
        st.info("Final Supervisor output is unavailable for this workflow.")

    supervision = payload.get("supervision") or {}
    if supervision:
        with st.expander("Document Supervisor detail", expanded=False):
            st.write(supervision.get("summary", "No summary"))
            st.markdown("**Duplicate groups**")
            st.json(supervision.get("duplicate_groups", []))
            st.markdown("**Conflicts and semantic reconciliation**")
            st.json(supervision.get("conflicts", []))
            st.markdown("**Composite findings**")
            st.json(supervision.get("composite_findings", []))
            st.markdown("**Rule-score components**")
            st.json(supervision.get("metadata", {}).get("rule_score_components", []))

    st.markdown("### 13-section report")
    for section in sorted(payload["report_sections"], key=lambda item: item["order"]):
        expanded = section["order"] in {1, 2, 9}
        with st.expander(f"{section['order']}. {section['title']}", expanded=expanded):
            st.write(section["summary"])
            if section.get("metadata"):
                with st.expander("Structured section metadata", expanded=False):
                    st.json(section["metadata"])

    stage = stages_by_id.get("final_report")
    if stage is not None:
        notice = pending_notice(stage)
        if notice:
            st.info(notice)


def _render_system(payload: dict[str, object], stages) -> None:
    st.markdown("### System, provenance & diagnostics")
    st.caption("Engineering detail is intentionally separated from the decision workspace.")

    stage_rows = []
    for stage in stages:
        status = getattr(stage.status, "value", str(stage.status))
        stage_rows.append(
            {
                "Stage": stage.ordinal,
                "Name": stage.title,
                "Status": status,
                "Blocking gate": stage.blocking_gate or "",
                "Summary": stage.summary,
            }
        )
    st.markdown("#### Pipeline state")
    st.dataframe(stage_rows, hide_index=True, use_container_width=True)

    with st.expander("Stage limitations and pending outputs", expanded=False):
        any_notice = False
        for stage in stages:
            notice = pending_notice(stage)
            if notice:
                any_notice = True
                st.markdown(f"**{stage.ordinal}. {stage.title}**")
                st.write(notice)
                if stage.what_appears_when_unblocked:
                    for item in stage.what_appears_when_unblocked:
                        st.markdown(f"- {item}")
        if not any_notice:
            st.write("No pending stage notice is attached to this run.")

    st.markdown("#### Component status")
    st.dataframe(payload["component_statuses"], hide_index=True, use_container_width=True)

    with st.expander("Configuration & governance", expanded=False):
        st.json(
            {
                "configuration": payload["configuration"],
                "component_modes": payload["component_modes"],
                "governance": payload["governance"],
            }
        )

    errors = payload.get("errors") or []
    if errors:
        with st.expander(f"Structured errors · {len(errors)}", expanded=False):
            st.json(errors)
    else:
        st.success("No structured workflow error is recorded for this run.")

    with st.expander("Agent logs", expanded=False):
        st.json(payload.get("agent_logs") or [])


st.set_page_config(
    page_title="HK IPO Risk Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_competition_theme()
render_product_header()

scenario_names = list(SCENARIOS)
default_scenario = scenario_names.index("v0.4 offline + Final Supervisor")
scenario = st.sidebar.selectbox(
    "Runtime scenario",
    scenario_names,
    index=default_scenario,
    key="runtime_scenario",
    on_change=_clear_result,
)
config_path, needs_pdf = SCENARIOS[scenario]

st.sidebar.markdown("### Runtime policy")
st.sidebar.caption(f"Config · `{config_path}`")
st.sidebar.caption("Offline mode makes no external model call. AI mode reads credentials from environment variables and degrades safely when unavailable.")
st.sidebar.caption("Current formal gate · PR-H full governed end-to-end integration.")
if "analysis_result" in st.session_state:
    if st.sidebar.button("Clear current analysis", use_container_width=True):
        _clear_result()
        st.rerun()

st.markdown("<div class='section-eyebrow'>ANALYZE A PROSPECTUS</div>", unsafe_allow_html=True)
with st.form("analysis"):
    first, second, third = st.columns((1.4, 1, 1))
    with first:
        company = st.text_input("Company name", "Demo Biotech")
    with second:
        code = st.text_input("Stock code", "9999.HK")
    with third:
        listing = st.date_input("Listing date", date.today())
    uploaded = st.file_uploader("Prospectus PDF", type=["pdf"]) if needs_pdf else None
    submitted = st.form_submit_button("Run governed analysis", type="primary", use_container_width=True)

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
        st.error(str(exc))
    except Exception as exc:  # UI boundary: fail visibly instead of blanking the app.
        st.error(f"Analysis failed safely: {exc}")
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

    st.markdown("<div class='section-eyebrow'>CHANNEL AVAILABILITY</div>", unsafe_allow_html=True)
    render_channel_grid(payload)

    workspace_tabs = st.tabs(
        [
            "Overview",
            "Risks & Evidence",
            "Market & Model",
            "Supervisor & Report",
            "Roadmap",
            "System",
        ]
    )

    with workspace_tabs[0]:
        _render_overview(payload, stages)

    with workspace_tabs[1]:
        _render_risks_and_evidence(payload)

    with workspace_tabs[2]:
        _render_market_and_model(payload, stages_by_id)

    with workspace_tabs[3]:
        _render_supervisor_and_report(payload, result, stages_by_id)

    with workspace_tabs[4]:
        render_competition_roadmap()

    with workspace_tabs[5]:
        _render_system(payload, stages)
