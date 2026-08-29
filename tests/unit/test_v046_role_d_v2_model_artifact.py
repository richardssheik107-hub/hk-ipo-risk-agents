"""The runtime model file is only legitimate if it rebuilds the frozen identity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.modeling.role_d_v2_model_artifact import (
    ALERT_POLICY_FILE,
    ARTIFACT_FILES,
    FEATURE_MANIFEST_FILE,
    MODEL_FILE,
    MODEL_MANIFEST_FILE,
    RoleDV2ModelArtifactError,
    V2_PROMOTION_MANIFEST_NAME,
    materialize_model_artifact,
    reconstruct_governed_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_DIR = REPO_ROOT / "reports/frozen"
FEATURE_DIR = REPO_ROOT / "reports/v04_pr_b/core_features"
OUTCOME_PACK = REPO_ROOT / "data/competition/derived/prior_ipo_outcome_pack.json"
PR_C_MANIFEST = FROZEN_DIR / "v04_pr_c_5d_outcome_manifest.json"

pytestmark = pytest.mark.skipif(
    not OUTCOME_PACK.is_file(),
    reason="the governed outcome pack is not materialized in this checkout",
)


def _rows():
    return reconstruct_governed_rows(
        market_core_dir=FEATURE_DIR,
        outcome_pack_path=OUTCOME_PACK,
        pr_c_manifest_path=PR_C_MANIFEST,
    )


def test_the_reconstructed_cohort_is_the_frozen_cohort() -> None:
    rows, feature_names, binding = _rows()
    frozen = json.loads((FROZEN_DIR / V2_PROMOTION_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert (binding["development_count"], binding["validation_count"]) == (354, 70)
    assert binding["market_feature_manifest_hash"] == frozen["input_binding"]["market_feature_manifest_hash"]
    assert binding["raw_eod_sha256"] == frozen["input_binding"]["raw_eod_sha256"]
    assert len(feature_names) == 30
    assert all(row.cohort_year <= 2024 for row in rows)
    assert [row.case_id for row in rows] == sorted(row.case_id for row in rows)


def test_an_outcome_pack_from_a_different_eod_extract_is_refused(tmp_path) -> None:
    pack = json.loads(OUTCOME_PACK.read_text(encoding="utf-8"))
    pack["ipo_eod_sha256"] = "0" * 64
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(RoleDV2ModelArtifactError, match="different EOD extracts"):
        reconstruct_governed_rows(
            market_core_dir=FEATURE_DIR,
            outcome_pack_path=path,
            pr_c_manifest_path=PR_C_MANIFEST,
        )


def test_a_pack_carrying_blind_outcomes_is_refused(tmp_path) -> None:
    pack = json.loads(OUTCOME_PACK.read_text(encoding="utf-8"))
    pack["outcome_cohort_years"] = [*pack["outcome_cohort_years"], 2025]
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(RoleDV2ModelArtifactError, match="2025 Blind"):
        reconstruct_governed_rows(
            market_core_dir=FEATURE_DIR,
            outcome_pack_path=path,
            pr_c_manifest_path=PR_C_MANIFEST,
        )


def test_materialization_reproduces_the_frozen_model_bit_for_bit(tmp_path) -> None:
    frozen = json.loads((FROZEN_DIR / V2_PROMOTION_MANIFEST_NAME).read_text(encoding="utf-8"))
    result = materialize_model_artifact(
        model_dir=tmp_path / "package",
        market_core_dir=FEATURE_DIR,
        outcome_pack_path=OUTCOME_PACK,
        frozen_dir=FROZEN_DIR,
    )
    assert result["status"] == "pass"
    assert result["classifier_model_sha256"] == frozen["classifier_model_sha256"]
    assert result["frozen_identity_verified"] is True

    committed = REPO_ROOT / "models/role_d_v2"
    if (committed / MODEL_FILE).is_file():
        for name in ARTIFACT_FILES:
            assert (tmp_path / "package" / name).read_bytes() == (committed / name).read_bytes()


def test_the_written_package_declares_its_governance(tmp_path) -> None:
    materialize_model_artifact(
        model_dir=tmp_path / "package",
        market_core_dir=FEATURE_DIR,
        outcome_pack_path=OUTCOME_PACK,
        frozen_dir=FROZEN_DIR,
    )
    manifest = json.loads((tmp_path / "package" / MODEL_MANIFEST_FILE).read_text(encoding="utf-8"))
    alert_policy = json.loads((tmp_path / "package" / ALERT_POLICY_FILE).read_text(encoding="utf-8"))
    features = json.loads((tmp_path / "package" / FEATURE_MANIFEST_FILE).read_text(encoding="utf-8"))

    assert manifest["score_semantics"] == "uncalibrated_model_score_not_probability"
    assert manifest["blind_2025_y_accessed"] is False
    assert manifest["materialization"]["runtime_retraining"] is False
    assert manifest["materialization"]["overwrites_prior_frozen_identity"] is False
    single_case = alert_policy["single_case_policy"]
    assert single_case["validation_used_for_derivation"] is False
    assert single_case["blind_used_for_derivation"] is False
    assert single_case["consistency_report"]["labels_used"] is False
    assert features["model_expected_dimension"] == len(features["model_input_feature_names"])


def test_a_frozen_manifest_that_disagrees_stops_the_write(tmp_path) -> None:
    frozen_dir = tmp_path / "frozen"
    frozen_dir.mkdir()
    for name in (V2_PROMOTION_MANIFEST_NAME, "v04_pr_c_5d_outcome_manifest.json"):
        frozen_dir.joinpath(name).write_bytes((FROZEN_DIR / name).read_bytes())
    frozen = json.loads((frozen_dir / V2_PROMOTION_MANIFEST_NAME).read_text(encoding="utf-8"))
    frozen["classifier_model_sha256"] = "0" * 64
    (frozen_dir / V2_PROMOTION_MANIFEST_NAME).write_text(json.dumps(frozen), encoding="utf-8")

    package = tmp_path / "package"
    with pytest.raises(RoleDV2ModelArtifactError, match="frozen model identity"):
        materialize_model_artifact(
            model_dir=package,
            market_core_dir=FEATURE_DIR,
            outcome_pack_path=OUTCOME_PACK,
            frozen_dir=frozen_dir,
        )
    assert not (package / MODEL_FILE).exists()
