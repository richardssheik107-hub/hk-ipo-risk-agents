"""Streamlit presentation layer; it only calls IPOAnalysisService."""
from dataclasses import replace
from datetime import date

import streamlit as st

from ipo_risk.core.config import load_settings
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService


st.set_page_config(page_title="HK IPO Risk Agents", layout="wide")
st.title("HK IPO Risk Agents")
scenario = st.sidebar.selectbox(
    "验收场景",
    ["正常 Mock 分析", "Predictor 故障降级"],
    help="故障场景仅替换配置中的 Predictor，以验证 partial 结果可被安全呈现。",
)
with st.form("analysis"):
    company = st.text_input("Company name", "Demo Biotech")
    code = st.text_input("Stock code", "9999")
    listing = st.date_input("Listing date", date.today())
    submitted = st.form_submit_button("Run mock analysis")

if submitted:
    settings = load_settings()
    if scenario == "Predictor 故障降级":
        settings = replace(settings, predictor="fault")
    result = IPOAnalysisService(settings=settings).analyze(
        IPOAnalysisRequest(company_name=company, stock_code=code, listing_date=listing)
    )
    st.metric("Five-day decline risk", f"{result.prediction.risk_score:.0f}/100" if result.prediction else "N/A")
    st.write("Status:", result.status)
    if result.errors:
        st.error("分析以降级模式完成；失败详情如下。")
        st.json([error.model_dump(mode="json") for error in result.errors])

    st.subheader("Verified risks")
    for risk in result.verified_risks:
        with st.expander(f"{risk.risk_code}: {risk.risk_type}"):
            st.write(risk.conclusion)
            st.markdown("**Evidence**")
            st.json([item.model_dump(mode="json") for item in risk.evidence])
            st.markdown("**Calculation**")
            st.json(risk.calculation.model_dump(mode="json") if risk.calculation else {"status": "not_required_or_unavailable"})

    st.subheader("Pending risks")
    for risk in result.pending_risks:
        with st.expander(f"{risk.risk_code}: {risk.risk_type}"):
            st.write(risk.conclusion)
            st.markdown("**Evidence**")
            st.json([item.model_dump(mode="json") for item in risk.evidence])
            st.markdown("**Calculation**")
            st.json(risk.calculation.model_dump(mode="json") if risk.calculation else {"status": "pending_or_not_required"})

    st.subheader("Prediction result")
    st.json(result.prediction.model_dump(mode="json") if result.prediction else {"status": "unavailable"})
    st.subheader("Report sections")
    st.json([section.model_dump(mode="json") for section in result.report_sections])
    st.subheader("Execution logs")
    st.json([log.model_dump(mode="json") for log in result.agent_logs])
