"""Deterministic PR-D bindings for frozen bulk upstream artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ipo_risk.modeling.canonical_dataset import (
    load_target_artifact,
    market_core_block,
    oracle_document_block,
    production_document_block,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash


PR_D_INPUT_BINDING_VERSION = "v04_pr_d_input_binding_v1"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"input_binding invalid_json path={path.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"input_binding expected_object path={path.name}")
    return payload


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_identity(path: Path) -> dict[str, str]:
    return {"filename": path.name, "sha256": _file_sha256(path)}


def _feature_order_hash(payload: Mapping[str, Any]) -> str:
    return canonical_hash(list(payload.get("feature_names") or ()))


def _case_files(directory: Path, *, component: str) -> list[Path]:
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError(f"input_binding component={component} category=empty_artifact_set")
    return paths


def _component_identity(
    directory: Path,
    *,
    component: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    identities: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for path in _case_files(directory, component=component):
        payload = _read_json(path)
        case_id = str(payload.get("case_id") or "")
        if not case_id:
            raise ValueError(
                f"input_binding component={component} category=missing_case_id file={path.name}"
            )
        if path.stem != case_id:
            raise ValueError(
                f"input_binding component={component} category=filename_case_mismatch "
                f"file={path.name} case_id={case_id}"
            )
        if case_id in seen:
            raise ValueError(
                f"input_binding component={component} category=duplicate_case case_id={case_id}"
            )
        seen.add(case_id)
        if component == "production_document":
            block = production_document_block(payload)
            schema_version = block.schema_version
            policy_version = None
            manifest_hash = block.manifest_hash
            feature_order_hash = _feature_order_hash(payload)
            content_hash = block.artifact_hash
        elif component == "market_core":
            block = market_core_block(payload)
            schema_version = block.schema_version
            policy_version = block.policy_version
            manifest_hash = block.manifest_hash
            feature_order_hash = _feature_order_hash(payload)
            content_hash = block.artifact_hash
        elif component == "oracle_document":
            block = oracle_document_block(payload)
            schema_version = block.schema_version
            policy_version = block.policy_version
            manifest_hash = block.manifest_hash
            feature_order_hash = _feature_order_hash(payload)
            content_hash = block.artifact_hash
        elif component == "outcome_target":
            target = load_target_artifact(payload)
            schema_version = str(payload.get("schema_version") or "v04_5d_outcome_target_v1")
            policy_version = str(payload.get("policy_version") or "v04_5d_outcome_policy_v1")
            manifest_hash = target.policy_hash
            feature_order_hash = None
            content_hash = target.content_hash()
        else:  # pragma: no cover - internal caller invariant
            raise ValueError(f"unknown binding component: {component}")
        entry = {
            "case_id": case_id,
            "schema_version": schema_version,
            "policy_version": policy_version,
            "manifest_hash": manifest_hash,
            "feature_order_hash": feature_order_hash,
            "content_hash": content_hash,
        }
        entries.append(entry)
        identities[case_id] = {
            "case_id": case_id,
            "stock_code": payload.get("stock_code"),
            "cohort_year": payload.get("cohort_year"),
            "listing_date": payload.get("listing_date"),
            "dataset_split": payload.get("dataset_split"),
        }
    entries.sort(key=lambda item: item["case_id"])
    case_ids = [item["case_id"] for item in entries]
    return (
        {
            "component": component,
            "count": len(entries),
            "case_set_hash": canonical_hash(case_ids),
            "identity_set_hash": canonical_hash(
                [identities[case_id] for case_id in case_ids]
            ),
            "artifact_set_hash": canonical_hash(entries),
        },
        identities,
    )


def _verify_pr_c_manifest(pr_c: Mapping[str, Any]) -> None:
    declared = pr_c.get("freeze_manifest_hash")
    actual = canonical_hash(
        {key: value for key, value in pr_c.items() if key != "freeze_manifest_hash"}
    )
    if declared != actual:
        raise ValueError(
            "input_binding component=outcome_target category=freeze_manifest_hash_mismatch "
            f"expected={declared} actual={actual}"
        )


def build_pr_d_input_binding(
    *,
    production_dir: Path,
    market_core_dir: Path,
    target_dir: Path,
    oracle_dir: Path | None,
    pr_a_manifest_path: Path,
    pr_b_manifest_path: Path,
    pr_c_manifest_path: Path,
) -> dict[str, Any]:
    """Build and validate a path-independent binding for PR-D inputs."""

    pr_c = _read_json(pr_c_manifest_path)
    _verify_pr_c_manifest(pr_c)
    production, production_ids = _component_identity(
        production_dir, component="production_document"
    )
    market, market_ids = _component_identity(market_core_dir, component="market_core")
    targets, target_ids = _component_identity(target_dir, component="outcome_target")
    components = [production, market, targets]
    official_ids = set(production_ids)
    for component, identities in ((market, market_ids), (targets, target_ids)):
        actual_ids = set(identities)
        if actual_ids != official_ids:
            missing = sorted(official_ids - actual_ids)
            orphan = sorted(actual_ids - official_ids)
            raise ValueError(
                f"input_binding component={component['component']} category=case_set_mismatch "
                f"missing={missing[:3]} orphan={orphan[:3]}"
            )
        mismatched = [
            case_id
            for case_id in sorted(official_ids)
            if identities[case_id] != production_ids[case_id]
        ]
        if mismatched:
            raise ValueError(
                f"input_binding component={component['component']} category=identity_mismatch "
                f"case_id={mismatched[0]}"
            )
    if len(official_ids) != pr_c.get("official_case_count"):
        raise ValueError(
            "input_binding category=official_count_mismatch "
            f"expected={pr_c.get('official_case_count')} actual={len(official_ids)}"
        )
    target_entries = []
    policy_hashes: set[str] = set()
    threshold_hashes: set[str] = set()
    for path in _case_files(target_dir, component="outcome_target"):
        payload = _read_json(path)
        target = load_target_artifact(payload)
        target_entries.append({"case_id": target.case_id, "content_hash": target.content_hash()})
        policy_hashes.add(target.policy_hash)
        threshold_hashes.add(target.threshold_hash)
    recomputed_target_set_hash = canonical_hash(sorted(target_entries, key=lambda x: x["case_id"]))
    if recomputed_target_set_hash != pr_c.get("target_set_hash"):
        raise ValueError(
            "input_binding component=outcome_target category=target_set_hash_mismatch "
            f"expected={pr_c.get('target_set_hash')} actual={recomputed_target_set_hash}"
        )
    if policy_hashes != {pr_c.get("policy_hash")}:
        raise ValueError("input_binding component=outcome_target category=policy_hash_drift")
    if threshold_hashes != {pr_c.get("threshold_hash")}:
        raise ValueError("input_binding component=outcome_target category=threshold_hash_drift")
    oracle_status: dict[str, Any] = {"status": "not_supplied"}
    if oracle_dir is not None:
        oracle, _ = _component_identity(oracle_dir, component="oracle_document")
        oracle_status = oracle | {"status": "historical_pr_a_frozen_snapshot"}
    body: dict[str, Any] = {
        "binding_version": PR_D_INPUT_BINDING_VERSION,
        "official_case_count": len(official_ids),
        "official_case_set_hash": production["case_set_hash"],
        "official_identity_set_hash": production["identity_set_hash"],
        "upstream_manifests": {
            "pr_a": _manifest_identity(pr_a_manifest_path),
            "pr_b": _manifest_identity(pr_b_manifest_path),
            "pr_c": _manifest_identity(pr_c_manifest_path),
        },
        "components": {item["component"]: item for item in components},
        "pr_c_freeze_manifest_hash": pr_c["freeze_manifest_hash"],
        "pr_c_target_set_hash": recomputed_target_set_hash,
        "pr_c_policy_hash": next(iter(policy_hashes)),
        "pr_c_threshold_hash": next(iter(threshold_hashes)),
        "oracle": oracle_status,
        "market_extended_status": "not_supplied_governed_optional",
        "blind_2025_y_accessed": False,
    }
    return body | {"binding_manifest_hash": canonical_hash(body)}


def verify_pr_d_input_binding(
    binding: Mapping[str, Any],
    **build_kwargs: Any,
) -> dict[str, Any]:
    """Recompute all bulk identities and compare with a committed binding."""

    body = {key: value for key, value in binding.items() if key != "binding_manifest_hash"}
    if binding.get("binding_manifest_hash") != canonical_hash(body):
        raise ValueError("input_binding category=binding_manifest_hash_mismatch")
    actual = build_pr_d_input_binding(**build_kwargs)
    if dict(binding) != actual:
        expected_components = binding.get("components", {})
        actual_components = actual.get("components", {})
        for name in ("production_document", "market_core", "outcome_target"):
            expected_hash = expected_components.get(name, {}).get("artifact_set_hash")
            actual_hash = actual_components.get(name, {}).get("artifact_set_hash")
            if expected_hash != actual_hash:
                raise ValueError(
                    f"input_binding component={name} category=artifact_set_hash_mismatch "
                    f"expected={expected_hash} actual={actual_hash}"
                )
        raise ValueError("input_binding category=manifest_mismatch")
    return actual
