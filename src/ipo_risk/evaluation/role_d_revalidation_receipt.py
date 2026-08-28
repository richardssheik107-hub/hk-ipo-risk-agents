"""Validate the immutable current-main Role-D revalidation receipt."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

RECEIPT_VERSION = "v045_role_d_current_main_revalidation_receipt_v1"
RECEIPT_STATUS = "current_main_strict_revalidation_pass"
EXPECTED_BASE_MAIN = "8211cc4a59e07529ad39faaa47ab3fcb35f565f5"
EXPECTED_ARTIFACT_SHA256 = {
    "test_predictions.csv": (
        "8521dabe3f976e5c532f55fe1571294eb9555ae644a32d524233680af74fa93a"
    ),
    "multi_horizon_results.csv": (
        "f2d3382f2618e3d328155e9a37e81cd01a156cfc0787c8bc42320237dbb56725"
    ),
    "evaluation_summary.json": (
        "9eb0568a9253c410c30f2183e1fa58606313620954b88500f1d3f7104cc073c2"
    ),
    "ai_vs_offline_report.json": (
        "e5fc17b93cc535fcd966bf78ef1aea4b74fa3c79da9577beb90ac76c7f25e197"
    ),
}
EXPECTED_PRODUCT_CASES = (
    "ipo_2024_02410",
    "ipo_2024_02460",
    "ipo_2024_01318",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_LOCAL_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:Users|home|mnt|tmp)/)")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def validate_role_d_revalidation_receipt(
    receipt_path: Path,
    *,
    pr_f_manifest_path: Path,
    pr_e_manifest_path: Path,
    metric_protocol_path: Path,
) -> dict[str, Any]:
    """Fail closed on receipt drift, unsafe governance, or binding drift."""

    blockers: list[str] = []
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool, message: str) -> None:
        checks[name] = bool(condition)
        if not condition:
            blockers.append(message)

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "passed": False,
            "verdict": "FAIL",
            "checks": checks,
            "blockers": [f"invalid current-main revalidation receipt: {exc}"],
        }
    if not isinstance(receipt, dict):
        return {
            "passed": False,
            "verdict": "FAIL",
            "checks": checks,
            "blockers": ["current-main revalidation receipt must be an object"],
        }

    source = _mapping(receipt.get("source"))
    check(
        "identity",
        receipt.get("receipt_version") == RECEIPT_VERSION
        and receipt.get("status") == RECEIPT_STATUS
        and source.get("repository")
        == "richardssheik107-hub/hk-ipo-risk-agents"
        and source.get("base_main_commit") == EXPECTED_BASE_MAIN,
        "receipt identity or base-main binding drifted",
    )
    evaluation = _mapping(receipt.get("evaluation"))
    check(
        "strict_acceptance",
        evaluation.get("gate") == "D1_multi_horizon_evaluation"
        and evaluation.get("verdict") == "PASS"
        and evaluation.get("case_count") == 70
        and tuple(evaluation.get("horizons") or ()) == (1, 5, 20, 60)
        and evaluation.get("acceptance_check_count")
        == evaluation.get("acceptance_pass_count")
        == 12,
        "strict D1 acceptance evidence drifted",
    )
    check(
        "artifact_hashes",
        receipt.get("artifact_sha256") == EXPECTED_ARTIFACT_SHA256,
        "canonical current-main artifact hashes drifted",
    )
    determinism = _mapping(receipt.get("determinism"))
    check(
        "determinism",
        determinism.get("same_directory_resume_byte_identical") is True
        and determinism.get("fresh_directory_rebuild_byte_identical") is True,
        "deterministic rebuild evidence is incomplete",
    )
    governance = _mapping(receipt.get("governance"))
    check(
        "governance",
        bool(governance)
        and all(value is False for value in governance.values()),
        "Role-D governance flags are unsafe",
    )
    handoff = _mapping(receipt.get("product_handoff"))
    handoff_hashes = _mapping(handoff.get("file_sha256"))
    check(
        "product_handoff",
        tuple(handoff.get("case_ids") or ()) == EXPECTED_PRODUCT_CASES
        and handoff.get("label_free") is True
        and handoff.get("validated") is True
        and len(handoff_hashes) == 4
        and all(_SHA256.fullmatch(str(value)) for value in handoff_hashes.values()),
        "final-three product handoff evidence drifted",
    )
    bindings = _mapping(receipt.get("input_bindings"))
    try:
        local_hashes = {
            "pr_f_frozen_manifest_sha256": _sha256(pr_f_manifest_path),
            "pr_e_frozen_manifest_sha256": _sha256(pr_e_manifest_path),
            "metric_protocol_sha256": _sha256(metric_protocol_path),
        }
    except OSError as exc:
        blockers.append(f"cannot read a committed binding: {exc}")
        local_hashes = {}
    check(
        "committed_bindings",
        bool(local_hashes)
        and all(bindings.get(name) == value for name, value in local_hashes.items()),
        "receipt does not match committed PR-E/PR-F/protocol bindings",
    )
    decision = _mapping(receipt.get("model_decision"))
    check(
        "model_decision_boundary",
        decision.get("decision_owner") == "A"
        and decision.get("status") == "pending_a_owned_promotion_review"
        and decision.get("recommended_review_option") == "promote_v2"
        and decision.get("frozen_pr_f_retained_until_decision") is True,
        "receipt overstates or changes the A-owned model decision",
    )
    check(
        "portable_receipt",
        _LOCAL_PATH.search(json.dumps(receipt, ensure_ascii=False)) is None,
        "receipt leaks a local absolute path",
    )
    passed = not blockers and all(checks.values())
    return {
        "receipt_version": receipt.get("receipt_version"),
        "passed": passed,
        "verdict": "PASS" if passed else "FAIL",
        "checks": checks,
        "blockers": blockers,
    }
