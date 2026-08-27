from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from ipo_risk.evaluation.role_d_m5 import (
    RoleDM5Error,
    compile_payloads,
    five_day_metrics,
    write_payloads,
)


def _fixture(*, cohort_year: int = 2024, corrupt_five_day: bool = False):
    scores = [0.92, 0.15, 0.81, 0.25, 0.65, 0.45, 0.35, 0.72, 0.05, 0.55]
    labels = [True, False, True, False, True, False, False, True, False, False]
    returns_5d = [-0.20 if label else 0.04 for label in labels]
    metrics = five_day_metrics(labels, scores, 0.5)
    predictions = []
    metadata = {}
    bars = {}
    driver_rows = []
    for index, (score, label, return_5d) in enumerate(
        zip(scores, labels, returns_5d, strict=True)
    ):
        case_id = f"ipo-2024-{index:03d}"
        stock_code = f"{index + 1:04d}.HK"
        predictions.append(
            {
                "case_id": case_id,
                "poor_performer_5d": label,
                "poor_performer_score": score,
                "raw_return_5d": return_5d,
                "raw_return_5d_prediction": -0.12 if label else 0.02,
            }
        )
        metadata[case_id] = SimpleNamespace(
            case_id=case_id,
            stock_code=stock_code,
            cohort_year=cohort_year,
            listing_date=date(cohort_year, 1, 2),
            listing_price=Decimal("100"),
        )
        closes = [Decimal("101")] * 60
        closes[4] = Decimal(str(100 * return_5d + 100))
        if corrupt_five_day and index == 0:
            closes[4] = Decimal("99")
        bars[stock_code] = [
            SimpleNamespace(
                trading_date=date(cohort_year, 1, 2) + timedelta(days=day),
                close=close,
            )
            for day, close in enumerate(closes)
        ]
        driver_rows.append(
            {
                "case_id": case_id,
                "top_drivers": [{"feature": "market_core__signal", "shap": score}],
            }
        )
    pr_f = [
        {
            "cohort": "full_production",
            "feature_group": "PM",
            "evaluation_protocol": "development_fit_2024_validation",
            "blind_2025_y_accessed": False,
            "classification_metrics": metrics,
            "case_predictions": predictions,
            "explainability": {"single_ipo_drivers": driver_rows},
        }
    ]
    pr_e = [
        {
            "cohort": "full_production",
            "feature_group": "PM",
            "model_family": "logistic_regression",
            "evaluation_protocol": "development_fit_2024_validation",
            "metrics": {
                "precision": 0.75,
                "recall": 0.75,
                "f1": 0.75,
                "pr_auc": 0.80,
                "roc_auc": 0.80,
            },
        }
    ]
    return pr_f, pr_e, metadata, bars


def _compile(*, cohort_year: int = 2024, corrupt_five_day: bool = False):
    pr_f, pr_e, metadata, bars = _fixture(
        cohort_year=cohort_year, corrupt_five_day=corrupt_five_day
    )
    return compile_payloads(
        pr_f_results=pr_f,
        pr_e_results=pr_e,
        metadata_by_case=metadata,
        bars_for_stock=lambda stock_code, _listing_date: bars[stock_code],
        market_source={"provider": "governed-test-store"},
        source_hashes={"pr_f": "a" * 64, "pr_e": "b" * 64},
    )


def test_role_d_compiles_governed_four_horizon_handoff() -> None:
    payloads = _compile()

    assert len(payloads.predictions) == 10
    assert len(payloads.horizons) == 10
    assert payloads.horizons[0]["return_5d"] == pytest.approx(-0.20)
    assert {"return_1d", "return_5d", "return_20d", "return_60d"} <= set(
        payloads.horizons[0]
    )
    assert payloads.predictions[0]["score_semantics"] == (
        "uncalibrated_model_score_not_probability"
    )
    assert json.loads(payloads.predictions[0]["top_shap_drivers_json"])[0][
        "feature"
    ] == "market_core__signal"
    summary = payloads.evaluation_summary
    assert summary["status"] == "complete"
    assert summary["evaluation_split"] == "2024_validation"
    assert summary["five_day_metrics"]["sample_count"] == 10
    assert summary["five_day_metrics"]["base_prevalence"] == pytest.approx(0.4)
    assert summary["blind_2025_y_accessed"] is False
    assert payloads.ai_vs_offline["interpretation_policy"] == (
        "descriptive_only_no_validation_retuning"
    )


def test_role_d_rejects_blind_year_or_frozen_five_day_drift() -> None:
    with pytest.raises(RoleDM5Error, match="2024 Validation only"):
        _compile(cohort_year=2025)
    with pytest.raises(RoleDM5Error, match="5D return disagrees"):
        _compile(corrupt_five_day=True)


def test_role_d_rejects_missing_frozen_classification_threshold() -> None:
    pr_f, pr_e, metadata, bars = _fixture()
    del pr_f[0]["classification_metrics"]["classification_threshold"]
    with pytest.raises(RoleDM5Error, match="classification threshold is missing"):
        compile_payloads(
            pr_f_results=pr_f,
            pr_e_results=pr_e,
            metadata_by_case=metadata,
            bars_for_stock=lambda stock_code, _listing_date: bars[stock_code],
            market_source={"provider": "governed-test-store"},
            source_hashes={"pr_f": "a" * 64, "pr_e": "b" * 64},
        )


def test_role_d_writes_exact_submission_files_and_resume_is_safe(tmp_path) -> None:
    payloads = _compile()
    first_hashes = write_payloads(tmp_path, payloads)
    second_hashes = write_payloads(tmp_path, payloads, resume=True)

    assert first_hashes == second_hashes
    assert set(first_hashes) == {
        "test_predictions.csv",
        "multi_horizon_results.csv",
        "evaluation_summary.json",
        "ai_vs_offline_report.json",
    }
    with (tmp_path / "test_predictions.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 10
    assert rows[0]["dataset_split"] == "validation"
    with pytest.raises(RoleDM5Error, match="output exists"):
        write_payloads(tmp_path, payloads)
