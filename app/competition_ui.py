"""Competition-facing Streamlit presentation helpers.

The UI stays presentation-only: every value rendered here is either static product
copy or derived from an already-produced result payload. No risk, Evidence, market
observation, model score, or completion claim is created by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Iterable

import streamlit as st


@dataclass(frozen=True)
class FutureModule:
    code: str
    title: str
    purpose: str


FUTURE_MODULES = (
    FutureModule(
        "CH-1",
        "Multi-horizon validation",
        "Add governed 1D / 20D / 60D outcomes alongside the frozen 5D baseline.",
    ),
    FutureModule(
        "CH-2",
        "Document benchmark",
        "Measure risk-category Precision / Recall / F1 / Evidence Recall before targeted Agent or Retriever changes.",
    ),
    FutureModule(
        "CH-3",
        "Market sentiment",
        "Add PIT IPO heat, recent-IPO performance, liquidity and comparable-market context.",
    ),
    FutureModule(
        "CH-4",
        "Conflict arbitration",
        "Detect cross-Agent conflicts, re-check Evidence and preserve unresolved uncertainty.",
    ),
    FutureModule(
        "CH-5",
        "Evidence review",
        "Add page/bbox evidence highlighting, screenshots and human-review audit trail.",
    ),
    FutureModule(
        "CH-6",
        "Competition evaluation",
        "Run the final unified evaluation, demo matrix and submission freeze.",
    ),
)


_CHANNEL_COPY = {
    "document": "Prospectus risk intelligence",
    "market": "Governed pre-listing context",
    "model": "Frozen per-case model handoff",
    "rule": "Deterministic prioritization",
}

_DOMAIN_LABELS = {
    "financial": "Financial",
    "legal": "Legal & Compliance",
    "business": "Business",
}


def apply_competition_theme() -> None:
    """Apply an app-like, neutral workspace theme without changing behavior."""

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1480px;
            padding-top: 1rem;
            padding-bottom: 3.5rem;
        }
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 92% 0%, rgba(37,99,235,.075), transparent 22rem),
                radial-gradient(circle at 12% 18%, rgba(15,118,110,.055), transparent 26rem);
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128,128,128,.16);
            background: rgba(128,128,128,.025);
        }
        [data-testid="stSidebar"] .block-container {padding-top: 1rem;}
        div[data-testid="stForm"] {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 18px;
            padding: 1rem 1.05rem .85rem 1.05rem;
            background: rgba(128,128,128,.035);
            box-shadow: 0 10px 34px rgba(15,23,42,.035);
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 16px;
            padding: .85rem 1rem;
            background: rgba(128,128,128,.035);
            min-height: 104px;
        }
        [data-testid="stMetricLabel"] {font-weight: 650; letter-spacing: .01em;}
        [data-testid="stMetricValue"] {font-weight: 760;}
        div[data-testid="stExpander"] {
            border: 1px solid rgba(128,128,128,.16);
            border-radius: 14px;
            overflow: hidden;
            background: rgba(128,128,128,.018);
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(128,128,128,.14);
            border-radius: 14px;
            overflow: hidden;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .35rem;
            overflow-x: auto;
            padding-bottom: .15rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: .55rem .9rem;
            font-weight: 620;
        }
        .stTabs [aria-selected="true"] {
            background: rgba(37,99,235,.09);
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 10px;
            font-weight: 650;
        }
        .ipo-hero {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: 22px;
            padding: 1.35rem 1.5rem 1.25rem 1.5rem;
            margin-bottom: .9rem;
            background:
                linear-gradient(135deg, rgba(37,99,235,.105), rgba(15,118,110,.055) 58%, rgba(128,128,128,.02));
            box-shadow: 0 18px 50px rgba(15,23,42,.045);
        }
        .ipo-hero-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1.5rem;
            flex-wrap: wrap;
        }
        .ipo-kicker {
            font-size: .73rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
            opacity: .68;
        }
        .ipo-title {
            font-size: clamp(1.8rem, 3vw, 2.65rem);
            font-weight: 790;
            line-height: 1.08;
            letter-spacing: -.025em;
            margin: .28rem 0 .48rem 0;
        }
        .ipo-subtitle {font-size: .98rem; opacity: .76; max-width: 900px; line-height: 1.62;}
        .ipo-badge-row {display:flex; gap:.38rem; flex-wrap:wrap; margin-top:.85rem;}
        .ipo-badge, .status-chip, .risk-chip {
            display: inline-flex;
            align-items: center;
            gap: .28rem;
            border-radius: 999px;
            border: 1px solid rgba(128,128,128,.2);
            padding: .24rem .56rem;
            font-size: .75rem;
            font-weight: 680;
            line-height: 1.2;
            background: rgba(128,128,128,.045);
        }
        .status-good {border-color: rgba(5,150,105,.28); background: rgba(5,150,105,.08);}
        .status-warn {border-color: rgba(217,119,6,.3); background: rgba(217,119,6,.09);}
        .status-bad {border-color: rgba(220,38,38,.28); background: rgba(220,38,38,.08);}
        .status-muted {opacity: .74;}
        .case-shell {
            display:flex;
            align-items:flex-end;
            justify-content:space-between;
            gap:1rem;
            flex-wrap:wrap;
            margin: 1.2rem 0 .8rem 0;
        }
        .case-name {font-size:1.6rem; font-weight:770; letter-spacing:-.015em; line-height:1.15;}
        .case-meta {font-size:.86rem; opacity:.7; margin-top:.28rem;}
        .section-eyebrow {
            font-size:.72rem;
            font-weight:800;
            letter-spacing:.1em;
            text-transform:uppercase;
            opacity:.62;
            margin:.15rem 0 .35rem 0;
        }
        .channel-grid {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:.7rem;
            margin:.55rem 0 .9rem 0;
        }
        .channel-card {
            border:1px solid rgba(128,128,128,.17);
            border-radius:15px;
            padding:.8rem .9rem;
            background:rgba(128,128,128,.03);
            min-height:92px;
        }
        .channel-top {display:flex; align-items:center; justify-content:space-between; gap:.5rem;}
        .channel-name {font-size:.84rem; font-weight:760;}
        .channel-copy {font-size:.76rem; opacity:.64; margin-top:.42rem; line-height:1.38;}
        .pipeline-grid {
            display:grid;
            grid-template-columns:repeat(7,minmax(0,1fr));
            gap:.48rem;
            margin:.55rem 0 1.05rem 0;
        }
        .pipeline-card {
            border:1px solid rgba(128,128,128,.15);
            border-radius:12px;
            padding:.62rem .68rem;
            background:rgba(128,128,128,.025);
            min-height:78px;
        }
        .pipeline-index {font-size:.68rem; opacity:.55; font-weight:760; letter-spacing:.06em;}
        .pipeline-title {font-size:.76rem; font-weight:720; line-height:1.28; margin:.2rem 0 .35rem 0;}
        .pipeline-status {font-size:.69rem; opacity:.76;}
        .empty-flow {
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:.7rem;
            margin:1rem 0 .4rem 0;
        }
        .empty-step {
            border:1px solid rgba(128,128,128,.16);
            border-radius:15px;
            padding:.9rem;
            background:rgba(128,128,128,.025);
        }
        .empty-step-no {font-size:.7rem; opacity:.55; font-weight:800;}
        .empty-step-title {font-size:.91rem; font-weight:750; margin:.22rem 0;}
        .empty-step-copy {font-size:.77rem; opacity:.68; line-height:1.42;}
        .roadmap-grid {
            display:grid;
            grid-template-columns:repeat(3,minmax(0,1fr));
            gap:.72rem;
            margin:.7rem 0 1rem 0;
        }
        .roadmap-card {
            border:1px solid rgba(128,128,128,.16);
            border-radius:15px;
            padding:.9rem;
            background:rgba(128,128,128,.026);
            min-height:142px;
        }
        .roadmap-code {font-size:.72rem; font-weight:800; letter-spacing:.08em; opacity:.58;}
        .roadmap-title {font-size:.95rem; font-weight:760; margin:.28rem 0 .38rem 0;}
        .roadmap-copy {font-size:.78rem; opacity:.67; line-height:1.46;}
        .roadmap-state {font-size:.68rem; font-weight:760; margin-top:.65rem; opacity:.58;}
        @media (max-width: 1050px) {
            .channel-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
            .pipeline-grid {grid-template-columns:repeat(4,minmax(0,1fr));}
            .roadmap-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
        }
        @media (max-width: 720px) {
            .channel-grid, .pipeline-grid, .empty-flow, .roadmap-grid {grid-template-columns:1fr;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_product_header() -> None:
    st.markdown(
        """
        <div class="ipo-hero">
          <div class="ipo-hero-row">
            <div>
              <div class="ipo-kicker">HK IPO Risk Intelligence</div>
              <div class="ipo-title">Evidence-first IPO Risk Workspace</div>
              <div class="ipo-subtitle">
                从招股书风险、Evidence 与确定性 Calculation，到上市前 Market-X、模型信号和 Final Supervisor，
                用一个可审计工作台完成港股 IPO 风险分析。缺失通道按 fail-closed 原则明确展示，不补造结果。
              </div>
              <div class="ipo-badge-row">
                <span class="ipo-badge">Governed v0.4</span>
                <span class="ipo-badge">Evidence-first</span>
                <span class="ipo-badge">Audit-first</span>
                <span class="ipo-badge">Fail-closed</span>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state() -> None:
    """Explain the product flow before a case is run, without fake output."""

    st.markdown("<div class='section-eyebrow'>HOW THE WORKSPACE WORKS</div>", unsafe_allow_html=True)
    steps = (
        ("01", "Prospectus", "Upload a real prospectus and bind the IPO identity."),
        ("02", "Risk Agents", "Financial, Legal and Business channels extract evidence-backed risks."),
        ("03", "Context & Signals", "Governed Market-X, deterministic rule and frozen model channels are attached when available."),
        ("04", "Final Supervisor", "Cross-channel synthesis produces an auditable final report with explicit uncertainty."),
    )
    cards = []
    for number, title, copy in steps:
        cards.append(
            "<div class='empty-step'>"
            f"<div class='empty-step-no'>{escape(number)}</div>"
            f"<div class='empty-step-title'>{escape(title)}</div>"
            f"<div class='empty-step-copy'>{escape(copy)}</div>"
            "</div>"
        )
    st.markdown("<div class='empty-flow'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption("Run a case above to enter the analysis workspace. No demo metric is rendered before a real result exists.")


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


def risk_inventory_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    """Return a compact risk inventory from already-renderable domain payloads."""

    rows: list[dict[str, object]] = []
    for domain in ("financial", "legal", "business"):
        domain_payload = (payload.get("domains") or {}).get(domain) or {}
        for risk in domain_payload.get("risks") or []:
            rows.append(
                {
                    "Domain": _DOMAIN_LABELS[domain],
                    "Risk": risk.get("risk_code", "Unavailable"),
                    "Level": risk.get("level", "Unavailable"),
                    "Rule score": risk.get("score", "Unavailable"),
                    "Verification": risk.get("verification_status", "Unavailable"),
                    "Evidence": len(risk.get("evidence") or []),
                }
            )
    return rows


def domain_summary_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for domain in ("financial", "legal", "business"):
        item = (payload.get("domains") or {}).get(domain) or {}
        counts = item.get("status_counts") or {}
        rows.append(
            {
                "Domain": _DOMAIN_LABELS[domain],
                "Risks": item.get("risk_count", 0),
                "Verified": counts.get("verified", 0),
                "Needs review": counts.get("needs_review", 0),
                "Status": item.get("status", "unavailable"),
            }
        )
    return rows


def _status_tone(status: object) -> str:
    normalized = str(status or "unavailable").lower()
    if normalized in {"available", "completed", "verified"}:
        return "status-good"
    if normalized in {"partial", "needs_review", "pending"}:
        return "status-warn"
    if normalized in {"failed", "rejected", "error"}:
        return "status-bad"
    return "status-muted"


def render_case_header(payload: dict[str, Any]) -> None:
    profile = payload.get("profile") or {}
    company = escape(str(profile.get("company_name") or "Unavailable"))
    stock_code = escape(str(profile.get("stock_code") or "Unavailable"))
    listing_date = escape(str(profile.get("listing_date") or "Unavailable"))
    industry = escape(str(profile.get("industry") or "Unavailable"))
    result_status = escape(str(payload.get("status") or "unavailable").upper())
    tone = _status_tone(payload.get("status"))
    st.markdown(
        "<div class='case-shell'>"
        "<div>"
        f"<div class='case-name'>{company} <span style='opacity:.5;font-weight:620'>· {stock_code}</span></div>"
        f"<div class='case-meta'>Listing {listing_date} · {industry}</div>"
        "</div>"
        f"<span class='status-chip {tone}'>{result_status}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_executive_snapshot(payload: dict[str, Any]) -> None:
    """Put the decision story before engineering detail for a 30-second demo."""

    prediction = payload.get("prediction") or {}
    counts = payload.get("risk_status_counts") or {}
    states = channel_state_map(payload)
    available_market, total_market = available_market_observation_count(payload)

    st.markdown("<div class='section-eyebrow'>EXECUTIVE SNAPSHOT</div>", unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric(
        "Rule risk signal",
        prediction.get("risk_score", "Unavailable"),
        prediction.get("risk_level", ""),
    )
    cols[1].metric("Verified risks", counts.get("verified", 0))
    cols[2].metric("Evidence refs", evidence_reference_count(payload))
    cols[3].metric(
        "Market context",
        f"{available_market}/{total_market}" if total_market else states.get("market", "Unavailable"),
    )
    cols[4].metric("Model channel", states.get("model", "Unavailable").upper())

    final = payload.get("final_supervision") or {}
    if final:
        with st.container(border=True):
            st.markdown("**Final Supervisor synthesis**")
            st.write(final.get("summary") or "No synthesis summary was produced.")
            uncertainty = final.get("uncertainty_statement")
            if uncertainty:
                st.caption(uncertainty)


def render_channel_grid(payload: dict[str, Any]) -> None:
    states = channel_state_map(payload)
    cards: list[str] = []
    for channel in ("document", "market", "model", "rule"):
        status = states.get(channel, "unavailable")
        tone = _status_tone(status)
        cards.append(
            "<div class='channel-card'>"
            "<div class='channel-top'>"
            f"<div class='channel-name'>{escape(channel.title())}</div>"
            f"<span class='status-chip {tone}'>{escape(str(status).upper())}</span>"
            "</div>"
            f"<div class='channel-copy'>{escape(_CHANNEL_COPY[channel])}</div>"
            "</div>"
        )
    st.markdown("<div class='channel-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_pipeline_strip(stages: Iterable[object]) -> None:
    """Render the seven governed stages as a compact workspace progress strip."""

    cards: list[str] = []
    for stage in stages:
        status_obj = getattr(stage, "status", "unavailable")
        status = getattr(status_obj, "value", status_obj)
        tone = _status_tone(status)
        title = str(getattr(stage, "title", "Stage"))
        summary = str(getattr(stage, "summary", ""))
        ordinal = str(getattr(stage, "ordinal", ""))
        cards.append(
            f"<div class='pipeline-card' title='{escape(summary, quote=True)}'>"
            f"<div class='pipeline-index'>STAGE {escape(ordinal)}</div>"
            f"<div class='pipeline-title'>{escape(title)}</div>"
            f"<span class='status-chip {tone}'>{escape(str(status).replace('_', ' ').upper())}</span>"
            "</div>"
        )
    st.markdown("<div class='pipeline-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


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
    st.markdown("### Competition hardening roadmap")
    st.caption(
        "These are presentation slots for the post-v0.4.3 competition track. They render no metric or factual output until governed implementations land."
    )
    cards: list[str] = []
    for item in FUTURE_MODULES:
        cards.append(
            "<div class='roadmap-card'>"
            f"<div class='roadmap-code'>{escape(item.code)}</div>"
            f"<div class='roadmap-title'>{escape(item.title)}</div>"
            f"<div class='roadmap-copy'>{escape(item.purpose)}</div>"
            "<div class='roadmap-state'>PLANNED AFTER v0.4.3</div>"
            "</div>"
        )
    st.markdown("<div class='roadmap-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
