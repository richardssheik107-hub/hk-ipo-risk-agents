"""Validate the recorded Role-D M5 materialization receipt.

The licensed EOD archive and the full frozen PR-E/PR-F research runtimes are
intentionally not committed.  The receipt records the immutable evidence from
the governed external materialization, while this validator binds that record
to the committed frozen manifests and metric protocol.

A passing receipt is historical release evidence.  It is not a substitute for
``check_v045_role_d_m5.py`` when the external immutable inputs are available.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

RECEIPT_VERSION = "v045_role_d_m5_materialization_receipt_v1"
RECEIPT_STATUS = "recorded_external_materialization_pass"
EVIDENCE_CLASS = "recorded_external_materialization_receipt"
EXPECTED_REPOSITORY = "richardssheik107-hub/hk-ipo-risk-agents"
EXPECTED_PULL_REQUEST = 141
EXPECTED_MERGE_COMMIT = "2eb4bea6104e47c6472848d826e2572018909094"
EXPECTED_COMMENT_ID = 5438960640
EXPECTED_EVIDENCE_URL = (
    "https://github.com/richardssheik107-hub/hk-ipo-risk-agents/"
    "pull/141#issuecomment-5438960640"
)
EXPECTED_ARTIFACTS = (
    "test_predictions.csv",
    "multi_horizon_results.csv",
    "evaluation_summary.json",
    "ai_vs_offline_report.json",
)
EXPECTED_METRICS = (
    "precision",
    "recall",
    "f1",
    "pr_auc",
    "roc_auc",
    "top_10pct_hit_rate",
    "top_20pct_hit_rate",
    "base_prevalence",
)
EXPECTED_HORIZONS = (1, 5, 20, 60)
EXPECTED_CASE_COUNT = 70
EXPECTED_EOD_ROWS = 433_776
EXPECTED_EOD_CASES = 438
EXPECTED_RAW_EOD_SHA256 = (
    "190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152"
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"(?:^|\s)[A-Za-z]:[\\/]")
_UNIX_LOCAL_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])/(?:Users|home|mnt|private|tmp|var/folders)/[^\s\"']+"
)
_SECRET_KEYS = {"api_key", "authorization", "credential", "password", "secret", "token"}


def _load_json(path: Path, *, label: str, blockers: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append(f"{label} is missing: {path.as_posix()}")
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        blockers.append(f"{label} is unreadable or invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        blockers.append(f"{label} must be a JSON object")
        return None
    return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _recorded_at_is_valid(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _finite_unit_interval(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _has_local_absolute_path(value: str) -> bool:
    return bool(
        _WINDOWS_ABSOLUTE_PATH.search(value)
        or _UNIX_LOCAL_ABSOLUTE_PATH.search(value)
    )


def _walk_payload(
    value: Any,
    *,
    path: str = "$",
) -> tuple[list[str], list[str]]:
    absolute_paths: list[str] = []
    secret_values: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            child = f"{path}.{key_text}"
            if key_text.lower() in _SECRET_KEYS and item not in (None, "", False):
                secret_values.append(child)
            child_paths, child_secrets = _walk_payload(item, path=child)
            absolute_paths.extend(child_paths)
            secret_values.extend(child_secrets)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child_paths, child_secrets = _walk_payload(item, path=f"{path}[{index}]")
            absolute_paths.extend(child_paths)
            secret_values.extend(child_secrets)
    elif isinstance(value, str) and _has_local_absolute_path(value):
        absolute_paths.append(path)
    return absolute_paths, secret_values


def _normalized_pr_f_runtime_outputs(manifest: Mapping[str, Any]) -> dict[str, Any]:
    outputs = _mapping(manifest.get("runtime_outputs"))
    return {
        "run_manifest.json": outputs.get("run_manifest_sha256"),
        "model_results.json": outputs.get("model_results_sha256"),
        "model_comparison.json": outputs.get("model_comparison_sha256"),
    }


def _normalized_pr_e_runtime_outputs(manifest: Mapping[str, Any]) -> dict[str, Any]:
    outputs = _mapping(manifest.get("runtime_outputs"))

    def artifact_hash(name: str) -> Any:
        value = outputs.get(f"reports/v04_pr_e/{name}")
        return _mapping(value).get("sha256")

    return {
        "run_manifest.json": artifact_hash("run_manifest.json"),
        "baseline_results.json": artifact_hash("baseline_results.json"),
        "value_diagnostic.json": artifact_hash("value_diagnostic.json"),
    }


def validate_role_d_materialization_receipt(
    receipt_path: Path,
    *,
    pr_f_manifest_path: Path,
    pr_e_manifest_path: Path,
    metric_protocol_path: Path,
) -> dict[str, Any]:
    """Validate one immutable Role-D receipt against committed source-of-truth files."""

    blockers: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool, message: str) -> None:
        passed = bool(condition)
        checks[name] = passed
        if not passed:
            blockers.append(message)

    receipt = _load_json(receipt_path, label="Role-D receipt", blockers=blockers)
    pr_f = _load_json(pr_f_manifest_path, label="PR-F frozen manifest", blockers=blockers)
    pr_e = _load_json(pr_e_manifest_path, label="PR-E frozen manifest", blockers=blockers)
    protocol = _load_json(metric_protocol_path, label="metric protocol", blockers=blockers)
    if receipt is None or pr_f is None or pr_e is None or protocol is None:
        return {
            "receipt_version": None if receipt is None else receipt.get("receipt_version"),
            "status": "invalid",
            "verdict": "FAIL",
            "passed": False,
            "checks": checks,
            "blockers": blockers,
        }

    check(
        "receipt_version",
        receipt.get("receipt_version") == RECEIPT_VERSION,
        "unsupported Role-D receipt version",
    )
    check(
        "evidence_class",
        receipt.get("evidence_class") == EVIDENCE_CLASS,
        "Role-D receipt evidence_class is invalid",
    )
    check(
        "receipt_status",
        receipt.get("status") == RECEIPT_STATUS,
        "Role-D receipt status is not a recorded external materialization pass",
    )
    check(
        "recorded_at",
        _recorded_at_is_valid(receipt.get("recorded_at")),
        "Role-D receipt recorded_at must be an RFC3339 UTC timestamp",
    )

    source = _mapping(receipt.get("source"))
    check(
        "source_repository",
        source.get("repository") == EXPECTED_REPOSITORY,
        "Role-D receipt repository identity is invalid",
    )
    check(
        "source_pull_request",
        source.get("pull_request") == EXPECTED_PULL_REQUEST,
        "Role-D receipt pull-request identity is invalid",
    )
    check(
        "source_merge_commit",
        source.get("merge_commit") == EXPECTED_MERGE_COMMIT
        and _COMMIT_SHA.fullmatch(str(source.get("merge_commit") or "")) is not None,
        "Role-D receipt merge commit is invalid",
    )
    check(
        "source_comment",
        source.get("evidence_comment_id") == EXPECTED_COMMENT_ID
        and source.get("evidence_url") == EXPECTED_EVIDENCE_URL,
        "Role-D receipt evidence comment binding is invalid",
    )

    post_listing = _mapping(protocol.get("post_listing"))
    protocol_version = protocol.get("protocol_version")
    required_horizons = tuple(post_listing.get("required_horizons") or ())
    required_metrics = tuple(post_listing.get("five_day_metrics") or ())

    evaluation = _mapping(receipt.get("evaluation"))
    check(
        "evaluation_gate",
        evaluation.get("gate") == "D1_multi_horizon_evaluation"
        and evaluation.get("verdict") == "PASS",
        "Role-D receipt does not record D1_multi_horizon_evaluation=PASS",
    )
    check(
        "evaluation_split",
        evaluation.get("split") == "2024_validation",
        "Role-D receipt evaluation split must be 2024_validation",
    )
    check(
        "evaluation_case_count",
        evaluation.get("case_count") == EXPECTED_CASE_COUNT,
        "Role-D receipt evaluation case count must be 70",
    )
    check(
        "evaluation_horizons",
        tuple(evaluation.get("horizons") or ()) == EXPECTED_HORIZONS
        and required_horizons == EXPECTED_HORIZONS,
        "Role-D receipt/protocol horizons must be exactly 1D/5D/20D/60D",
    )
    check(
        "evaluation_primary_horizon",
        evaluation.get("primary_horizon") == post_listing.get("primary_horizon") == 5,
        "Role-D receipt/protocol primary horizon must be 5D",
    )
    check(
        "evaluation_label_definition",
        evaluation.get("significant_drop_5d_definition")
        == post_listing.get("significant_drop_5d_definition")
        == "return_5d <= -0.10",
        "Role-D receipt/protocol significant-drop definition drifted",
    )
    check(
        "official_threshold_policy",
        post_listing.get("official_absolute_metric_threshold_defined") is False,
        "metric protocol must explicitly state no official absolute M5 threshold",
    )

    bindings = _mapping(receipt.get("input_bindings"))
    protocol_binding = _mapping(bindings.get("metric_protocol"))
    check(
        "metric_protocol_binding",
        protocol_binding.get("path") == "configs/v045_competition_metric_protocol.json"
        and protocol_binding.get("protocol_version") == protocol_version,
        "Role-D receipt metric-protocol binding is invalid",
    )

    pr_f_binding = _mapping(bindings.get("pr_f"))
    pr_f_cohort = _mapping(_mapping(pr_f.get("cohorts")).get("full_production"))
    pr_f_semantics = _mapping(pr_f.get("formal_conclusion")).get("score_semantics")
    check(
        "pr_f_manifest_state",
        pr_f.get("status") == "complete_frozen"
        and pr_f.get("formal_gate_passed") is True
        and pr_f.get("blind_2025_y_accessed") is False,
        "PR-F frozen manifest is not complete, gate-passed, and Blind-safe",
    )
    check(
        "pr_f_binding",
        pr_f_binding.get("manifest_path") == "reports/frozen/v04_pr_f_lightgbm_manifest.json"
        and pr_f_binding.get("execution_revision") == pr_f.get("execution_revision")
        and pr_f_binding.get("development_count") == pr_f_cohort.get("development") == 354
        and pr_f_binding.get("validation_count") == pr_f_cohort.get("validation") == EXPECTED_CASE_COUNT
        and pr_f_binding.get("score_semantics") == pr_f_semantics
        == "uncalibrated_model_score_not_probability"
        and pr_f_binding.get("model_result_hash") == pr_f.get("model_result_hash")
        and pr_f_binding.get("runtime_outputs") == _normalized_pr_f_runtime_outputs(pr_f),
        "Role-D receipt PR-F binding does not match the frozen manifest",
    )
    check(
        "pr_f_hash_shapes",
        _valid_sha256(pr_f.get("model_result_hash"))
        and all(_valid_sha256(value) for value in _normalized_pr_f_runtime_outputs(pr_f).values()),
        "PR-F frozen hashes are malformed",
    )

    pr_e_binding = _mapping(bindings.get("pr_e"))
    pr_e_cohort = _mapping(_mapping(pr_e.get("cohorts")).get("full_production"))
    check(
        "pr_e_manifest_state",
        pr_e.get("status") == "complete_frozen"
        and pr_e.get("formal_gate_passed") is True
        and pr_e.get("blind_2025_y_accessed") is False,
        "PR-E frozen manifest is not complete, gate-passed, and Blind-safe",
    )
    check(
        "pr_e_binding",
        pr_e_binding.get("manifest_path") == "reports/frozen/v04_pr_e_baseline_manifest.json"
        and pr_e_binding.get("execution_revision") == pr_e.get("execution_revision")
        and pr_e_binding.get("development_count") == pr_e_cohort.get("development") == 354
        and pr_e_binding.get("validation_count") == pr_e_cohort.get("validation") == EXPECTED_CASE_COUNT
        and pr_e_binding.get("results_hash") == pr_e.get("results_hash")
        and pr_e_binding.get("diagnostic_hash") == pr_e.get("diagnostic_hash")
        and pr_e_binding.get("runtime_outputs") == _normalized_pr_e_runtime_outputs(pr_e),
        "Role-D receipt PR-E binding does not match the frozen manifest",
    )
    check(
        "pr_e_hash_shapes",
        _valid_sha256(pr_e.get("results_hash"))
        and _valid_sha256(pr_e.get("diagnostic_hash"))
        and all(_valid_sha256(value) for value in _normalized_pr_e_runtime_outputs(pr_e).values()),
        "PR-E frozen hashes are malformed",
    )

    eod = _mapping(bindings.get("governed_eod"))
    check(
        "governed_eod_binding",
        eod.get("source_filename") == "hkshareeodprices.csv"
        and eod.get("source_sha256") == EXPECTED_RAW_EOD_SHA256
        and eod.get("filtered_store_row_count") == EXPECTED_EOD_ROWS
        and eod.get("target_ipo_count") == EXPECTED_EOD_CASES,
        "Role-D receipt governed EOD binding does not match the recorded materialization",
    )

    artifacts = _mapping(receipt.get("artifact_sha256"))
    check(
        "artifact_contract",
        set(artifacts) == set(EXPECTED_ARTIFACTS)
        and all(_valid_sha256(artifacts.get(name)) for name in EXPECTED_ARTIFACTS),
        "Role-D receipt must bind exactly four canonical artifact SHA-256 values",
    )

    metrics = _mapping(receipt.get("five_day_metrics"))
    check(
        "metric_contract",
        set(metrics) == set(EXPECTED_METRICS)
        and required_metrics == EXPECTED_METRICS
        and all(_finite_unit_interval(metrics.get(name)) for name in EXPECTED_METRICS),
        "Role-D receipt metric set or value range is invalid",
    )

    governance = _mapping(receipt.get("governance"))
    expected_governance = {
        "blind_2025_y_accessed": False,
        "validation_retuning_performed": False,
        "pr_e_retrained": False,
        "pr_f_retrained": False,
        "score_direction_inverted": False,
        "score_calibrated": False,
        "score_called_probability": False,
        "substitute_market_data_used": False,
        "missing_market_data_fake_filled": False,
        "runtime_artifacts_committed": False,
        "licensed_eod_committed": False,
        "deterministic_resume": "passed_byte_identical",
    }
    check(
        "governance",
        dict(governance) == expected_governance,
        "Role-D receipt governance declarations are incomplete or unsafe",
    )

    limitations = _mapping(receipt.get("limitations"))
    expected_limitations = {
        "evidence_is_recorded_not_live_rerun": True,
        "external_immutable_inputs_required_for_live_rerun": True,
        "receipt_substitutes_for_strict_checker": False,
        "fresh_directory_rebuild_recorded": False,
        "final_three_product_handoff_materialized": False,
        "v2_candidate_promoted": False,
    }
    check(
        "limitations",
        dict(limitations) == expected_limitations,
        "Role-D receipt limitations must preserve the recorded-vs-live evidence boundary",
    )

    absolute_paths, secret_values = _walk_payload(receipt)
    check(
        "no_absolute_local_paths",
        not absolute_paths,
        "Role-D receipt contains local absolute paths: " + ", ".join(absolute_paths),
    )
    check(
        "no_secrets",
        not secret_values,
        "Role-D receipt contains secret-like values: " + ", ".join(secret_values),
    )

    return {
        "receipt_version": receipt.get("receipt_version"),
        "status": receipt.get("status"),
        "verdict": "PASS" if not blockers else "FAIL",
        "passed": not blockers,
        "checks": checks,
        "blockers": blockers,
        "recorded_at": receipt.get("recorded_at"),
        "evaluation_case_count": evaluation.get("case_count"),
        "artifact_count": len(artifacts),
        "metric_count": len(metrics),
        "evidence_url": source.get("evidence_url"),
    }
