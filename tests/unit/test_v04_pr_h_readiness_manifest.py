"""Audit the deliberately blocked PR-H readiness artifact."""

from __future__ import annotations

import json
from pathlib import Path


PATH = Path("reports/frozen/v04_pr_h_e2e_readiness_manifest.json")


def _payload() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_readiness_manifest_never_claims_a_completed_gate() -> None:
    payload = _payload()
    assert payload["formal_gate_passed"] is False
    assert payload["v04_baseline_e2e_frozen"] is False
    assert payload["real_demo_case_count"] < payload["minimum_required_demo_cases"]
    assert payload["pr_h_status"] == "blocked_missing_frozen_runtime_inputs"


def test_readiness_manifest_records_the_real_channel_gap_and_blind_guard() -> None:
    payload = _payload()
    assert payload["blind_2025_y_accessed"] is False
    assert payload["upstream_pr_a_through_pr_f_rerun"] is False
    case = payload["demo_cases"][0]
    assert case["channel_states"] == {
        "document": "available",
        "market": "available",
        "model": "disabled",
        "rule": "available",
    }
    assert case["evidence_traceability_passed"] is True
    assert case["determinism"]["passed"] is True


def test_readiness_manifest_contains_no_local_absolute_path() -> None:
    serialized = PATH.read_text(encoding="utf-8")
    assert "C:\\Users\\" not in serialized
    assert "/Users/" not in serialized
