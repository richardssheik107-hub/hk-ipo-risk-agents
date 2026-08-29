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

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.final_supervision import ModelDriver

PRODUCT_MANIFEST_NAME = "product_runtime_manifest.json"
PRODUCT_SIGNALS_NAME = "product_case_signals.json"
PRODUCT_CHECKSUMS_NAME = "SHA256SUMS.txt"
PRODUCT_README_NAME = "README_PRODUCT_RUNTIME_HANDOFF.md"
PRODUCT_MANIFEST_VERSION = "v04_pr_f_product_runtime_handoff_v1"
PRODUCTION_COHORT = "full_production"
PRODUCTION_FEATURE_GROUP = "PM"

PRODUCT_FILES = frozenset(
    {
        PRODUCT_MANIFEST_NAME,
        PRODUCT_SIGNALS_NAME,
        PRODUCT_CHECKSUMS_NAME,
        PRODUCT_README_NAME,
    }
)
CHECKSUMMED_PRODUCT_FILES = (
    PRODUCT_MANIFEST_NAME,
    PRODUCT_SIGNALS_NAME,
    PRODUCT_README_NAME,
)
PRODUCT_README = (
    "# PR-F Product Runtime Handoff\n\n"
    "This directory is a deterministic, label-free projection of the frozen PR-F result.\n"
    "It contains only case identity, the frozen uncalibrated model score, and frozen SHAP "
    "drivers. It is not a probability, does not retrain or rescore the model, and contains "
    "no outcome labels or 2025 Blind outcomes.\n"
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"\b[A-Za-z]:[\\/]")
_UNIX_LOCAL_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])/(?:Users|home|mnt|private|var/folders)/[^\s\"']+"
)
_SHA256 = re.compile(r"[0-9a-f]{64}")

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

_ROLE_D_PREDICTION_FIELDS = (
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
)


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


def _has_local_absolute_path(text: str) -> bool:
    return bool(_WINDOWS_ABSOLUTE_PATH.search(text) or _UNIX_LOCAL_ABSOLUTE_PATH.search(text))


def _read_checksums(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ProductRuntimeHandoffError("product checksum manifest is unreadable") from exc
    checksums: dict[str, str] = {}
    for line in lines:
        parts = line.split()
        if len(parts) != 2 or _SHA256.fullmatch(parts[0]) is None:
            raise ProductRuntimeHandoffError("product checksum manifest has invalid syntax")
        name = parts[1]
        if name in checksums:
            raise ProductRuntimeHandoffError("product checksum manifest contains duplicate entries")
        checksums[name] = parts[0]
    if set(checksums) != set(CHECKSUMMED_PRODUCT_FILES):
        raise ProductRuntimeHandoffError("product checksum manifest does not cover the exact contract")
    return checksums


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

    signals = [
        {
            "case_id": case_id,
            "score": float(rows_by_case[case_id]["poor_performer_score"]),
            "drivers": _driver_rows(artifact, case_id),
        }
        for case_id in requested
    ]
    _validate_signal_rows(signals)
    return signals


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


def _validate_signal_rows(signals: list[dict[str, Any]]) -> None:
    _assert_label_free(signals)
    seen: set[str] = set()
    for signal in signals:
        if not isinstance(signal, dict) or set(signal) != _ALLOWED_SIGNAL_KEYS:
            raise ProductRuntimeHandoffError("product case-signal schema drift")
        case_id = signal.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ProductRuntimeHandoffError("product case ids must be unique non-empty strings")
        seen.add(case_id)
        score = signal.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise ProductRuntimeHandoffError("product score must be a finite number")
        drivers = signal.get("drivers")
        if not isinstance(drivers, list):
            raise ProductRuntimeHandoffError("product driver payload is not a list")
        for driver in drivers:
            if not isinstance(driver, dict) or set(driver) != _ALLOWED_DRIVER_KEYS:
                raise ProductRuntimeHandoffError("product driver schema drift")
            if not isinstance(driver.get("feature"), str) or not driver["feature"]:
                raise ProductRuntimeHandoffError("product driver feature is invalid")
            if not isinstance(driver.get("component"), str) or not driver["component"]:
                raise ProductRuntimeHandoffError("product driver component is invalid")
            for key in ("feature_value", "shap_value"):
                value = driver.get(key)
                if value is None and key == "feature_value":
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ProductRuntimeHandoffError(f"product driver {key} is invalid")
                if not math.isfinite(float(value)):
                    raise ProductRuntimeHandoffError(f"product driver {key} is not finite")


def validate_product_handoff(
    run_dir: Path,
    *,
    expected_source_model_result_hash: str,
    expected_case_ids: Sequence[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate the complete four-file, label-free product handoff.

    This is deliberately stricter than validating one case signal: consumers
    reject partial packages, extra files, checksum drift, local path leakage,
    and a changed final-case set.
    """

    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise ProductRuntimeHandoffError("product runtime directory is missing")
    actual_entries = {path.name for path in run_dir.iterdir()}
    if actual_entries != PRODUCT_FILES or not all(
        (run_dir / name).is_file() for name in PRODUCT_FILES
    ):
        raise ProductRuntimeHandoffError("product runtime directory must contain exactly four files")

    manifest_path = run_dir / PRODUCT_MANIFEST_NAME
    signals_path = run_dir / PRODUCT_SIGNALS_NAME
    readme_path = run_dir / PRODUCT_README_NAME
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProductRuntimeHandoffError("product runtime manifest is unreadable") from exc
    if _has_local_absolute_path(manifest_text):
        raise ProductRuntimeHandoffError("product runtime manifest contains a local absolute path")
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
    if manifest.get("case_signal_file") != PRODUCT_SIGNALS_NAME:
        raise ProductRuntimeHandoffError("product case-signal file is missing or unexpected")

    signals = _read_json(signals_path)
    if not isinstance(signals, list):
        raise ProductRuntimeHandoffError("product case-signal payload is not a list")
    _validate_signal_rows(signals)
    if _sha256_file(signals_path) != manifest.get("case_signal_sha256"):
        raise ProductRuntimeHandoffError("product case-signal checksum mismatch")
    try:
        case_count = int(manifest.get("case_count", -1))
    except (TypeError, ValueError) as exc:
        raise ProductRuntimeHandoffError("product case count is invalid") from exc
    if len(signals) != case_count:
        raise ProductRuntimeHandoffError("product case count does not match manifest")

    if expected_case_ids is not None:
        expected = tuple(dict.fromkeys(str(value).strip() for value in expected_case_ids))
        actual = tuple(str(signal["case_id"]) for signal in signals)
        if actual != expected:
            raise ProductRuntimeHandoffError("product case ids do not match the qualified handoff set")

    try:
        readme = readme_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProductRuntimeHandoffError("product handoff README is unreadable") from exc
    if readme != PRODUCT_README:
        raise ProductRuntimeHandoffError("product handoff README drifted from the contract")

    checksums = _read_checksums(run_dir / PRODUCT_CHECKSUMS_NAME)
    for name in CHECKSUMMED_PRODUCT_FILES:
        if _sha256_file(run_dir / name) != checksums[name]:
            raise ProductRuntimeHandoffError(f"product package checksum mismatch: {name}")
    return manifest, signals


def write_product_handoff(
    source_run_dir: Path,
    output_dir: Path,
    *,
    expected_source_model_result_hash: str,
    case_ids: Iterable[str],
    source_pr_f: Mapping[str, Any] | None = None,
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
    _validate_signal_rows(signals)

    return _write_product_package(
        output_dir,
        signals,
        expected_source_model_result_hash=expected_source_model_result_hash,
        source_pr_f=source_pr_f,
    )


def _write_product_package(
    output_dir: Path,
    signals: list[dict[str, Any]],
    *,
    expected_source_model_result_hash: str,
    source_pr_f: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the canonical four-file package from already-validated signals."""

    output_dir = Path(output_dir)
    _validate_signal_rows(signals)
    output_dir.mkdir(parents=True, exist_ok=True)
    signals_path = output_dir / PRODUCT_SIGNALS_NAME
    signals_path.write_text(
        json.dumps(signals, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "manifest_version": PRODUCT_MANIFEST_VERSION,
        "source_model_result_hash": expected_source_model_result_hash,
        "source_pr_f": dict(source_pr_f or {}),
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
    (output_dir / PRODUCT_README_NAME).write_text(PRODUCT_README, encoding="utf-8")
    checksum_lines = [
        f"{_sha256_file(output_dir / name)}  {name}"
        for name in CHECKSUMMED_PRODUCT_FILES
    ]
    (output_dir / PRODUCT_CHECKSUMS_NAME).write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    validated, _ = validate_product_handoff(
        output_dir,
        expected_source_model_result_hash=expected_source_model_result_hash,
        expected_case_ids=[signal["case_id"] for signal in signals],
    )
    return validated


def project_case_signals_from_role_d_predictions(
    predictions_path: Path,
    *,
    expected_predictions_sha256: str,
    case_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Recover the frozen product projection from a receipt-bound D export.

    ``test_predictions.csv`` is a deterministic projection of the verified
    PR-F runtime produced by Role D.  This recovery path is intentionally
    narrower than the normal PR-F builder: it accepts only the byte-identical
    export named by the immutable current-main receipt and removes every label
    and realised-return column before writing a product package.
    """

    predictions_path = Path(predictions_path)
    if _SHA256.fullmatch(expected_predictions_sha256) is None:
        raise ProductRuntimeHandoffError("receipt prediction checksum is invalid")
    if not predictions_path.is_file():
        raise ProductRuntimeHandoffError("receipt-bound test_predictions.csv is missing")
    if _sha256_file(predictions_path) != expected_predictions_sha256:
        raise ProductRuntimeHandoffError(
            "test_predictions.csv does not match the immutable Role-D receipt"
        )

    try:
        with predictions_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != _ROLE_D_PREDICTION_FIELDS:
                raise ProductRuntimeHandoffError(
                    "Role-D prediction export schema drifted from the frozen contract"
                )
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ProductRuntimeHandoffError("Role-D prediction export is unreadable") from exc

    rows_by_case: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if not case_id or case_id in rows_by_case:
            raise ProductRuntimeHandoffError(
                "Role-D prediction export case ids must be unique and non-empty"
            )
        rows_by_case[case_id] = row

    requested = tuple(
        dict.fromkeys(str(case_id).strip() for case_id in case_ids if str(case_id).strip())
    )
    if not requested:
        raise ProductRuntimeHandoffError("at least one receipt-qualified case id is required")
    missing = [case_id for case_id in requested if case_id not in rows_by_case]
    if missing:
        raise ProductRuntimeHandoffError(
            "receipt-qualified cases are absent from test_predictions.csv: "
            + ", ".join(missing)
        )

    signals: list[dict[str, Any]] = []
    for case_id in requested:
        row = rows_by_case[case_id]
        if (
            row.get("cohort_year") != "2024"
            or row.get("dataset_split") != "validation"
            or row.get("model") != "lightgbm"
            or row.get("feature_group") != PRODUCTION_FEATURE_GROUP
            or row.get("score_semantics")
            != "uncalibrated_model_score_not_probability"
        ):
            raise ProductRuntimeHandoffError(
                f"Role-D prediction identity drift for {case_id}"
            )
        try:
            score = float(row["poor_performer_score"])
            drivers = json.loads(row["top_shap_drivers_json"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProductRuntimeHandoffError(
                f"Role-D score or SHAP payload is invalid for {case_id}"
            ) from exc
        if not math.isfinite(score) or not isinstance(drivers, list):
            raise ProductRuntimeHandoffError(
                f"Role-D score or SHAP payload is invalid for {case_id}"
            )
        signals.append({"case_id": case_id, "score": score, "drivers": drivers})

    _validate_signal_rows(signals)
    return signals


def write_receipt_bound_product_handoff(
    predictions_path: Path,
    output_dir: Path,
    *,
    expected_predictions_sha256: str,
    expected_product_sha256: Mapping[str, str],
    expected_source_model_result_hash: str,
    case_ids: Iterable[str],
    source_pr_f: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reproduce, byte for byte, the product package recorded by the receipt."""

    expected = {str(name): str(value) for name, value in expected_product_sha256.items()}
    if set(expected) != PRODUCT_FILES or any(
        _SHA256.fullmatch(value) is None for value in expected.values()
    ):
        raise ProductRuntimeHandoffError(
            "receipt product checksums do not cover the exact four-file contract"
        )
    signals = project_case_signals_from_role_d_predictions(
        predictions_path,
        expected_predictions_sha256=expected_predictions_sha256,
        case_ids=case_ids,
    )
    manifest = _write_product_package(
        output_dir,
        signals,
        expected_source_model_result_hash=expected_source_model_result_hash,
        source_pr_f=source_pr_f,
    )
    actual = {name: _sha256_file(Path(output_dir) / name) for name in PRODUCT_FILES}
    if actual != expected:
        raise ProductRuntimeHandoffError(
            "recovered product package does not match the immutable Role-D receipt"
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

    _, signals = validate_product_handoff(
        run_dir,
        expected_source_model_result_hash=expected_source_model_result_hash,
    )

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
