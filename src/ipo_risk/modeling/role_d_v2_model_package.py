"""Names, paths and versions of the frozen Role-D V2 runtime model package.

This module is deliberately dependency-free.  The product import graph must not
require LightGBM or scikit-learn -- they are optional extras -- so the identity
of the model package lives here, apart from the builder that trains it and the
runtime that scores with it.  Both of those import their heavy dependencies
where they are used, not where the package is merely named.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


MODEL_ARTIFACT_VERSION = "v046_role_d_v2_frozen_model_artifact_v1"
FEATURE_MANIFEST_VERSION = "v046_role_d_v2_feature_manifest_v1"
ALERT_POLICY_ARTIFACT_VERSION = "v046_role_d_v2_alert_policy_v1"
SINGLE_CASE_ALERT_POLICY_VERSION = "v046_role_d_v2_single_case_alert_cutoff_v1"

MODEL_NAME = "lightgbm_role_d_v2"
MODEL_FILE = "model.txt"
MODEL_MANIFEST_FILE = "model_manifest.json"
FEATURE_MANIFEST_FILE = "feature_manifest.json"
ALERT_POLICY_FILE = "alert_policy.json"
CHECKSUM_FILE = "SHA256SUMS.txt"
ARTIFACT_FILES = (
    MODEL_FILE,
    MODEL_MANIFEST_FILE,
    FEATURE_MANIFEST_FILE,
    ALERT_POLICY_FILE,
)

DEFAULT_MODEL_DIR = Path("models/role_d_v2")
DEFAULT_MARKET_CORE_DIR = Path("reports/v04_pr_b/core_features")
DEFAULT_OUTCOME_PACK = Path("data/competition/derived/prior_ipo_outcome_pack.json")
DEFAULT_FROZEN_DIR = Path("reports/frozen")

V2_PROMOTION_MANIFEST_NAME = "v045_role_d_v2_promotion_manifest.json"
PR_C_MANIFEST_NAME = "v04_pr_c_5d_outcome_manifest.json"

SCORE_SEMANTICS = "uncalibrated_model_score_not_probability"
CALIBRATION_STATUS = "assessment_only_uncalibrated"
LABEL_RULE = "raw_return_5d <= poor_performer_threshold"
MISSINGNESS_POLICY = (
    "missing_feature_is_passed_to_lightgbm_as_nan_exactly_as_in_the_frozen_training_matrix"
)
METRIC_TOLERANCE = 1e-12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
