"""Compatibility shim for Evidence Viewer during partial frontend updates.

PR #180 added an optional replay argument to ``render_evidence_viewer``. A local
checkout can temporarily contain the new Streamlit caller and the older two-
argument viewer (for example after a partial file sync). Inspect the callable
before invoking it so that version skew degrades to the live two-argument viewer
instead of crashing the whole application.

The current viewer also accepts the keyword-only ``expert`` flag used by the
technical backend. Older three-argument replay viewers and two-argument live
viewers do not, so that flag is forwarded only when the loaded callable can
accept it.
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


def _supports_expert(viewer: Callable[..., Any]) -> bool:
    """Return whether ``viewer`` can accept ``expert`` as a keyword argument."""

    try:
        parameters = inspect.signature(viewer).parameters.values()
    except (TypeError, ValueError):
        return True
    return any(
        (
            parameter.name == "expert"
            and parameter.kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        )
        or parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def render_evidence_viewer(
    payload: dict[str, Any],
    pdf_bytes: bytes | None,
    replay: Any | None = None,
    *,
    expert: bool = False,
) -> None:
    """Call the current viewer or either supported legacy signature."""

    if _supports_replay(_render_evidence_viewer):
        args = (payload, pdf_bytes, replay)
    else:
        args = (payload, pdf_bytes)

    if _supports_expert(_render_evidence_viewer):
        _render_evidence_viewer(*args, expert=expert)
    else:
        _render_evidence_viewer(*args)
