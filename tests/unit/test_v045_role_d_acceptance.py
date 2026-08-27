from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from ipo_risk.evaluation.role_d_acceptance import check_role_d_acceptance
from ipo_risk.evaluation.role_d_m5 import build_role_d_handoff, five_day_metrics, sha256_file
from ipo_risk.market.eod_store import OUTPUT_COLUMNS, build_store
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider
from ipo_risk.schemas.canonical_modeling import canonical_hash


REPO_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = REPO_ROOT / "configs" / "v045_competition_metric_protocol.json"


def _write_csv(path: Path, fieldnames, rows, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fixture(tmp_path: Path, *, invalid_eod_rows: int = 0) -> dict[str, Path]:
    catalog = tmp_path / "catalog"
    raw_root = tmp_path / "raw"
    cache = tmp_path / "cache"
    pr_f_dir = tmp_path / "pr_f"
    pr_e_dir = tmp_path / "pr_e"
    frozen = tmp_path / "frozen"
    role_d = tmp_path / "role_d"
    for path in (catalog, raw_root, pr_f_dir, pr_e_dir, frozen):
        path.mkdir(parents=True)

    listing_date = date(2024, 1, 2)
    bridge_rows = []
    prospectus_rows = []
    eod_rows = []
    labels: list[bool] = []
    scores: list[float] = []
    baseline_scores: list[float] = []
    case_predictions = []
    driver_rows = []
    for index in range(1, 71):
        case_id = f"ipo_2024_{index:05d}"
        stock_code = f"{index:04d}.HK"
        label = index % 3 == 0
        return_5d = -0.20 if label else 0.05
        score = ((index * 17) % 100) / 100
        baseline_score = ((index * 11) % 100) / 100
        labels.append(label)
        scores.append(score)
        baseline_scores.append(baseline_score)
        bridge_rows.append(
            {
                "case_id": case_id,
                "stock_code_wind": stock_code,
                "official_listed_date": listing_date.isoformat(),
                "official_ipo_price": "100",
                "official_match_status": "matched",
            }
        )
        prospectus_rows.append({"case_id": case_id, "sha256": f"{index:064x}"})
        for session in range(60):
            trading_date = listing_date + timedelta(days=session)
            close = 100 * (1 + return_5d) if session == 4 else 101 + (session / 100)
            eod_rows.append(
                {
                    "OBJECT_ID": f"{case_id}-{session + 1}",
                    "S_INFO_WINDCODE": stock_code,
                    "TRADE_DT": trading_date.strftime("%Y%m%d"),
                    "S_DQ_OPEN": "100",
                    "S_DQ_HIGH": "130",
                    "S_DQ_LOW": "70",
                    "S_DQ_CLOSE": f"{close:.10f}",
                    "S_DQ_VOLUME": "1000",
                    "S_DQ_AMOUNT": "10000",
                    "S_DQ_PRECLOSE": "100",
                    "S_DQ_ADJCLOSE": f"{close:.10f}",
                }
            )
        case_predictions.append(
            {
                "case_id": case_id,
                "poor_performer_5d": label,
                "poor_performer_score": score,
                "raw_return_5d": return_5d,
                "raw_return_5d_prediction": -0.12 if label else 0.02,
            }
        )
        driver_rows.append(
            {
                "case_id": case_id,
                "top_drivers": [
                    {
                        "feature": "market_core__signal",
                        "component": "market_core",
                        "feature_value": float(index),
                        "shap_value": score - 0.5,
                    }
                ],
            }
        )

    for index in range(invalid_eod_rows):
        invalid_date = listing_date + timedelta(days=60 + index)
        eod_rows.append(
            {
                "OBJECT_ID": f"invalid-price-{index}",
                "S_INFO_WINDCODE": "0001.HK",
                "TRADE_DT": invalid_date.strftime("%Y%m%d"),
                "S_DQ_OPEN": "100",
                "S_DQ_HIGH": "130",
                "S_DQ_LOW": "70",
                "S_DQ_CLOSE": "0",
                "S_DQ_VOLUME": "1000",
                "S_DQ_AMOUNT": "10000",
                "S_DQ_PRECLOSE": "100",
                "S_DQ_ADJCLOSE": "0",
            }
        )

    _write_csv(catalog / "ipo_official_master_bridge.csv", list(bridge_rows[0]), bridge_rows)
    _write_csv(catalog / "ipo_prospectus_manifest.csv", ["case_id", "sha256"], prospectus_rows)
    raw_path = raw_root / "hkshareeodprices.csv"
    _write_csv(raw_path, OUTPUT_COLUMNS, eod_rows, encoding="gb18030")
    _write_json(
        catalog / "v04_source_manifest.json",
        {
            "entries": [
                {
                    "logical_id": "ipo_eod",
                    "sha256": sha256_file(raw_path),
                    "coverage": {"invalid_ohlcv_rows": invalid_eod_rows},
                    "provenance": {"invalid_row_policy": "exclude_and_report"},
                }
            ]
        },
    )
    build_store(
        data_root=raw_root,
        catalog_dir=catalog,
        cache_dir=cache,
        expected_case_count=70,
    )

    pr_f_metrics = five_day_metrics(labels, scores, 0.5)
    pr_f_results = [
        {
            "cohort": "full_production",
            "feature_group": "PM",
            "evaluation_protocol": "development_fit_2024_validation",
            "development_count": 354,
            "evaluation_count": 70,
            "blind_2025_y_accessed": False,
            "classification_metrics": pr_f_metrics,
            "case_predictions": case_predictions,
            "explainability": {"single_ipo_drivers": driver_rows},
        }
    ]
    pr_f_hash = canonical_hash(pr_f_results)
    pr_f_run = {"model_result_hash": pr_f_hash, "blind_2025_y_accessed": False}
    pr_f_comparison = {"status": "complete", "blind_2025_y_accessed": False}
    _write_json(pr_f_dir / "run_manifest.json", pr_f_run)
    _write_json(pr_f_dir / "model_results.json", pr_f_results)
    _write_json(pr_f_dir / "model_comparison.json", pr_f_comparison)

    pr_e_metrics = five_day_metrics(labels, baseline_scores, 0.5)
    pr_e_results = [
        {
            "cohort": "full_production",
            "feature_group": "PM",
            "model_family": "logistic_regression",
            "evaluation_protocol": "development_fit_2024_validation",
            "development_count": 354,
            "evaluation_count": 70,
            "metrics": pr_e_metrics,
        }
    ]
    diagnostic = {"status": "complete", "blind_2025_y_accessed": False}
    pr_e_hash = canonical_hash(pr_e_results)
    diagnostic_hash = canonical_hash(diagnostic)
    pr_e_run = {
        "results_hash": pr_e_hash,
        "diagnostic_hash": diagnostic_hash,
        "blind_2025_y_accessed": False,
    }
    _write_json(pr_e_dir / "run_manifest.json", pr_e_run)
    _write_json(pr_e_dir / "baseline_results.json", pr_e_results)
    _write_json(pr_e_dir / "value_diagnostic.json", diagnostic)

    pr_f_manifest = frozen / "v04_pr_f_lightgbm_manifest.json"
    _write_json(
        pr_f_manifest,
        {
            "status": "complete_frozen",
            "formal_gate_passed": True,
            "blind_2025_y_accessed": False,
            "cohorts": {"full_production": {"development": 354, "validation": 70}},
            "runtime_outputs": {
                "run_manifest_sha256": sha256_file(pr_f_dir / "run_manifest.json"),
                "model_results_sha256": sha256_file(pr_f_dir / "model_results.json"),
                "model_comparison_sha256": sha256_file(pr_f_dir / "model_comparison.json"),
            },
            "model_result_hash": pr_f_hash,
        },
    )
    pr_e_manifest = frozen / "v04_pr_e_baseline_manifest.json"
    _write_json(
        pr_e_manifest,
        {
            "status": "complete_frozen",
            "formal_gate_passed": True,
            "blind_2025_y_accessed": False,
            "cohorts": {"full_production": {"development": 354, "validation": 70}},
            "runtime_outputs": {
                "reports/v04_pr_e/run_manifest.json": {
                    "sha256": sha256_file(pr_e_dir / "run_manifest.json")
                },
                "reports/v04_pr_e/baseline_results.json": {
                    "sha256": sha256_file(pr_e_dir / "baseline_results.json")
                },
                "reports/v04_pr_e/value_diagnostic.json": {
                    "sha256": sha256_file(pr_e_dir / "value_diagnostic.json")
                },
            },
            "results_hash": pr_e_hash,
            "diagnostic_hash": diagnostic_hash,
        },
    )

    provider = FilteredEODV2MarketDataProvider(
        store_path=cache / "v04_ipo_eod.csv",
        manifest_path=cache / "v04_ipo_eod.manifest.json",
        catalog_dir=catalog,
        expected_case_count=70,
    )
    build_role_d_handoff(
        pr_f_run_dir=pr_f_dir,
        pr_f_frozen_manifest=pr_f_manifest,
        pr_e_run_dir=pr_e_dir,
        pr_e_frozen_manifest=pr_e_manifest,
        market_provider=provider,
        output_dir=role_d,
    )
    return {
        "catalog": catalog,
        "cache": cache,
        "pr_f": pr_f_dir,
        "pr_e": pr_e_dir,
        "pr_f_manifest": pr_f_manifest,
        "pr_e_manifest": pr_e_manifest,
        "role_d": role_d,
    }


def _check(paths: dict[str, Path]) -> dict:
    return check_role_d_acceptance(
        role_d_dir=paths["role_d"],
        pr_f_run_dir=paths["pr_f"],
        pr_e_run_dir=paths["pr_e"],
        pr_f_frozen_manifest=paths["pr_f_manifest"],
        pr_e_frozen_manifest=paths["pr_e_manifest"],
        filtered_eod_store=paths["cache"] / "v04_ipo_eod.csv",
        filtered_eod_manifest=paths["cache"] / "v04_ipo_eod.manifest.json",
        catalog_dir=paths["catalog"],
        metric_protocol=PROTOCOL,
        expected_official_case_count=70,
    )


def _mutate_csv(path: Path, mutate) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or ())
    mutate(rows, fieldnames)
    _write_csv(path, fieldnames, rows)


def test_strict_role_d_acceptance_passes_complete_governed_fixture(tmp_path: Path) -> None:
    report = _check(_fixture(tmp_path))
    assert report["passed"] is True, report["blockers"]
    assert report["verdict"] == "PASS"
    assert report["expected_validation_count"] == 70
    assert all(item["passed"] for item in report["checks"])


def test_cataloged_excluded_invalid_eod_rows_are_governed_not_a_false_failure(
    tmp_path: Path,
) -> None:
    report = _check(_fixture(tmp_path, invalid_eod_rows=1))
    assert report["passed"] is True, report["blockers"]
    check = next(item for item in report["checks"] if item["name"] == "governed_filtered_eod")
    assert check["detail"]["invalid_price_rows"] == 1
    assert check["detail"]["cataloged_invalid_price_rows"] == 1
    assert check["detail"]["invalid_row_policy"] == "exclude_and_report"


def test_cataloged_invalid_eod_row_count_drift_fails_closed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    source_manifest = paths["catalog"] / "v04_source_manifest.json"
    payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    payload["entries"][0]["coverage"]["invalid_ohlcv_rows"] = 1
    _write_json(source_manifest, payload)
    report = _check(paths)
    check = next(item for item in report["checks"] if item["name"] == "governed_filtered_eod")
    assert check["passed"] is False
    assert check["detail"]["invalid_price_rows"] == 0
    assert check["detail"]["cataloged_invalid_price_rows"] == 1


def test_missing_fourth_formal_artifact_fails_closed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    (paths["role_d"] / "ai_vs_offline_report.json").unlink()
    report = _check(paths)
    assert report["passed"] is False
    assert report["checks"][0]["name"] == "canonical_four_file_contract"


@pytest.mark.parametrize(
    ("mutation", "expected_check"),
    [
        ("missing_horizon_column", "artifact_columns"),
        ("short_case_set", "exact_2024_validation_case_set"),
        ("duplicate_case", "exact_2024_validation_case_set"),
        ("blind_case", "independent_row_and_session_validation"),
        ("wrong_split", "independent_row_and_session_validation"),
        ("wrong_5d_label", "independent_row_and_session_validation"),
        ("wrong_predicted_label", "independent_row_and_session_validation"),
        ("probability_semantics", "independent_row_and_session_validation"),
        ("wrong_target_date", "independent_row_and_session_validation"),
    ],
)
def test_strict_checker_rejects_case_and_row_corruption(
    tmp_path: Path, mutation: str, expected_check: str
) -> None:
    paths = _fixture(tmp_path)
    prediction_path = paths["role_d"] / "test_predictions.csv"
    horizon_path = paths["role_d"] / "multi_horizon_results.csv"
    if mutation == "missing_horizon_column":
        _mutate_csv(
            horizon_path,
            lambda rows, fields: (
                fields.remove("return_60d"),
                [row.pop("return_60d") for row in rows],
            ),
        )
    elif mutation == "short_case_set":
        _mutate_csv(prediction_path, lambda rows, _: rows.pop())
    elif mutation == "duplicate_case":
        _mutate_csv(prediction_path, lambda rows, _: rows.__setitem__(1, dict(rows[1], case_id=rows[0]["case_id"])))
    elif mutation == "blind_case":
        _mutate_csv(prediction_path, lambda rows, _: rows[0].__setitem__("cohort_year", "2025"))
    elif mutation == "wrong_split":
        _mutate_csv(horizon_path, lambda rows, _: rows[0].__setitem__("dataset_split", "development"))
    elif mutation == "wrong_5d_label":
        _mutate_csv(horizon_path, lambda rows, _: rows[0].__setitem__("significant_drop_5d", "True" if rows[0]["significant_drop_5d"] == "False" else "False"))
    elif mutation == "wrong_predicted_label":
        _mutate_csv(prediction_path, lambda rows, _: rows[0].__setitem__("predicted_significant_drop_5d", "True" if rows[0]["predicted_significant_drop_5d"] == "False" else "False"))
    elif mutation == "probability_semantics":
        _mutate_csv(prediction_path, lambda rows, _: rows[0].__setitem__("score_semantics", "probability"))
    elif mutation == "wrong_target_date":
        _mutate_csv(horizon_path, lambda rows, _: rows[0].__setitem__("target_trading_date_60d", "2024-12-31"))
    report = _check(paths)
    failed = {item["name"] for item in report["checks"] if not item["passed"]}
    assert expected_check in failed


@pytest.mark.parametrize(
    "mutation",
    ["metric", "source_hash", "blind", "retuned", "delta", "absolute_path"],
)
def test_strict_checker_rejects_summary_and_comparison_corruption(
    tmp_path: Path, mutation: str
) -> None:
    paths = _fixture(tmp_path)
    summary_path = paths["role_d"] / "evaluation_summary.json"
    comparison_path = paths["role_d"] / "ai_vs_offline_report.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    if mutation == "metric":
        summary["five_day_metrics"]["precision"] += 0.1
    elif mutation == "source_hash":
        summary["source_hashes"]["pr_f_model_results_sha256"] = "0" * 64
    elif mutation == "blind":
        summary["blind_2025_y_accessed"] = True
    elif mutation == "retuned":
        comparison["threshold_or_model_retuned_on_validation"] = True
    elif mutation == "delta":
        comparison["ai_minus_offline"]["f1"] += 0.1
    elif mutation == "absolute_path":
        summary["debug_path"] = "C:\\Users\\someone\\private\\runtime"
    _write_json(summary_path, summary)
    _write_json(comparison_path, comparison)
    report = _check(paths)
    assert report["passed"] is False


def test_strict_checker_rejects_fewer_than_60_governed_sessions(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    store = paths["cache"] / "v04_ipo_eod.csv"
    with store.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or ())
    removed = next(
        index
        for index, row in enumerate(rows)
        if row["S_INFO_WINDCODE"] == "0001.HK"
    )
    rows.pop(removed)
    _write_csv(store, fieldnames, rows)
    manifest_path = paths["cache"] / "v04_ipo_eod.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_count"] -= 1
    _write_json(manifest_path, manifest)

    report = _check(paths)

    assert report["passed"] is False
    row_check = next(
        item
        for item in report["checks"]
        if item["name"] == "independent_row_and_session_validation"
    )
    assert any("fewer than 60 governed sessions" in error for error in row_check["detail"]["errors"])


def test_extra_file_in_canonical_directory_is_rejected(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    (paths["role_d"] / "helper.json").write_text("{}", encoding="utf-8")
    report = _check(paths)
    assert report["passed"] is False
    assert report["checks"][0]["detail"]["extra"] == ["helper.json"]


def test_extra_directory_in_canonical_directory_is_rejected(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    (paths["role_d"] / "helper").mkdir()
    report = _check(paths)
    assert report["passed"] is False
    assert report["checks"][0]["detail"]["extra"] == ["helper"]
    assert report["checks"][0]["detail"]["non_file_entries"] == ["helper"]


def test_checker_cli_failure_returns_nonzero_and_writes_outside_canonical(tmp_path: Path) -> None:
    role_d = tmp_path / "role_d"
    role_d.mkdir()
    output = tmp_path / "acceptance" / "acceptance.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "check_v045_role_d_m5.py"),
            "--role-d-dir",
            str(role_d),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is False
