"""Evidence Viewer: the prospectus page beside the claim that cites it.

The left half renders the actual PDF page with the cited region outlined; the
right half shows the risk, the LLM structured facts, the deterministic
Calculation and the Verifier's ruling for that same Evidence.  Nothing here
edits Evidence: page numbers, geometry and identities come from the parser and
from PyMuPDF's own search of that page, and are displayed as they are or
reported as unavailable.

The box is drawn by the same localiser the screenshot export uses, so the page a
reviewer sees here is the page the submission ships.  Its caption always names
the granularity that was achieved: a located snippet line, a matched keyword, or
the parser's page-level union -- which is never presented as a snippet box.

Rendering needs the original PDF bytes.  When the run did not come from an upload
in this session the viewer says so and still shows the Evidence text, because a
missing page image must not hide the claim it supports.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from ipo_risk.runtime.evidence_screenshots import (
    GRANULARITY_KEYWORD,
    GRANULARITY_SNIPPET,
    EvidenceCapture,
    EvidenceCaptureError,
    capture_evidence_page,
)

from competition_runtime_view import evidence_catalog, evidence_label
from competition_ui import (
    render_profile_grid,
    render_state_panel,
    risk_level_label,
    section_header,
    status_badge,
)


def _display(value: object) -> str:
    return "不可用" if value in (None, "", {}, []) else str(value)


def _capture(item: dict[str, Any]) -> EvidenceCapture:
    """The catalog row as the localiser's input; nothing is added to it."""

    metadata = item.get("evidence_metadata") or {}
    return EvidenceCapture(
        evidence_id=str(item.get("evidence_id") or ""),
        page=item.get("page"),
        snippet=item.get("text") or "",
        matched_keywords=tuple(
            str(keyword)
            for keyword in (metadata.get("matched_keywords") or [])
            if str(keyword).strip()
        ),
        recorded_bbox=item.get("bbox"),
        recorded_bbox_granularity=metadata.get("bbox_granularity"),
    )


def _localisation_caption(region: Any) -> str:
    """Say which granularity the drawn box actually has, every time."""

    if region.granularity == GRANULARITY_SNIPPET:
        return (
            "红框由 PyMuPDF 在本页搜索该条 Evidence 片段原文得到，是精确到行的真实 PDF 坐标。"
        )
    if region.granularity == GRANULARITY_KEYWORD:
        return (
            "该条 Evidence 片段未能整行命中，红框是检索实际匹配到的关键词在本页的真实坐标，"
            "覆盖范围小于完整片段。"
        )
    if region.rects:
        return (
            "该条 Evidence 未能在本页精确定位，红框是解析器记录的页级文本范围"
            f"（{region.granularity}），不是精确片段框。"
        )
    return "该条 Evidence 没有可用坐标，页面按原样展示，未绘制高亮框。"


def render_evidence_viewer(payload: dict[str, Any], pdf_bytes: bytes | None) -> None:
    """Draw the two-pane Evidence Viewer for the current analysis."""

    catalog = evidence_catalog(payload)
    section_header(
        "Evidence Viewer",
        "招股书原页与 bbox 高亮和风险结论并排核验；页码、坐标与 Evidence 身份均来自解析器，界面不做修补。",
        "Source verification",
    )
    if not catalog:
        render_state_panel(
            "Evidence 不可用",
            "unavailable",
            "本次运行没有任何附着在风险项上的 Evidence，因此没有可展示的证据页。",
        )
        return

    labels = [evidence_label(item) for item in catalog]
    chosen = st.selectbox("风险 / Evidence 清单", range(len(catalog)), format_func=lambda index: labels[index])
    item = catalog[chosen]

    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;gap:.75rem;"
        "flex-wrap:wrap;margin:.25rem 0 .7rem'>"
        f"<strong>{item.get('risk_code') or '未命名风险'}</strong>"
        f"{status_badge(item.get('verification_status'))}</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns((0.82, 1.38), gap="large")
    with left:
        section_header("风险与验证", "结论、身份与 Verifier 判定。")
        render_profile_grid(
            (
                ("风险等级", risk_level_label(item.get("risk_level"))),
                ("产出 Agent", _display(item.get("agent_name"))),
                ("验证状态", _display(item.get("verification_status"))),
                ("Evidence ID", item["evidence_id"]),
                ("PDF 页码", _display(item.get("page"))),
                ("检索相关度", _display(item.get("relevance_score"))),
            )
        )
        st.markdown("**结论**")
        st.write(item.get("risk_conclusion") or "该风险项没有结论文本。")
        notes = item.get("verification_notes")
        if notes:
            st.caption(f"Verifier 复核说明 · {notes}")

    with right:
        section_header("证据原文", "PDF 原页、定位框与被引用文本。")
        page = item.get("page")
        if pdf_bytes is None:
            st.warning(
                "当前会话没有保留本次分析所用的 PDF 原文件，无法渲染原页。"
                "重新在本页上传并运行同一份招股书即可看到高亮页面。"
            )
        elif page is None:
            st.warning("该条 Evidence 没有页码，解析阶段未能定位到具体页，因此不渲染页面。")
        else:
            try:
                image, region, _, _ = capture_evidence_page(pdf_bytes, _capture(item))
            except EvidenceCaptureError as exc:
                st.error(f"该页无法渲染：{exc}")
            except Exception as exc:  # a render failure must not blank the workspace
                st.error(f"该页无法渲染：{type(exc).__name__}: {exc}")
            else:
                st.image(image, caption=f"招股书第 {page} 页", width="stretch")
                st.caption(_localisation_caption(region))
        with st.expander("Evidence 原文", expanded=True):
            st.write(item.get("text") or "该条 Evidence 没有可展示的原文。")

    section_header("审计明细", "Calculation、metadata 与来源定位保持完整可见。")
    calculation = item.get("calculation")
    with st.expander("确定性 Calculation", expanded=calculation is not None):
        if calculation:
            st.json(calculation)
        else:
            st.write("该风险项没有关联确定性计算；其结论不依赖数值计算。")

    metadata = item.get("risk_metadata") or {}
    with st.expander("Metadata / Diagnostics", expanded=False):
        st.markdown(f"**章节** · {_display(item.get('section'))}")
        if metadata:
            st.json(metadata)
        else:
            st.write("该风险项没有结构化事实记录。")
