"""HTTP surface for the E lane.

The API is an adapter, not a second brain: it reads persisted analysis results
and writes reviewer decisions through the same application services the
Streamlit console uses.  It never runs an analysis, never recomputes a machine
verdict and never edits one.
"""

from __future__ import annotations

from ipo_risk.api.human_review import build_app, create_app

__all__ = ["build_app", "create_app"]
