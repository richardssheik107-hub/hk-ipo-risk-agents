"""Contract tests for the label-free PR-F product handoff."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from ipo_risk.modeling.pr_f_product_handoff import (
    PRODUCT_CHECKSUMS_NAME,
    PRODUCT_MANIFEST_NAME,
    PRODUCT_README_NAME,
    PRODUCT_SIGNALS_NAME,
    PRODUCT_FILES,
    ProductRuntimeHandoffError,
    project_case_signals_from_role_d_predictions,
    read_product_case_signal,
    validate_product_handoff,
    write_receipt_bound_product_handoff,
    write_product_handoff,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash


def _payload() -> list[dict]:
    return [{
        "cohort": "full_production",
        "feature_group": "PM",
        "case_predictions": [
            {
                "case_id": "ipo_2024_00001",
                "poor_performer_score": 0.25,
                "poor_performer_5d": False,
                "raw_return_5d": 0.1,
            },
            {
                "case_id": "ipo_2024_00002",
                "poor_performer_score": 0.75,
                "poor_performer_5d": True,
                "raw_return_5d": -0.2,
            },
        ],
        "explainability": {"single_ipo_drivers": [{
            "case_id": "ipo_2024_00001",
            "top_drivers": [{
                "feature": "market_core__prior_ipo_count_20d",
                "component": "market_core",
                "feature_value": 3.0,
                "shap_value": -0.125,
            }],
        }]},
    }]


def _source(tmp_path: Path, *, blind: bool = False, claimed_hash: str | None = None) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    payload = _payload()
    result_hash = canonical_hash(payload)
    (source / "run_manifest.json").write_text(json.dumps({
        "model_result_hash": claimed_hash or result_hash,
        "blind_2025_y_accessed": blind,
    }), encoding="utf-8")
    (source / "model_results.json").write_text(json.dumps(payload), encoding="utf-8")
    return source, result_hash


def _write(tmp_path: Path) -> tuple[Path, str]:
    source, result_hash = _source(tmp_path)
    output = tmp_path / "handoff"
    write_product_handoff(
        source,
        output,
        expected_source_model_result_hash=result_hash,
        case_ids=["ipo_2024_00001", "ipo_2024_00002"],
        source_pr_f={"pr_f_version": "frozen-v1", "execution_revision": "abc"},
    )
    return output, result_hash


def test_writes_only_the_four_governed_artifacts(tmp_path) -> None:
    output, _ = _write(tmp_path)
    assert {path.name for path in output.iterdir()} == {
        PRODUCT_MANIFEST_NAME, PRODUCT_SIGNALS_NAME, PRODUCT_CHECKSUMS_NAME, PRODUCT_README_NAME,
    }


def test_projection_contains_no_target_labels(tmp_path) -> None:
    output, _ = _write(tmp_path)
    signals = json.loads((output / PRODUCT_SIGNALS_NAME).read_text(encoding="utf-8"))
    assert set(signals[0]) == {"case_id", "score", "drivers"}
    serialized = json.dumps(signals)
    assert "poor_performer_5d" not in serialized
    assert "raw_return_5d" not in serialized


def test_manifest_binds_source_and_signal_hash(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    manifest = json.loads((output / PRODUCT_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["source_model_result_hash"] == result_hash
    assert manifest["source_pr_f"]["execution_revision"] == "abc"
    assert manifest["contains_target_labels"] is False
    assert manifest["blind_2025_y_accessed"] is False
    actual = hashlib.sha256((output / PRODUCT_SIGNALS_NAME).read_bytes()).hexdigest()
    assert manifest["case_signal_sha256"] == actual


def test_checksums_cover_manifest_signals_and_readme(tmp_path) -> None:
    output, _ = _write(tmp_path)
    checksums = (output / PRODUCT_CHECKSUMS_NAME).read_text(encoding="utf-8")
    assert PRODUCT_MANIFEST_NAME in checksums
    assert PRODUCT_SIGNALS_NAME in checksums
    assert PRODUCT_README_NAME in checksums


def test_reader_returns_exact_score_and_driver_direction(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    signal = read_product_case_signal(
        output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
    )
    assert signal is not None
    score, drivers = signal
    assert score == 0.25
    assert drivers[0].direction == "decreases"


def test_complete_package_validator_binds_exact_case_order(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    manifest, signals = validate_product_handoff(
        output,
        expected_source_model_result_hash=result_hash,
        expected_case_ids=["ipo_2024_00001", "ipo_2024_00002"],
    )
    assert manifest["case_count"] == 2
    assert [row["case_id"] for row in signals] == ["ipo_2024_00001", "ipo_2024_00002"]


def test_complete_package_rejects_wrong_qualified_case_set(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    with pytest.raises(ProductRuntimeHandoffError, match="qualified handoff set"):
        validate_product_handoff(
            output,
            expected_source_model_result_hash=result_hash,
            expected_case_ids=["ipo_2024_00002", "ipo_2024_00001"],
        )


def test_source_run_manifest_hash_mismatch_fails(tmp_path) -> None:
    source, result_hash = _source(tmp_path, claimed_hash="0" * 64)
    with pytest.raises(ProductRuntimeHandoffError, match="run manifest"):
        write_product_handoff(
            source, tmp_path / "out", expected_source_model_result_hash=result_hash,
            case_ids=["ipo_2024_00001"],
        )


def test_actual_source_content_hash_mismatch_fails(tmp_path) -> None:
    source, result_hash = _source(tmp_path)
    tampered = _payload()
    tampered[0]["case_predictions"][0]["poor_performer_score"] = 0.99
    (source / "model_results.json").write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="model_results"):
        write_product_handoff(
            source, tmp_path / "out", expected_source_model_result_hash=result_hash,
            case_ids=["ipo_2024_00001"],
        )


def test_source_reporting_blind_access_fails(tmp_path) -> None:
    source, result_hash = _source(tmp_path, blind=True)
    with pytest.raises(ProductRuntimeHandoffError, match="blind"):
        write_product_handoff(
            source, tmp_path / "out", expected_source_model_result_hash=result_hash,
            case_ids=["ipo_2024_00001"],
        )


def _role_d_predictions(path: Path) -> str:
    fields = [
        "case_id", "stock_code", "cohort_year", "dataset_split", "model",
        "feature_group", "poor_performer_score", "score_semantics",
        "classification_threshold", "predicted_significant_drop_5d",
        "predicted_return_5d", "actual_significant_drop_5d",
        "actual_return_5d", "top_shap_drivers_json",
    ]
    drivers = {
        "ipo_2024_00001": [{
            "feature": "market_core__prior_ipo_count_20d",
            "component": "market_core",
            "feature_value": 3.0,
            "shap_value": -0.125,
        }],
        "ipo_2024_00002": [],
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for index, case_id in enumerate(drivers, start=1):
            writer.writerow({
                "case_id": case_id,
                "stock_code": f"000{index}.HK",
                "cohort_year": 2024,
                "dataset_split": "validation",
                "model": "lightgbm",
                "feature_group": "PM",
                "poor_performer_score": 0.25 if index == 1 else 0.75,
                "score_semantics": "uncalibrated_model_score_not_probability",
                "classification_threshold": 0.5,
                "predicted_significant_drop_5d": index == 2,
                "predicted_return_5d": 0.1 if index == 1 else -0.2,
                "actual_significant_drop_5d": index == 2,
                "actual_return_5d": 0.1 if index == 1 else -0.2,
                "top_shap_drivers_json": json.dumps(
                    drivers[case_id], sort_keys=True, separators=(",", ":")
                ),
            })
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_receipt_bound_recovery_is_byte_identical_to_full_source(tmp_path) -> None:
    source, result_hash = _source(tmp_path)
    expected_dir = tmp_path / "expected"
    source_pr_f = {"execution_revision": "abc"}
    write_product_handoff(
        source,
        expected_dir,
        expected_source_model_result_hash=result_hash,
        case_ids=["ipo_2024_00001", "ipo_2024_00002"],
        source_pr_f=source_pr_f,
    )
    expected_hashes = {
        name: hashlib.sha256((expected_dir / name).read_bytes()).hexdigest()
        for name in PRODUCT_FILES
    }
    predictions = tmp_path / "test_predictions.csv"
    prediction_hash = _role_d_predictions(predictions)

    recovered = tmp_path / "recovered"
    write_receipt_bound_product_handoff(
        predictions,
        recovered,
        expected_predictions_sha256=prediction_hash,
        expected_product_sha256=expected_hashes,
        expected_source_model_result_hash=result_hash,
        case_ids=["ipo_2024_00001", "ipo_2024_00002"],
        source_pr_f=source_pr_f,
    )

    assert {
        name: hashlib.sha256((recovered / name).read_bytes()).hexdigest()
        for name in PRODUCT_FILES
    } == expected_hashes
    signals = json.loads((recovered / PRODUCT_SIGNALS_NAME).read_text(encoding="utf-8"))
    assert all("actual_return_5d" not in row for row in signals)


def test_receipt_bound_recovery_rejects_prediction_byte_drift(tmp_path) -> None:
    predictions = tmp_path / "test_predictions.csv"
    expected_hash = _role_d_predictions(predictions)
    predictions.write_text(predictions.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ProductRuntimeHandoffError, match="immutable Role-D receipt"):
        project_case_signals_from_role_d_predictions(
            predictions,
            expected_predictions_sha256=expected_hash,
            case_ids=["ipo_2024_00001"],
        )


def test_unknown_case_fails_instead_of_being_fabricated(tmp_path) -> None:
    source, result_hash = _source(tmp_path)
    with pytest.raises(ProductRuntimeHandoffError, match="not in the frozen"):
        write_product_handoff(
            source, tmp_path / "out", expected_source_model_result_hash=result_hash,
            case_ids=["ipo_2024_99999"],
        )


def test_tampered_signal_checksum_fails_closed(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    (output / PRODUCT_SIGNALS_NAME).write_text("[]", encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="checksum"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_tampered_readme_checksum_fails_closed(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    (output / PRODUCT_README_NAME).write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="README"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_tampered_checksum_manifest_fails_closed(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    checksum_path = output / PRODUCT_CHECKSUMS_NAME
    checksum_path.write_text(checksum_path.read_text(encoding="utf-8") + "0" * 64 + "  extra\n")
    with pytest.raises(ProductRuntimeHandoffError, match="exact contract"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_extra_product_file_fails_closed(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    (output / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="exactly four files"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_extra_product_directory_fails_closed(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    (output / "unexpected").mkdir()
    with pytest.raises(ProductRuntimeHandoffError, match="exactly four files"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_manifest_local_absolute_path_fails_closed_even_with_updated_checksum(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    manifest_path = output / PRODUCT_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_pr_f"]["runtime_dir"] = r"C:\\private\\runtime"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checksum_path = output / PRODUCT_CHECKSUMS_NAME
    lines = checksum_path.read_text(encoding="utf-8").splitlines()
    lines[0] = f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  {PRODUCT_MANIFEST_NAME}"
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="absolute path"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_injected_target_label_fails_even_with_updated_checksum(tmp_path) -> None:
    output, result_hash = _write(tmp_path)
    signals_path = output / PRODUCT_SIGNALS_NAME
    signals = json.loads(signals_path.read_text(encoding="utf-8"))
    signals[0]["target"] = 1
    signals_path.write_text(json.dumps(signals), encoding="utf-8")
    manifest_path = output / PRODUCT_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_signal_sha256"] = hashlib.sha256(signals_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ProductRuntimeHandoffError, match="forbidden"):
        read_product_case_signal(
            output, expected_source_model_result_hash=result_hash, case_id="ipo_2024_00001"
        )


def test_missing_product_manifest_signals_legacy_fallback(tmp_path) -> None:
    assert read_product_case_signal(
        tmp_path, expected_source_model_result_hash="0" * 64, case_id="ipo_2024_00001"
    ) is None
