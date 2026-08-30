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

A replayed run has no PDF at all -- that is the point of the offline bundle -- so
it shows the screenshot the export already produced for that Evidence, with the
granularity the manifest recorded.  An Evidence item the export refused has no
image here either: another item's page would be a false claim about where this
one came from.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from ipo_risk.runtime.demo_replay import ReplayScreenshots
from ipo_risk.runtime.evidence_screenshots import (
    GRANULARITY_KEYWORD,
    GRANULARITY_SNIPPET,
    EvidenceCapture,
    EvidenceCaptureError,
    capture_evidence_page,
)

from competition_runtime_view import evidence_catalog
from competition_ui import (
    render_profile_grid,
    render_state_panel,
    risk_display_name,
    risk_level_label,
    section_header,
    status_badge,
)
from judge_copy import judge_status_label, risk_conclusion_zh, to_simplified_ui, verifier_note_zh


def _display(value: object) -> str:
    return "不可用" if value in (None, "", {}, []) else to_simplified_ui(value)


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
            "红框由 PyMuPDF 在本页搜索该条证据片段原文得到，是精确到行的真实 PDF 坐标。"
        )
    if region.granularity == GRANULARITY_KEYWORD:
        return (
            "该条证据片段未能整行命中，红框是检索实际匹配到的关键词在本页的真实坐标，"
            "覆盖范围小于完整片段。"
        )
    if region.rects:
        return (
            "该条证据未能在本页精确定位，红框是解析器记录的页级文本范围"
            f"（{region.granularity}），不是精确片段框。"
        )
    return "该条证据没有可用坐标，页面按原样展示，未绘制高亮框。"


def _replay_caption(record: dict[str, Any]) -> str:
    """Say what the exported image shows, in the manifest's own terms."""

    if not record.get("highlight_drawn"):
        return "该条证据没有可用坐标，导出的截图为原页，未绘制高亮框。"
    if record.get("granularity") == GRANULARITY_SNIPPET:
        return "红框由 PyMuPDF 在本页搜索该条证据片段原文得到，是精确到行的真实 PDF 坐标。"
    if record.get("granularity") == GRANULARITY_KEYWORD:
        return "红框是检索实际匹配到的关键词在本页的真实坐标，覆盖范围小于完整片段。"
    return (
        "红框是解析器记录的页级文本范围"
        f"（{record.get('granularity')}），不是精确片段框。"
    )


def _render_replay_page(
    item: dict[str, Any], page: object, replay: ReplayScreenshots, *, expert: bool = False
) -> None:
    """Show the exported screenshot for this Evidence, or say there is none."""

    evidence_id = str(item.get("evidence_id") or "")
    record = replay.record(evidence_id)
    image_path = replay.image_path(evidence_id)
    if record is None or image_path is None:
        st.warning(
            "本次回放的截图产物里没有这条证据的图片，因此不展示原页；"
            "不会用其它证据的页面顶替。"
        )
        return
    st.image(str(image_path), caption=f"招股书第 {record.get('page', page)} 页（导出截图）", width="stretch")
    if expert:
        st.caption(_replay_caption(record))
        st.caption(f"截图 SHA-256 · `{record.get('sha256') or '—'}`")
    elif record.get("highlight_drawn"):
        st.caption("已在招股书原页标出这条结论引用的位置。")
    else:
        st.caption("已显示招股书原页；这条证据没有可用的定位框。")


def render_evidence_viewer(
    payload: dict[str, Any],
    pdf_bytes: bytes | None,
    replay: ReplayScreenshots | None = None,
    *,
    expert: bool = False,
) -> None:
    """Draw the two-pane Evidence Viewer for the current analysis or replay."""

    catalog = evidence_catalog(payload)
    section_header(
        "原文证据核验",
        "在同一页面对照风险结论、招股书原页与引用位置；引用文字保持招股书原样。",
        "来源核验",
    )
    if not catalog:
        render_state_panel(
            "原文证据不可用",
            "unavailable",
            "本次运行没有任何附着在风险项上的原文证据，因此没有可展示的证据页。",
        )
        return

    labels = [f"{index + 1}. {risk_display_name(item.get('risk_code'))} · 第 {item.get('page') or '—'} 页" for index, item in enumerate(catalog)]
    chosen = st.selectbox("选择要核验的风险证据", range(len(catalog)), format_func=lambda index: labels[index])
    item = catalog[chosen]

    st.markdown(
        "<div style='display:flex;justify-content:space-between;align-items:center;gap:.75rem;"
        "flex-wrap:wrap;margin:.25rem 0 .7rem'>"
        f"<strong>{risk_display_name(item.get('risk_code'))}</strong>"
        f"{status_badge(item.get('verification_status'))}</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns((0.82, 1.38), gap="large")
    with left:
        section_header("风险与验证", "先理解风险，再对照右侧招股书原文。")
        profile_rows = [
            ("风险等级", risk_level_label(item.get("risk_level"))),
            ("验证状态", judge_status_label(item.get("verification_status"))),
            ("招股书页码", _display(item.get("page"))),
        ]
        if expert:
            profile_rows.extend(
                [
                    ("产出智能体", _display(item.get("agent_name"))),
                    ("证据编号", item["evidence_id"]),
                    ("检索相关度", _display(item.get("relevance_score"))),
                ]
            )
        render_profile_grid(profile_rows)
        st.markdown("**结论**")
        st.write(risk_conclusion_zh({
            "risk_code": item.get("risk_code"),
            "metadata": item.get("risk_metadata") or {},
            "calculation": item.get("calculation"),
            "evidence": [item],
        }))
        notes = item.get("verification_notes")
        if notes:
            st.caption(f"复核说明 · {verifier_note_zh(notes)}")

    with right:
        section_header("证据原文", "招股书原页、引用位置与被引用文本。")
        page = item.get("page")
        if replay is not None:
            _render_replay_page(item, page, replay, expert=expert)
        elif pdf_bytes is None:
            st.warning(
                "当前会话没有保留本次分析所用的 PDF 原文件，无法渲染原页。"
                "重新在本页上传并运行同一份招股书即可看到高亮页面。"
            )
        elif page is None:
            st.warning("该条证据没有页码，解析阶段未能定位到具体页，因此不渲染页面。")
        else:
            try:
                image, region, _, _ = capture_evidence_page(pdf_bytes, _capture(item))
            except EvidenceCaptureError as exc:
                st.error(f"该页无法渲染：{exc}")
            except Exception as exc:  # a render failure must not blank the workspace
                st.error(f"该页无法渲染：{type(exc).__name__}: {exc}")
            else:
                st.image(image, caption=f"招股书第 {page} 页", width="stretch")
                if expert:
                    st.caption(_localisation_caption(region))
                elif region.rects:
                    st.caption("已在招股书原页标出这条结论引用的位置。")
                else:
                    st.caption("已显示招股书原页；这条证据没有可用的定位框。")
        with st.expander("招股书原文证据", expanded=True):
            st.write(item.get("text") or "该条证据没有可展示的原文。")

    if expert:
        section_header("审计明细", "计算依据、结构化字段与来源定位保持完整可见。")
        calculation = item.get("calculation")
        with st.expander("确定性计算", expanded=calculation is not None):
            if calculation:
                st.json(calculation)
            else:
                st.write("该风险项没有关联确定性计算；其结论不依赖数值计算。")

        metadata = item.get("risk_metadata") or {}
        with st.expander("结构化字段与诊断", expanded=False):
            st.markdown(f"**章节** · {_display(item.get('section'))}")
            if metadata:
                st.json(metadata)
            else:
                st.write("该风险项没有结构化事实记录。")
