"""Streamlit presentation layer; it only calls IPOAnalysisService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json

import streamlit as st

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
    "v0.3 enhanced AI": ("configs/v03_ai.yaml", True),
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


def _display_value(value: object) -> str:
    return "Unavailable" if value in (None, "", {}) else str(value)


def _render_risk(risk: dict[str, object]) -> None:
    title = (
        f"{RISK_TITLES.get(str(risk['risk_code']), str(risk['risk_code']))} · "
        f"{risk['level']} · rule score {risk['score']} · "
        f"{risk['verification_status']}"
    )
    with st.expander(title, expanded=True):
        st.caption(f"Risk code: {risk['risk_code']}")
        if risk.get("category") in {"legal", "business"}:
            st.caption("v0.3 severity is provisional; deterministic policy does not auto-escalate to high/critical.")
        st.write(risk["conclusion"])
        st.caption(f"Verifier notes: {_display_value(risk.get('verification_notes'))}")
        calculation = risk.get("calculation")
        if calculation:
            st.markdown("**Deterministic Calculation**")
            st.json(calculation)
        st.markdown("**Evidence**")
        evidence_items = risk.get("evidence") or []
        if not evidence_items:
            st.info("No Evidence is attached; this item cannot be treated as verified.")
        for evidence in evidence_items:
            st.markdown(
                f"`{evidence['evidence_id']}` · physical PDF page "
                f"**{_display_value(evidence.get('page'))}**"
            )
            st.write(evidence["text"])
        if risk.get("metadata"):
            with st.expander("Structured facts / metadata"):
                st.json(risk["metadata"])


st.set_page_config(page_title="HK IPO Risk Agents", page_icon="📊", layout="wide")
st.title("HK IPO Risk Agents")
st.caption("港股 IPO 招股书证据驱动多智能体风险分析 · Evidence-driven multi-agent review")

scenario = st.sidebar.selectbox("Runtime scenario", list(SCENARIOS))
config_path, needs_pdf = SCENARIOS[scenario]
st.sidebar.markdown(f"**Configuration:** `{config_path}`")
st.sidebar.info(
    "Offline mode makes no external model call. AI mode reads credentials only from "
    "environment variables and degrades safely when unavailable."
)

with st.form("analysis"):
    company = st.text_input("Company name", "Demo Biotech")
    code = st.text_input("Stock code", "9999.HK")
    listing = st.date_input("Listing date", date.today())
    uploaded = st.file_uploader("Prospectus PDF", type=["pdf"]) if needs_pdf else None
    submitted = st.form_submit_button("Run analysis", type="primary")

if submitted:
    try:
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
                result = IPOAnalysisService(settings=settings).analyze(request)
        else:
            request = build_analysis_request(
                company_name=company,
                stock_code=code,
                listing_date=listing,
                prospectus_path="mock://prospectus",
                use_mock=True,
                workflow_version=settings.workflow_version,
            )
            result = IPOAnalysisService(settings=settings).analyze(request)
    except ValueError as exc:
        st.error(str(exc))
    else:
        payload = result_payload(result)
        profile = payload["profile"]
        prediction = payload["prediction"] or {}
        counts = payload["risk_status_counts"]

        st.subheader("IPO Profile and runtime")
        profile_columns = st.columns(4)
        profile_columns[0].metric("Company", _display_value(profile.get("company_name")))
        profile_columns[1].metric("Stock code", _display_value(profile.get("stock_code")))
        profile_columns[2].metric("Listing date", _display_value(profile.get("listing_date")))
        profile_columns[3].metric("Industry", _display_value(profile.get("industry")))
        st.dataframe(
            [
                {
                    "Issue price": _display_value(profile.get("issue_price")),
                    "Issue size": _display_value(profile.get("issue_size")),
                    "Security category": _display_value(profile.get("security_category")),
                    "IPO data source": _display_value(profile.get("source")),
                    "Match status": _display_value(profile.get("match_status")),
                    "Workflow": payload["workflow_version"],
                    "Runtime mode": payload["configuration"].get("runtime_mode", "Unavailable"),
                    "LLM mode": payload["component_modes"].get("llm_status", "Unavailable"),
                    "Result status": payload["status"],
                    "Parsed pages": payload["document"].get("parsed_chunk_count", "Unavailable"),
                    "Parser errors": payload["document"].get("parser_error_count", 0),
                }
            ],
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Overall risk dashboard")
        metrics = st.columns(6)
        metrics[0].metric("Overall rule score", _display_value(prediction.get("risk_score")))
        metrics[1].metric("Rule level", _display_value(prediction.get("risk_level")))
        metrics[2].metric("Verified", counts["verified"])
        metrics[3].metric("Needs review", counts["needs_review"])
        metrics[4].metric("Pending", counts["pending"])
        metrics[5].metric("Rejected", counts["rejected"])
        st.warning(
            "Rule scores are deterministic prioritization signals—not probabilities, "
            "stock-return forecasts, or investment/legal advice."
        )

        overview, financial, legal, business, supervisor, diagnostics = st.tabs(
            ["Overview", "Financial", "Legal", "Business", "Supervisor", "Diagnostics"]
        )
        with overview:
            st.subheader("Report sections")
            for section in payload["report_sections"]:
                st.markdown(f"### {section['order']}. {section['title']}")
                st.write(section["summary"])
            stem = safe_download_stem(result.stock_code)
            first, second = st.columns(2)
            first.download_button(
                "Download complete Markdown report",
                markdown_report(result),
                file_name=f"{stem}-risk-report.md",
                mime="text/markdown",
            )
            second.download_button(
                "Download structured JSON",
                json.dumps(payload, ensure_ascii=False, indent=2),
                file_name=f"{stem}-risk-result.json",
                mime="application/json",
            )

        domain_tabs = {"financial": financial, "legal": legal, "business": business}
        for domain in DOMAINS:
            with domain_tabs[domain]:
                domain_data = payload["domains"][domain]
                st.caption(
                    f"Agent status: {domain_data['status']} · "
                    f"risk count: {domain_data['risk_count']}"
                )
                domain_counts = domain_data["status_counts"]
                status_columns = st.columns(4)
                status_columns[0].metric("Verified", domain_counts.get("verified", 0))
                status_columns[1].metric("Needs review", domain_counts.get("needs_review", 0))
                status_columns[2].metric("Pending", domain_counts.get("pending", 0))
                status_columns[3].metric("Rejected", domain_counts.get("rejected", 0))
                if domain_data["diagnostics"]:
                    with st.expander("Agent diagnostics"):
                        st.json(domain_data["diagnostics"])
                if not domain_data["risks"]:
                    st.info("No risk item was produced for this domain.")
                for risk in domain_data["risks"]:
                    _render_risk(risk)

        with supervisor:
            supervision = payload["supervision"]
            if not supervision:
                st.info("Supervisor output is unavailable for this workflow.")
            else:
                st.subheader("Cross-domain synthesis")
                st.write(supervision.get("summary", "No summary"))
                st.markdown("**Duplicate groups**")
                st.json(supervision.get("duplicate_groups", []))
                st.markdown("**Conflicts and semantic reconciliation**")
                st.json(supervision.get("conflicts", []))
                st.markdown("**Composite findings**")
                st.json(supervision.get("composite_findings", []))
                st.markdown("**Rule-score components**")
                st.json(supervision.get("metadata", {}).get("rule_score_components", []))

        with diagnostics:
            st.subheader("Component modes and status")
            st.dataframe(payload["component_statuses"], hide_index=True, use_container_width=True)
            st.subheader("Configuration and governance")
            st.json(
                {
                    "configuration": payload["configuration"],
                    "component_modes": payload["component_modes"],
                    "governance": payload["governance"],
                }
            )
            st.subheader("Structured errors")
            st.json(payload["errors"])
            st.subheader("Agent logs")
            st.json(payload["agent_logs"])
