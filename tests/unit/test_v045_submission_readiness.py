from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
from uuid import NAMESPACE_URL, uuid5
import zipfile

import pytest

from ipo_risk.runtime.submission_readiness import (
    ROLE_E_CASE_REQUIRED,
    _scan_path_for_sensitive_material,
    build_artifact_index,
    build_submission_readiness,
    finalize_readiness_with_artifact_index,
    package_submission_bundle,
    write_artifact_index,
    write_submission_audits,
)


def _json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv(path: Path, fieldnames: list[str], row: dict | list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(row if isinstance(row, list) else [row])


def _repo(root: Path) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    protocol = "v045_competition_metric_protocol_v2_existing_gold_only"
    (root / "README.md").write_text(
        f"# project\n{protocol}\n尚未标记 `COMPETITION_READY`\n", encoding="utf-8"
    )
    for name in (
        "V0.4_RELEASE_ACCEPTANCE.md",
        "V045_CURRENT_EXECUTION_PLAN.md",
        "ROADMAP.md",
        "SUBMISSION_RUNBOOK.md",
    ):
        text = f"# {name}\n{protocol}\n"
        if name == "V0.4_RELEASE_ACCEPTANCE.md":
            text += "Current verdict: **NOT YET COMPETITION_READY**\n"
        (root / "docs" / name).write_text(text, encoding="utf-8")
    (root / ".env.example").write_text("IPO_RISK_LLM_API_KEY=\n", encoding="utf-8")
    for name in ("CHANGELOG.md", "AGENTS.md", "pyproject.toml", "environment.yml"):
        (root / name).write_text(f"fixture {name}\n", encoding="utf-8")
    for name in (
        "COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md",
        "V04_FIVE_PERSON_EXECUTION_PLAN.md",
    ):
        (root / "docs" / name).write_text(f"# {name}\n{protocol}\n", encoding="utf-8")
    for dirname in ("src", "app", "configs", "scripts"):
        path = root / dirname / "fixture.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{dirname} fixture\n", encoding="utf-8")


def _role_b(root: Path) -> None:
    manifest_hash = "ef" * 32
    _json(
        root / "existing_gold_evaluable_manifest.json",
        {
            "metric_protocol_version": "v045_competition_metric_protocol_v2_existing_gold_only",
            "manifest_hash": manifest_hash,
            "existing_gold_source": "frozen Expert Annotation / Oracle",
            "evaluable_development_case_count": 79,
            "evaluable_validation_case_count": 19,
            "new_manual_annotations_added": False,
            "existing_gold_modified": False,
            "blind_2025_outcome_accessed": False,
            "source_governance": {
                "source_inventory_matches_frozen": True,
                "frozen_manifest_hash": "aa" * 32,
            },
        },
    )
    _json(
        root / "document_benchmark_summary.json",
        {
            "metric_protocol_version": "v045_competition_metric_protocol_v2_existing_gold_only",
            "existing_gold_source": "frozen Expert Annotation / Oracle",
            "existing_gold_source_hash_or_manifest": manifest_hash,
            "split": "development",
            "evaluation_scope": "full_split",
            "evaluable_development_case_count": 79,
            "evaluable_validation_case_count": 19,
            "expected_case_count_for_split": 79,
            "evaluated_case_count": 79,
            "missing_case_ids": [],
            "real_llm_cases": 79,
            "external_llm_called": True,
            "risk_extraction": {"official_aligned_accuracy": 0.82},
            "evidence_coverage": {"coverage_recall": 0.86},
            "retrieval_diagnostics": {
                "recall_at_1": 0.5,
                "recall_at_3": 0.7,
                "recall_at_5": 0.8,
                "recall_at_10": 0.9,
                "recall_at_20": 0.95,
            },
            "measurement_gate": {"competition_pass_claim_eligible": True},
            "validation_one_shot": True,
            "validation_post_hoc_tuning": False,
            "new_manual_annotations_added": False,
            "existing_gold_modified": False,
            "blind_2025_outcome_accessed": False,
        },
    )
    _csv(
        root / "risk_benchmark.csv",
        ["risk_code", "source_manifest_key", "source_annotation_hash"],
        {"risk_code": "r", "source_manifest_key": "m", "source_annotation_hash": "ab" * 32},
    )
    _csv(
        root / "evidence_benchmark.csv",
        ["risk_code", "source_manifest_key", "source_annotation_hash"],
        {"risk_code": "r", "source_manifest_key": "m", "source_annotation_hash": "ab" * 32},
    )
def _role_d(root: Path) -> None:
    case_ids = [f"ipo_2024_{index:05d}" for index in range(1, 71)]
    prediction_fields = [
        "case_id",
        "stock_code",
        "cohort_year",
        "dataset_split",
        "model",
        "feature_group",
        "poor_performer_score",
        "score_semantics",
        "classification_threshold",
        "predicted_significant_drop_5d",
        "predicted_return_5d",
        "actual_significant_drop_5d",
        "actual_return_5d",
        "top_shap_drivers_json",
    ]
    _csv(
        root / "test_predictions.csv",
        prediction_fields,
        [
            {
                "case_id": case_id,
                "stock_code": f"{index:04d}.HK",
                "cohort_year": 2024,
                "dataset_split": "validation",
                "model": "lightgbm",
                "feature_group": "PM",
                "poor_performer_score": 0.2,
                "score_semantics": "uncalibrated_model_score_not_probability",
                "classification_threshold": 0.5,
                "predicted_significant_drop_5d": False,
                "predicted_return_5d": 0.01,
                "actual_significant_drop_5d": False,
                "actual_return_5d": 0.02,
                "top_shap_drivers_json": "[]",
            }
            for index, case_id in enumerate(case_ids, start=1)
        ],
    )
    fields = ["case_id", "return_1d", "return_5d", "return_20d", "return_60d"]
    _csv(
        root / "multi_horizon_results.csv",
        fields,
        [
            {
                "case_id": case_id,
                "return_1d": 0.01,
                "return_5d": 0.02,
                "return_20d": 0.03,
                "return_60d": 0.04,
            }
            for case_id in case_ids
        ],
    )
    _json(
        root / "evaluation_summary.json",
        {
            "metric_protocol_version": "v045_competition_metric_protocol_v2_existing_gold_only",
            "blind_2025_y_accessed": False,
            "status": "complete",
            "role_d_m5_version": "v045_role_d_m5_handoff_v2",
            "evaluation_split": "2024_validation",
            "evaluation_count": 70,
            "horizons": ["1D", "5D", "20D", "60D"],
            "significant_drop_5d_definition": "return_5d <= -0.10",
            "score_semantics": "uncalibrated_model_score_not_probability",
            "threshold_or_model_retuned_on_validation": False,
            "source_hashes": {"market": "cd" * 32},
            "five_day_metrics": {
                "precision": 0.5,
                "recall": 0.5,
                "f1": 0.5,
                "pr_auc": 0.5,
                "roc_auc": 0.5,
                "top_10pct_hit_rate": 0.5,
                "top_20pct_hit_rate": 0.5,
                "base_prevalence": 0.5,
            },
        },
    )
    _json(
        root / "ai_vs_offline_report.json",
        {
            "comparison_scope": "same_2024_validation_full_production_PM",
            "ai_model": {
                "name": "frozen_lightgbm",
                "score_semantics": "uncalibrated_model_score_not_probability",
                "metrics": {
                    "precision": 0.5,
                    "recall": 0.5,
                    "f1": 0.5,
                    "pr_auc": 0.5,
                    "roc_auc": 0.5,
                    "top_10pct_hit_rate": 0.5,
                    "top_20pct_hit_rate": 0.5,
                    "base_prevalence": 0.5,
                },
            },
            "offline_baseline": {
                "name": "frozen_logistic_regression",
                "metrics": {},
            },
            "interpretation_policy": "descriptive_only_no_validation_retuning",
            "threshold_or_model_retuned_on_validation": False,
            "blind_2025_y_accessed": False,
        },
    )


def _case_payload(case_id: str, stock_code: str, listing_date: str, digest: str) -> dict:
    request_id = str(uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date}:{digest}"))
    return {
        "case_id": case_id,
        "stock_code": stock_code,
        "listing_date": listing_date,
        "status": "completed",
        "deterministic_request_id": request_id,
        "parsed_chunk_count": 100,
        "final_supervision_content_hash": "ab" * 32,
        "channel_states": {"document": "available", "market": "available", "model": "unavailable", "rule": "available"},
        "gate_e1": {"satisfied": True},
        "traceability": {"overall_traceability": 1.0},
        "prospectus_verification": {"sha256": digest},
        "creates_no_new_risk": True,
        "probability_claimed": False,
    }


def _role_e(root: Path, gate_satisfied: bool = True) -> None:
    cases = []
    for index, (case_id, stock_code, listing_date) in enumerate(
        (
            ("ipo_2024_02410", "2410.HK", "2024-08-20"),
            ("ipo_2024_02460", "2460.HK", "2024-10-23"),
            ("ipo_2024_01318", "1318.HK", "2024-12-10"),
        ),
        start=1,
    ):
        digest = f"{index:02x}" * 32
        case = _case_payload(case_id, stock_code, listing_date, digest)
        case["gate_e1"] = {"satisfied": gate_satisfied}
        cases.append(case)
        case_root = root / case_id
        verification = {
            "sha256": digest,
            "sha256_matches_frozen_catalog": True,
            "size_matches_frozen_catalog": True,
            "page_count_matches_frozen_catalog": True,
            "path_recorded": False,
        }
        sidecar = {
            "identity": {
                "run_id": f"run-{index}",
                "provenance": {
                    "workflow": "v04_competition",
                    "trace_schema_version": "v04_e_agent_trace_v1",
                    "conflict_policy_version": "v04_e_conflict_policy_v1",
                    "recheck_policy_version": "v04_e_recheck_policy_v1",
                },
            },
            "trace_events": [
                {
                    "event_id": f"market-{index}",
                    "event_type": "market",
                    "agent_name": "market_intelligence",
                    "tool_or_skill": "IPOHeatSkill",
                    "evidence_ids": ["market_feature:hsi"],
                    "calculation_ids": [],
                    "details": {},
                },
                {
                    "event_id": f"conflict-{index}",
                    "event_type": "conflict",
                    "agent_name": "conflict_detector",
                    "action": "detect_cross_agent_conflict",
                    "tool_or_skill": "deterministic_conflict_policy",
                    "evidence_ids": ["ev-1"],
                    "calculation_ids": [],
                    "details": {},
                },
                {
                    "event_id": f"recheck-{index}",
                    "event_type": "retriever",
                    "agent_name": "targeted_recheck",
                    "action": "targeted_re_retrieval",
                    "tool_or_skill": "keyword",
                    "evidence_ids": ["ev-1"],
                    "calculation_ids": [],
                    "recheck_id": f"recheck-{index}",
                    "details": {},
                },
                {
                    "event_id": f"verifier-{index}",
                    "event_type": "verifier",
                    "agent_name": "targeted_recheck",
                    "action": "verifier_challenge",
                    "tool_or_skill": "specialized_v03",
                    "evidence_ids": ["ev-1"],
                    "calculation_ids": [],
                    "details": {},
                },
                {
                    "event_id": f"final-{index}",
                    "event_type": "llm",
                    "agent_name": "llm_final_supervisor",
                    "action": "final_supervision",
                    "tool_or_skill": "LLMProvider.generate_structured",
                    "provider_name": "openai_responses",
                    "model_name": "model",
                    "prompt_version": "v04_final_supervision_v1",
                    "request_id": f"req-{index}",
                    "raw_response_hash": "cd" * 32,
                    "latency_ms": 50,
                    "evidence_ids": ["ev-1"],
                    "calculation_ids": [],
                    "details": {},
                },
            ],
        }
        gate = {
            "satisfied": gate_satisfied,
            "successful_llm_arbitration": gate_satisfied,
            "deterministic_fallback_used": not gate_satisfied,
            "provider_is_real_remote": True,
            "provider_trace": {
                "provider_name": "openai_responses",
                "model_name": "model",
                "prompt_version": "v04_final_supervision_v1",
                "request_id": f"req-{index}",
                "raw_response_hash": "cd" * 32,
                "latency_ms": 50,
            },
            "out_of_scope_reference_check": {
                "status": "passed" if gate_satisfied else "not_applicable",
                "out_of_scope_reference_count": 0 if gate_satisfied else None,
            },
            "severity_floor_respected": True if gate_satisfied else None,
        }
        market_context = {
            "status": "available",
            "observations": [
                {
                    "name": "recent_ipo_break_rate",
                    "value": 0.3,
                    "unit": "ratio",
                    "availability": "available",
                    "missing_reason": None,
                    "derivation": "governed fixture",
                    "source": "governed_test",
                }
            ],
            "provenance": {
                "feature_pipeline": "governed_pr_b_core",
                "case_id": case_id,
                "stock_code": stock_code,
                "listing_date": listing_date,
                "dataset_split": "validation",
                "artifact_content_hash": "de" * 32,
                "cutoff_semantics": "strictly_before_target_listing_date",
                "source_provenance": {"official_bridge_sha256": "bc" * 32},
                "extended_readiness_sha256": None,
            },
        }
        analysis = {
            "metadata": {
                "market_context": market_context,
                "market_intelligence": {
                    "market_regime": {"missingness": {"hsi_return_5d": "source_unavailable"}},
                    "interpretation": {
                        "summary": "Governed market context is available.",
                        "key_drivers": [
                            {
                                "statement": "Recent IPO conditions are governed.",
                                "source_feature_ids": ["recent_ipo_break_rate"],
                            }
                        ],
                    },
                },
                "final_supervision": {
                    "channel_states": [
                        {"channel": "market", "status": "available", "reason": "governed"}
                    ],
                    "market_context": market_context,
                },
            }
        }
        final_supervision = {
            "composition": {"summary": "governed fixture"},
            "llm_synthesis": {
                "outcome": "accepted" if gate_satisfied else "provider_call_failed",
                "call": gate["provider_trace"],
            },
        }
        for name in ROLE_E_CASE_REQUIRED:
            if name == "prospectus_verification.json":
                _json(case_root / name, verification)
            elif name == "trace_sidecar.json":
                _json(case_root / name, sidecar)
            elif name == "gate_e1_evidence.json":
                _json(case_root / name, gate)
            elif name == "final_supervision.json":
                _json(case_root / name, final_supervision)
            elif name == "analysis_result.json":
                _json(case_root / name, analysis)
            elif name.endswith(".json"):
                _json(case_root / name, {})
            else:
                (case_root / name).parent.mkdir(parents=True, exist_ok=True)
                (case_root / name).write_text("recorded artifact\n", encoding="utf-8")
    _json(
        root / "summary.json",
        {
            "code_base_sha": "12" * 20,
            "cases_manifest_sha256": "34" * 32,
            "config_sha256": "56" * 32,
            "declared_case_count": 3,
            "executed_case_count": 3,
            "all_prospectus_sha256_verified": True,
            "blind_2025_y_accessed": False,
            "outcome_labels_accessed": False,
            "gate_e1": {"satisfied": gate_satisfied},
            "cases": cases,
        },
    )
    _json(
        root / "explanation_quality.json",
        {
            "metric_protocol_version": "v045_competition_metric_protocol_v2_existing_gold_only",
            "declared_case_count": 3,
            "reviewed_case_count": 3,
            "mean_score": 4.0,
            "min_case_score": 4.0,
            "satisfied": True,
            "unmet_conditions": [],
            "cases": [
                {
                    "case_id": case["case_id"],
                    "human_reviewer_count": 2,
                    "passed": True,
                    "reviews": [
                        {"reviewer_id": "reviewer_1", "reviewer_kind": "human"},
                        {"reviewer_id": "reviewer_2", "reviewer_kind": "human"},
                    ],
                }
                for case in cases
            ],
        },
    )
    _json(root / "market_final_matrix_validation.json", {"satisfied": True, "cases": cases})


def _ready_tree(tmp_path: Path):
    repo = tmp_path / "repo"
    b = tmp_path / "b"
    d = tmp_path / "d"
    e = tmp_path / "e"
    a = tmp_path / "a"
    _repo(repo)
    _role_b(b)
    _role_d(d)
    _role_e(e)
    return repo, b, d, e, a


def _build_finalized(repo: Path, b: Path, d: Path, e: Path, a: Path):
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        latest_main_ci_passed=True,
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    first_index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    finalize_readiness_with_artifact_index(readiness, first_index)
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    before = json.dumps(readiness, ensure_ascii=False, sort_keys=True)
    finalize_readiness_with_artifact_index(readiness, index)
    assert json.dumps(readiness, ensure_ascii=False, sort_keys=True) == before
    write_artifact_index(a / "artifact_index.json", index)
    return readiness, blind, provenance, determinism, index


def test_all_governed_handoffs_produce_competition_ready(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    readiness, blind, provenance, determinism, index = _build_finalized(repo, b, d, e, a)
    assert readiness["competition_ready"] is True
    assert readiness["verdict"] == "COMPETITION_READY"
    assert blind["passed"] is True
    assert provenance["passed"] is True
    assert determinism["passed"] is True
    assert all(gate["passed"] for gate in readiness["gates"])
    assert index["passed"] is True


def test_unaccepted_real_provider_gate_blocks_submission(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _role_e(e, gate_satisfied=False)
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    assert readiness["competition_ready"] is False
    assert any("Gate E1" in blocker for blocker in readiness["blockers"])


def test_missing_multi_horizon_column_blocks_d(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _csv(d / "multi_horizon_results.csv", ["case_id", "return_1d"], {"case_id": "c", "return_1d": 0.01})
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    assert readiness["competition_ready"] is False
    d_gate = next(item for item in readiness["gates"] if item["owner"] == "D")
    assert d_gate["passed"] is False
    assert "return_60d" in " ".join(d_gate["blockers"])


def test_missing_ai_vs_offline_report_blocks_d(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    (d / "ai_vs_offline_report.json").unlink()
    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    d_gate = next(item for item in readiness["gates"] if item["owner"] == "D")
    assert d_gate["passed"] is False
    assert "ai_vs_offline_report.json" in " ".join(d_gate["blockers"])


def test_role_d_requires_exact_70_case_validation_handoff(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    prediction_path = d / "test_predictions.csv"
    with prediction_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)[:-1]
        fieldnames = list(reader.fieldnames or ())
    _csv(prediction_path, fieldnames, rows)
    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    d_gate = next(item for item in readiness["gates"] if item["owner"] == "D")
    assert d_gate["passed"] is False
    assert any("exactly 70" in item for item in d_gate["blockers"])


def test_role_d_rejects_probability_semantics_and_incomplete_comparison(
    tmp_path: Path,
) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    summary_path = d / "evaluation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["score_semantics"] = "probability"
    _json(summary_path, summary)
    comparison_path = d / "ai_vs_offline_report.json"
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    comparison["comparison_scope"] = "different_cases"
    _json(comparison_path, comparison)
    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    d_gate = next(item for item in readiness["gates"] if item["owner"] == "D")
    assert d_gate["passed"] is False
    assert any("non-probability" in item for item in d_gate["blockers"])


def test_legacy_role_b_pass_bools_cannot_replace_metric_v2_measurement(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    path = b / "document_benchmark_summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["risk_target_at_least_80_percent"] = True
    summary["evidence_target_at_least_85_percent"] = True
    summary["risk_extraction"]["official_aligned_accuracy"] = 0.79
    summary["evidence_coverage"]["coverage_recall"] = 0.84
    _json(path, summary)

    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    b_gate = next(item for item in readiness["gates"] if item["owner"] == "B")
    assert b_gate["passed"] is False
    assert any("M1" in item for item in b_gate["blockers"])
    assert any("M2" in item for item in b_gate["blockers"])


def test_missing_m4_human_review_artifact_blocks_e(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    (e / "explanation_quality.json").unlink()
    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    e_gate = next(item for item in readiness["gates"] if item["owner"] == "E")
    assert e_gate["passed"] is False
    assert any("M4" in item for item in e_gate["blockers"])


def test_market_missing_feature_cannot_be_zero_filled(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    path = e / "ipo_2024_02410" / "analysis_result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    result["metadata"]["market_context"]["observations"].append(
        {
            "name": "hsi_return_5d",
            "value": 0,
            "unit": "ratio",
            "availability": "available",
            "missing_reason": None,
            "derivation": "invalid zero fill",
            "source": "test",
        }
    )
    _json(path, result)

    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    c_gate = next(item for item in readiness["gates"] if item["owner"] == "C")
    assert c_gate["passed"] is False
    case = next(item for item in c_gate["details"]["cases"] if item["case_id"] == "ipo_2024_02410")
    assert case["zero_fill_detected"] is True


def test_traceability_below_one_cannot_pass_e(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    path = e / "summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["cases"][0]["traceability"]["overall_traceability"] = 0.99
    _json(path, summary)
    readiness, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    e_gate = next(item for item in readiness["gates"] if item["owner"] == "E")
    assert e_gate["passed"] is False
    assert any("traceability" in item for item in e_gate["blockers"])


def test_blind_access_flag_blocks_readiness(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    path = d / "evaluation_summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["blind_2025_y_accessed"] = True
    _json(path, summary)
    readiness, blind, *_ = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    assert blind["passed"] is False
    assert readiness["competition_ready"] is False


def test_empty_provider_trace_identity_cannot_pass_e_or_determinism(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    path = e / "ipo_2024_02410" / "gate_e1_evidence.json"
    gate = json.loads(path.read_text(encoding="utf-8"))
    gate["provider_trace"]["raw_response_hash"] = ""
    _json(path, gate)

    readiness, _, _, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        latest_main_ci_passed=True,
    )
    e_gate = next(item for item in readiness["gates"] if item["owner"] == "E")
    assert e_gate["passed"] is False
    assert e_gate["details"]["cases"][0]["provider_trace_complete"] is False
    assert determinism["passed"] is False


def test_latest_main_ci_requires_an_explicit_attestation(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    a_gate = next(item for item in readiness["gates"] if item["owner"] == "A")
    assert a_gate["passed"] is False
    assert any("latest-main CI" in item for item in a_gate["blockers"])


def test_missing_required_source_keeps_artifact_index_and_readiness_closed(
    tmp_path: Path,
) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    (repo / "CHANGELOG.md").unlink()
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        latest_main_ci_passed=True,
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    finalize_readiness_with_artifact_index(readiness, index)
    assert index["passed"] is False
    assert "source/CHANGELOG.md" in index["missing"]
    assert readiness["competition_ready"] is False
    assert any("artifact index is not PASS" in item for item in readiness["blockers"])


def test_duplicate_ai_vs_offline_handoffs_are_rejected(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _json(
        b / "ai_vs_offline_report.json",
        {"comparison": "duplicate", "blind_2025_outcome_accessed": False},
    )
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        latest_main_ci_passed=True,
    )
    a_gate = next(item for item in readiness["gates"] if item["owner"] == "A")
    assert a_gate["details"]["security_audit_passed"] is False
    index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    assert "artifacts/evaluation/ai_vs_offline_report.json" in index[
        "duplicate_logical_paths"
    ]


def test_audit_writer_and_index_hash_real_files(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _, _, _, _, index = _build_finalized(repo, b, d, e, a)
    assert index["artifact_count"] > 20
    assert all(len(item["sha256"]) == 64 for item in index["artifacts"])


def test_the_audits_never_write_the_local_path_their_own_packager_forbids(
    tmp_path: Path,
) -> None:
    """The tooling must not refuse its own output.

    The audits are packaged and shipped, and the packager rejects any artifact
    carrying a local absolute path. Recording the role directories verbatim made
    that self-contradictory whenever the dirs were passed as absolute paths --
    which is exactly what a run outside the working tree does. The scan itself is
    the oracle here, so the producer and the check cannot drift apart again.
    """
    repo, b, d, e, a = _ready_tree(tmp_path)
    assert b.is_absolute(), "the fixture must exercise absolute role directories"

    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    for written in sorted(a.glob("*.json")):
        assert _scan_path_for_sensitive_material(written) == [], written.name


def test_packager_refuses_before_competition_ready(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    a.mkdir(parents=True, exist_ok=True)
    _json(a / "submission_readiness.json", {"competition_ready": False})
    with pytest.raises(RuntimeError, match="COMPETITION_READY"):
        package_submission_bundle(
            repo_root=repo,
            role_b_dir=b,
            role_d_dir=d,
            role_e_dir=e,
            a_output_dir=a,
            output_zip=tmp_path / "submission.zip",
        )


def test_require_ready_cli_returns_nonzero_when_a_hard_gate_is_missing(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    (e / "explanation_quality.json").unlink()
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_v045_submission_readiness.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo-root",
            str(repo),
            "--role-b-dir",
            str(b),
            "--role-d-dir",
            str(d),
            "--role-e-dir",
            str(e),
            "--output-dir",
            str(a),
            "--latest-main-ci-passed",
            "--require-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert '"competition_ready": false' in completed.stdout


def test_packager_refuses_an_artifact_changed_after_indexing(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _build_finalized(repo, b, d, e, a)
    with (b / "risk_benchmark.csv").open("a", encoding="utf-8") as handle:
        handle.write("changed,after,index\n")
    with pytest.raises(RuntimeError, match="hash/size mismatch"):
        package_submission_bundle(
            repo_root=repo,
            role_b_dir=b,
            role_d_dir=d,
            role_e_dir=e,
            a_output_dir=a,
            output_zip=tmp_path / "submission.zip",
        )


def test_security_scanner_rejects_sensitive_material_and_local_paths(tmp_path: Path) -> None:
    private_key = tmp_path / "credential.txt"
    private_key.write_text("-----BEGIN PRIVATE KEY-----\nnot-real\n", encoding="utf-8")
    bearer = tmp_path / "token.txt"
    bearer.write_text("Bearer " + "a" * 32, encoding="utf-8")
    local_path = tmp_path / "path.txt"
    local_path.write_text("C:\\Users\\someone\\private\\file.json", encoding="utf-8")
    licensed = tmp_path / "prospectus.pdf"
    licensed.write_bytes(b"not a real pdf")
    model = tmp_path / "unapproved.joblib"
    model.write_bytes(b"not a real model")
    env_file = tmp_path / ".ENV"
    env_file.write_text("KEY=value\n", encoding="utf-8")
    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * (5 * 1024 * 1024 + 1))

    assert "private-key material detected" in _scan_path_for_sensitive_material(private_key)
    assert "Bearer token-like secret detected" in _scan_path_for_sensitive_material(bearer)
    assert "local absolute path detected" in _scan_path_for_sensitive_material(local_path)
    assert any("forbidden licensed" in item for item in _scan_path_for_sensitive_material(licensed))
    assert any("model file" in item for item in _scan_path_for_sensitive_material(model))
    assert any("secret-bearing filename" in item for item in _scan_path_for_sensitive_material(env_file))
    assert "oversized file rejected from submission allowlist" in _scan_path_for_sensitive_material(
        oversized
    )


def test_packager_rejects_a_source_file_added_after_indexing(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _build_finalized(repo, b, d, e, a)
    added = repo / "src" / "added_after_index.py"
    added.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact index and package allowlist differ"):
        package_submission_bundle(
            repo_root=repo,
            role_b_dir=b,
            role_d_dir=d,
            role_e_dir=e,
            a_output_dir=a,
            output_zip=tmp_path / "submission.zip",
        )


def test_ready_packager_has_manifest_and_no_pdf(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _build_finalized(repo, b, d, e, a)
    manifest = package_submission_bundle(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        output_zip=tmp_path / "submission.zip",
    )
    assert manifest["competition_ready"] is True
    assert len(manifest["bundle_sha256"]) == 64
    with zipfile.ZipFile(tmp_path / "submission.zip") as archive:
        names = archive.namelist()
        assert "submission_manifest.json" in names
        assert not any(name.casefold().endswith(".pdf") for name in names)
        assert not any("data/explanation_quality/reviews.json" in name for name in names)
        assert not any("__pycache__" in name or name.startswith("tests/") for name in names)
        embedded = json.loads(archive.read("submission_manifest.json"))
        assert embedded["security"]["licensed_pdf_included"] is False
