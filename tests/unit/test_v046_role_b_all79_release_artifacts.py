from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from ipo_risk.runtime.submission_readiness import audit_role_b
from scripts.export_v046_role_b_all79_release import _inspect_value, _validate_csv


ROOT = Path(__file__).parents[2]
ROLE_B = ROOT / "reports" / "v045_role_b"
DETAILS = ROLE_B / "all79_final"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_all79_release_receipt_is_hash_bound_and_safe() -> None:
    manifest = _json(DETAILS / "run_manifest.json")
    assert manifest["schema_version"] == "v046_role_b_all79_release_receipt_v1"
    assert manifest["run_id"] == "finaldayA_bundle10_real_all79_001"
    assert manifest["case_count"] == 79
    assert manifest["full_development_executed"] is True
    assert manifest["selected_mode"] == "offline"
    assert manifest["source_execution_git_dirty"] is False
    assert manifest["validation_opened"] is False
    assert manifest["blind_2025_outcome_accessed"] is False
    assert manifest["raw_journal_included"] is False
    assert manifest["raw_prompt_included"] is False
    assert manifest["raw_response_included"] is False
    assert manifest["prospectus_or_evidence_text_included"] is False
    assert manifest["pdf_or_cache_included"] is False
    assert manifest["secret_included"] is False

    for artifact in manifest["artifacts"]:
        path = ROLE_B / artifact["path"]
        assert path.is_file(), artifact["path"]
        assert path.stat().st_size == artifact["size_bytes"]
        assert _sha(path) == artifact["sha256"]

    expected_detail_files = {
        Path(item["path"]).name
        for item in manifest["artifacts"]
        if item["path"].startswith("all79_final/")
    } | {"run_manifest.json", "SHA256SUMS.txt"}
    actual_detail_files = {path.name for path in DETAILS.iterdir() if path.is_file()}
    assert actual_detail_files == expected_detail_files

    recorded = {}
    for line in (DETAILS / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        recorded[relative] = digest
    assert recorded["all79_final/run_manifest.json"] == _sha(DETAILS / "run_manifest.json")
    for artifact in manifest["artifacts"]:
        assert recorded[artifact["path"]] == artifact["sha256"]


def test_all79_release_metrics_and_promotion_decision_are_truthful() -> None:
    gated = _json(ROLE_B / "document_benchmark_summary.json")
    offline = _json(DETAILS / "offline_document_benchmark_summary.json")
    quality = _json(DETAILS / "llm_call_quality.json")
    monotonicity = _json(DETAILS / "monotonicity_report.json")
    best = _json(DETAILS / "best_iteration.json")
    gold = _json(ROLE_B / "existing_gold_manifest_receipt.json")
    calls = _json(DETAILS / "llm_call_manifest.json")

    assert gated["evaluated_case_count"] == 79
    assert gated["real_llm_cases"] == 79
    assert gated["risk_extraction"]["correct_positive_count"] == 61
    assert gated["risk_extraction"]["evaluable_positive_count"] == 102
    assert gated["evidence_coverage"]["covered_existing_gold_count"] == 93
    assert gated["evidence_coverage"]["evaluable_existing_gold_count"] == 191
    assert gated["measurement_gate"]["official_m1_pass"] is False
    assert gated["measurement_gate"]["official_m2_pass"] is False

    assert offline["risk_extraction"]["correct_positive_count"] == 70
    assert offline["evidence_coverage"]["covered_existing_gold_count"] == 103
    assert best["selected_mode"] == "offline"
    assert best["real_llm_candidate_accepted"] is False
    assert quality["call_count"] == 316
    assert quality["real_llm_case_count"] == 79
    assert quality["structured_scope_valid_count"] == 310
    assert quality["fallback_count"] == 6
    assert quality["transport_failure_count"] == 0
    assert quality["raw_prompt_persisted"] is False
    assert quality["raw_response_persisted"] is False
    assert monotonicity["deterministic_risks_removed_by_llm_count"] == 9
    assert monotonicity["deterministic_evidence_removed_by_llm_count"] == 12
    assert monotonicity["satisfied"] is False

    assert calls["record_count"] == 316
    assert calls["network_request_count"] == 323
    assert calls["failure_count"] == 6
    assert calls["request_ids_hashed"] is True
    assert calls["provider_responses_hashed"] is True
    assert calls["raw_prompt_included"] is False
    assert calls["raw_response_included"] is False
    assert calls["structured_payload_included"] is False
    assert len(calls["records"]) == 316
    for call in calls["records"]:
        assert len(call["request_id_hash"]) == 64
        assert len(call["raw_response_hash"]) == 64
        if call["outcome"] == "success":
            assert len(call["structured_payload_hash"]) == 64
        else:
            assert call["structured_payload_hash"] is None
        assert call["latency_ms"] >= 0

    assert gold["artifact_scope"] == "metadata_receipt_only"
    assert gold["source_full_manifest_included"] is False
    assert gold["risk_units_included"] is False
    assert gold["evidence_units_included"] is False
    assert gold["exact_evidence_text_included"] is False
    assert "risk_units" not in gold
    assert "evidence_units" not in gold


def test_all79_release_gate_fails_closed_on_measured_thresholds() -> None:
    gate = audit_role_b(ROLE_B)

    assert gate.passed is False
    assert gate.blockers == (
        "M1 Existing-Gold official-aligned accuracy >=80% is not demonstrated",
        "M2 Existing-Gold Evidence Coverage Recall >=85% is not demonstrated",
        "Role-B Validation one-shot/no-post-hoc-tuning attestation is missing",
    )


def test_all79_export_guard_rejects_raw_values_and_local_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="forbidden JSON field"):
        _inspect_value({"raw_response": "provider payload"}, source=tmp_path / "unsafe.json")
    with pytest.raises(ValueError, match="forbidden JSON field"):
        _inspect_value({"structured_payload": {"risk": "raw"}}, source=tmp_path / "unsafe.json")
    with pytest.raises(ValueError, match="forbidden JSON field"):
        _inspect_value({"company_name": "private issuer"}, source=tmp_path / "unsafe.json")
    with pytest.raises(ValueError, match="forbidden string"):
        _inspect_value(
            {"artifact": "C:/Users/example/private/result.json"},
            source=tmp_path / "unsafe.json",
        )

    _inspect_value(
        {
            "raw_response_persisted": False,
            "exact_text_hash": "0" * 64,
            "provider": "openai_responses",
        },
        source=tmp_path / "safe.json",
    )


def test_all79_export_guard_rejects_csv_schema_drift(tmp_path: Path) -> None:
    path = tmp_path / "risk_benchmark.csv"
    path.write_text("case_id,unexpected_raw_text\ncase-1,secret\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected CSV schema"):
        _validate_csv(path)
