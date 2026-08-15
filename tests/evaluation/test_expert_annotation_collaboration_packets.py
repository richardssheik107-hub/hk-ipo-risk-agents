"""Safety checks for tracked GPT Expert blind collaboration packets."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


ROOT = Path("docs/annotation/gpt_expert_v1_1")
PROGRESS_STATUSES = {
    "not_started",
    "in_progress",
    "completed",
    "validation_failed",
    "needs_review",
    "audit_completed",
    "adjudication_required",
    "finalized",
}
ASSIGNMENT_COLUMNS = {
    "task_index",
    "taskset_version",
    "case_id",
    "stock_code",
    "company_name",
    "source_year",
    "dataset_split",
    "primary_annotator",
    "primary_status",
    "second_pass_annotator",
    "second_pass_status",
    "adjudication_status",
    "final_status",
    "notes",
}


def _manifest() -> list[dict[str, str]]:
    with (ROOT / "source_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_collaboration_manifest_is_frozen_100_case_taskset() -> None:
    rows = _manifest()
    assert len(rows) == 100
    assert len({row["case_id"] for row in rows}) == 100
    assert len({row["stock_code"] for row in rows}) == 100
    assert {row["taskset_version"] for row in rows} == {"expert_golden_100_v1"}
    assert {row["dataset_split"] for row in rows} == {
        "development", "development_exception", "validation"
    }
    assert all("2025" not in row["case_id"] for row in rows)


def test_every_packet_has_all_risks_and_blank_answers() -> None:
    for row in _manifest():
        packet = ROOT / "case_packets" / row["case_id"] / "blank_annotation.json"
        payload = json.loads(packet.read_text(encoding="utf-8"))
        assert payload["annotation_version"] == "gpt_expert_v1.1"
        assert {risk["risk_code"] for risk in payload["risks"]} == set(V03_ENABLED_RISK_CODES)
        assert len(payload["risks"]) == len(V03_ENABLED_RISK_CODES)
        for risk in payload["risks"]:
            assert risk["applicable"] is None
            assert risk["expected_status"] is None
            assert risk["expected_level"] is None
            assert risk["confidence"] is None
            assert risk["reasoning"] is None
            assert risk["calculation_required"] is None
        assert payload["evidence"] == []
        metadata = payload["metadata"]
        assert metadata["blind_annotation"] is True
        assert metadata["human_golden_visible_to_annotator"] is False
        assert metadata["output_contract"] == "ExpertAnnotationBundle"
        assert "0.0 to 1.0" in metadata["confidence_constraint"]
        assert set(metadata["evidence_object_schema"]) == {
            "case_id", "risk_code", "page", "evidence_role", "requirement",
            "source_authority", "exact_text", "evidence_reason", "confidence",
        }


def test_packets_contain_no_paths_or_answer_artifacts() -> None:
    forbidden = (
        "C:" + "/" + "Users" + "/",
        "C:" + "\\" + "Users" + "\\",
        "source_pdf_path",
        "gold_page",
        "v03_golden_case_manifest",
        "PILOT_DIAGNOSTIC_ONLY.json",
    )
    for path in ROOT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8-sig")
            assert not any(marker in text for marker in forbidden), path


def test_assignment_tracker_matches_frozen_taskset() -> None:
    with (ROOT / "team_case_assignment.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        assert set(reader.fieldnames or ()) == ASSIGNMENT_COLUMNS
        rows = list(reader)
    assert len(rows) == 100
    assert {row["case_id"] for row in rows} == {row["case_id"] for row in _manifest()}
    assert {row["taskset_version"] for row in rows} == {"expert_golden_100_v1"}
    assert {row["task_index"] for row in rows} == {str(index) for index in range(1, 101)}


def test_assignment_uses_only_documented_progress_statuses() -> None:
    with (ROOT / "team_case_assignment.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    status_fields = ("primary_status", "second_pass_status", "adjudication_status", "final_status")
    for row in rows:
        for field in status_fields:
            assert not row[field] or row[field] in PROGRESS_STATUSES


def test_collaboration_branch_has_no_expert_result_tree() -> None:
    assert not (ROOT / "expert_results").exists()


def test_official_2410_packet_uses_catalog_identity_and_legacy_packet_is_preserved() -> None:
    taskset = ROOT / "case_packets" / "ipo_2024_02410" / "blank_annotation.json"
    payload = json.loads(taskset.read_text(encoding="utf-8"))
    assert payload["stock_code"] == "2410.HK"
    assert payload["case_id"] == payload["document_id"] == "ipo_2024_02410"
    assert (ROOT / "case_packets" / "real_case_001").is_dir()
