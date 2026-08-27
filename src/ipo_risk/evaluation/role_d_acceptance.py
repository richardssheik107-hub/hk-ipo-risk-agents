"""Strict, read-only acceptance for the frozen Role-D M5 handoff.

The builder proves that a governed projection can be produced.  This module is
the independent consumer-side check: it reopens the frozen PR-E/PR-F runtime,
the governed EOD store, and the four canonical Role-D artifacts, then
recomputes every acceptance-critical relationship without changing any input.
"""

from __future__ import annotations

import csv
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from ipo_risk.evaluation.role_d_m5 import (
    PR_E_MODEL_NAME,
    PR_F_MODEL_NAME,
    PRODUCTION_COHORT,
    PRODUCTION_FEATURE_GROUP,
    _select_pr_e_artifact,
    _select_pr_f_artifact,
    _verify_pr_e_runtime,
    _verify_pr_f_runtime,
    five_day_metrics,
    sha256_file,
)
from ipo_risk.market.eod_store import EXPECTED_OFFICIAL_CASE_COUNT
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider


ROLE_D_ACCEPTANCE_VERSION = "v045_role_d_m5_acceptance_v1"
CANONICAL_ROLE_D_FILES = frozenset(
    {
        "test_predictions.csv",
        "multi_horizon_results.csv",
        "evaluation_summary.json",
        "ai_vs_offline_report.json",
    }
)
SCORE_SEMANTICS = "uncalibrated_model_score_not_probability"
EVALUATION_SPLIT = "2024_validation"
COMPARISON_SCOPE = "same_2024_validation_full_production_PM"
INTERPRETATION_POLICY = "descriptive_only_no_validation_retuning"
_WINDOWS_ABSOLUTE_PATH = re.compile(r"\b[A-Za-z]:\\")
_UNIX_LOCAL_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])/(?:Users|home|mnt|private|var/folders)/[^\s\"']+"
)


class RoleDAcceptanceError(ValueError):
    """The supplied Role-D evidence cannot be accepted."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoleDAcceptanceError(f"invalid JSON artifact: {path.name}") from exc
    if not isinstance(payload, dict):
        raise RoleDAcceptanceError(f"JSON artifact must be an object: {path.name}")
    return payload


def _read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = tuple(reader.fieldnames or ())
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise RoleDAcceptanceError(f"invalid CSV artifact: {path.name}") from exc
    if not header:
        raise RoleDAcceptanceError(f"CSV artifact has no header: {path.name}")
    return header, rows


def _record_path(path: Path) -> str:
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise RoleDAcceptanceError(f"{label} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RoleDAcceptanceError(f"{label} must be numeric") from exc
    if not math.isfinite(parsed):
        raise RoleDAcceptanceError(f"{label} must be finite")
    return parsed


def _bool(value: Any, label: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RoleDAcceptanceError(f"{label} must be an explicit boolean")


def _close(left: Any, right: Any, *, tolerance: float = 1e-12) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)
    except (TypeError, ValueError):
        return left == right


def _definition_threshold(definition: Any) -> Decimal:
    text = str(definition or "").strip()
    match = re.fullmatch(r"return_5d\s*<=\s*(-?\d+(?:\.\d+)?)", text)
    if match is None:
        raise RoleDAcceptanceError("invalid significant_drop_5d definition")
    return Decimal(match.group(1))


def _artifact_has_local_absolute_path(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    return bool(_WINDOWS_ABSOLUTE_PATH.search(text) or _UNIX_LOCAL_ABSOLUTE_PATH.search(text))


def _required_source_hashes(
    *,
    pr_f_run_dir: Path,
    pr_e_run_dir: Path,
    pr_f_frozen_manifest: Path,
    pr_e_frozen_manifest: Path,
) -> dict[str, str]:
    return {
        "pr_f_run_manifest_sha256": sha256_file(pr_f_run_dir / "run_manifest.json"),
        "pr_f_model_results_sha256": sha256_file(pr_f_run_dir / "model_results.json"),
        "pr_f_model_comparison_sha256": sha256_file(pr_f_run_dir / "model_comparison.json"),
        "pr_e_run_manifest_sha256": sha256_file(pr_e_run_dir / "run_manifest.json"),
        "pr_e_baseline_results_sha256": sha256_file(pr_e_run_dir / "baseline_results.json"),
        "pr_e_value_diagnostic_sha256": sha256_file(pr_e_run_dir / "value_diagnostic.json"),
        "pr_f_frozen_manifest_sha256": sha256_file(pr_f_frozen_manifest),
        "pr_e_frozen_manifest_sha256": sha256_file(pr_e_frozen_manifest),
    }


def _cataloged_eod_invalid_row_policy(catalog_dir: Path) -> tuple[int, str]:
    manifest = _read_json(Path(catalog_dir) / "v04_source_manifest.json")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RoleDAcceptanceError("v04 source manifest entries are unavailable")
    matches = [
        item
        for item in entries
        if isinstance(item, dict) and item.get("logical_id") == "ipo_eod"
    ]
    if len(matches) != 1:
        raise RoleDAcceptanceError(
            "v04 source manifest must contain exactly one ipo_eod entry"
        )
    entry = matches[0]
    coverage = entry.get("coverage")
    provenance = entry.get("provenance")
    if not isinstance(coverage, dict) or not isinstance(provenance, dict):
        raise RoleDAcceptanceError("ipo_eod catalog governance is incomplete")
    raw_expected = coverage.get("invalid_ohlcv_rows")
    if isinstance(raw_expected, bool):
        raise RoleDAcceptanceError("cataloged invalid EOD row count is invalid")
    try:
        expected = int(raw_expected)
    except (TypeError, ValueError) as exc:
        raise RoleDAcceptanceError("cataloged invalid EOD row count is invalid") from exc
    if expected < 0 or raw_expected != expected:
        raise RoleDAcceptanceError("cataloged invalid EOD row count is invalid")
    policy = provenance.get("invalid_row_policy")
    if policy != "exclude_and_report":
        raise RoleDAcceptanceError("cataloged invalid EOD row policy is unsupported")
    return expected, str(policy)


def _metric_values_match(
    actual: Mapping[str, Any], expected: Mapping[str, Any], keys: Sequence[str]
) -> bool:
    return all(key in actual and key in expected and _close(actual[key], expected[key]) for key in keys)


def check_role_d_acceptance(
    *,
    role_d_dir: Path,
    pr_f_run_dir: Path,
    pr_e_run_dir: Path,
    pr_f_frozen_manifest: Path,
    pr_e_frozen_manifest: Path,
    filtered_eod_store: Path,
    filtered_eod_manifest: Path,
    catalog_dir: Path,
    metric_protocol: Path,
    expected_official_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
) -> dict[str, Any]:
    """Return a deterministic PASS/FAIL report without mutating any input."""

    role_d_dir = Path(role_d_dir)
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def record(name: str, passed: bool, detail: Any, blocker: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            blockers.append(blocker)

    actual_entries = (
        {path.name for path in role_d_dir.iterdir()} if role_d_dir.is_dir() else set()
    )
    actual_files = (
        {path.name for path in role_d_dir.iterdir() if path.is_file()}
        if role_d_dir.is_dir()
        else set()
    )
    non_file_entries = actual_entries - actual_files
    canonical_contract_ok = (
        actual_entries == CANONICAL_ROLE_D_FILES
        and actual_files == CANONICAL_ROLE_D_FILES
    )
    record(
        "canonical_four_file_contract",
        canonical_contract_ok,
        {
            "expected": sorted(CANONICAL_ROLE_D_FILES),
            "actual": sorted(actual_entries),
            "missing": sorted(CANONICAL_ROLE_D_FILES - actual_files),
            "extra": sorted(actual_entries - CANONICAL_ROLE_D_FILES),
            "non_file_entries": sorted(non_file_entries),
        },
        "Role-D canonical directory must contain exactly the four formal artifacts",
    )
    if not CANONICAL_ROLE_D_FILES <= actual_files:
        return {
            "schema_version": ROLE_D_ACCEPTANCE_VERSION,
            "verdict": "FAIL",
            "passed": False,
            "role_d_dir": _record_path(role_d_dir),
            "checks": checks,
            "blockers": blockers,
        }

    try:
        protocol = _read_json(metric_protocol)
        post_listing = protocol.get("post_listing") or {}
        required_sessions = tuple(int(value) for value in post_listing.get("required_horizons") or ())
        required_metric_keys = tuple(str(value) for value in post_listing.get("five_day_metrics") or ())
        significant_definition = str(post_listing.get("significant_drop_5d_definition") or "")
        significant_threshold = _definition_threshold(significant_definition)
        protocol_ok = all(
            (
                protocol.get("status") == "FROZEN_BEFORE_VALIDATION_REEVALUATION",
                required_sessions == (1, 5, 20, 60),
                len(required_metric_keys) == 8,
                post_listing.get("official_absolute_metric_threshold_defined") is False,
            )
        )
        record(
            "frozen_metric_protocol",
            protocol_ok,
            {
                "protocol_version": protocol.get("protocol_version"),
                "required_horizons": list(required_sessions),
                "five_day_metrics": list(required_metric_keys),
                "significant_drop_5d_definition": significant_definition,
            },
            "frozen M5 metric protocol is incomplete or drifted",
        )
    except (RoleDAcceptanceError, OSError, TypeError, ValueError) as exc:
        record("frozen_metric_protocol", False, {"error": str(exc)}, "frozen M5 metric protocol is invalid")
        return {
            "schema_version": ROLE_D_ACCEPTANCE_VERSION,
            "verdict": "FAIL",
            "passed": False,
            "role_d_dir": _record_path(role_d_dir),
            "checks": checks,
            "blockers": blockers,
        }

    try:
        pr_f_run, pr_f_results, _ = _verify_pr_f_runtime(pr_f_run_dir, pr_f_frozen_manifest)
        pr_e_run, pr_e_results = _verify_pr_e_runtime(pr_e_run_dir, pr_e_frozen_manifest)
        pr_f_frozen = _read_json(pr_f_frozen_manifest)
        pr_e_frozen = _read_json(pr_e_frozen_manifest)
        pr_f = _select_pr_f_artifact(pr_f_results)
        pr_e = _select_pr_e_artifact(pr_e_results)
        expected_count = int(((pr_f_frozen.get("cohorts") or {}).get(PRODUCTION_COHORT) or {}).get("validation"))
        pr_e_count = int(((pr_e_frozen.get("cohorts") or {}).get(PRODUCTION_COHORT) or {}).get("validation"))
        frozen_runtime_ok = all(
            (
                expected_count == 70,
                pr_e_count == expected_count,
                pr_f.get("evaluation_count") == expected_count,
                pr_e.get("evaluation_count") == expected_count,
                pr_f_run.get("blind_2025_y_accessed") is False,
                pr_e_run.get("blind_2025_y_accessed") is False,
            )
        )
        record(
            "frozen_pr_e_pr_f_runtime",
            frozen_runtime_ok,
            {
                "pr_f_model_result_hash": pr_f_frozen.get("model_result_hash"),
                "pr_e_results_hash": pr_e_frozen.get("results_hash"),
                "expected_validation_count": expected_count,
                "pr_e_validation_count": pr_e_count,
                "blind_2025_y_accessed": False,
            },
            "frozen PR-E/PR-F runtime identity or 354/70 cohort contract is invalid",
        )
    except Exception as exc:  # fail closed on any frozen-runtime parser drift
        record("frozen_pr_e_pr_f_runtime", False, {"error": str(exc)}, "frozen PR-E/PR-F runtime verification failed")
        return {
            "schema_version": ROLE_D_ACCEPTANCE_VERSION,
            "verdict": "FAIL",
            "passed": False,
            "role_d_dir": _record_path(role_d_dir),
            "checks": checks,
            "blockers": blockers,
        }

    try:
        provider = FilteredEODV2MarketDataProvider(
            store_path=filtered_eod_store,
            manifest_path=filtered_eod_manifest,
            catalog_dir=catalog_dir,
            expected_case_count=expected_official_case_count,
        )
        provider_identity = provider.provider_identity
        readiness = provider.readiness_report()
        expected_invalid_rows, invalid_row_policy = _cataloged_eod_invalid_row_policy(
            catalog_dir
        )
        record(
            "governed_filtered_eod",
            readiness.duplicate_rows == 0
            and readiness.invalid_price_rows == expected_invalid_rows,
            {
                **provider_identity,
                "official_case_count": readiness.ipo_total,
                "duplicate_rows": readiness.duplicate_rows,
                "invalid_price_rows": readiness.invalid_price_rows,
                "cataloged_invalid_price_rows": expected_invalid_rows,
                "invalid_row_policy": invalid_row_policy,
                "horizon_coverage": dict(readiness.horizon_coverage),
            },
            "governed filtered EOD store failed integrity checks",
        )
    except Exception as exc:  # provider is the authoritative store validator
        record("governed_filtered_eod", False, {"error": str(exc)}, "governed filtered EOD verification failed")
        return {
            "schema_version": ROLE_D_ACCEPTANCE_VERSION,
            "verdict": "FAIL",
            "passed": False,
            "role_d_dir": _record_path(role_d_dir),
            "checks": checks,
            "blockers": blockers,
        }

    try:
        pred_header, prediction_rows = _read_csv(role_d_dir / "test_predictions.csv")
        horizon_header, horizon_rows = _read_csv(role_d_dir / "multi_horizon_results.csv")
        summary = _read_json(role_d_dir / "evaluation_summary.json")
        comparison = _read_json(role_d_dir / "ai_vs_offline_report.json")
    except RoleDAcceptanceError as exc:
        record("artifact_parsing", False, {"error": str(exc)}, "Role-D artifacts cannot be parsed")
        return {
            "schema_version": ROLE_D_ACCEPTANCE_VERSION,
            "verdict": "FAIL",
            "passed": False,
            "role_d_dir": _record_path(role_d_dir),
            "checks": checks,
            "blockers": blockers,
        }

    prediction_required = {
        "case_id", "stock_code", "cohort_year", "dataset_split", "model",
        "feature_group", "poor_performer_score", "score_semantics",
        "classification_threshold", "predicted_significant_drop_5d",
        "predicted_return_5d", "actual_significant_drop_5d", "actual_return_5d",
        "top_shap_drivers_json",
    }
    horizon_required = {
        "case_id", "stock_code", "cohort_year", "dataset_split", "listing_date",
        "significant_drop_5d",
        *(f"return_{session}d" for session in required_sessions),
        *(f"target_trading_date_{session}d" for session in required_sessions),
    }
    record(
        "artifact_columns",
        prediction_required <= set(pred_header) and horizon_required <= set(horizon_header),
        {
            "missing_prediction_columns": sorted(prediction_required - set(pred_header)),
            "missing_horizon_columns": sorted(horizon_required - set(horizon_header)),
        },
        "Role-D CSV column contract is incomplete",
    )

    def index_rows(rows: Sequence[dict[str, str]], label: str) -> tuple[dict[str, dict[str, str]], list[str]]:
        indexed: dict[str, dict[str, str]] = {}
        duplicates: list[str] = []
        for row in rows:
            case_id = str(row.get("case_id") or "").strip()
            if not case_id or case_id in indexed:
                duplicates.append(case_id or "<empty>")
            else:
                indexed[case_id] = row
        return indexed, duplicates

    pred_by_case, pred_duplicates = index_rows(prediction_rows, "prediction")
    horizon_by_case, horizon_duplicates = index_rows(horizon_rows, "horizon")
    frozen_predictions = list(pr_f.get("case_predictions") or [])
    expected_order = [str(item.get("case_id") or "") for item in frozen_predictions]
    expected_cases = set(expected_order)
    case_contract_ok = all(
        (
            len(prediction_rows) == expected_count,
            len(horizon_rows) == expected_count,
            len(expected_cases) == expected_count,
            not pred_duplicates,
            not horizon_duplicates,
            set(pred_by_case) == expected_cases,
            set(horizon_by_case) == expected_cases,
            [row.get("case_id") for row in prediction_rows] == sorted(expected_cases),
            [row.get("case_id") for row in horizon_rows] == sorted(expected_cases),
        )
    )
    record(
        "exact_2024_validation_case_set",
        case_contract_ok,
        {
            "expected_count": expected_count,
            "prediction_rows": len(prediction_rows),
            "horizon_rows": len(horizon_rows),
            "prediction_duplicates": pred_duplicates,
            "horizon_duplicates": horizon_duplicates,
            "missing_prediction_cases": sorted(expected_cases - set(pred_by_case)),
            "extra_prediction_cases": sorted(set(pred_by_case) - expected_cases),
            "missing_horizon_cases": sorted(expected_cases - set(horizon_by_case)),
            "extra_horizon_cases": sorted(set(horizon_by_case) - expected_cases),
        },
        "Role-D artifacts do not contain the exact deterministic 70-case 2024 Validation set",
    )

    frozen_by_case = {str(item.get("case_id")): item for item in frozen_predictions}
    driver_by_case = {
        str(item.get("case_id")): list(item.get("top_drivers") or [])
        for item in ((pr_f.get("explainability") or {}).get("single_ipo_drivers") or [])
        if isinstance(item, dict) and item.get("case_id")
    }
    metadata_by_case = {item.case_id: item for item in provider.iter_listing_metadata()}
    frozen_threshold = _finite_float(
        (pr_f.get("classification_metrics") or {}).get("classification_threshold"),
        "frozen PR-F classification threshold",
    )
    row_errors: list[str] = []
    for case_id in expected_order:
        if case_id not in pred_by_case or case_id not in horizon_by_case:
            continue
        prediction = pred_by_case[case_id]
        horizon = horizon_by_case[case_id]
        frozen_row = frozen_by_case[case_id]
        metadata = metadata_by_case.get(case_id)
        try:
            if metadata is None:
                raise RoleDAcceptanceError("missing governed metadata")
            if int(prediction["cohort_year"]) != 2024 or int(horizon["cohort_year"]) != 2024:
                raise RoleDAcceptanceError("cohort_year is not 2024")
            if prediction["dataset_split"] != "validation" or horizon["dataset_split"] != "validation":
                raise RoleDAcceptanceError("dataset_split is not validation")
            if prediction["stock_code"] != metadata.stock_code or horizon["stock_code"] != metadata.stock_code:
                raise RoleDAcceptanceError("stock_code disagrees with governed metadata")
            if metadata.listing_date is None or horizon["listing_date"] != metadata.listing_date.isoformat():
                raise RoleDAcceptanceError("listing_date disagrees with governed metadata")
            if metadata.listing_price is None or Decimal(metadata.listing_price) <= 0:
                raise RoleDAcceptanceError("official listing price is missing or non-positive")
            bars = provider.get_daily_bars(metadata.stock_code, start_date=metadata.listing_date)
            if len(bars) < max(required_sessions):
                raise RoleDAcceptanceError("fewer than 60 governed sessions")
            if any(bars[index].trading_date >= bars[index + 1].trading_date for index in range(len(bars) - 1)):
                raise RoleDAcceptanceError("governed sessions are not strictly ordered")
            for session in required_sessions:
                bar = bars[session - 1]
                actual_return = _finite_float(horizon[f"return_{session}d"], f"{case_id} return_{session}d")
                expected_return = float(Decimal(bar.close) / Decimal(metadata.listing_price) - Decimal(1))
                if bar.close <= 0 or not _close(actual_return, expected_return, tolerance=1e-10):
                    raise RoleDAcceptanceError(f"return_{session}d formula mismatch")
                if horizon[f"target_trading_date_{session}d"] != bar.trading_date.isoformat():
                    raise RoleDAcceptanceError(f"target_trading_date_{session}d mismatch")
            actual_return_5d = _finite_float(horizon["return_5d"], f"{case_id} return_5d")
            actual_drop = actual_return_5d <= float(significant_threshold)
            if _bool(horizon["significant_drop_5d"], f"{case_id} significant_drop_5d") != actual_drop:
                raise RoleDAcceptanceError("5D label does not match the frozen definition")
            if not _close(actual_return_5d, frozen_row.get("raw_return_5d"), tolerance=1e-10):
                raise RoleDAcceptanceError("governed 5D return disagrees with frozen PR-F")
            if actual_drop != bool(frozen_row.get("poor_performer_5d")):
                raise RoleDAcceptanceError("governed 5D label disagrees with frozen PR-F")
            if prediction["model"] != PR_F_MODEL_NAME or prediction["feature_group"] != PRODUCTION_FEATURE_GROUP:
                raise RoleDAcceptanceError("prediction model/feature group is not frozen lightgbm/PM")
            if prediction["score_semantics"] != SCORE_SEMANTICS:
                raise RoleDAcceptanceError("prediction score semantics drifted")
            score = _finite_float(prediction["poor_performer_score"], f"{case_id} score")
            threshold = _finite_float(prediction["classification_threshold"], f"{case_id} threshold")
            if not _close(score, frozen_row.get("poor_performer_score")) or not _close(threshold, frozen_threshold):
                raise RoleDAcceptanceError("score or threshold disagrees with frozen PR-F")
            if _bool(prediction["predicted_significant_drop_5d"], f"{case_id} predicted label") != (score >= threshold):
                raise RoleDAcceptanceError("predicted label does not equal score >= frozen threshold")
            if not _close(prediction["predicted_return_5d"], frozen_row.get("raw_return_5d_prediction")):
                raise RoleDAcceptanceError("predicted return disagrees with frozen PR-F")
            if not _close(prediction["actual_return_5d"], actual_return_5d, tolerance=1e-10):
                raise RoleDAcceptanceError("prediction actual return disagrees with horizon table")
            if _bool(prediction["actual_significant_drop_5d"], f"{case_id} actual label") != actual_drop:
                raise RoleDAcceptanceError("prediction actual label disagrees with horizon table")
            drivers = json.loads(prediction["top_shap_drivers_json"])
            if not isinstance(drivers, list) or drivers != driver_by_case.get(case_id, []):
                raise RoleDAcceptanceError("SHAP drivers disagree with frozen PR-F")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, RoleDAcceptanceError) as exc:
            row_errors.append(f"{case_id}: {exc}")
    record(
        "independent_row_and_session_validation",
        not row_errors and len(expected_order) == expected_count,
        {"validated_case_count": expected_count - len(row_errors), "errors": row_errors},
        "Role-D per-case score/label/session/return/SHAP validation failed",
    )

    recomputed_metrics: dict[str, Any] = {}
    metric_errors: list[str] = []
    try:
        labels = [
            _bool(horizon_by_case[case_id]["significant_drop_5d"], f"{case_id} label")
            for case_id in expected_order
        ]
        scores = [
            _finite_float(pred_by_case[case_id]["poor_performer_score"], f"{case_id} score")
            for case_id in expected_order
        ]
        recomputed_metrics = five_day_metrics(labels, scores, frozen_threshold)
        summary_metrics = summary.get("five_day_metrics") or {}
        frozen_metrics = pr_f.get("classification_metrics") or {}
        for key in required_metric_keys:
            if not _close(summary_metrics.get(key), recomputed_metrics.get(key)):
                metric_errors.append(f"summary metric mismatch: {key}")
        for key in ("precision", "recall", "f1", "pr_auc", "roc_auc"):
            if not _close(recomputed_metrics.get(key), frozen_metrics.get(key)):
                metric_errors.append(f"frozen PR-F metric mismatch: {key}")
    except (KeyError, RoleDAcceptanceError, ValueError) as exc:
        metric_errors.append(str(exc))
    record(
        "independent_five_day_metric_recomputation",
        not metric_errors,
        {"recomputed": recomputed_metrics, "errors": metric_errors},
        "Role-D five-day metrics do not reproduce from the canonical CSV",
    )

    expected_horizon_labels = [f"{value}D" for value in required_sessions]
    summary_ok = all(
        (
            summary.get("status") == "complete",
            bool(str(summary.get("role_d_m5_version") or "").strip()),
            summary.get("metric_protocol_version") == protocol.get("protocol_version"),
            summary.get("evaluation_split") == EVALUATION_SPLIT,
            summary.get("evaluation_count") == expected_count,
            summary.get("horizons") == expected_horizon_labels,
            summary.get("significant_drop_5d_definition") == significant_definition,
            summary.get("score_semantics") == SCORE_SEMANTICS,
            summary.get("threshold_or_model_retuned_on_validation") is False,
            summary.get("blind_2025_y_accessed") is False,
        )
    )
    record(
        "evaluation_summary_contract",
        summary_ok,
        {
            "status": summary.get("status"),
            "role_d_m5_version": summary.get("role_d_m5_version"),
            "evaluation_split": summary.get("evaluation_split"),
            "evaluation_count": summary.get("evaluation_count"),
            "horizons": summary.get("horizons"),
            "blind_2025_y_accessed": summary.get("blind_2025_y_accessed"),
        },
        "Role-D evaluation summary contract is incomplete or drifted",
    )

    baseline_metrics = pr_e.get("metrics") or {}
    comparison_errors: list[str] = []
    ai_metrics = (comparison.get("ai_model") or {}).get("metrics") or {}
    offline_metrics = (comparison.get("offline_baseline") or {}).get("metrics") or {}
    if not _metric_values_match(ai_metrics, summary.get("five_day_metrics") or {}, required_metric_keys):
        comparison_errors.append("AI metrics disagree with evaluation summary")
    if not _metric_values_match(offline_metrics, baseline_metrics, tuple(baseline_metrics)):
        comparison_errors.append("offline metrics disagree with frozen PR-E")
    deltas = comparison.get("ai_minus_offline") or {}
    for key in ("precision", "recall", "f1", "pr_auc", "roc_auc"):
        expected_delta = (
            None
            if recomputed_metrics.get(key) is None or baseline_metrics.get(key) is None
            else float(recomputed_metrics[key]) - float(baseline_metrics[key])
        )
        if not _close(deltas.get(key), expected_delta):
            comparison_errors.append(f"AI-minus-offline delta mismatch: {key}")
    comparison_ok = all(
        (
            comparison.get("comparison_scope") == COMPARISON_SCOPE,
            (comparison.get("ai_model") or {}).get("name") == "frozen_lightgbm",
            (comparison.get("ai_model") or {}).get("score_semantics") == SCORE_SEMANTICS,
            (comparison.get("offline_baseline") or {}).get("name") == "frozen_logistic_regression",
            comparison.get("interpretation_policy") == INTERPRETATION_POLICY,
            comparison.get("threshold_or_model_retuned_on_validation") is False,
            comparison.get("blind_2025_y_accessed") is False,
            not comparison_errors,
        )
    )
    record(
        "frozen_ai_vs_offline_comparison",
        comparison_ok,
        {"ai_model": (comparison.get("ai_model") or {}).get("name"), "offline_baseline": (comparison.get("offline_baseline") or {}).get("name"), "errors": comparison_errors},
        "Role-D AI-vs-offline report is not a complete frozen descriptive comparison",
    )

    expected_hashes = _required_source_hashes(
        pr_f_run_dir=pr_f_run_dir,
        pr_e_run_dir=pr_e_run_dir,
        pr_f_frozen_manifest=pr_f_frozen_manifest,
        pr_e_frozen_manifest=pr_e_frozen_manifest,
    )
    actual_hashes = summary.get("source_hashes") or {}
    source_hash_errors = [
        key for key, expected in expected_hashes.items() if actual_hashes.get(key) != expected
    ]
    market_source = summary.get("market_source") or {}
    market_identity_errors = [
        key for key, expected in provider_identity.items() if market_source.get(key) != expected
    ]
    record(
        "complete_source_provenance",
        not source_hash_errors and not market_identity_errors,
        {"source_hash_mismatches": source_hash_errors, "market_identity_mismatches": market_identity_errors},
        "Role-D source provenance is incomplete or disagrees with frozen/runtime/EOD inputs",
    )

    path_leaks = sorted(
        name
        for name in CANONICAL_ROLE_D_FILES
        if _artifact_has_local_absolute_path(role_d_dir / name)
    )
    record(
        "portable_artifacts",
        not path_leaks,
        {"absolute_path_leaks": path_leaks},
        "Role-D artifacts contain local absolute paths",
    )

    passed = not blockers and all(item["passed"] for item in checks)
    return {
        "schema_version": ROLE_D_ACCEPTANCE_VERSION,
        "verdict": "PASS" if passed else "FAIL",
        "passed": passed,
        "role_d_dir": _record_path(role_d_dir),
        "metric_protocol_version": protocol.get("protocol_version"),
        "expected_validation_count": expected_count,
        "checks": checks,
        "blockers": blockers,
        "governance": {
            "pr_e_retrained": False,
            "pr_f_retrained": False,
            "validation_retuning_performed": False,
            "score_direction_inverted": False,
            "classification_threshold_changed": False,
            "score_calibrated": False,
            "blind_2025_y_accessed": False,
            "artifacts_modified_by_checker": False,
        },
    }
