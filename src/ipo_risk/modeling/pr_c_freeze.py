"""Fail-closed acceptance checks for the formal PR-C materialization.

The materializer deliberately keeps large per-case artifacts outside Git.  This
module turns those artifacts into a small, reviewable freeze manifest only when
the complete governed 438-case Gate passes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ipo_risk.schemas.market import MarketDatasetSplit, MarketLabelAvailability
from ipo_risk.schemas.outcomes import (
    FiveDayOutcomePolicy,
    FiveDayOutcomeTarget,
    FrozenFiveDayThreshold,
)


PR_C_FREEZE_MANIFEST_VERSION = "v04_pr_c_freeze_manifest_v1"
EXPECTED_RAW_EOD_SHA256 = (
    "190e45ffb0e3b2708410d854bf9d59176816d4b1eea656b6ba1f27964c007152"
)
EXPECTED_OFFICIAL_BRIDGE_SHA256 = (
    "751de6968ad8935ad45a8cd2841adbdc498d2bce6bb87153a1930959f4f85198"
)
EXPECTED_UNAVAILABLE_CASE_IDS = (
    "ipo_2020_01248",
    "ipo_2020_06688",
    "ipo_2020_06813",
    "ipo_2021_01491",
    "ipo_2022_06678",
    "ipo_2022_07841",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing PR-C artifact: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid PR-C JSON artifact: {path.name}") from exc


@dataclass(frozen=True)
class PRCFreezeExpectations:
    """Measured invariants expected from one governed PR-C source snapshot."""

    official_case_count: int
    development_case_count: int
    validation_case_count: int
    available_count: int
    development_available_count: int
    validation_available_count: int
    unavailable_case_ids: tuple[str, ...]
    raw_eod_sha256: str
    official_bridge_sha256: str


FORMAL_PR_C_EXPECTATIONS = PRCFreezeExpectations(
    official_case_count=438,
    development_case_count=368,
    validation_case_count=70,
    available_count=432,
    development_available_count=362,
    validation_available_count=70,
    unavailable_case_ids=EXPECTED_UNAVAILABLE_CASE_IDS,
    raw_eod_sha256=EXPECTED_RAW_EOD_SHA256,
    official_bridge_sha256=EXPECTED_OFFICIAL_BRIDGE_SHA256,
)


def audit_pr_c_freeze(
    output_dir: Path,
    *,
    expectations: PRCFreezeExpectations = FORMAL_PR_C_EXPECTATIONS,
) -> dict[str, Any]:
    """Validate a complete materialization and return a compact freeze manifest."""

    policy_payload = _read_json(output_dir / "frozen_threshold_policy.json")
    run_manifest = _read_json(output_dir / "run_manifest.json")
    coverage_payload = _read_json(output_dir / "coverage.json")
    reproducibility = _read_json(output_dir / "reproducibility_report.json")

    policy = FiveDayOutcomePolicy.model_validate(policy_payload.get("policy"))
    threshold = FrozenFiveDayThreshold.model_validate(
        policy_payload.get("threshold")
    )
    if policy_payload.get("policy_hash") != policy.content_hash():
        raise ValueError("PR-C policy hash mismatch")
    if threshold.policy_hash != policy.content_hash():
        raise ValueError("PR-C threshold was frozen under a different policy")
    if policy_payload.get("threshold_hash") != threshold.content_hash():
        raise ValueError("PR-C threshold hash mismatch")
    if policy_payload.get("threshold_fit_split") != "development":
        raise ValueError("PR-C threshold was not fitted on Development")
    if policy_payload.get("validation_used_for_threshold") is not False:
        raise ValueError("Validation was used for PR-C threshold fitting")
    if policy_payload.get("blind_used_for_threshold") is not False:
        raise ValueError("Blind was used for PR-C threshold fitting")

    summary = coverage_payload.get("summary")
    records = coverage_payload.get("records")
    if not isinstance(summary, dict) or not isinstance(records, list):
        raise ValueError("PR-C coverage artifact has an invalid shape")
    if run_manifest != summary:
        raise ValueError("PR-C run manifest and coverage summary disagree")
    if len(records) != expectations.official_case_count:
        raise ValueError("PR-C coverage does not contain all official cases")

    case_ids = [str(row.get("case_id", "")) for row in records]
    if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("PR-C coverage case IDs are not unique and ordered")
    if summary.get("coverage_content_hash") != _hash(records):
        raise ValueError("PR-C coverage content hash mismatch")

    split_counts = {
        split: sum(row.get("dataset_split") == split for row in records)
        for split in ("development", "validation")
    }
    available_by_split = {
        split: sum(
            row.get("dataset_split") == split
            and row.get("target_available") is True
            for row in records
        )
        for split in ("development", "validation")
    }
    unavailable_case_ids = tuple(
        sorted(
            str(row["case_id"])
            for row in records
            if row.get("target_status") == MarketLabelAvailability.UNAVAILABLE.value
        )
    )
    failed = [row for row in records if row.get("target_status") == "failed"]
    if failed or summary.get("failure_count") != 0:
        raise ValueError("PR-C formal freeze requires zero generation/build failures")
    if any(
        not row.get("missing_reason")
        for row in records
        if row.get("target_status") == MarketLabelAvailability.UNAVAILABLE.value
    ):
        raise ValueError("PR-C unavailable target is missing an explicit reason")
    if any(
        row.get("abnormal_return_status")
        != "unavailable_without_governed_benchmark"
        for row in records
    ):
        raise ValueError("PR-C abnormal-return policy drifted")

    expected_counts = {
        "official": expectations.official_case_count,
        "development": expectations.development_case_count,
        "validation": expectations.validation_case_count,
        "available": expectations.available_count,
        "development_available": expectations.development_available_count,
        "validation_available": expectations.validation_available_count,
    }
    actual_counts = {
        "official": len(records),
        "development": split_counts["development"],
        "validation": split_counts["validation"],
        "available": sum(row.get("target_available") is True for row in records),
        "development_available": available_by_split["development"],
        "validation_available": available_by_split["validation"],
    }
    if actual_counts != expected_counts:
        raise ValueError(
            f"PR-C measured coverage mismatch: expected={expected_counts}, "
            f"actual={actual_counts}"
        )
    if unavailable_case_ids != tuple(sorted(expectations.unavailable_case_ids)):
        raise ValueError("PR-C unavailable case IDs do not match the governed EOD audit")
    if threshold.development_sample_count != expectations.development_available_count:
        raise ValueError("PR-C threshold population does not match available Development")

    source_context = summary.get("source_context")
    if not isinstance(source_context, dict):
        raise ValueError("PR-C source context is missing")
    if source_context.get("raw_eod_sha256") != expectations.raw_eod_sha256:
        raise ValueError("PR-C raw EOD checksum does not match the governed source")
    if (
        source_context.get("official_bridge_sha256")
        != expectations.official_bridge_sha256
    ):
        raise ValueError("PR-C official bridge checksum mismatch")
    if source_context.get("blind_outcomes_included") is not False:
        raise ValueError("PR-C source context indicates Blind outcome access")
    if summary.get("blind_2025_y_accessed") is not False:
        raise ValueError("PR-C summary indicates Blind outcome access")

    if reproducibility.get("verify_determinism_requested") is not True:
        raise ValueError("PR-C determinism verification was not requested")
    if reproducibility.get("passed") is not True:
        raise ValueError("PR-C determinism verification did not pass")
    if reproducibility.get("mismatch_count") != 0:
        raise ValueError("PR-C determinism verification found mismatches")
    if reproducibility.get("checked_case_count") != expectations.official_case_count:
        raise ValueError("PR-C determinism did not check all official cases")
    if reproducibility.get("coverage_content_hash") != summary.get(
        "coverage_content_hash"
    ):
        raise ValueError("PR-C reproducibility coverage hash mismatch")

    target_dir = output_dir / "targets"
    target_paths = sorted(target_dir.glob("*.json")) if target_dir.is_dir() else []
    if len(target_paths) != expectations.official_case_count:
        raise ValueError("PR-C target artifact count does not match official coverage")
    coverage_by_case = {str(row["case_id"]): row for row in records}
    target_hashes: list[dict[str, str]] = []
    for path in target_paths:
        payload = _read_json(path)
        declared_hash = payload.pop("content_hash", None)
        target = FiveDayOutcomeTarget.model_validate(payload)
        if path.stem != target.case_id or target.case_id not in coverage_by_case:
            raise ValueError(f"PR-C target identity mismatch: {path.name}")
        content_hash = target.content_hash()
        row = coverage_by_case[target.case_id]
        if declared_hash != content_hash or row.get("target_hash") != content_hash:
            raise ValueError(f"PR-C target hash mismatch: {target.case_id}")
        if target.policy_hash != policy.content_hash():
            raise ValueError(f"PR-C target policy mismatch: {target.case_id}")
        if target.threshold_hash != threshold.content_hash():
            raise ValueError(f"PR-C target threshold mismatch: {target.case_id}")
        if target.dataset_split is MarketDatasetSplit.BLIND or target.cohort_year == 2025:
            raise ValueError("PR-C target directory contains a Blind row")
        target_hashes.append({"case_id": target.case_id, "content_hash": content_hash})

    manifest = {
        "manifest_version": PR_C_FREEZE_MANIFEST_VERSION,
        "gate_passed": True,
        "pr_c_version": summary.get("pr_c_version"),
        "target_schema_version": policy.target_schema_version,
        "policy_version": policy.version,
        "policy_hash": policy.content_hash(),
        "threshold_method": threshold.method.value,
        "threshold_quantile": str(threshold.quantile),
        "poor_performer_threshold": str(threshold.threshold),
        "threshold_hash": threshold.content_hash(),
        "threshold_fit_split": "development",
        "official_case_count": actual_counts["official"],
        "available_count": actual_counts["available"],
        "unavailable_count": len(unavailable_case_ids),
        "development_available_count": actual_counts["development_available"],
        "validation_available_count": actual_counts["validation_available"],
        "unavailable_case_ids": unavailable_case_ids,
        "failure_count": 0,
        "coverage_content_hash": summary.get("coverage_content_hash"),
        "target_set_hash": _hash(target_hashes),
        "determinism_checked_case_count": reproducibility.get("checked_case_count"),
        "determinism_mismatch_count": 0,
        "abnormal_return_status": "unavailable_without_governed_benchmark",
        "validation_used_for_threshold": False,
        "blind_2025_y_accessed": False,
        "source_revision": source_context.get("git_revision"),
        "raw_eod_sha256": source_context.get("raw_eod_sha256"),
        "official_bridge_sha256": source_context.get("official_bridge_sha256"),
    }
    manifest["freeze_manifest_hash"] = _hash(manifest)
    return manifest

