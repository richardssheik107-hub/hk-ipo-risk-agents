"""Safety checks for tracked GPT Expert blind collaboration packets."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES


ROOT = Path("docs/annotation/gpt_expert_v1_1")


def _manifest() -> list[dict[str, str]]:
    with (ROOT / "source_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_collaboration_manifest_is_14_case_development_only() -> None:
    rows = _manifest()
    assert len(rows) == 14
    assert len({row["case_id"] for row in rows}) == 14
    assert {row["dataset_split"] for row in rows} <= {"development", "development_exception"}
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
        assert payload["metadata"] == {
            "blind_annotation": True,
            "human_golden_visible_to_annotator": False,
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


def test_assignment_starts_unassigned() -> None:
    with (ROOT / "team_case_assignment.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 14
    for row in rows:
        assert not row["primary_annotator"]
        assert not row["primary_status"]
        assert not row["second_pass_annotator"]
        assert not row["second_pass_status"]
        assert not row["adjudication_status"]
        assert not row["final_status"]
        assert not row["notes"]


def test_collaboration_branch_has_no_expert_result_tree() -> None:
    assert not (ROOT / "expert_results").exists()
