"""Streamlit presentation layer; it only calls IPOAnalysisService."""
from dataclasses import replace
from datetime import date

import streamlit as st

from presenters import (
    build_analysis_request,
    result_payload,
    temporary_pdf,
    validate_pdf_upload,
)
from ipo_risk.core.config import load_settings
from ipo_risk.services.analysis_service import IPOAnalysisService


st.set_page_config(page_title="HK IPO Risk Agents", layout="wide")
st.title("HK IPO Risk Agents")
scenario = st.sidebar.selectbox(
    "验收场景",
    ["Mock演示", "真实PDF现金跑道分析", "Predictor故障降级"],
    help="真实模式只启用PDF、关键词检索和现金跑道纵向链路。",
)
with st.form("analysis"):
    company = st.text_input("Company name", "Demo Biotech")
    code = st.text_input("Stock code", "9999")
    listing = st.date_input("Listing date", date.today())
    uploaded = (
        st.file_uploader("Prospectus PDF", type=["pdf"])
        if scenario == "真实PDF现金跑道分析"
        else None
    )
    submitted = st.form_submit_button("Run analysis")

if submitted:
    try:
        if scenario == "真实PDF现金跑道分析":
            if uploaded is None:
                raise ValueError("Please upload a prospectus PDF.")
            content = uploaded.getvalue()
            validate_pdf_upload(uploaded.name, content)
            settings = load_settings("configs/real_pdf.yaml")
            with temporary_pdf(content) as prospectus_path:
                request = build_analysis_request(
                    company_name=company,
                    stock_code=code,
                    listing_date=listing,
                    prospectus_path=prospectus_path,
                    use_mock=False,
                )
                result = IPOAnalysisService(settings=settings).analyze(request)
        else:
            settings = load_settings("configs/mock.yaml")
            if scenario == "Predictor故障降级":
                settings = replace(settings, predictor="fault")
            request = build_analysis_request(
                company_name=company,
                stock_code=code,
                listing_date=listing,
                prospectus_path="mock://prospectus",
                use_mock=True,
            )
            result = IPOAnalysisService(settings=settings).analyze(request)
    except ValueError as exc:
        st.error(str(exc))
    else:
        payload = result_payload(result)
        st.metric(
            "Deterministic five-day decline risk score",
            f"{result.prediction.risk_score:.0f}/100" if result.prediction else "N/A",
        )
        st.caption("该分数为确定性规则分，不是上市后下跌概率，不构成投资建议。")
        st.write("Status:", payload["status"])

        st.subheader("Component modes")
        st.json(payload["component_modes"])
        st.subheader("PDF parsing")
        st.json(payload["document"])
        st.subheader("Real slice status")
        st.json(payload["real_slice"])

        st.subheader("Verified risks")
        st.json(payload["verified_risks"])
        st.subheader("Pending and rejected risks")
        st.json(
            {
                "pending": payload["pending_risks"],
                "rejected": payload["rejected_risks"],
            }
        )
        st.subheader("Prediction result")
        st.json(payload["prediction"] or {"status": "unavailable"})
        st.subheader("Report sections")
        st.json(payload["report_sections"])
        st.subheader("Errors")
        st.json(payload["errors"])
        st.subheader("Execution logs")
        st.json(payload["agent_logs"])
