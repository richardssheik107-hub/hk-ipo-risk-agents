from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.runtime.product_capability_acceptance import (
    REQUIRED_CAPABILITIES,
    ProductCapabilityAcceptanceError,
    build_capability_manifest,
    build_product_acceptance,
    verify_persisted,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_current_governed_evidence_closes_g5_without_opening_validation() -> None:
    artifact = build_product_acceptance(REPO_ROOT)
    assert artifact["status"] == "pass"
    assert artifact["truthful_channel_states"] is True
    assert set(artifact["modes"]) == {
        "offline_demo_replay",
        "historical_governed_ipo",
        "fresh_new_ipo_analysis",
    }
    assert artifact["governance"]["validation_opened"] is False
    assert artifact["governance"]["blind_2025_y_accessed"] is False


def test_current_capability_manifest_is_complete_and_qualitative() -> None:
    artifact = build_capability_manifest(REPO_ROOT)
    assert artifact["status"] == "pass"
    assert artifact["capabilities"] == list(REQUIRED_CAPABILITIES)
    assert all(item["status"] == "pass" for item in artifact["capability_details"])
    assert all(
        item["classification"] == "QUALITATIVE_DEMONSTRATION"
        and item["included_in_m1_m2"] is False
        for item in artifact["capability_details"]
    )


def test_stale_persisted_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = build_product_acceptance(REPO_ROOT)
    path = tmp_path / "product_acceptance.json"
    stale = {**artifact, "truthful_channel_states": False}
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(ProductCapabilityAcceptanceError, match="stale"):
        verify_persisted(artifact, path)

