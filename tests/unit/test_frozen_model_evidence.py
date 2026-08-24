"""Guards for the read-only consumer of the frozen PR-F model result."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

from ipo_risk.modeling.frozen_model_evidence import (
    NOT_VALIDATED_PHRASE,
    FrozenModelEvidenceError,
    load_case_prediction,
    load_frozen_cohort_evidence,
    power_statement,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.final_supervision import ChannelStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_DIR = REPO_ROOT / "reports" / "frozen"
MANIFEST = FROZEN_DIR / "v04_pr_f_lightgbm_manifest.json"
# docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md forbids these framings for a gap the
# cohort cannot resolve.
FORBIDDEN_FRAMING = re.compile(r"useless|no signal|no value|worthless", re.IGNORECASE)


def _tampered(tmp_path: Path, **overrides) -> Path:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload.update(overrides)
    target = tmp_path / "v04_pr_f_lightgbm_manifest.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_reads_the_real_committed_manifest() -> None:
    evidence = load_frozen_cohort_evidence(FROZEN_DIR)
    assert evidence.model_name == "lightgbm"
    assert evidence.calibration_status == "assessment_only_uncalibrated"
    assert evidence.score_semantics == "uncalibrated_model_score_not_probability"
    assert evidence.validation_cohort_size == 70


def test_both_frozen_intervals_span_zero() -> None:
    """Neither ablation gain is resolvable, which is why the sign must be hidden."""
    evidence = load_frozen_cohort_evidence(FROZEN_DIR)
    assert evidence.production_gain.roc_auc_gain == 0.0
    assert (evidence.production_gain.interval_low, evidence.production_gain.interval_high) == (0.0, 0.0)
    assert evidence.production_gain.spans_zero
    assert not evidence.production_gain.sign_is_informative
    assert evidence.oracle_gain.interval_low < 0.0 < evidence.oracle_gain.interval_high
    assert evidence.oracle_gain.spans_zero


def test_cohort_statements_use_only_the_supportable_framing() -> None:
    for statement in load_frozen_cohort_evidence(FROZEN_DIR).statements():
        assert NOT_VALIDATED_PHRASE in statement
        assert not FORBIDDEN_FRAMING.search(statement), statement


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"status": "draft"}, "not complete_frozen"),
        ({"formal_gate_passed": False}, "did not pass its gate"),
        ({"blind_2025_y_accessed": True}, "blind 2025 access"),
        ({"calibration_status": "calibrated"}, "calibration status"),
        ({"formal_conclusion": {"score_semantics": "calibrated_probability"}}, "score semantics"),
    ],
)
def test_manifest_validation_fails_closed(tmp_path, overrides, match) -> None:
    with pytest.raises(FrozenModelEvidenceError, match=match):
        load_frozen_cohort_evidence(_tampered(tmp_path, **overrides))


def test_missing_manifest_fails_closed(tmp_path) -> None:
    with pytest.raises(FrozenModelEvidenceError, match="not found"):
        load_frozen_cohort_evidence(tmp_path)


def test_absent_case_id_is_named_not_guessed(tmp_path) -> None:
    view = load_case_prediction(tmp_path, FROZEN_DIR, case_id=None)
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "ipo_identity_not_bound_to_the_governed_case_catalog"
    assert view.score is None and view.drivers == ()
    assert view.score_semantics == "uncalibrated_model_score"


def test_absent_local_artifacts_are_named_not_guessed(tmp_path) -> None:
    """The normal state of a fresh checkout: PR-F runtime output is not committed."""
    view = load_case_prediction(tmp_path, FROZEN_DIR, case_id="ipo_2024_00300")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "frozen_pr_f_runtime_artifacts_are_not_present_locally"


def _result_payload(rows: list[dict], drivers: list[dict] | None = None) -> list[dict]:
    return [{
        "cohort": "full_production", "feature_group": "PM",
        "classification_metrics": {"roc_auc": 0.4246},
        "case_predictions": rows,
        "explainability": {"single_ipo_drivers": drivers or []},
    }]


def _run_dir(
    tmp_path: Path,
    *,
    result_hash: str,
    rows: list[dict],
    drivers: list[dict] | None = None,
    blind_2025_y_accessed: bool = False,
) -> tuple[Path, list[dict]]:
    run = tmp_path / "pr_f"
    run.mkdir()
    payload = _result_payload(rows, drivers)
    (run / "run_manifest.json").write_text(json.dumps({
        "model_result_hash": result_hash,
        "blind_2025_y_accessed": blind_2025_y_accessed,
    }), encoding="utf-8")
    (run / "model_results.json").write_text(json.dumps(payload), encoding="utf-8")
    return run, payload


def _rows(n: int = 8) -> list[dict]:
    return [{"case_id": f"ipo_2024_{i:05d}", "poor_performer_5d": i % 2 == 0,
             "poor_performer_score": 0.1 * i, "raw_return_5d": -0.01 * i,
             "raw_return_5d_prediction": -0.02 * i} for i in range(n)]


def _frozen_hash() -> str:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["model_result_hash"]


def _frozen_dir_for_payload(tmp_path: Path, payload: list[dict]) -> Path:
    frozen = tmp_path / "frozen"
    frozen.mkdir()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["model_result_hash"] = canonical_hash(payload)
    (frozen / MANIFEST.name).write_text(json.dumps(manifest), encoding="utf-8")
    return frozen


def test_unbound_local_artifacts_are_refused_entirely(tmp_path) -> None:
    """A stale run is never partially consumed; the manifest hash gate comes first."""
    run, _ = _run_dir(tmp_path, result_hash="0" * 64, rows=_rows())
    view = load_case_prediction(run, FROZEN_DIR, case_id="ipo_2024_00000")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "local_pr_f_artifacts_do_not_match_the_frozen_hash"
    assert view.score is None


def test_copying_the_frozen_hash_does_not_bind_tampered_result_content(tmp_path) -> None:
    """The actual model_results payload is hashed; the run manifest is not trusted by itself."""
    run, _ = _run_dir(tmp_path, result_hash=_frozen_hash(), rows=_rows())
    view = load_case_prediction(run, FROZEN_DIR, case_id="ipo_2024_00000")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "local_pr_f_model_results_do_not_match_the_frozen_hash"
    assert view.score is None


def test_bound_artifacts_yield_the_per_case_score_and_drivers(tmp_path) -> None:
    drivers = [{"case_id": "ipo_2024_00000", "base_value": 0.3, "top_drivers": [
        {"feature": "market_core__hsi_return_5d", "component": "market_core",
         "feature_value": -0.02, "shap_value": 0.11},
        {"feature": "production_document__cash_runway__score", "component": "production_document",
         "feature_value": None, "shap_value": -0.07},
    ]}]
    payload = _result_payload(_rows(), drivers)
    frozen = _frozen_dir_for_payload(tmp_path, payload)
    run, written = _run_dir(tmp_path, result_hash=canonical_hash(payload), rows=_rows(), drivers=drivers)
    assert written == payload
    view = load_case_prediction(run, frozen, case_id="ipo_2024_00000")
    assert view.status is ChannelStatus.AVAILABLE
    assert view.score == 0.0
    assert [d.direction for d in view.drivers] == ["increases", "decreases"]
    assert view.drivers[1].feature_value is None
    assert view.calibration_status == "uncalibrated"


def test_case_outside_the_frozen_validation_cohort_is_named(tmp_path) -> None:
    payload = _result_payload(_rows())
    frozen = _frozen_dir_for_payload(tmp_path, payload)
    run, _ = _run_dir(tmp_path, result_hash=canonical_hash(payload), rows=_rows())
    view = load_case_prediction(run, frozen, case_id="ipo_2024_99999")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "case_is_not_in_the_frozen_2024_validation_cohort"


def test_local_manifest_reporting_blind_access_is_refused(tmp_path) -> None:
    payload = _result_payload(_rows())
    frozen = _frozen_dir_for_payload(tmp_path, payload)
    run, _ = _run_dir(
        tmp_path,
        result_hash=canonical_hash(payload),
        rows=_rows(),
        blind_2025_y_accessed=True,
    )
    view = load_case_prediction(run, frozen, case_id="ipo_2024_00000")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "local_pr_f_runtime_manifest_reports_blind_2025_access"


def test_invalid_local_json_is_refused_without_leaking_an_exception(tmp_path) -> None:
    run = tmp_path / "pr_f"
    run.mkdir()
    (run / "run_manifest.json").write_text("{broken", encoding="utf-8")
    (run / "model_results.json").write_text("[]", encoding="utf-8")
    view = load_case_prediction(run, FROZEN_DIR, case_id="ipo_2024_00000")
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == "frozen_pr_f_runtime_artifacts_are_invalid_json"


def test_power_counts_come_from_labels_never_from_pr_auc(tmp_path) -> None:
    """The 25/45 and 7/12 splits in the audit doc are inferred; these are measured."""
    run, _ = _run_dir(tmp_path, result_hash="unused", rows=_rows(10))
    artifact = json.loads((run / "model_results.json").read_text(encoding="utf-8"))[0]
    evidence = load_frozen_cohort_evidence(FROZEN_DIR)
    statement = power_statement(artifact, evidence.production_gain)
    assert statement is not None
    assert "5 positive / 5 negative" in statement


def test_degenerate_cohort_yields_no_statement_rather_than_infinity(tmp_path) -> None:
    """math.inf in metadata would break the analysis-result JSON round trip."""
    rows = [{"case_id": "ipo_2024_00000", "poor_performer_5d": False, "poor_performer_score": 0.1,
             "raw_return_5d": 0.0, "raw_return_5d_prediction": 0.0}]
    run, _ = _run_dir(tmp_path, result_hash="unused", rows=rows)
    artifact = json.loads((run / "model_results.json").read_text(encoding="utf-8"))[0]
    evidence = load_frozen_cohort_evidence(FROZEN_DIR)
    assert power_statement(artifact, evidence.production_gain) is None


def test_no_non_finite_value_escapes_the_cohort_evidence() -> None:
    payload = load_frozen_cohort_evidence(FROZEN_DIR).model_dump(mode="json")

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, float):
            assert math.isfinite(value), value

    walk(payload)
