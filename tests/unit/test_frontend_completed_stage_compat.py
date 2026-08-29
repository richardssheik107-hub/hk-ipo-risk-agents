"""Regression guard for current-case completion vs legacy UI Gate copy."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / "app" / "pipeline_stages.py"
_SPEC = importlib.util.spec_from_file_location("pipeline_stages_completed_compat", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
pipeline_stages = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = pipeline_stages
_SPEC.loader.exec_module(pipeline_stages)


def test_completed_current_case_uses_green_legacy_presentation_value() -> None:
    payload = {
        "status": "completed",
        "risk_status_counts": {"verified": 1, "needs_review": 0, "pending": 0, "rejected": 0},
        "verified_risks": [{"risk_id": "r-1", "evidence": [{"evidence_id": "e-1"}]}],
        "pending_risks": [],
        "rejected_risks": [],
        "prediction": {"risk_score": 61.0, "risk_level": "high"},
        # Deliberately omit Market-X and model handoffs. A completed product run
        # must keep those channels explicitly unavailable without turning their
        # stages amber or reviving old PR-A/PR-B/PR-F/PR-H Gate copy.
        "supervision": {"duplicate_groups": [], "conflicts": [], "composite_findings": []},
        "report_sections": [{"title": "Summary"}],
    }

    stages = pipeline_stages.resolve_stages(payload)

    assert len(stages) == 7
    assert all(stage.is_available for stage in stages)
    assert all(stage.status.value == "available" for stage in stages)
    assert pipeline_stages.blocking_gates() == ()


def test_genuinely_incomplete_surface_stays_partial() -> None:
    stages = pipeline_stages.resolve_stages({})
    assert any(stage.status.value == "partial" for stage in stages)
