"""Governed Role-D M5 multi-horizon evaluation handoff.

This module consumes the already-frozen PR-E/PR-F evaluation artifacts and the
governed filtered IPO EOD store.  It never trains, tunes, rescales, or accesses
2025 Blind outcomes.  The four submission files are deterministic projections
of those inputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ipo_risk.schemas.canonical_modeling import canonical_hash


ROLE_D_M5_VERSION = "v045_role_d_m5_handoff_v1"
METRIC_PROTOCOL_VERSION = "v045_competition_metric_protocol_v2_existing_gold_only"
SIGNIFICANT_DROP_5D_THRESHOLD = Decimal("-0.10")
HORIZON_SESSIONS = {"1d": 1, "5d": 5, "20d": 20, "60d": 60}
PRODUCTION_COHORT = "full_production"
PRODUCTION_FEATURE_GROUP = "PM"
PR_F_MODEL_NAME = "lightgbm"
PR_E_MODEL_NAME = "logistic_regression"


class RoleDM5Error(ValueError):
    """A Role-D handoff cannot be produced from the supplied governed inputs."""


@dataclass(frozen=True)
class RoleDPayloads:
    predictions: tuple[dict[str, Any], ...]
    horizons: tuple[dict[str, Any], ...]
    evaluation_summary: dict[str, Any]
    ai_vs_offline: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoleDM5Error(f"invalid Role-D JSON input: {path}") from exc


def _require_false(payload: Mapping[str, Any], key: str, label: str) -> None:
    if payload.get(key) is not False:
        raise RoleDM5Error(f"{label} does not prove {key}=false")


def _verify_pr_f_runtime(
    run_dir: Path, frozen_manifest_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    frozen = _read_json(frozen_manifest_path)
    if not isinstance(frozen, dict):
        raise RoleDM5Error("PR-F frozen manifest must be a JSON object")
    if frozen.get("status") != "complete_frozen" or frozen.get("formal_gate_passed") is not True:
        raise RoleDM5Error("Role D requires the complete frozen PR-F Gate")
    _require_false(frozen, "blind_2025_y_accessed", "PR-F frozen manifest")

    run_path = run_dir / "run_manifest.json"
    results_path = run_dir / "model_results.json"
    comparison_path = run_dir / "model_comparison.json"
    expected = frozen.get("runtime_outputs") or {}
    checks = {
        run_path: expected.get("run_manifest_sha256"),
        results_path: expected.get("model_results_sha256"),
        comparison_path: expected.get("model_comparison_sha256"),
    }
    for path, checksum in checks.items():
        if not path.is_file() or not isinstance(checksum, str):
            raise RoleDM5Error(f"missing frozen PR-F runtime input: {path}")
        if sha256_file(path) != checksum:
            raise RoleDM5Error(f"PR-F runtime checksum mismatch: {path.name}")

    run = _read_json(run_path)
    results = _read_json(results_path)
    comparison = _read_json(comparison_path)
    if not isinstance(run, dict) or not isinstance(results, list) or not isinstance(comparison, dict):
        raise RoleDM5Error("PR-F runtime JSON shapes are incompatible")
    _require_false(run, "blind_2025_y_accessed", "PR-F run manifest")
    if canonical_hash(results) != frozen.get("model_result_hash"):
        raise RoleDM5Error("PR-F model_results do not match the frozen result hash")
    if run.get("model_result_hash") != frozen.get("model_result_hash"):
        raise RoleDM5Error("PR-F run manifest result hash drift")
    return run, results, comparison


def _verify_pr_e_runtime(
    run_dir: Path, frozen_manifest_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    frozen = _read_json(frozen_manifest_path)
    if not isinstance(frozen, dict):
        raise RoleDM5Error("PR-E frozen manifest must be a JSON object")
    if frozen.get("status") != "complete_frozen" or frozen.get("formal_gate_passed") is not True:
        raise RoleDM5Error("Role D requires the complete frozen PR-E Gate")
    _require_false(frozen, "blind_2025_y_accessed", "PR-E frozen manifest")

    outputs = frozen.get("runtime_outputs") or {}
    paths = {
        run_dir / "run_manifest.json": outputs.get("reports/v04_pr_e/run_manifest.json", {}).get("sha256"),
        run_dir / "baseline_results.json": outputs.get("reports/v04_pr_e/baseline_results.json", {}).get("sha256"),
        run_dir / "value_diagnostic.json": outputs.get("reports/v04_pr_e/value_diagnostic.json", {}).get("sha256"),
    }
    for path, checksum in paths.items():
        if not path.is_file() or not isinstance(checksum, str):
            raise RoleDM5Error(f"missing frozen PR-E runtime input: {path}")
        if sha256_file(path) != checksum:
            raise RoleDM5Error(f"PR-E runtime checksum mismatch: {path.name}")

    run = _read_json(run_dir / "run_manifest.json")
    results = _read_json(run_dir / "baseline_results.json")
    diagnostic = _read_json(run_dir / "value_diagnostic.json")
    if not isinstance(run, dict) or not isinstance(results, list) or not isinstance(diagnostic, dict):
        raise RoleDM5Error("PR-E runtime JSON shapes are incompatible")
    _require_false(run, "blind_2025_y_accessed", "PR-E run manifest")
    if canonical_hash(results) != frozen.get("results_hash"):
        raise RoleDM5Error("PR-E baseline_results do not match the frozen result hash")
    if canonical_hash(diagnostic) != frozen.get("diagnostic_hash"):
        raise RoleDM5Error("PR-E value_diagnostic does not match the frozen diagnostic hash")
    return run, results


def _select_pr_f_artifact(results: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    matches = [
        row
        for row in results
        if row.get("cohort") == PRODUCTION_COHORT
        and row.get("feature_group") == PRODUCTION_FEATURE_GROUP
    ]
    if len(matches) != 1:
        raise RoleDM5Error("PR-F must contain exactly one full_production PM result")
    artifact = matches[0]
    if artifact.get("evaluation_protocol") != "development_fit_2024_validation":
        raise RoleDM5Error("PR-F production result is not the frozen 2024 Validation run")
    _require_false(artifact, "blind_2025_y_accessed", "PR-F production result")
    return artifact


def _select_pr_e_artifact(results: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    matches = [
        row
        for row in results
        if row.get("cohort") == PRODUCTION_COHORT
        and row.get("feature_group") == PRODUCTION_FEATURE_GROUP
        and row.get("model_family") == PR_E_MODEL_NAME
        and row.get("evaluation_protocol") == "development_fit_2024_validation"
    ]
    if len(matches) != 1:
        raise RoleDM5Error("PR-E must contain exactly one full_production PM logistic result")
    return matches[0]


def _top_drivers(artifact: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = (artifact.get("explainability") or {}).get("single_ipo_drivers") or []
    return {
        str(row["case_id"]): list(row.get("top_drivers") or [])
        for row in rows
        if isinstance(row, dict) and row.get("case_id")
    }


def _top_fraction_hit_rate(labels: np.ndarray, scores: np.ndarray, fraction: float) -> float:
    count = max(1, int(math.ceil(len(labels) * fraction)))
    order = sorted(range(len(labels)), key=lambda index: (-scores[index], index))
    return float(np.mean(labels[order[:count]]))


def five_day_metrics(labels: Sequence[bool], scores: Sequence[float], threshold: float) -> dict[str, Any]:
    y = np.asarray(labels, dtype=int)
    score = np.asarray(scores, dtype=float)
    if len(y) == 0 or len(y) != len(score):
        raise RoleDM5Error("five-day metric inputs are empty or misaligned")
    if not np.isfinite(score).all():
        raise RoleDM5Error("five-day scores must be finite")
    predicted = (score >= threshold).astype(int)
    both = len(np.unique(y)) == 2
    return {
        "sample_count": int(len(y)),
        "positive_count": int(np.sum(y)),
        "base_prevalence": float(np.mean(y)),
        "classification_threshold": float(threshold),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "pr_auc": float(average_precision_score(y, score)) if both else None,
        "roc_auc": float(roc_auc_score(y, score)) if both else None,
        "top_10pct_hit_rate": _top_fraction_hit_rate(y, score, 0.10),
        "top_20pct_hit_rate": _top_fraction_hit_rate(y, score, 0.20),
        "top_fraction_definition": "positive_rate_within_highest_scoring_fraction",
    }


def compile_payloads(
    *,
    pr_f_results: Sequence[Mapping[str, Any]],
    pr_e_results: Sequence[Mapping[str, Any]],
    metadata_by_case: Mapping[str, Any],
    bars_for_stock: Callable[[str, Any], Sequence[Any]],
    market_source: Mapping[str, Any],
    source_hashes: Mapping[str, str],
) -> RoleDPayloads:
    """Create deterministic Role-D payloads from already-verified inputs."""

    pr_f = _select_pr_f_artifact(pr_f_results)
    pr_e = _select_pr_e_artifact(pr_e_results)
    case_predictions = list(pr_f.get("case_predictions") or [])
    if not case_predictions:
        raise RoleDM5Error("PR-F production result contains no case predictions")
    drivers = _top_drivers(pr_f)
    classification_threshold = float(
        (pr_f.get("classification_metrics") or {}).get("classification_threshold", 0.5)
    )

    horizon_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    labels: list[bool] = []
    scores: list[float] = []
    seen: set[str] = set()
    for predicted in case_predictions:
        case_id = str(predicted.get("case_id") or "")
        if not case_id or case_id in seen:
            raise RoleDM5Error("PR-F case predictions require unique non-empty case IDs")
        seen.add(case_id)
        metadata = metadata_by_case.get(case_id)
        if metadata is None:
            raise RoleDM5Error(f"governed EOD metadata is missing case {case_id}")
        if metadata.cohort_year != 2024:
            raise RoleDM5Error(f"Role-D final evaluation accepts 2024 Validation only: {case_id}")
        if metadata.listing_price is None or Decimal(metadata.listing_price) <= 0:
            raise RoleDM5Error(f"missing positive official listing price: {case_id}")
        if metadata.listing_date is None:
            raise RoleDM5Error(f"missing official listing date: {case_id}")
        bars = list(bars_for_stock(metadata.stock_code, metadata.listing_date))
        if len(bars) < HORIZON_SESSIONS["60d"]:
            raise RoleDM5Error(f"fewer than 60 governed sessions for {case_id}")

        returns: dict[str, Decimal] = {}
        dates: dict[str, str] = {}
        base = Decimal(metadata.listing_price)
        for name, sessions in HORIZON_SESSIONS.items():
            bar = bars[sessions - 1]
            returns[name] = Decimal(bar.close) / base - Decimal(1)
            dates[name] = bar.trading_date.isoformat()
        frozen_return_5d = float(predicted["raw_return_5d"])
        if not math.isclose(float(returns["5d"]), frozen_return_5d, rel_tol=0, abs_tol=1e-10):
            raise RoleDM5Error(f"governed 5D return disagrees with frozen PR-F for {case_id}")

        actual_drop = returns["5d"] <= SIGNIFICANT_DROP_5D_THRESHOLD
        frozen_drop = bool(predicted["poor_performer_5d"])
        if actual_drop != frozen_drop:
            raise RoleDM5Error(f"governed 5D label disagrees with frozen PR-F for {case_id}")
        score = float(predicted["poor_performer_score"])
        if not math.isfinite(score):
            raise RoleDM5Error(f"non-finite frozen PR-F score for {case_id}")
        labels.append(actual_drop)
        scores.append(score)

        horizon_rows.append(
            {
                "case_id": case_id,
                "stock_code": metadata.stock_code,
                "cohort_year": 2024,
                "dataset_split": "validation",
                "listing_date": metadata.listing_date.isoformat(),
                **{f"return_{name}": float(returns[name]) for name in HORIZON_SESSIONS},
                **{f"target_trading_date_{name}": dates[name] for name in HORIZON_SESSIONS},
                "significant_drop_5d": actual_drop,
            }
        )
        prediction_rows.append(
            {
                "case_id": case_id,
                "stock_code": metadata.stock_code,
                "cohort_year": 2024,
                "dataset_split": "validation",
                "model": PR_F_MODEL_NAME,
                "feature_group": PRODUCTION_FEATURE_GROUP,
                "poor_performer_score": score,
                "score_semantics": "uncalibrated_model_score_not_probability",
                "classification_threshold": classification_threshold,
                "predicted_significant_drop_5d": score >= classification_threshold,
                "predicted_return_5d": float(predicted["raw_return_5d_prediction"]),
                "actual_significant_drop_5d": actual_drop,
                "actual_return_5d": float(returns["5d"]),
                "top_shap_drivers_json": json.dumps(
                    drivers.get(case_id, []), ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            }
        )

    horizon_rows.sort(key=lambda row: row["case_id"])
    prediction_rows.sort(key=lambda row: row["case_id"])
    metrics = five_day_metrics(labels, scores, classification_threshold)
    frozen_metrics = pr_f.get("classification_metrics") or {}
    for key in ("precision", "recall", "f1", "pr_auc", "roc_auc"):
        expected = frozen_metrics.get(key)
        actual = metrics.get(key)
        if expected is not None and actual is not None and not math.isclose(
            float(expected), float(actual), rel_tol=0, abs_tol=1e-12
        ):
            raise RoleDM5Error(f"recomputed PR-F metric drift: {key}")

    baseline_metrics = dict(pr_e.get("metrics") or {})
    metric_deltas = {
        key: (
            None
            if metrics.get(key) is None or baseline_metrics.get(key) is None
            else float(metrics[key]) - float(baseline_metrics[key])
        )
        for key in ("precision", "recall", "f1", "pr_auc", "roc_auc")
    }
    summary = {
        "role_d_m5_version": ROLE_D_M5_VERSION,
        "metric_protocol_version": METRIC_PROTOCOL_VERSION,
        "status": "complete",
        "evaluation_split": "2024_validation",
        "evaluation_count": len(horizon_rows),
        "horizons": ["1D", "5D", "20D", "60D"],
        "significant_drop_5d_definition": "return_5d <= -0.10",
        "five_day_metrics": metrics,
        "market_source": dict(market_source),
        "source_hashes": dict(sorted(source_hashes.items())),
        "score_semantics": "uncalibrated_model_score_not_probability",
        "threshold_or_model_retuned_on_validation": False,
        "blind_2025_y_accessed": False,
    }
    comparison = {
        "role_d_m5_version": ROLE_D_M5_VERSION,
        "comparison_scope": "same_2024_validation_full_production_PM",
        "ai_model": {
            "name": "frozen_lightgbm",
            "metrics": metrics,
            "score_semantics": "uncalibrated_model_score_not_probability",
        },
        "offline_baseline": {
            "name": "frozen_logistic_regression",
            "metrics": baseline_metrics,
        },
        "ai_minus_offline": metric_deltas,
        "interpretation_policy": "descriptive_only_no_validation_retuning",
        "threshold_or_model_retuned_on_validation": False,
        "blind_2025_y_accessed": False,
    }
    return RoleDPayloads(
        predictions=tuple(prediction_rows),
        horizons=tuple(horizon_rows),
        evaluation_summary=summary,
        ai_vs_offline=comparison,
    )


def _write_text(path: Path, content: str, *, resume: bool) -> None:
    if path.exists() and resume:
        if path.read_text(encoding="utf-8") != content:
            raise RoleDM5Error(f"Role-D resume conflict: {path}")
        return
    if path.exists() and not resume:
        raise RoleDM5Error(f"Role-D output exists; use --resume: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _csv_text(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        raise RoleDM5Error("Role-D CSV output cannot be empty")
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def write_payloads(output_dir: Path, payloads: RoleDPayloads, *, resume: bool = False) -> dict[str, str]:
    rendered = {
        "test_predictions.csv": _csv_text(payloads.predictions),
        "multi_horizon_results.csv": _csv_text(payloads.horizons),
        "evaluation_summary.json": json.dumps(
            payloads.evaluation_summary, ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n",
        "ai_vs_offline_report.json": json.dumps(
            payloads.ai_vs_offline, ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n",
    }
    for name, content in rendered.items():
        _write_text(output_dir / name, content, resume=resume)
    return {name: sha256_file(output_dir / name) for name in sorted(rendered)}


def build_role_d_handoff(
    *,
    pr_f_run_dir: Path,
    pr_f_frozen_manifest: Path,
    pr_e_run_dir: Path,
    pr_e_frozen_manifest: Path,
    market_provider: Any,
    output_dir: Path,
    resume: bool = False,
) -> dict[str, Any]:
    pr_f_run, pr_f_results, _ = _verify_pr_f_runtime(
        pr_f_run_dir, pr_f_frozen_manifest
    )
    pr_e_run, pr_e_results = _verify_pr_e_runtime(
        pr_e_run_dir, pr_e_frozen_manifest
    )
    metadata = {
        item.case_id: item
        for item in market_provider.iter_listing_metadata()
        if item.cohort_year == 2024
    }

    def bars_for_stock(stock_code: str, listing_date: Any) -> Sequence[Any]:
        return market_provider.get_daily_bars(stock_code, start_date=listing_date)

    payloads = compile_payloads(
        pr_f_results=pr_f_results,
        pr_e_results=pr_e_results,
        metadata_by_case=metadata,
        bars_for_stock=bars_for_stock,
        market_source=market_provider.provider_identity,
        source_hashes={
            "pr_f_run_manifest_sha256": sha256_file(pr_f_run_dir / "run_manifest.json"),
            "pr_f_model_results_sha256": sha256_file(pr_f_run_dir / "model_results.json"),
            "pr_e_run_manifest_sha256": sha256_file(pr_e_run_dir / "run_manifest.json"),
            "pr_e_baseline_results_sha256": sha256_file(pr_e_run_dir / "baseline_results.json"),
            "pr_f_frozen_manifest_sha256": sha256_file(pr_f_frozen_manifest),
            "pr_e_frozen_manifest_sha256": sha256_file(pr_e_frozen_manifest),
        },
    )
    output_hashes = write_payloads(output_dir, payloads, resume=resume)
    return {
        "status": payloads.evaluation_summary["status"],
        "evaluation_count": payloads.evaluation_summary["evaluation_count"],
        "output_hashes": output_hashes,
        "pr_f_model_result_hash": pr_f_run["model_result_hash"],
        "pr_e_results_hash": pr_e_run["results_hash"],
        "blind_2025_y_accessed": False,
    }
