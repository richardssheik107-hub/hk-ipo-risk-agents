"""Streamlit presentation layer; it only calls IPOAnalysisService."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import json

import streamlit as st

from presenters import (
    build_analysis_request,
    markdown_report,
    result_payload,
    temporary_pdf,
    validate_pdf_upload,
)
from ipo_risk.core.config import load_settings
from ipo_risk.services.analysis_service import IPOAnalysisService


SCENARIOS = {
    "Mock 演示": ("configs/mock.yaml", False),
    "v0.2 现金跑道": ("configs/real_pdf.yaml", True),
    "v0.3 离线增强": ("configs/v03_offline.yaml", True),
    "v0.3 AI 增强": ("configs/v03_ai.yaml", True),
    "Predictor 故障降级": ("configs/mock.yaml", False),
}

st.set_page_config(page_title="HK IPO Risk Agents", layout="wide")
st.title("港股 IPO 招股书风险分析")
scenario = st.sidebar.selectbox("运行场景", list(SCENARIOS))
config_path, needs_pdf = SCENARIOS[scenario]
st.sidebar.caption(
    "v0.3 离线模式不访问外部模型；AI 增强模式仅从环境变量读取凭证。"
)

with st.form("analysis"):
    company = st.text_input("公司名称", "Demo Biotech")
    code = st.text_input("股票代码", "9999.HK")
    listing = st.date_input("上市日期", date.today())
    uploaded = st.file_uploader("招股书 PDF", type=["pdf"]) if needs_pdf else None
    submitted = st.form_submit_button("开始分析")

if submitted:
    try:
        settings = load_settings(config_path)
        if scenario == "Predictor 故障降级":
            settings = replace(settings, predictor="fault")
        if needs_pdf:
            if uploaded is None:
                raise ValueError("请上传招股书 PDF。")
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
        score = result.prediction.risk_score if result.prediction else None
        first, second, third = st.columns(3)
        first.metric("状态", payload["status"])
        second.metric("工作流", payload["workflow_version"])
        third.metric("五日规则风险分", f"{score:.0f}/100" if score is not None else "N/A")
        st.caption("规则分数不是下跌概率，不构成投资、法律或上市建议。")

        overview, risks_tab, audit = st.tabs(["报告", "风险与证据", "运行审计"])
        with overview:
            for section in result.report_sections:
                st.subheader(section.title)
                st.write(section.summary)
            st.download_button(
                "下载 Markdown 报告",
                markdown_report(result),
                file_name=f"{result.stock_code or 'ipo'}-risk-report.md",
                mime="text/markdown",
            )
            st.download_button(
                "下载结构化 JSON",
                json.dumps(payload, ensure_ascii=False, indent=2),
                file_name=f"{result.stock_code or 'ipo'}-risk-result.json",
                mime="application/json",
            )
        with risks_tab:
            financial_tab, legal_tab, business_tab = st.tabs(["Financial", "Legal", "Business"])
            domain_tabs = {
                "financial": financial_tab,
                "legal": legal_tab,
                "business": business_tab,
            }
            all_risks = [
                *result.verified_risks,
                *result.pending_risks,
                *result.rejected_risks,
            ]
            for domain, tab in domain_tabs.items():
                with tab:
                    domain_risks = [item for item in all_risks if item.category.value == domain]
                    diagnostic = payload["component_diagnostics"].get(domain, {})
                    st.caption(f"Agent status: {'completed' if domain_risks else 'no risk emitted'}")
                    if diagnostic:
                        st.json(diagnostic)
                    for risk in domain_risks:
                        st.markdown(
                            f"**{risk.risk_code}** · {risk.level.value} · "
                            f"rule score {risk.score:.0f} · {risk.verification_status.value}"
                        )
                        st.write(risk.conclusion)
                        if risk.calculation is not None:
                            st.json(
                                {
                                    "formula": risk.calculation.formula,
                                    "inputs": risk.calculation.inputs,
                                    "unit": risk.calculation.unit,
                                    "result": risk.calculation.result,
                                    "evidence_ids": risk.calculation.evidence_ids,
                                }
                            )
                        for evidence in risk.evidence:
                            with st.expander(f"PDF page {evidence.page} · {evidence.evidence_id}"):
                                st.write(evidence.text)
                        if risk.metadata:
                            with st.expander("Structured facts / metadata"):
                                st.json(risk.metadata)
            st.subheader("Supervisor")
            st.json(payload["supervision"] or {"status": "not_available"})
        with audit:
            st.subheader("组件模式与治理状态")
            st.json(
                {
                    "configuration": payload["configuration"],
                    "component_modes": payload["component_modes"],
                    "governance": payload["governance"],
                }
            )
            st.subheader("解析与组件诊断")
            st.json(
                {
                    "document": payload["document"],
                    "diagnostics": payload["component_diagnostics"],
                    "errors": payload["errors"],
                }
            )
            st.subheader("Agent 日志")
            st.json(payload["agent_logs"])
