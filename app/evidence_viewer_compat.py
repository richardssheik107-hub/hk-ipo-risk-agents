"""Compatibility shim for Evidence Viewer during partial frontend updates.

PR #180 added an optional replay argument to ``render_evidence_viewer``. A local
checkout can temporarily contain the new Streamlit caller and the older two-
argument viewer (for example after a partial file sync).  Inspect the callable
before invoking it so that version skew degrades to the live two-argument viewer
instead of crashing the whole application.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from evidence_viewer import render_evidence_viewer as _render_evidence_viewer


def _supports_replay(viewer: Callable[..., Any]) -> bool:
    try:
        parameters = inspect.signature(viewer).parameters.values()
    except (TypeError, ValueError):
        return True
    return any(
        parameter.name == "replay"
        or parameter.kind
        in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}
        for parameter in parameters
    )


def render_evidence_viewer(
    payload: dict[str, Any],
    pdf_bytes: bytes | None,
    replay: Any | None = None,
) -> None:
    """Call either the current three-argument viewer or the legacy two-arg one."""

    if _supports_replay(_render_evidence_viewer):
        _render_evidence_viewer(payload, pdf_bytes, replay)
    else:
        _render_evidence_viewer(payload, pdf_bytes)
