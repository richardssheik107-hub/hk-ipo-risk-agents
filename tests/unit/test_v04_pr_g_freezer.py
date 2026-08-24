"""Fail-closed tests for the deterministic PR-G freezer."""

from __future__ import annotations

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.freeze_v04_pr_g_manifest import PRGFreezeError, freeze


def _fixture(tmp_path: Path) -> dict:
    pdf = tmp_path / "prospectus.pdf"
    pdf.write_bytes(b"real prospectus fixture")
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    (frozen / "v04_pr_f_lightgbm_manifest.json").write_text(json.dumps({
        "status": "complete_frozen", "formal_gate_passed": True,
        "blind_2025_y_accessed": False, "freeze_manifest_hash": "f" * 64,
    }), encoding="utf-8")
    bridge = tmp_path / "bridge.csv"
    with bridge.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "stock_code_wind", "official_match_status", "official_listed_date", "selected_name",
        ])
        writer.writeheader()
        writer.writerow({"stock_code_wind": "2410.HK", "official_match_status": "matched",
                         "official_listed_date": "2024-08-20", "selected_name": "Official Co"})
    review = tmp_path / "A_REVIEW.md"
    review.write_text("Decision: GATE REVIEW PASS", encoding="utf-8")
    draft = {
        "manifest_version": "v04_pr_g_freeze_manifest_v1",
        "pr_g_version": "v04_pr_g_final_supervision_v1",
        "status": "implementation_complete_awaiting_gate_review",
        "formal_gate_passed": False,
        "case_identity": {"company_name": "Official Co", "stock_code": "2410.HK",
                          "listing_date": "2024-08-20"},
        "closed_loop": {"prospectus_sha256": pdf_hash, "analysis_status": "completed",
                        "report_section_count": 13, "verified_risk_count": 1},
        "channel_states": [],
        "market_channel": {"status": "unavailable_error"},
        "model_channel": {"frozen_pr_f_manifest": "v04_pr_f_lightgbm_manifest.json",
                          "frozen_pr_f_manifest_hash": "f" * 64,
                          "score_semantics": "uncalibrated_model_score"},
        "traceability": {"all_references_resolve": True, "referenced_evidence_count": 2,
                         "indexed_evidence_count": 2},
        "creates_no_new_risk": True, "probability_claimed": False,
        "blind_2025_y_accessed": False, "final_supervision_content_hash": "a" * 64,
    }
    draft_path = tmp_path / "draft.json"
    draft_path.write_text(json.dumps(draft), encoding="utf-8")
    return {"draft": draft, "draft_path": draft_path, "pdf": pdf, "frozen": frozen,
            "bridge": bridge, "review": review}


def _run(fx: dict) -> dict:
    fx["draft_path"].write_text(json.dumps(fx["draft"]), encoding="utf-8")
    return freeze(draft_path=fx["draft_path"], prospectus_path=fx["pdf"],
                  official_bridge_path=fx["bridge"], frozen_dir=fx["frozen"],
                  source_revision="1" * 40, a_review_path=fx["review"])


def test_valid_real_draft_freezes_deterministically(tmp_path) -> None:
    fx = _fixture(tmp_path)
    first = _run(fx)
    second = _run(fx)
    assert first == second
    assert first["status"] == "complete_frozen"
    assert first["formal_gate_passed"] is True
    assert first["blind_2025_y_accessed"] is False


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("closed_loop", "prospectus_sha256"), "0" * 64, "prospectus bytes"),
        (("case_identity", "listing_date"), "2024-01-01", "listing date"),
        (("closed_loop", "analysis_status"), "partial", "not completed"),
        (("traceability", "all_references_resolve"), False, "traceability"),
        (("probability_claimed",), True, "probability"),
        (("blind_2025_y_accessed",), True, "Blind"),
        (("creates_no_new_risk",), False, "new risk"),
        (("model_channel", "frozen_pr_f_manifest_hash"), "0" * 64, "PR-F identity"),
    ],
)
def test_gate_invariant_drift_fails_closed(tmp_path, path, value, match) -> None:
    fx = _fixture(tmp_path)
    cursor = fx["draft"]
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(PRGFreezeError, match=match):
        _run(fx)


def test_missing_a_review_pass_fails_closed(tmp_path) -> None:
    fx = _fixture(tmp_path)
    fx["review"].write_text("review pending", encoding="utf-8")
    with pytest.raises(PRGFreezeError, match="does not record PASS"):
        _run(fx)


def test_freeze_preserves_honest_unavailable_channels(tmp_path) -> None:
    fx = _fixture(tmp_path)
    result = _run(fx)
    assert result["market_channel"]["status"] == "unavailable_error"
    assert result["model_channel"]["score_semantics"] == "uncalibrated_model_score"
