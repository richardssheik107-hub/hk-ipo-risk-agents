"""Regression tests for the committed V2 release and conditional promotion record."""

from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.modeling.role_d_v2_release import validate_release


ROOT = Path(__file__).resolve().parents[2]


def test_committed_v2_release_recalculates_without_blockers() -> None:
    result = validate_release(
        freeze_manifest_path=ROOT / "reports/frozen/v045_role_d_v2_promotion_manifest.json",
        receipt_path=ROOT / "reports/frozen/v045_role_d_v2_promotion_receipt.json",
        role_d_dir=ROOT / "reports/v045_role_d_v2",
        handoff_dir=ROOT / "reports/v045_role_d_v2_product_handoff_final3",
    )
    assert result == {
        "status": "pass",
        "passed": True,
        "blockers": [],
        "case_count": 70,
        "artifact_count": 4,
        "handoff_case_count": 3,
    }


def test_promotion_is_effective_only_through_a_owned_merge() -> None:
    manifest = json.loads(
        (ROOT / "reports/frozen/v045_role_d_v2_promotion_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    decision = manifest["promotion_record"]
    assert decision["decision"] == "promote_v2"
    assert decision["decision_owner"] == "A"
    assert decision["status"] == "effective_on_a_owned_merge"
    assert decision["prior_frozen_pr_f_preserved"] is True
    assert manifest["blind_2025_y_accessed"] is False


def test_v2_freeze_locks_development_selected_policy() -> None:
    manifest = json.loads(
        (ROOT / "reports/frozen/v045_role_d_v2_promotion_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    selection = manifest["selection"]
    assert selection["validation_used_for_selection"] is False
    assert selection["alert_fraction"] == 0.475
    assert selection["selected_features"] == [
        "ipo_count_30d",
        "ipo_count_60d",
        "recent_ipo_break_rate",
        "recent_ipo_return_5d",
        "same_industry_ipo_count_180d",
        "same_industry_recent_break_rate",
        "same_industry_recent_return_5d",
    ]
