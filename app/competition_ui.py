"""Competition-facing Streamlit presentation helpers.

This module is deliberately presentation-only: it derives labels and counts from
already-produced result payloads and never creates market/model/risk facts.
Future CH-* modules are shown as planned placeholders until governed runtime data
exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st


@dataclass(frozen=True)
class FutureModule:
    code: str
    title: str
    purpose: str


FUTURE_MODULES = (
    FutureModule("CH-1", "Multi-horizon validation", "Add governed 1D / 20D / 60D outcomes alongside the frozen 5D baseline."),
    FutureModule("CH-2", "Document benchmark", "Measure risk-category Precision / Recall / F1 / Evidence Recall before targeted Agent or Retriever changes."),
    FutureModule("CH-3", "Market sentiment", "Add PIT IPO heat, recent-IPO performance, liquidity and comparable-market context."),
    FutureModule("CH-4", "Conflict arbitration", "Detect cross-Agent conflicts, re-check Evidence and preserve unresolved uncertainty."),
    FutureModule("CH-5", "Evidence review", "Add page/bbox evidence highlighting, screenshots and human-review audit trail."),
    FutureModule("CH-6", "Competition evaluation", "Run the final unified evaluation, demo matrix and submission freeze."),
)


def apply_competition_theme() -> None:
    """Apply a conservative product theme without changing Streamlit behavior."""
    st.markdown(
        """
        <style>
        .block-container {max-width: 1500px; padding-top: 1.4rem; padding-bottom: 3rem;}
        [data-testid="stSidebar"] {border-right: 1px solid rgba(128,128,128,.18);}
        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.20);
            border-radius: 14px;
            padding: .9rem 1rem;
            background: rgba(128,128,128,.045);
        }
        [data-testid="stMetricLabel"] {font-weight: 650;}
        div[data-testid="stExpander"] {border-radius: 14px;}
        .stTabs [data-baseweb="tab-list"] {gap: .25rem; overflow-x: auto;}
        .stTabs [data-baseweb="tab"] {border-radius: 10px 10px 0 0; padding-left: .8rem; padding-right: .8rem;}
        .ipo-hero {
            border: 1px solid rgba(128,128,128,.20);
            border-radius: 22px;
            padding: 1.35rem 1.45rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, rgba(61,90,254,.09), rgba(0,191,165,.055));
        }
        .ipo-kicker {font-size: .78rem; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; opacity: .72;}
        .ipo-title {font-size: 2rem; font-weight: 780; line-height: 1.15; margin: .25rem 0 .4rem 0;}
        .ipo-subtitle {font-size: 1rem; opacity: .78; max-width: 900px;}
        .roadmap-badge {
            display: inline-block; margin: .15rem .28rem .15rem 0; padding: .26rem .58rem;
            border-radius: 999px; border: 1px solid rgba(128,128,128,.25); font-size: .78rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_product_header() -> None:
    st.markdown(
        """
        <div class="ipo-hero">
          <div class="ipo-kicker">HK IPO Risk Intelligence · v0.4 baseline</div>
          <div class="ipo-title">Evidence-driven IPO Risk Command Center</div>
          <div class="ipo-subtitle">
            招股书风险识别、可追溯 Evidence、上市前 Market-X、模型信号与 Final Supervisor 的统一工作台。
            当前页面只展示真实可用通道；缺失运行资产会明确标记为 unavailable / disabled。
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def channel_state_map(payload: dict[str, Any]) -> dict[str, str]:
    final = payload.get("final_supervision") or {}
    states = final.get("channel_states") or []
    return {str(item.get("channel")): str(item.get("status", "unavailable")) for item in states}


def evidence_reference_count(payload: dict[str, Any]) -> int:
    count = 0
    for risk in payload.get("verified_risks") or []:
        count += len(risk.get("evidence") or [])
    return count


def available_market_observation_count(payload: dict[str, Any]) -> tuple[int, int]:
    market = payload.get("market_context") or {}
    observations = market.get("observations") or []
    available = sum(1 for item in observations if item.get("availability") == "available")
    return available, len(observations)


def render_executive_snapshot(payload: dict[str, Any]) -> None:
    """Put the decision story before engineering detail for a 30-second demo."""
    prediction = payload.get("prediction") or {}
    states = channel_state_map(payload)
    available_market, total_market = available_market_observation_count(payload)

    st.markdown("## Executive risk overview")
    cols = st.columns(4)
    cols[0].metric("Rule risk signal", prediction.get("risk_score", "Unavailable"), prediction.get("risk_level", ""))
    cols[1].metric("Evidence references", evidence_reference_count(payload))
    cols[2].metric("Market context", f"{available_market}/{total_market}" if total_market else states.get("market", "Unavailable"))
    cols[3].metric("Model channel", states.get("model", "Unavailable").upper())

    final = payload.get("final_supervision") or {}
    if final:
        st.markdown("### Final Supervisor")
        st.write(final.get("summary") or "No synthesis summary was produced.")
        channel_cols = st.columns(4)
        for column, name in zip(channel_cols, ("document", "market", "model", "rule"), strict=True):
            column.metric(name.title(), states.get(name, "unavailable").upper())
        uncertainty = final.get("uncertainty_statement")
        if uncertainty:
            st.info(uncertainty)


def roadmap_rows() -> list[dict[str, str]]:
    return [
        {
            "Stage": item.code,
            "Module": item.title,
            "Status": "PLANNED AFTER v0.4.3",
            "Purpose": item.purpose,
        }
        for item in FUTURE_MODULES
    ]


def render_competition_roadmap() -> None:
    st.subheader("Competition hardening roadmap")
    st.caption(
        "These modules are pre-wired as presentation slots only. They intentionally show no metrics or factual outputs until their governed implementations land."
    )
    st.dataframe(roadmap_rows(), hide_index=True, use_container_width=True)
    st.markdown(
        "<span class='roadmap-badge'>CH-1 Multi-horizon</span>"
        "<span class='roadmap-badge'>CH-2 Document benchmark</span>"
        "<span class='roadmap-badge'>CH-3 Market sentiment</span>"
        "<span class='roadmap-badge'>CH-4 Conflict arbitration</span>"
        "<span class='roadmap-badge'>CH-5 Evidence review</span>"
        "<span class='roadmap-badge'>CH-6 Final evaluation</span>",
        unsafe_allow_html=True,
    )
