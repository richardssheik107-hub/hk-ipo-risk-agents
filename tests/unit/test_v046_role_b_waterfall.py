from __future__ import annotations

import copy
import json

import pytest

from ipo_risk.evaluation.role_b_waterfall import (
    NOT_AVAILABLE,
    NOT_PROVEN,
    RoleBWaterfallError,
    TRACE_VERSION,
    build_monotonicity_report,
    build_retrieval_waterfall,
    build_risk_pipeline_waterfall,
)


CASE_ID = "ipo_2023_00001"


def _manifest() -> dict:
    return {
        "manifest_hash": "gold-manifest",
        "risk_units": [
            {
                "risk_unit_id": "risk-1",
                "case_id": CASE_ID,
                "split": "development",
                "source_risk_code": "redemption_rights",
            },
            {
                "risk_unit_id": "risk-2",
                "case_id": CASE_ID,
                "split": "development",
                "source_risk_code": "customer_concentration",
            },
            # Global coverage manifests contain Validation rows. They are safe
            # so long as the selected evaluator/trace rows remain Development.
            {
                "risk_unit_id": "risk-validation",
                "case_id": "ipo_2024_00002",
                "split": "validation",
                "source_risk_code": "redemption_rights",
            },
        ],
        "evidence_units": [
            {
                "evidence_unit_id": "evidence-1",
                "case_id": CASE_ID,
                "split": "development",
                "source_risk_code": "redemption_rights",
            },
            {
                "evidence_unit_id": "evidence-2",
                "case_id": CASE_ID,
                "split": "development",
                "source_risk_code": "customer_concentration",
            },
            {
                "evidence_unit_id": "evidence-validation",
                "case_id": "ipo_2024_00002",
                "split": "validation",
                "source_risk_code": "redemption_rights",
            },
        ],
    }


def _risk_rows() -> list[dict]:
    return [
        {
            "risk_unit_id": "risk-1",
            "case_id": CASE_ID,
            "split": "development",
            "source_risk_code": "redemption_rights",
            "competition_risk_family": "redemption_rights",
            "predicted_present": True,
            "predicted_positive": True,
            "predicted_bucket": "verified",
            "status_match": True,
            "level_match": True,
            "calculation_match": True,
            "evidence_hit": True,
            "correct": True,
        },
        {
            "risk_unit_id": "risk-2",
            "case_id": CASE_ID,
            "split": "development",
            "source_risk_code": "customer_concentration",
            "competition_risk_family": "customer_concentration",
            "predicted_present": False,
            "predicted_positive": False,
            "predicted_bucket": "",
            "status_match": False,
            "level_match": False,
            "calculation_match": False,
            "evidence_hit": False,
            "correct": False,
        },
    ]


def _evidence_rows() -> list[dict]:
    return [
        {
            "evidence_unit_id": "evidence-1",
            "case_id": CASE_ID,
            "split": "development",
            "source_risk_code": "redemption_rights",
            "competition_risk_family": "redemption_rights",
            "page": 12,
            "exact_text_hash": "hash-1",
            "covered": True,
            "rank": 1,
        },
        {
            "evidence_unit_id": "evidence-2",
            "case_id": CASE_ID,
            "split": "development",
            "source_risk_code": "customer_concentration",
            "competition_risk_family": "customer_concentration",
            "page": 20,
            "exact_text_hash": "hash-2",
            "covered": False,
            "rank": "",
        },
    ]


def test_final_only_risk_waterfall_is_monotone() -> None:
    report = build_risk_pipeline_waterfall(_manifest(), _risk_rows())

    assert report["trace_status"] == "FINAL_ONLY_WITHOUT_PIPELINE_TRACE"
    assert [stage["count"] for stage in report["waterfall"]] == [2, 1, 1, 1, 1, 1, 1, 1]
    assert report["units"][0]["deterministic_candidate_present"] == NOT_AVAILABLE
    assert report["units"][1]["first_failure_stage"] == "final_risk_absent"
    assert report["validation_opened"] is False
    assert report["blind_2025_outcome_accessed"] is False


def test_missing_candidate_trace_is_not_counted_as_zero_or_miss() -> None:
    report = build_retrieval_waterfall(_manifest(), _evidence_rows())

    assert report["trace_status"] == "NOT_AVAILABLE_WITHOUT_CANDIDATE_TRACE"
    assert report["observed_candidate_trace_count"] == 0
    assert report["candidate_recall_at_20_observed_only"] == NOT_AVAILABLE
    assert report["waterfall"][1]["count"] == NOT_AVAILABLE
    assert report["units"][0]["gold_evidence_in_top20"] == NOT_AVAILABLE
    assert report["units"][0]["candidate_generation_miss"] == NOT_AVAILABLE
    assert report["final_covered_count"] == 1


def test_complete_candidate_trace_builds_retrieval_waterfall_without_raw_text() -> None:
    trace = [
        {
            "trace_version": TRACE_VERSION,
            "trace_kind": "retrieval",
            "evidence_unit_id": "evidence-1",
            "case_id": CASE_ID,
            "split": "development",
            "retrieval_query_family": ["rights", "redemption"],
            "candidate_count": 5,
            "first_gold_rank": 2,
            "agent_consumed": True,
            "text": "must-not-survive",
            "raw_response": "must-not-survive",
        },
        {
            "trace_version": TRACE_VERSION,
            "trace_kind": "retrieval",
            "evidence_unit_id": "evidence-2",
            "case_id": CASE_ID,
            "split": "development",
            "retrieval_query_family": "customer_concentration",
            "candidate_count": 20,
            "first_gold_rank": None,
            "agent_consumed": False,
            "exact_text": "must-not-survive",
        },
    ]

    report = build_retrieval_waterfall(_manifest(), _evidence_rows(), trace)

    assert report["trace_status"] == "AVAILABLE"
    assert [stage["count"] for stage in report["waterfall"]] == [2, 1, 1, 1]
    assert report["units"][0]["gold_evidence_in_top1"] is False
    assert report["units"][0]["gold_evidence_in_top3"] is True
    assert report["units"][1]["candidate_generation_miss"] is True
    serialized = json.dumps(report, sort_keys=True)
    assert "must-not-survive" not in serialized
    assert "raw_response" not in serialized


def test_optional_risk_trace_enriches_only_whitelisted_fields() -> None:
    trace = [
        {
            "trace_version": TRACE_VERSION,
            "trace_kind": "risk_pipeline",
            "risk_unit_id": "risk-1",
            "case_id": CASE_ID,
            "split": "development",
            "deterministic_candidate_present": True,
            "llm_request_success": True,
            "llm_structured_valid": True,
            "llm_scope_valid": True,
            "llm_candidate_present": True,
            "llm_abstained": False,
            "candidate_conflict": False,
            "normalization_success": True,
            "reconciliation_success": True,
            "candidate_after_reconciliation": True,
            "verifier_outcome": "verified",
            "final_evidence_ids": ["ev-2", "ev-1", "ev-1"],
            "prompt": "must-not-survive",
        },
        {
            "trace_version": TRACE_VERSION,
            "trace_kind": "risk_pipeline",
            "risk_unit_id": "risk-2",
            "case_id": CASE_ID,
            "split": "development",
            "deterministic_candidate_present": False,
            "llm_request_success": True,
            "llm_structured_valid": True,
            "llm_scope_valid": True,
            "llm_candidate_present": False,
            "llm_abstained": True,
            "candidate_conflict": False,
            "normalization_success": False,
            "reconciliation_success": False,
            "candidate_after_reconciliation": False,
            "verifier_outcome": "not_reached",
            "final_evidence_ids": [],
        },
    ]

    report = build_risk_pipeline_waterfall(_manifest(), _risk_rows(), trace)

    assert report["trace_status"] == "AVAILABLE"
    assert report["units"][0]["deterministic_candidate_present"] is True
    assert report["units"][0]["final_evidence_ids"] == ["ev-1", "ev-2"]
    assert "must-not-survive" not in json.dumps(report, sort_keys=True)


@pytest.mark.parametrize(
    ("target", "case_id", "split"),
    [
        ("risk", "ipo_2024_00002", "validation"),
        ("evidence", "ipo_2025_00003", "development"),
    ],
)
def test_validation_and_blind_rows_are_rejected(target: str, case_id: str, split: str) -> None:
    manifest = _manifest()
    if target == "risk":
        rows = _risk_rows()
        rows[0]["risk_unit_id"] = "risk-validation"
        rows[0]["case_id"] = case_id
        rows[0]["split"] = split
        with pytest.raises(RoleBWaterfallError, match="non_development|validation_or_blind"):
            build_risk_pipeline_waterfall(manifest, rows)
    else:
        manifest["evidence_units"].append(
            {
                "evidence_unit_id": "evidence-blind",
                "case_id": case_id,
                "split": split,
                "source_risk_code": "redemption_rights",
            }
        )
        rows = _evidence_rows()
        rows[0]["evidence_unit_id"] = "evidence-blind"
        rows[0]["case_id"] = case_id
        rows[0]["split"] = split
        with pytest.raises(RoleBWaterfallError, match="validation_or_blind"):
            build_retrieval_waterfall(manifest, rows)


def _identity(*, journal: str | None = None) -> dict:
    identity = {
        "split": "development",
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "code_fingerprint": "code",
        "subset_hash": "subset",
        "gold_manifest_hash": "gold-manifest",
        "evaluator_version": "evaluator",
    }
    if journal is not None:
        identity.update(
            {
                "provider": "openai_responses",
                "model": "model",
                "transport": "responses",
                "prompt_set_hash": "prompts",
                "schema_set_hash": "schemas",
                "llm_journal_hash": journal,
            }
        )
    return identity


def _mode_result(mode: str, *, journal: str | None = None) -> dict:
    summary = {
        "m1": 0.5,
        "m2": 0.5,
        "per_risk": {
            "redemption_rights": {"official_aligned_accuracy": 1.0},
            "customer_concentration": {"official_aligned_accuracy": 0.0},
        },
    }
    return {
        "identity": _identity(journal=journal),
        "summary": summary,
        "risk_rows": copy.deepcopy(_risk_rows()),
        "evidence_rows": copy.deepcopy(_evidence_rows()),
        "canonical_result_hashes": {CASE_ID: "offline-canonical"},
        "mode": mode,
    }


def _mode_results() -> dict:
    return {
        "offline": _mode_result("offline"),
        "shadow": _mode_result("shadow", journal="journal"),
        "gated": _mode_result("gated", journal="journal"),
    }


def test_monotonicity_is_proven_only_with_same_identity_journal_and_shadow_output() -> None:
    report = build_monotonicity_report(_mode_results(), _manifest())

    assert report["status"] == "PROVEN"
    assert report["satisfied"] is True
    assert report["offline_vs_shadow"]["canonical_results_equal"] is True
    assert report["offline_vs_gated"]["m1_delta"] == 0.0
    assert report["offline_vs_gated"]["m2_delta"] == 0.0
    assert report["deterministic_risks_removed_by_llm_count"] == 0
    assert report["deterministic_evidence_removed_by_llm_count"] == 0


def test_monotonicity_is_not_proven_when_journal_identity_differs() -> None:
    modes = _mode_results()
    modes["gated"]["identity"]["llm_journal_hash"] = "different-journal"

    report = build_monotonicity_report(modes, _manifest())

    assert report["status"] == NOT_PROVEN
    assert report["satisfied"] == NOT_PROVEN
    assert "llm_identity_mismatch:llm_journal_hash" in report["reasons"]


def test_monotonicity_detects_removed_deterministic_units() -> None:
    modes = _mode_results()
    gated_risk = modes["gated"]["risk_rows"][0]
    gated_risk.update(
        {
            "predicted_present": False,
            "predicted_positive": False,
            "predicted_bucket": "",
            "status_match": False,
            "level_match": False,
            "calculation_match": False,
            "evidence_hit": False,
            "correct": False,
        }
    )
    modes["gated"]["evidence_rows"][0].update({"covered": False, "rank": ""})
    modes["gated"]["summary"]["m1"] = 0.0
    modes["gated"]["summary"]["m2"] = 0.0

    report = build_monotonicity_report(modes, _manifest())

    assert report["status"] == "PROVEN"
    assert report["satisfied"] is False
    assert report["deterministic_risk_unit_ids_removed"] == ["risk-1"]
    assert report["deterministic_evidence_unit_ids_removed"] == ["evidence-1"]
    assert report["per_risk_regressions"] == ["risk-1"]
