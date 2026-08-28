from __future__ import annotations

import csv
import json
from pathlib import Path

from ipo_risk.evaluation.role_b_cross_run import compare_cross_run


def _record(case_id: str, restoration: bool) -> dict[str, object]:
    evidence_ids = ["e-1", "e-2"]
    return {
        "identity": {
            "case_id": case_id,
            "task_name": "shareholder_rights_extract",
            "evidence_content_hash": "evidence-hash",
            "ordered_allowed_evidence_ids": evidence_ids,
            "prompt_hash": "prompt-hash",
            "prompt_version": "legal_shareholder_rights_v1",
            "provider": "openai_responses",
            "model": "ark-code-latest",
            "response_model": "ShareholderRightCandidate",
            "response_schema_hash": "schema-hash",
            "runtime_config_hash": "runtime-hash",
            "transport": "responses",
        },
        "response_hash": f"response-{restoration}",
        "structured_payload": {
            "right_type": "redemption_right",
            "holder": "Pre-IPO investors",
            "is_effective": True,
            "survives_listing": False,
            "termination_event": "listing",
            "termination_timing": "upon listing",
            "restoration_clause": restoration,
            "restoration_condition": "listing application fails" if restoration else "",
            "evidence_ids": ["e-1"],
        },
    }


def _write_journal(root: Path, record: dict[str, object]) -> None:
    root.mkdir()
    (root / "record.json").write_text(json.dumps(record), encoding="utf-8")


def _write_lifecycle(path: Path, m1: bool) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "risk_code", "m1_correct", "gold_evidence_count"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "ipo_2020_09600",
                "risk_code": "redemption_rights",
                "m1_correct": str(m1),
                "gold_evidence_count": "1",
            }
        )


def test_identical_inputs_with_payload_change_are_llm_response_variance(tmp_path: Path) -> None:
    journal_a = tmp_path / "journal-a"
    journal_b = tmp_path / "journal-b"
    _write_journal(journal_a, _record("ipo_2020_09600", True))
    _write_journal(journal_b, _record("ipo_2020_09600", False))
    lifecycle_a = tmp_path / "a.csv"
    lifecycle_b = tmp_path / "b.csv"
    _write_lifecycle(lifecycle_a, True)
    _write_lifecycle(lifecycle_b, False)

    result = compare_cross_run(
        run_a_journal=journal_a,
        run_b_journal=journal_b,
        run_a_lifecycle=lifecycle_a,
        run_b_lifecycle=lifecycle_b,
    )

    assert result["classification"] == "LLM_RESPONSE_VARIANCE"
    assert result["identity_mismatch_count"] == 0
    assert result["structured_payload_variance_case_count"] == 1
    assert result["cases"][0]["run_a_replay"]["builder_status"] == "built"
    assert result["cases"][0]["run_b_replay"]["builder_status"] == "not_applicable"
    assert result["network_calls"] == 0

