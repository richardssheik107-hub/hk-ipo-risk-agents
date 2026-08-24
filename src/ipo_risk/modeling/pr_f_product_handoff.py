"""Sanitized product-runtime projection of the frozen PR-F result.

The formal PR-F ``model_results.json`` contains evaluation labels and other
research-only fields.  A product/demo runtime should not need those labels just
to display the already-frozen per-case score and SHAP drivers.

This module creates and validates a small derived handoff that is *bound to* the
frozen PR-F ``model_result_hash`` but contains only:

- case id;
- the frozen uncalibrated score already present in PR-F;
- the frozen top SHAP drivers already present in PR-F.

It never trains, scores, recalculates SHAP, or copies target labels.  The source
full PR-F result is verified by canonical hash before projection.  The derived
file has its own byte SHA-256 in a manifest and is fail-closed on read.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.final_supervision import ModelDriver

PRODUCT_MANIFEST_NAME = "product_runtime_manifest.json"
PRODUCT_SIGNALS_NAME = "product_case_signals.json"
PRODUCT_MANIFEST_VERSION = "v04_pr_f_product_runtime_handoff_v1"
PRODUCTION_COHORT = "full_production"
PRODUCTION_FEATURE_GROUP = "PM"

_ALLOWED_SIGNAL_KEYS = {"case_id", "score", "drivers"}
_ALLOWED_DRIVER_KEYS = {"feature", "component", "feature_value", "shap_value"}
_FORBIDDEN_LABEL_KEYS = {
    "poor_performer_5d",
    "raw_return_5d",
    "raw_return_5d_prediction",
    "target",
    "label",
    "y",
}


class ProductRuntimeHandoffError(ValueError):
    """A product-runtime projection cannot be trusted or produced safely."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProductRuntimeHandoffError(f"invalid JSON: {path.name}") from exc


def _production_artifact(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in results
            if item.get("cohort") == PRODUCTION_COHORT
            and item.get("feature_group") == PRODUCTION_FEATURE_GROUP
        ),
        None,
    )


def _driver_rows(artifact: dict[str, Any], case_id: str) -> list[dict[str, Any]]:
    explainability = artifact.get("explainability") or {}
    entry = next(
        (
            item
            for item in explainability.get("single_ipo_drivers", [])
            if item.get("case_id") == case_id
        ),
        None,
    )
    if entry is None:
        return []
    return [
        {
            "feature": str(driver["feature"]),
            "component": str(driver.get("component") or "unclassified"),
            "feature_value": (
                None if driver.get("feature_value") is None else float(driver["feature_value"])
            ),
            "shap_value": float(driver["shap_value"]),
        }
        for driver in entry.get("top_drivers", [])
    ]


def project_case_signals(
    results: list[dict[str, Any]],
    *,
    expected_source_model_result_hash: str,
    case_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Project selected frozen PR-F validation cases into a label-free payload."""
    if canonical_hash(results) != expected_source_model_result_hash:
        raise ProductRuntimeHandoffError("source model_results do not match the frozen model_result_hash")
    artifact = _production_artifact(results)
    if artifact is None:
        raise ProductRuntimeHandoffError("frozen PR-F results carry no full_production PM artifact")

    rows_by_case = {
        str(row.get("case_id")): row
        for row in artifact.get("case_predictions", [])
        if row.get("case_id")
    }
    requested = tuple(dict.fromkeys(str(case_id).strip() for case_id in case_ids if str(case_id).strip()))
    if not requested:
        raise ProductRuntimeHandoffError("at least one case id is required")

    missing = [case_id for case_id in requested if case_id not in rows_by_case]
    if missing:
        raise ProductRuntimeHandoffError(
            "requested cases are not in the frozen full_production validation artifact: "
            + ", ".join(missing[:5])
        )

    return [
        {
            "case_id": case_id,
            "score": float(rows_by_case[case_id]["poor_performer_score"]),
            "drivers": _driver_rows(artifact, case_id),
        }
        for case_id in requested
    ]


def _assert_label_free(signals: list[dict[str, Any]]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            forbidden = _FORBIDDEN_LABEL_KEYS.intersection(value)
            if forbidden:
                raise ProductRuntimeHandoffError(
                    "product handoff contains forbidden evaluation label fields: "
                    + ", ".join(sorted(forbidden))
                )
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(signals)


def write_product_handoff(
    source_run_dir: Path,
    output_dir: Path,
    *,
    expected_source_model_result_hash: str,
    case_ids: Iterable[str],
) -> dict[str, Any]:
    """Verify the full frozen source and write a small label-free product handoff."""
    source_run_dir = Path(source_run_dir)
    output_dir = Path(output_dir)
    run_manifest_path = source_run_dir / "run_manifest.json"
    results_path = source_run_dir / "model_results.json"
    if not run_manifest_path.is_file() or not results_path.is_file():
        raise ProductRuntimeHandoffError("source PR-F run_manifest.json/model_results.json are required")

    source_manifest = _read_json(run_manifest_path)
    source_results = _read_json(results_path)
    if not isinstance(source_manifest, dict) or not isinstance(source_results, list):
        raise ProductRuntimeHandoffError("source PR-F runtime artifacts have incompatible JSON shapes")
    if source_manifest.get("model_result_hash") != expected_source_model_result_hash:
        raise ProductRuntimeHandoffError("source run manifest does not match the frozen model_result_hash")
    if source_manifest.get("blind_2025_y_accessed") is not False:
        raise ProductRuntimeHandoffError("source run manifest does not prove blind_2025_y_accessed=false")

    signals = project_case_signals(
        source_results,
        expected_source_model_result_hash=expected_source_model_result_hash,
        case_ids=case_ids,
    )
    _assert_label_free(signals)

    output_dir.mkdir(parents=True, exist_ok=True)
    signals_path = output_dir / PRODUCT_SIGNALS_NAME
    signals_path.write_text(
        json.dumps(signals, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": PRODUCT_MANIFEST_VERSION,
        "source_model_result_hash": expected_source_model_result_hash,
        "case_signal_file": PRODUCT_SIGNALS_NAME,
        "case_signal_sha256": _sha256_file(signals_path),
        "case_count": len(signals),
        "contains_target_labels": False,
        "blind_2025_y_accessed": False,
        "score_semantics": "uncalibrated_model_score",
    }
    (output_dir / PRODUCT_MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def read_product_case_signal(
    run_dir: Path,
    *,
    expected_source_model_result_hash: str,
    case_id: str,
) -> tuple[float, tuple[ModelDriver, ...]] | None:
    """Read one sanitized product signal.

    Returns ``None`` when this directory is not a product handoff, allowing the
    caller to fall back to the exact full PR-F runtime format.  If a product
    manifest exists but fails validation, an exception is raised so the caller
    can fail closed rather than silently falling back.
    """
    run_dir = Path(run_dir)
    manifest_path = run_dir / PRODUCT_MANIFEST_NAME
    if not manifest_path.is_file():
        return None

    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ProductRuntimeHandoffError("product runtime manifest has incompatible shape")
    if manifest.get("manifest_version") != PRODUCT_MANIFEST_VERSION:
        raise ProductRuntimeHandoffError("unsupported product runtime manifest version")
    if manifest.get("source_model_result_hash") != expected_source_model_result_hash:
        raise ProductRuntimeHandoffError("product runtime source hash does not match frozen PR-F")
    if manifest.get("contains_target_labels") is not False:
        raise ProductRuntimeHandoffError("product runtime manifest does not prove label-free content")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ProductRuntimeHandoffError("product runtime manifest reports blind 2025 access")
    if manifest.get("score_semantics") != "uncalibrated_model_score":
        raise ProductRuntimeHandoffError("product runtime score semantics are incompatible")

    signals_path = run_dir / str(manifest.get("case_signal_file") or "")
    if signals_path.name != PRODUCT_SIGNALS_NAME or not signals_path.is_file():
        raise ProductRuntimeHandoffError("product case-signal file is missing or unexpected")
    if _sha256_file(signals_path) != manifest.get("case_signal_sha256"):
        raise ProductRuntimeHandoffError("product case-signal checksum mismatch")

    signals = _read_json(signals_path)
    if not isinstance(signals, list):
        raise ProductRuntimeHandoffError("product case-signal payload is not a list")
    _assert_label_free(signals)
    if len(signals) != int(manifest.get("case_count", -1)):
        raise ProductRuntimeHandoffError("product case count does not match manifest")

    for signal in signals:
        if not isinstance(signal, dict) or set(signal) != _ALLOWED_SIGNAL_KEYS:
            raise ProductRuntimeHandoffError("product case-signal schema drift")
        if not isinstance(signal.get("drivers"), list):
            raise ProductRuntimeHandoffError("product driver payload is not a list")
        for driver in signal["drivers"]:
            if not isinstance(driver, dict) or set(driver) != _ALLOWED_DRIVER_KEYS:
                raise ProductRuntimeHandoffError("product driver schema drift")

    row = next((item for item in signals if item.get("case_id") == case_id), None)
    if row is None:
        raise ProductRuntimeHandoffError("case is not present in the sanitized product handoff")

    drivers = tuple(
        ModelDriver(
            feature=str(driver["feature"]),
            component=str(driver["component"]),
            feature_value=(
                None if driver.get("feature_value") is None else float(driver["feature_value"])
            ),
            shap_value=float(driver["shap_value"]),
            direction="increases" if float(driver["shap_value"]) >= 0 else "decreases",
        )
        for driver in row["drivers"]
    )
    return float(row["score"]), drivers
