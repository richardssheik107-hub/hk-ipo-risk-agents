"""Evidence Viewer: the prospectus page beside the claim that cites it.

The left half renders the actual PDF page with the Evidence bounding box drawn
on it; the right half shows the risk, the LLM structured facts, the deterministic
Calculation and the Verifier's ruling for that same Evidence.  Nothing here
edits Evidence: page numbers, bounding boxes and identities come from the parser
and are displayed as they are, or reported as unavailable.

Rendering needs the original PDF bytes.  When the run did not come from an upload
in this session the viewer says so and still shows the Evidence text, because a
missing page image must not hide the claim it supports.
"""

from __future__ import annotations

from typing import Any, Sequence

import streamlit as st

from competition_runtime_view import evidence_catalog, evidence_label
from competition_ui import risk_level_label

PAGE_RENDER_DPI = 130
_HIGHLIGHT = (0.85, 0.16, 0.16)


class PageRenderError(RuntimeError):
    """The requested prospectus page could not be rendered."""


def render_page_png(
    pdf_bytes: bytes,
    page_number: int,
    bbox: Sequence[float] | None = None,
    *,
    dpi: int = PAGE_RENDER_DPI,
) -> bytes:
    """Render one 1-indexed PDF page to PNG, outlining ``bbox`` when supplied."""

    import pymupdf

    if not pdf_bytes:
        raise PageRenderError("no prospectus bytes are available for this run")
    if page_number < 1:
        raise PageRenderError(f"page number {page_number} is not a 1-indexed page")
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if page_number > document.page_count:
                raise PageRenderError(
                    f"page {page_number} is beyond the document's {document.page_count} page(s)"
                )
            page = document.load_page(page_number - 1)
            if bbox is not None and len(tuple(bbox)) == 4:
                rectangle = pymupdf.Rect(*bbox)
                if not rectangle.is_empty:
                    annotation = page.add_rect_annot(rectangle)
                    annotation.set_colors(stroke=_HIGHLIGHT)
                    annotation.set_border(width=1.6)
                    annotation.update(opacity=0.9)
            return page.get_pixmap(dpi=dpi).tobytes("png")
    except PageRenderError:
        raise
    except Exception as exc:  # a rendering failure must not blank the workspace
        raise PageRenderError(f"{type(exc).__name__}: {exc}") from exc


def _display(value: object) -> str:
    return "不可用" if value in (None, "", {}, []) else str(value)


def render_evidence_viewer(payload: dict[str, Any], pdf_bytes: bytes | None) -> None:
    """Draw the two-pane Evidence Viewer for the current analysis."""

    catalog = evidence_catalog(payload)
    st.markdown("### Evidence Viewer")
    st.caption(
        "左侧为招股书原页与 bbox 高亮，右侧为该 Evidence 支撑的风险结论、结构化事实、"
        "确定性 Calculation 与 Verifier 判定。页码与 bbox 来自解析器，界面不做任何修补。"
    )
    if not catalog:
        st.info("本次运行没有任何附着在风险项上的 Evidence，因此没有可展示的证据页。")
        return

    labels = [evidence_label(item) for item in catalog]
    chosen = st.selectbox("选择 Evidence", range(len(catalog)), format_func=lambda index: labels[index])
    item = catalog[chosen]

    left, right = st.columns((1.15, 1))
    with left:
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
                image = render_page_png(pdf_bytes, int(page), item.get("bbox"))
            except PageRenderError as exc:
                st.error(f"该页无法渲染：{exc}")
            else:
                st.image(image, caption=f"招股书第 {page} 页", use_container_width=True)
                if item.get("bbox") is None:
                    st.caption("该条 Evidence 没有 bbox，页面按原样展示，未绘制高亮框。")
        with st.expander("Evidence 原文", expanded=True):
            st.write(item.get("text") or "该条 Evidence 没有可展示的原文。")

    with right:
        st.markdown(f"#### {item.get('risk_code') or '未命名风险'}")
        st.markdown(
            f"- 风险等级：**{risk_level_label(item.get('risk_level'))}**\n"
            f"- 产出 Agent：`{_display(item.get('agent_name'))}`\n"
            f"- Verifier 判定：`{_display(item.get('verification_status'))}`\n"
            f"- Evidence ID：`{item['evidence_id']}`\n"
            f"- 章节：{_display(item.get('section'))}\n"
            f"- 检索相关度：{_display(item.get('relevance_score'))}"
        )
        st.markdown("**风险结论**")
        st.write(item.get("risk_conclusion") or "该风险项没有结论文本。")
        notes = item.get("verification_notes")
        if notes:
            st.caption(f"Verifier 复核说明 · {notes}")

        calculation = item.get("calculation")
        with st.expander("确定性 Calculation", expanded=calculation is not None):
            if calculation:
                st.json(calculation)
            else:
                st.write("该风险项没有关联确定性计算；其结论不依赖数值计算。")

        metadata = item.get("risk_metadata") or {}
        with st.expander("LLM 结构化事实 / metadata", expanded=False):
            if metadata:
                st.json(metadata)
            else:
                st.write("该风险项没有结构化事实记录。")
