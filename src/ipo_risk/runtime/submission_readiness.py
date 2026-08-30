"""Role-A final competition readiness, audit, indexing, and packaging helpers.

This module is deliberately read-only with respect to B/C/D/E outputs. It never
fills a missing metric, market fact, model score, Evidence item, or LLM result.
Instead it converts the final hand-offs into an auditable PASS/FAIL decision and
produces the A-owned CH-6 evidence needed for submission.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5
import zipfile


READINESS_SCHEMA_VERSION = "v045_submission_readiness_v1"
ARTIFACT_INDEX_SCHEMA_VERSION = "v045_submission_artifact_index_v1"
BLIND_AUDIT_SCHEMA_VERSION = "v045_blind_audit_v1"
PROVENANCE_AUDIT_SCHEMA_VERSION = "v045_provenance_audit_v1"
DETERMINISM_AUDIT_SCHEMA_VERSION = "v045_determinism_audit_v1"
PACKAGE_SCHEMA_VERSION = "v045_submission_package_v1"
MARKET_VALIDATION_SCHEMA_VERSION = "v045_market_final_matrix_validation_v1"
SECURITY_AUDIT_SCHEMA_VERSION = "v045_submission_security_audit_v1"
DOCUMENTATION_AUDIT_SCHEMA_VERSION = "v045_documentation_consistency_audit_v1"
METRIC_PROTOCOL_VERSION = "v045_competition_metric_protocol_v2_existing_gold_only"
SIGNIFICANT_DROP_5D_DEFINITION = "return_5d <= -0.10"
FINAL_CASE_IDS = (
    "ipo_2024_02410",
    "ipo_2024_02460",
    "ipo_2024_01318",
)

ROLE_B_REQUIRED = (
    "existing_gold_evaluable_manifest.json",
    "document_benchmark_summary.json",
    "risk_benchmark.csv",
    "evidence_benchmark.csv",
)
ROLE_D_REQUIRED = (
    "test_predictions.csv",
    "multi_horizon_results.csv",
    "evaluation_summary.json",
    "ai_vs_offline_report.json",
)
ROLE_E_CASE_REQUIRED = (
    "analysis_result.json",
    "final_supervision.json",
    "conflicts.json",
    "rechecks.json",
    "trace_sidecar.json",
    "traceability.json",
    "prospectus_verification.json",
    "agent_reasoning_log.json",
    "agent_reasoning_log.md",
    "case_report.md",
    "gate_e1_evidence.json",
    "evidence_export.json",
    "human_review_export.json",
)
REQUIRED_HORIZONS = ("return_1d", "return_5d", "return_20d", "return_60d")
REQUIRED_CALL_TRACE_FIELDS = (
    "provider_name",
    "model_name",
    "prompt_version",
    "request_id",
    "raw_response_hash",
    "latency_ms",
)
CI_ATTESTATION_BLOCKER = "latest-main CI has not been explicitly attested as PASS"
ARTIFACT_INDEX_BLOCKER = "artifact index has not been generated and verified"
ARTIFACT_INDEX_LOGICAL_PATH = "artifacts/role_a/artifact_index.json"

# Package source allowlist: repository code/config/docs only. Licensed PDFs and
# local competition data are intentionally not reachable from this list.
SOURCE_ROOT_FILES = (
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "pyproject.toml",
    "environment.yml",
    ".env.example",
)
SOURCE_ROOT_DIRS = ("src", "app", "configs", "scripts")
SUBMISSION_DOCS = (
    "docs/SUBMISSION_RUNBOOK.md",
    "docs/V0.4_RELEASE_ACCEPTANCE.md",
    "docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md",
    "docs/V04_FIVE_PERSON_EXECUTION_PLAN.md",
)

_FORBIDDEN_PACKAGE_SUFFIXES = {
    ".pdf",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".pkl",
    ".pickle",
    ".joblib",
    ".onnx",
    ".pt",
    ".pth",
    ".ckpt",
    ".safetensors",
}
_FORBIDDEN_PACKAGE_NAMES = {".env", "id_rsa", "id_ed25519"}
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_TOKEN_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
_BEARER_TOKEN_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}\b", re.I)
_AWS_ACCESS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_WINDOWS_ABS_RE = re.compile(r"\b[A-Za-z]:\\(?:Users|Documents and Settings|home|mnt)\\", re.I)
_UNIX_LOCAL_ABS_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home|mnt|private|var/folders)/[^\s\"']+")
_NUMBER_IN_PROSE_RE = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?")


@dataclass(frozen=True)
class GateResult:
    name: str
    owner: str
    passed: bool
    details: dict[str, Any]
    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "owner": self.owner,
            "passed": self.passed,
            "blockers": list(self.blockers),
            "details": self.details,
        }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_header_and_rows(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), len(rows)


def _bool_is_false(payload: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in payload:
            return payload[key] is False
    return False


def _traceability_value(case: dict[str, Any]) -> float | None:
    value = case.get("traceability")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("overall_traceability", "traceability", "ratio", "value"):
            candidate = value.get(key)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return float(candidate)
    return None


def _provider_call_trace_complete(call: dict[str, Any]) -> bool:
    """Require usable call identity, not merely present keys or empty strings."""

    identity_fields = tuple(
        field for field in REQUIRED_CALL_TRACE_FIELDS if field not in {"raw_response_hash", "latency_ms"}
    )
    identities_present = all(bool(str(call.get(field) or "").strip()) for field in identity_fields)
    response_hash = str(call.get("raw_response_hash") or "").strip()
    response_hash_valid = bool(re.fullmatch(r"[0-9a-fA-F]{64}", response_hash))
    latency = call.get("latency_ms")
    latency_valid = (
        isinstance(latency, (int, float))
        and not isinstance(latency, bool)
        and float(latency) >= 0.0
    )
    return identities_present and response_hash_valid and latency_valid


def _result_status(value: Any) -> str:
    return str(value or "").strip().casefold()


def audit_role_b(role_b_dir: Path) -> GateResult:
    missing = [name for name in ROLE_B_REQUIRED if not (role_b_dir / name).is_file()]
    if missing:
        return GateResult(
            "B1_real_llm_document_benchmark",
            "B",
            False,
            {"artifact_dir": _record_path(role_b_dir), "missing_files": missing},
            tuple(f"missing Role-B artifact: {name}" for name in missing),
        )

    manifest = _read_json(role_b_dir / "existing_gold_evaluable_manifest.json")
    summary = _read_json(role_b_dir / "document_benchmark_summary.json")
    risk_header, risk_rows = _csv_header_and_rows(role_b_dir / "risk_benchmark.csv")
    evidence_header, evidence_rows = _csv_header_and_rows(role_b_dir / "evidence_benchmark.csv")

    risk = summary.get("risk_extraction") or {}
    evidence = summary.get("evidence_coverage") or {}
    diagnostics = summary.get("retrieval_diagnostics") or {}
    measurement = summary.get("measurement_gate") or {}
    accuracy = risk.get("official_aligned_accuracy")
    coverage = evidence.get("coverage_recall")
    risk_target = (
        isinstance(accuracy, (int, float))
        and not isinstance(accuracy, bool)
        and float(accuracy) >= 0.80
    )
    evidence_target = (
        isinstance(coverage, (int, float))
        and not isinstance(coverage, bool)
        and float(coverage) >= 0.85
    )
    real_llm_cases = int(summary.get("real_llm_cases") or 0)
    external_called = summary.get("external_llm_called") is True
    blind_safe = summary.get("blind_2025_outcome_accessed") is False
    protocol_ok = all(
        payload.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION
        for payload in (manifest, summary)
    )
    gold_frozen = all(
        (
            manifest.get("new_manual_annotations_added") is False,
            manifest.get("existing_gold_modified") is False,
            summary.get("new_manual_annotations_added") is False,
            summary.get("existing_gold_modified") is False,
            (manifest.get("source_governance") or {}).get("source_inventory_matches_frozen") is True,
        )
    )
    manifest_hash = manifest.get("manifest_hash")
    source_bound = bool(manifest_hash) and summary.get("existing_gold_source_hash_or_manifest") == manifest_hash
    development_case_count = int(summary.get("evaluable_development_case_count") or 0)
    evaluated_case_count = int(summary.get("evaluated_case_count") or 0)
    expected_case_count = int(summary.get("expected_case_count_for_split") or 0)
    full_development = all(
        (
            development_case_count == 79,
            expected_case_count == 79,
            evaluated_case_count == 79,
            str(summary.get("split") or "").casefold() == "development",
            summary.get("evaluation_scope") == "full_split",
            not (summary.get("missing_case_ids") or []),
            measurement.get("competition_pass_claim_eligible") is True,
        )
    )
    recall_keys = tuple(f"recall_at_{value}" for value in (1, 3, 5, 10, 20))
    recall_diagnostics_complete = all(
        isinstance(diagnostics.get(key), (int, float))
        and not isinstance(diagnostics.get(key), bool)
        for key in recall_keys
    )
    validation_one_shot = summary.get("validation_one_shot") is True and summary.get(
        "validation_post_hoc_tuning"
    ) is False
    risk_provenance_columns = {"source_manifest_key", "source_annotation_hash"} <= set(risk_header)
    evidence_provenance_columns = {"source_manifest_key", "source_annotation_hash"} <= set(
        evidence_header
    )
    passed = all(
        (
            protocol_ok,
            gold_frozen,
            source_bound,
            full_development,
            real_llm_cases == 79,
            external_called,
            risk_target,
            evidence_target,
            blind_safe,
            recall_diagnostics_complete,
            validation_one_shot,
            risk_rows > 0,
            evidence_rows > 0,
            risk_provenance_columns,
            evidence_provenance_columns,
        )
    )
    blockers: list[str] = []
    if not protocol_ok:
        blockers.append("Role-B handoff is not bound to the frozen Metric-v2 protocol")
    if not gold_frozen:
        blockers.append("Role-B handoff does not prove Existing Gold remained frozen and read-only")
    if not source_bound:
        blockers.append("Role-B summary is not bound to the frozen Existing-Gold manifest hash")
    if not full_development:
        blockers.append("Role-B ALL 79 Development full-split benchmark is not demonstrated")
    if real_llm_cases != 79 or not external_called:
        blockers.append("Role-B ALL 79 Development benchmark is not a complete real-LLM measurement")
    if not risk_target:
        blockers.append("M1 Existing-Gold official-aligned accuracy >=80% is not demonstrated")
    if not evidence_target:
        blockers.append("M2 Existing-Gold Evidence Coverage Recall >=85% is not demonstrated")
    if not blind_safe:
        blockers.append("Role-B benchmark does not explicitly attest 2025 Blind protection")
    if not recall_diagnostics_complete:
        blockers.append("Role-B Recall@1/@3/@5/@10/@20 diagnostics are incomplete")
    if not validation_one_shot:
        blockers.append("Role-B Validation one-shot/no-post-hoc-tuning attestation is missing")
    if risk_rows == 0 or evidence_rows == 0:
        blockers.append("Role-B benchmark CSVs are empty")
    if not risk_provenance_columns or not evidence_provenance_columns:
        blockers.append("Role-B benchmark CSVs lack Existing-Gold source provenance columns")
    return GateResult(
        "B1_real_llm_document_benchmark",
        "B",
        passed,
        {
            "artifact_dir": _record_path(role_b_dir),
            "metric_protocol_version": summary.get("metric_protocol_version"),
            "existing_gold_manifest_hash": manifest_hash,
            "existing_gold_source_bound": source_bound,
            "new_manual_annotations_added": summary.get("new_manual_annotations_added"),
            "existing_gold_modified": summary.get("existing_gold_modified"),
            "all_79_development_complete": full_development,
            "evaluated_case_count": evaluated_case_count,
            "real_llm_cases": real_llm_cases,
            "external_llm_called": external_called,
            "m1_official_aligned_accuracy": accuracy,
            "m1_official_threshold_met": risk_target,
            "m2_evidence_coverage_recall": coverage,
            "m2_official_threshold_met": evidence_target,
            "retrieval_diagnostics": {key: diagnostics.get(key) for key in recall_keys},
            "validation_one_shot_attested": validation_one_shot,
            "risk_rows": risk_rows,
            "risk_columns": risk_header,
            "evidence_rows": evidence_rows,
            "evidence_columns": evidence_header,
            "blind_2025_outcome_accessed": summary.get("blind_2025_outcome_accessed"),
        },
        tuple(blockers),
    )


def audit_role_d(role_d_dir: Path) -> GateResult:
    missing = [name for name in ROLE_D_REQUIRED if not (role_d_dir / name).is_file()]
    if missing:
        return GateResult(
            "D1_multi_horizon_evaluation",
            "D",
            False,
            {"artifact_dir": _record_path(role_d_dir), "missing_files": missing},
            tuple(f"missing Role-D artifact: {name}" for name in missing),
        )

    pred_header, pred_rows = _csv_header_and_rows(role_d_dir / "test_predictions.csv")
    horizon_header, horizon_rows = _csv_header_and_rows(role_d_dir / "multi_horizon_results.csv")
    summary = _read_json(role_d_dir / "evaluation_summary.json")
    comparison = _read_json(role_d_dir / "ai_vs_offline_report.json")
    missing_horizons = [name for name in REQUIRED_HORIZONS if name not in horizon_header]
    summary_status_ok = summary.get("status") == "complete"
    evaluation_count = summary.get("evaluation_count")
    exact_validation_count = (
        evaluation_count == 70 and pred_rows == 70 and horizon_rows == 70
    )
    evaluation_split_ok = summary.get("evaluation_split") == "2024_validation"
    horizon_contract_ok = summary.get("horizons") == ["1D", "5D", "20D", "60D"]
    blind_explicit = _bool_is_false(
        summary,
        "blind_2025_y_accessed",
        "blind_2025_outcome_accessed",
        "blind_2025_accessed",
    )
    protocol_ok = summary.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION
    definition_ok = summary.get("significant_drop_5d_definition") == SIGNIFICANT_DROP_5D_DEFINITION
    no_retuning = summary.get("threshold_or_model_retuned_on_validation") is False
    score_semantics_ok = (
        summary.get("score_semantics")
        == "uncalibrated_model_score_not_probability"
    )
    summary_metrics = summary.get("five_day_metrics") or {}
    comparison_ai = comparison.get("ai_model") or {}
    comparison_offline = comparison.get("offline_baseline") or {}
    comparison_safe = all(
        (
            comparison.get("comparison_scope")
            == "same_2024_validation_full_production_PM",
            comparison_ai.get("name") == "frozen_lightgbm",
            comparison_ai.get("score_semantics")
            == "uncalibrated_model_score_not_probability",
            comparison_ai.get("metrics") == summary_metrics,
            comparison_offline.get("name") == "frozen_logistic_regression",
            comparison.get("interpretation_policy")
            == "descriptive_only_no_validation_retuning",
            comparison.get("threshold_or_model_retuned_on_validation") is False,
            comparison.get("blind_2025_y_accessed") is False,
        )
    )
    metric_keys = {
        "precision",
        "recall",
        "f1",
        "pr_auc",
        "roc_auc",
        "top_10pct_hit_rate",
        "top_20pct_hit_rate",
        "base_prevalence",
    }
    metrics_complete = metric_keys <= set(summary_metrics)
    prediction_columns_ok = {
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
    } <= set(pred_header)
    passed = all(
        (
            summary_status_ok,
            exact_validation_count,
            evaluation_split_ok,
            horizon_contract_ok,
            not missing_horizons,
            pred_rows == horizon_rows,
            blind_explicit,
            protocol_ok,
            definition_ok,
            no_retuning,
            score_semantics_ok,
            comparison_safe,
            metrics_complete,
            prediction_columns_ok,
        )
    )
    blockers: list[str] = []
    if not summary_status_ok:
        blockers.append("Role-D evaluation_summary.json status is not complete")
    if not exact_validation_count:
        blockers.append("Role-D handoff does not contain exactly 70 frozen 2024 Validation cases")
    if not evaluation_split_ok:
        blockers.append("Role-D evaluation split is not 2024_validation")
    if not horizon_contract_ok:
        blockers.append("Role-D summary does not declare the exact 1D/5D/20D/60D horizons")
    if missing_horizons:
        blockers.append("multi_horizon_results.csv missing: " + ", ".join(missing_horizons))
    if not blind_explicit:
        blockers.append("evaluation_summary.json lacks an explicit false 2025 Blind access flag")
    if not protocol_ok:
        blockers.append("Role-D evaluation is not bound to the frozen Metric-v2 protocol")
    if not definition_ok:
        blockers.append("Role-D significant_drop_5d definition drifted from return_5d <= -0.10")
    if not no_retuning or not comparison_safe:
        blockers.append(
            "Role-D handoff does not preserve the frozen descriptive AI-vs-offline/no-retuning/Blind contract"
        )
    if not score_semantics_ok:
        blockers.append("Role-D summary does not preserve uncalibrated non-probability score semantics")
    if not metrics_complete:
        blockers.append("Role-D five-day metric set is incomplete")
    if not prediction_columns_ok:
        blockers.append("test_predictions.csv lacks governed score/label semantics")
    if pred_rows != horizon_rows:
        blockers.append("Role-D prediction and multi-horizon row counts differ")
    return GateResult(
        "D1_multi_horizon_evaluation",
        "D",
        passed,
        {
            "artifact_dir": _record_path(role_d_dir),
            "prediction_rows": pred_rows,
            "prediction_columns": pred_header,
            "multi_horizon_rows": horizon_rows,
            "multi_horizon_columns": horizon_header,
            "missing_required_horizons": missing_horizons,
            "metric_protocol_version": summary.get("metric_protocol_version"),
            "status": summary.get("status"),
            "evaluation_split": summary.get("evaluation_split"),
            "evaluation_count": evaluation_count,
            "horizons": summary.get("horizons"),
            "significant_drop_5d_definition": summary.get("significant_drop_5d_definition"),
            "threshold_or_model_retuned_on_validation": summary.get(
                "threshold_or_model_retuned_on_validation"
            ),
            "score_semantics": summary.get("score_semantics"),
            "five_day_metric_keys": sorted(summary_metrics.keys()),
            "ai_vs_offline_contract_passed": comparison_safe,
            "blind_2025_explicitly_protected": blind_explicit,
            "evaluation_summary_keys": sorted(summary),
        },
        tuple(blockers),
    )


def _case_dir(role_e_dir: Path, case: dict[str, Any]) -> Path:
    return role_e_dir / str(case.get("case_id") or "")


def _json_content_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _market_free_text(payload: Any, *, parent_key: str = "") -> Iterable[str]:
    """Yield LLM prose while excluding ids and other governed numeric labels."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).casefold()
            if lowered.endswith("_id") or lowered.endswith("_ids") or lowered in {
                "source_feature_ids",
                "driver_id",
            }:
                continue
            yield from _market_free_text(value, parent_key=lowered)
    elif isinstance(payload, list):
        for value in payload:
            yield from _market_free_text(value, parent_key=parent_key)
    elif isinstance(payload, str):
        yield payload


def _allowed_market_number_tokens(observations: Sequence[dict[str, Any]], listing_date: str) -> set[str]:
    # Window labels are part of the governed feature contract, not new market
    # observations. Listing-date components are also governed case identity.
    allowed = {"0", "1", "5", "20", "30", "60", "180"}
    allowed.update(part for part in listing_date.split("-") if part)
    for observation in observations:
        value = observation.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        numeric = float(value)
        candidates = {numeric, numeric * 100.0}
        for candidate in candidates:
            for precision in range(0, 7):
                rendered = f"{candidate:.{precision}f}".rstrip("0").rstrip(".")
                if rendered in {"", "-0"}:
                    rendered = "0"
                allowed.add(rendered)
    return allowed


def _source_feature_ids(payload: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "source_feature_ids" and isinstance(value, list):
                found.update(str(item) for item in value if item)
            else:
                found.update(_source_feature_ids(value))
    elif isinstance(payload, list):
        for value in payload:
            found.update(_source_feature_ids(value))
    return found


def audit_market_from_final_matrix(role_e_dir: Path, summary: dict[str, Any] | None = None) -> GateResult:
    if summary is None:
        summary_path = role_e_dir / "summary.json"
        if not summary_path.is_file():
            return GateResult(
                "C1_final_matrix_market_validation",
                "C",
                False,
                {"artifact_dir": _record_path(role_e_dir)},
                ("Role-E final matrix summary is missing",),
            )
        summary = _read_json(summary_path)

    cases = [case for case in summary.get("cases", []) if isinstance(case, dict)]
    case_ids = {str(case.get("case_id") or "") for case in cases}
    checked: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        root = _case_dir(role_e_dir, case)
        analysis_path = root / "analysis_result.json"
        trace_path = root / "trace_sidecar.json"
        if not analysis_path.is_file() or not trace_path.is_file():
            missing = [
                name
                for name, path in (
                    ("analysis_result.json", analysis_path),
                    ("trace_sidecar.json", trace_path),
                )
                if not path.is_file()
            ]
            blockers.append(f"{case_id}: missing Market validation artifact(s): {', '.join(missing)}")
            checked.append(
                {
                    "case_id": case_id,
                    "stock_code": case.get("stock_code"),
                    "satisfied": False,
                    "unmet_conditions": [f"missing {name}" for name in missing],
                }
            )
            continue

        result = _read_json(analysis_path)
        metadata = result.get("metadata") or {}
        composition = metadata.get("final_supervision") or {}
        channel_states = {
            str(item.get("channel") or ""): item
            for item in composition.get("channel_states", []) or []
            if isinstance(item, dict)
        }
        market_state = channel_states.get("market") or {}
        context = metadata.get("market_context") or composition.get("market_context") or {}
        intelligence = metadata.get("market_intelligence") or {}
        observations = [
            item for item in context.get("observations", []) or [] if isinstance(item, dict)
        ]
        provenance = context.get("provenance") or {}
        missingness = ((intelligence.get("market_regime") or {}).get("missingness") or {})
        missing_feature_ids = set(str(key) for key in missingness)
        observation_by_name = {str(item.get("name") or ""): item for item in observations}

        observation_contract_failures: list[str] = []
        for observation in observations:
            name = str(observation.get("name") or "")
            availability = str(observation.get("availability") or "")
            required_text = all(
                str(observation.get(key) or "").strip()
                for key in ("name", "availability", "source", "derivation", "unit")
            )
            value_contract = (
                observation.get("value") is not None
                if availability == "available"
                else bool(str(observation.get("missing_reason") or "").strip())
            )
            if not required_text or not value_contract:
                observation_contract_failures.append(name or "<unnamed>")

        pit_pass = all(
            (
                provenance.get("case_id") == case_id,
                provenance.get("stock_code") == case.get("stock_code"),
                provenance.get("listing_date") == case.get("listing_date"),
                provenance.get("cutoff_semantics") == "strictly_before_target_listing_date",
                bool(provenance.get("artifact_content_hash")),
                bool(provenance.get("source_provenance")),
            )
        )
        zero_filled = sorted(
            feature_id
            for feature_id in missing_feature_ids
            if feature_id in observation_by_name
            and observation_by_name[feature_id].get("availability") == "available"
            and observation_by_name[feature_id].get("value") == 0
        )
        governed_feature_ids = set(observation_by_name) | missing_feature_ids
        interpretation = intelligence.get("interpretation") or {}
        cited_feature_ids = _source_feature_ids(interpretation)
        unknown_feature_ids = sorted(cited_feature_ids - governed_feature_ids)
        allowed_numbers = _allowed_market_number_tokens(
            observations, str(case.get("listing_date") or "")
        )
        prose_numbers = {
            match.group(0)
            for text in _market_free_text(interpretation)
            for match in _NUMBER_IN_PROSE_RE.finditer(text)
        }
        fabricated_numbers = sorted(prose_numbers - allowed_numbers)
        fabricated_value_detected = bool(unknown_feature_ids or fabricated_numbers)

        market_trace_accounted = False
        market_event_count = 0
        sidecar = _read_json(trace_path)
        events = sidecar.get("trace_events", []) or []
        market_events = [
            event
            for event in events
            if isinstance(event, dict)
            and (
                str(event.get("event_type") or "").casefold() == "market"
                or "market" in str(event.get("agent_name") or "").casefold()
                or "market" in str(event.get("tool_or_skill") or "").casefold()
            )
        ]
        market_event_count = len(market_events)
        if market_events:
            market_trace_accounted = all(
                bool(
                    event.get("evidence_ids")
                    or event.get("calculation_ids")
                    or (event.get("details") or {}).get("no_evidence_reason")
                )
                for event in market_events
            )
        explicit_state = bool(market_state.get("status")) and bool(context.get("status"))
        industry_missing_preserved = all(
            not (
                feature_id in observation_by_name
                and observation_by_name[feature_id].get("availability") == "available"
            )
            for feature_id in missing_feature_ids
            if "industry" in feature_id and "return" in feature_id
        )
        blind_safe = summary.get("blind_2025_y_accessed") is False
        unmet: list[str] = []
        if not explicit_state:
            unmet.append("final supervision or MarketContext lacks an explicit state")
        if observation_contract_failures:
            unmet.append("Market observations have incomplete governed fields")
        if not pit_pass:
            unmet.append("Market provenance/PIT cutoff is incomplete or inconsistent")
        if zero_filled:
            unmet.append("missing market feature was represented as available zero")
        if fabricated_value_detected:
            unmet.append("Market output cites an ungoverned feature or numeric value")
        if not industry_missing_preserved:
            unmet.append("missing industry return was not preserved as unavailable")
        if market_event_count <= 0 or not market_trace_accounted:
            unmet.append("Market trace events are absent or unaccounted")
        if not blind_safe:
            unmet.append("2025 Blind protection is not explicit")
        case_passed = not unmet
        if unmet:
            blockers.append(f"{case_id}: " + "; ".join(unmet))
        checked.append(
            {
                "case_id": case_id,
                "stock_code": case.get("stock_code"),
                "market_channel_status": market_state.get("status"),
                "market_context_status": context.get("status"),
                "governed_observation_count": len(observations),
                "missing_observation_count": len(missing_feature_ids),
                "observation_contract_failures": observation_contract_failures,
                "fabricated_value_detected": fabricated_value_detected,
                "unknown_source_feature_ids": unknown_feature_ids,
                "fabricated_numeric_tokens": fabricated_numbers,
                "zero_fill_detected": bool(zero_filled),
                "zero_filled_feature_ids": zero_filled,
                "pit_violation_detected": not pit_pass,
                "industry_missingness_preserved": industry_missing_preserved,
                "extended_market_enabled": bool(provenance.get("extended_readiness_sha256")),
                "market_event_count": market_event_count,
                "trace_accounted": market_trace_accounted,
                "blind_2025_y_accessed": summary.get("blind_2025_y_accessed"),
                "market_context_content_hash": _json_content_hash(context),
                "satisfied": case_passed,
                "unmet_conditions": unmet,
            }
        )
    exact_matrix = case_ids == set(FINAL_CASE_IDS) and len(cases) == len(FINAL_CASE_IDS)
    passed = exact_matrix and all(item["satisfied"] for item in checked)
    if not exact_matrix:
        blockers.append("Market validation did not receive the exact frozen 3-case final matrix")
    return GateResult(
        "C1_final_matrix_market_validation",
        "C",
        passed,
        {
            "schema_version": MARKET_VALIDATION_SCHEMA_VERSION,
            "artifact_dir": _record_path(role_e_dir),
            "expected_case_ids": list(FINAL_CASE_IDS),
            "cases": checked,
        },
        tuple(blockers),
    )


def audit_role_e(role_e_dir: Path) -> GateResult:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return GateResult(
            "E1_real_provider_final_supervisor",
            "E",
            False,
            {"artifact_dir": _record_path(role_e_dir)},
            ("Role-E final matrix summary.json is missing",),
        )
    summary = _read_json(summary_path)
    cases = [case for case in summary.get("cases", []) if isinstance(case, dict)]
    declared = int(summary.get("declared_case_count") or len(cases))
    executed = int(summary.get("executed_case_count") or 0)
    gate = summary.get("gate_e1") or {}
    gate_satisfied = gate.get("satisfied") is True
    all_integrity = summary.get("all_prospectus_sha256_verified") is True
    blind_safe = summary.get("blind_2025_y_accessed") is False
    outcome_safe = summary.get("outcome_labels_accessed") is False

    case_checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        root = _case_dir(role_e_dir, case)
        missing_files = [name for name in ROLE_E_CASE_REQUIRED if not (root / name).is_file()]
        traceability = _traceability_value(case)
        case_gate = _read_json(root / "gate_e1_evidence.json") if not missing_files else {}
        supervision = _read_json(root / "final_supervision.json") if not missing_files else {}
        llm_synthesis = supervision.get("llm_synthesis") or {}
        synthesis_outcome = supervision.get("outcome") or llm_synthesis.get("outcome")
        sidecar = _read_json(root / "trace_sidecar.json") if not missing_files else {}
        provider_trace = case_gate.get("provider_trace") or case_gate.get("call") or {}
        scope = case_gate.get("out_of_scope_reference_check") or {}
        events = [item for item in sidecar.get("trace_events", []) or [] if isinstance(item, dict)]
        every_trace_event_accounted = bool(events) and all(
            bool(item.get("agent_name"))
            and bool(item.get("tool_or_skill"))
            and bool(
                item.get("evidence_ids")
                or item.get("calculation_ids")
                or (item.get("details") or {}).get("no_evidence_reason")
            )
            for item in events
        )
        trace_kinds = {
            "final_supervisor": any(
                "final_supervisor" in str(item.get("agent_name") or "").casefold()
                or "final_supervision" in str(item.get("action") or "").casefold()
                for item in events
            ),
            "conflict": any(str(item.get("event_type") or "").casefold() == "conflict" for item in events),
            "recheck": any(
                item.get("recheck_id")
                or "recheck" in str(item.get("agent_name") or "").casefold()
                for item in events
            ),
            "verifier": any(
                str(item.get("event_type") or "").casefold() == "verifier"
                or "verifier" in str(item.get("action") or "").casefold()
                for item in events
            ),
            "market": any("market" in str(item.get("agent_name") or "").casefold() for item in events),
        }
        call_complete = _provider_call_trace_complete(provider_trace)
        case_gate_satisfied = case_gate.get("satisfied") is True
        accepted = all(
            (
                synthesis_outcome == "accepted",
                case_gate.get("successful_llm_arbitration") is True,
                case_gate.get("deterministic_fallback_used") is False,
                case_gate.get("provider_is_real_remote") is True,
                call_complete,
                scope.get("status") == "passed",
                scope.get("out_of_scope_reference_count") == 0,
                case_gate.get("severity_floor_respected") is True,
                case.get("creates_no_new_risk") is True,
                case.get("probability_claimed") is False,
            )
        )
        passed = all(
            (
                not missing_files,
                case.get("status") == "completed",
                traceability == 1.0,
                every_trace_event_accounted,
                all(trace_kinds.values()),
                case_gate_satisfied,
                accepted,
            )
        )
        if missing_files:
            blockers.append(f"{case_id}: missing submission artifacts: {', '.join(missing_files)}")
        if case.get("status") != "completed":
            blockers.append(f"{case_id}: final case did not complete")
        if traceability != 1.0:
            blockers.append(f"{case_id}: measured traceability is not 1.0")
        if not every_trace_event_accounted or not all(trace_kinds.values()):
            blockers.append(f"{case_id}: Agent/Tool/Evidence trace categories are incomplete")
        if not case_gate_satisfied:
            blockers.append(f"{case_id}: real-provider Final Supervisor Gate E1 is not satisfied")
        if not accepted:
            blockers.append(
                f"{case_id}: Final Supervisor is not accepted real-provider arbitration with scope/severity PASS"
            )
        case_checks.append(
            {
                "case_id": case_id,
                "status": case.get("status"),
                "traceability": traceability,
                "trace_events_accounted": every_trace_event_accounted,
                "trace_kinds": trace_kinds,
                "synthesis_outcome": synthesis_outcome,
                "successful_llm_arbitration": case_gate.get("successful_llm_arbitration"),
                "deterministic_fallback_used": case_gate.get("deterministic_fallback_used"),
                "provider_is_real_remote": case_gate.get("provider_is_real_remote"),
                "provider_trace_complete": call_complete,
                "scope_status": scope.get("status"),
                "out_of_scope_reference_count": scope.get("out_of_scope_reference_count"),
                "severity_floor_respected": case_gate.get("severity_floor_respected"),
                "creates_no_new_risk": case.get("creates_no_new_risk"),
                "probability_claimed": case.get("probability_claimed"),
                "gate_e1_satisfied": case_gate_satisfied,
                "missing_files": missing_files,
                "passed": passed,
            }
        )

    exact_case_ids = {str(item.get("case_id") or "") for item in cases} == set(FINAL_CASE_IDS)
    if declared != 3 or executed != 3 or len(cases) != 3 or not exact_case_ids:
        blockers.append("final matrix is not the exact executed 2410/2460/1318 case set")
    if not all_integrity:
        blockers.append("not every executed prospectus passed frozen SHA-256 integrity")
    if not gate_satisfied:
        blockers.append("matrix-level Gate E1 is not satisfied")
    if not blind_safe or not outcome_safe:
        blockers.append("Role-E final matrix does not attest pre-listing/Blind isolation")

    explanation_path = role_e_dir / "explanation_quality.json"
    explanation: dict[str, Any] = {}
    m4_passed = False
    if not explanation_path.is_file():
        blockers.append("Role-E M4 explanation_quality.json is missing")
    else:
        explanation = _read_json(explanation_path)
        reviewed_cases = [item for item in explanation.get("cases", []) if isinstance(item, dict)]
        reviewed_case_ids = {str(item.get("case_id") or "") for item in reviewed_cases}
        per_case_reviewers_met = all(
            int(item.get("human_reviewer_count") or 0) >= 2
            and len(
                {
                    str(review.get("reviewer_id") or "")
                    for review in item.get("reviews", []) or []
                    if isinstance(review, dict)
                    and review.get("reviewer_kind") == "human"
                    and review.get("reviewer_id")
                }
            )
            >= 2
            and item.get("passed") is True
            for item in reviewed_cases
        )
        m4_passed = all(
            (
                explanation.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION,
                explanation.get("declared_case_count") == 3,
                explanation.get("reviewed_case_count") == 3,
                reviewed_case_ids == set(FINAL_CASE_IDS),
                per_case_reviewers_met,
                explanation.get("satisfied") is True,
                not (explanation.get("unmet_conditions") or []),
            )
        )
        if not m4_passed:
            blockers.append("Role-E M4 lacks two independent human reviews per case or misses its frozen thresholds")
    passed = all(
        (
            declared == 3,
            executed == 3,
            len(cases) == 3,
            exact_case_ids,
            all_integrity,
            gate_satisfied,
            blind_safe,
            outcome_safe,
            len(case_checks) == 3,
            all(item["passed"] for item in case_checks),
            m4_passed,
        )
    )
    return GateResult(
        "E1_real_provider_final_supervisor",
        "E",
        passed,
        {
            "artifact_dir": _record_path(role_e_dir),
            "declared_case_count": declared,
            "executed_case_count": executed,
            "all_prospectus_sha256_verified": all_integrity,
            "matrix_gate_e1_satisfied": gate_satisfied,
            "blind_2025_y_accessed": summary.get("blind_2025_y_accessed"),
            "outcome_labels_accessed": summary.get("outcome_labels_accessed"),
            "cases": case_checks,
            "m4": {
                "artifact_present": explanation_path.is_file(),
                "reviewed_case_count": explanation.get("reviewed_case_count"),
                "mean_score": explanation.get("mean_score"),
                "minimum_case_score": explanation.get("min_case_score"),
                "satisfied": m4_passed,
            },
        },
        tuple(blockers),
    )


def _blind_violations(payload: Any, *, location: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{location}.{key}"
            lowered = str(key).casefold()
            if "blind" in lowered and value not in (False, None, "", [], {}):
                violations.append(f"{child} carries non-false Blind state")
            if lowered in {"split", "dataset_split", "evaluation_split"} and "blind" in str(
                value
            ).casefold():
                violations.append(f"{child} selects a Blind split")
            violations.extend(_blind_violations(value, location=child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            violations.extend(_blind_violations(value, location=f"{location}[{index}]"))
    return violations


def build_blind_audit(role_b_dir: Path, role_d_dir: Path, role_e_dir: Path) -> dict[str, Any]:
    """Audit a closed allowlist of final artifacts without opening Blind data."""

    required_json = [
        role_b_dir / "existing_gold_evaluable_manifest.json",
        role_b_dir / "document_benchmark_summary.json",
        role_d_dir / "evaluation_summary.json",
        role_d_dir / "ai_vs_offline_report.json",
        role_e_dir / "summary.json",
    ]
    e_summary_path = role_e_dir / "summary.json"
    if e_summary_path.is_file():
        e_summary = _read_json(e_summary_path)
        for case in [item for item in e_summary.get("cases", []) if isinstance(item, dict)]:
            root = _case_dir(role_e_dir, case)
            required_json.extend(
                root / name
                for name in (
                    "analysis_result.json",
                    "final_supervision.json",
                    "trace_sidecar.json",
                    "agent_reasoning_log.json",
                )
            )

    checks: list[dict[str, Any]] = []
    for path in required_json:
        if not path.is_file():
            checks.append(
                {
                    "source": _record_path(path),
                    "exists": False,
                    "sha256": None,
                    "violations": ["required Blind-audit artifact is missing"],
                    "passed": False,
                }
            )
            continue
        try:
            payload = _read_json(path)
            violations = _blind_violations(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            violations = [f"artifact is not a JSON object: {type(exc).__name__}"]
        checks.append(
            {
                "source": _record_path(path),
                "exists": True,
                "size_bytes": path.stat().st_size,
                "sha256": _sha(path),
                "violations": violations,
                "passed": not violations,
            }
        )

    # These two explicit attestations are required in addition to the recursive
    # scan; an absent flag cannot be inferred as false.
    explicit_checks: list[dict[str, Any]] = []
    for path, keys in (
        (role_b_dir / "document_benchmark_summary.json", ("blind_2025_outcome_accessed",)),
        (role_d_dir / "evaluation_summary.json", ("blind_2025_y_accessed",)),
        (role_e_dir / "summary.json", ("blind_2025_y_accessed", "outcome_labels_accessed")),
    ):
        payload = _read_json(path) if path.is_file() else {}
        for key in keys:
            explicit_checks.append(
                {
                    "source": _record_path(path),
                    "assertion": f"{key} is explicitly false",
                    "value": payload.get(key),
                    "passed": payload.get(key) is False,
                }
            )
    passed = bool(checks) and all(check.get("passed") is True for check in checks + explicit_checks)
    return {
        "schema_version": BLIND_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "checks": checks,
        "explicit_attestations": explicit_checks,
        "scope": [item["source"] for item in checks],
        "blind_data_opened_by_audit": False,
        "statement": (
            "All governed final artifacts explicitly preserve the 2025 Blind boundary."
            if passed
            else "Blind audit is incomplete or contains a failing attestation; submission must remain blocked."
        ),
    }


def build_provenance_audit(
    role_e_dir: Path,
    role_b_dir: Path | None = None,
    role_d_dir: Path | None = None,
) -> dict[str, Any]:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return {
            "schema_version": PROVENANCE_AUDIT_SCHEMA_VERSION,
            "passed": False,
            "cases": [],
            "blockers": ["Role-E final summary is missing"],
        }
    summary = _read_json(summary_path)
    cases: list[dict[str, Any]] = []
    blockers: list[str] = []
    handoffs: list[dict[str, Any]] = []

    b_summary_path = (role_b_dir / "document_benchmark_summary.json") if role_b_dir else None
    b_manifest_path = (role_b_dir / "existing_gold_evaluable_manifest.json") if role_b_dir else None
    if b_summary_path and b_manifest_path and b_summary_path.is_file() and b_manifest_path.is_file():
        b_summary = _read_json(b_summary_path)
        b_manifest = _read_json(b_manifest_path)
        b_passed = all(
            (
                b_summary.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION,
                b_manifest.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION,
                bool(b_summary.get("existing_gold_source")),
                bool(b_manifest.get("manifest_hash")),
                b_summary.get("existing_gold_source_hash_or_manifest") == b_manifest.get("manifest_hash"),
                bool((b_manifest.get("source_governance") or {}).get("frozen_manifest_hash")),
            )
        )
        handoffs.append(
            {
                "owner": "B",
                "source": _record_path(b_summary_path),
                "sha256": _sha(b_summary_path),
                "manifest_sha256": _sha(b_manifest_path),
                "metric_protocol_version": b_summary.get("metric_protocol_version"),
                "existing_gold_source": b_summary.get("existing_gold_source"),
                "existing_gold_manifest_hash": b_manifest.get("manifest_hash"),
                "frozen_source_manifest_hash": (b_manifest.get("source_governance") or {}).get(
                    "frozen_manifest_hash"
                ),
                "passed": b_passed,
            }
        )
        if not b_passed:
            blockers.append("Role-B provenance is incomplete or not hash-bound to frozen Existing Gold")
    else:
        blockers.append("Role-B provenance artifacts are missing")

    d_summary_path = (role_d_dir / "evaluation_summary.json") if role_d_dir else None
    if d_summary_path and d_summary_path.is_file():
        d_summary = _read_json(d_summary_path)
        d_passed = all(
            (
                d_summary.get("metric_protocol_version") == METRIC_PROTOCOL_VERSION,
                bool(d_summary.get("evaluation_split")),
                bool(d_summary.get("source_hashes")),
                d_summary.get("significant_drop_5d_definition") == SIGNIFICANT_DROP_5D_DEFINITION,
            )
        )
        handoffs.append(
            {
                "owner": "D",
                "source": _record_path(d_summary_path),
                "sha256": _sha(d_summary_path),
                "metric_protocol_version": d_summary.get("metric_protocol_version"),
                "evaluation_split": d_summary.get("evaluation_split"),
                "source_hashes": d_summary.get("source_hashes"),
                "passed": d_passed,
            }
        )
        if not d_passed:
            blockers.append("Role-D provenance lacks protocol/split/source hashes")
    else:
        blockers.append("Role-D provenance artifact is missing")

    code_base_sha = summary.get("code_base_sha")
    cases_manifest_sha256 = summary.get("cases_manifest_sha256")
    config_sha256 = summary.get("config_sha256")
    matrix_identity_complete = all((code_base_sha, cases_manifest_sha256, config_sha256))
    if not matrix_identity_complete:
        blockers.append("Role-E matrix lacks code/base, case-manifest, or config SHA-256 identity")

    for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
        case_id = str(case.get("case_id") or "")
        root = _case_dir(role_e_dir, case)
        verification_path = root / "prospectus_verification.json"
        sidecar_path = root / "trace_sidecar.json"
        gate_path = root / "gate_e1_evidence.json"
        verification = _read_json(verification_path) if verification_path.is_file() else {}
        sidecar = _read_json(sidecar_path) if sidecar_path.is_file() else {}
        gate = _read_json(gate_path) if gate_path.is_file() else {}
        identity = sidecar.get("identity") or {}
        provenance = identity.get("provenance") or {}
        call = gate.get("provider_trace") or gate.get("call") or gate.get("provider_call") or {}
        if not call:
            # Gate-E evidence nests the exact call in different revisions; fall
            # back to final supervision evidence if present.
            final_path = root / "final_supervision.json"
            if final_path.is_file():
                final = _read_json(final_path)
                call = ((final.get("llm_synthesis") or {}).get("call") or {})
        accepted = gate.get("satisfied") is True
        call_complete = _provider_call_trace_complete(call)
        analysis_path = root / "analysis_result.json"
        analysis = _read_json(analysis_path) if analysis_path.is_file() else {}
        market_context = ((analysis.get("metadata") or {}).get("market_context") or {})
        market_provenance = market_context.get("provenance") or {}
        pit_complete = all(
            (
                market_provenance.get("case_id") == case_id,
                market_provenance.get("stock_code") == case.get("stock_code"),
                market_provenance.get("listing_date") == case.get("listing_date"),
                market_provenance.get("cutoff_semantics") == "strictly_before_target_listing_date",
                bool(market_provenance.get("artifact_content_hash")),
                bool(market_provenance.get("source_provenance")),
            )
        )
        case_passed = all(
            (
                verification.get("sha256_matches_frozen_catalog") is True,
                verification.get("size_matches_frozen_catalog") is True,
                verification.get("page_count_matches_frozen_catalog") is True,
                verification.get("path_recorded") is False,
                bool(identity.get("run_id")),
                bool(provenance.get("workflow")),
                bool(provenance.get("trace_schema_version")),
                bool(provenance.get("conflict_policy_version")),
                bool(provenance.get("recheck_policy_version")),
                matrix_identity_complete,
                call_complete,
                accepted,
                pit_complete,
            )
        )
        if not case_passed:
            blockers.append(f"{case_id}: incomplete prospectus/runtime/provider provenance")
        cases.append(
            {
                "case_id": case_id,
                "passed": case_passed,
                "prospectus_sha256": verification.get("sha256"),
                "sha256_matches_frozen_catalog": verification.get("sha256_matches_frozen_catalog"),
                "size_matches_frozen_catalog": verification.get("size_matches_frozen_catalog"),
                "page_count_matches_frozen_catalog": verification.get("page_count_matches_frozen_catalog"),
                "path_recorded": verification.get("path_recorded"),
                "run_id": identity.get("run_id"),
                "workflow": provenance.get("workflow"),
                "trace_schema_version": provenance.get("trace_schema_version"),
                "conflict_policy_version": provenance.get("conflict_policy_version"),
                "recheck_policy_version": provenance.get("recheck_policy_version"),
                "code_base_sha": code_base_sha,
                "cases_manifest_sha256": cases_manifest_sha256,
                "config_sha256": config_sha256,
                "gate_e1_satisfied": accepted,
                "provider_name": call.get("provider_name"),
                "model_name": call.get("model_name"),
                "prompt_version": call.get("prompt_version"),
                "request_id": call.get("request_id"),
                "raw_response_hash": call.get("raw_response_hash"),
                "provider_call_trace_complete": call_complete,
                "pit_provenance_complete": pit_complete,
                "dataset_split": market_provenance.get("dataset_split"),
                "market_artifact_content_hash": market_provenance.get("artifact_content_hash"),
            }
        )
    exact_cases = {case["case_id"] for case in cases} == set(FINAL_CASE_IDS)
    passed = all(
        (
            len(cases) == 3,
            exact_cases,
            matrix_identity_complete,
            len(handoffs) == 2,
            all(item["passed"] for item in handoffs),
            all(case["passed"] for case in cases),
        )
    )
    if len(cases) != 3 or not exact_cases:
        blockers.append("provenance audit did not receive the exact frozen 3-case matrix")
    return {
        "schema_version": PROVENANCE_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "handoffs": handoffs,
        "matrix_identity": {
            "code_base_sha": code_base_sha,
            "cases_manifest_sha256": cases_manifest_sha256,
            "config_sha256": config_sha256,
            "complete": matrix_identity_complete,
        },
        "cases": cases,
        "blockers": blockers,
    }


def _expected_request_id(case: dict[str, Any]) -> str | None:
    verification = case.get("prospectus_verification") or {}
    digest = verification.get("sha256")
    stock_code = case.get("stock_code")
    listing_date = case.get("listing_date")
    if not all((digest, stock_code, listing_date)):
        return None
    return str(uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date}:{digest}"))


def _calculation_payloads(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "calculation" and isinstance(value, dict) and value:
                found.append(value)
            else:
                found.extend(_calculation_payloads(value))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(_calculation_payloads(value))
    return found


def _case_deterministic_facets(role_e_dir: Path, case: dict[str, Any]) -> dict[str, Any]:
    root = _case_dir(role_e_dir, case)
    analysis_path = root / "analysis_result.json"
    gate_path = root / "gate_e1_evidence.json"
    analysis = _read_json(analysis_path) if analysis_path.is_file() else {}
    gate = _read_json(gate_path) if gate_path.is_file() else {}
    metadata = analysis.get("metadata") or {}
    market_context = metadata.get("market_context") or {}
    call = gate.get("provider_trace") or gate.get("call") or {}
    calculations = _calculation_payloads(analysis)
    calculations.sort(key=lambda item: _json_content_hash(item))
    return {
        "market_context_hash": _json_content_hash(market_context) if market_context else None,
        "calculation_set_hash": _json_content_hash(calculations) if calculations else None,
        "calculation_count": len(calculations),
        "traceability": _traceability_value(case),
        "provider_name": call.get("provider_name") or gate.get("provider_name"),
        "model_name": call.get("model_name"),
        "prompt_version": call.get("prompt_version"),
        "request_id": call.get("request_id"),
        "response_hash": call.get("raw_response_hash"),
    }


def build_determinism_audit(role_e_dir: Path, baseline_role_e_dir: Path | None = None) -> dict[str, Any]:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return {
            "schema_version": DETERMINISM_AUDIT_SCHEMA_VERSION,
            "passed": False,
            "cases": [],
            "pairwise_repeatability": "NOT_EVALUATED",
            "blockers": ["Role-E final summary is missing"],
        }
    summary = _read_json(summary_path)
    current_cases = {
        str(case.get("case_id")): case
        for case in summary.get("cases", [])
        if isinstance(case, dict) and case.get("case_id")
    }
    cases: list[dict[str, Any]] = []
    blockers: list[str] = []
    matrix_identity_complete = all(
        (
            summary.get("code_base_sha"),
            summary.get("cases_manifest_sha256"),
            summary.get("config_sha256"),
        )
    )
    if not matrix_identity_complete:
        blockers.append("matrix code/config/case-manifest identity is incomplete")
    for case_id, case in current_cases.items():
        expected = _expected_request_id(case)
        actual = case.get("deterministic_request_id")
        identity_pass = bool(expected) and actual == expected
        facets = _case_deterministic_facets(role_e_dir, case)
        provider_identity_complete = all(
            facets.get(key)
            for key in (
                "provider_name",
                "model_name",
                "prompt_version",
                "request_id",
                "response_hash",
            )
        )
        case_passed = all(
            (
                identity_pass,
                bool((case.get("prospectus_verification") or {}).get("sha256")),
                bool(facets.get("market_context_hash")),
                facets.get("traceability") == 1.0,
                bool(case.get("final_supervision_content_hash")),
                provider_identity_complete,
            )
        )
        if not case_passed:
            blockers.append(f"{case_id}: deterministic runtime identity/facets are incomplete")
        cases.append(
            {
                "case_id": case_id,
                "expected_request_id": expected,
                "actual_request_id": actual,
                "identity_reproducible": identity_pass,
                "prospectus_sha256": (case.get("prospectus_verification") or {}).get("sha256"),
                "final_supervision_content_hash": case.get("final_supervision_content_hash"),
                **facets,
                "passed": case_passed,
            }
        )

    pairwise = "NOT_EVALUATED"
    pairwise_checks: list[dict[str, Any]] = []
    if baseline_role_e_dir is not None:
        baseline_path = baseline_role_e_dir / "summary.json"
        if not baseline_path.is_file():
            blockers.append("baseline Role-E summary requested for pairwise determinism but missing")
            pairwise = "FAIL"
        else:
            baseline = _read_json(baseline_path)
            baseline_cases = {
                str(case.get("case_id")): case
                for case in baseline.get("cases", [])
                if isinstance(case, dict) and case.get("case_id")
            }
            pairwise = "PASS"
            if set(baseline_cases) != set(current_cases):
                pairwise = "FAIL"
                blockers.append("baseline and AI final matrices do not contain the same frozen cases")
            for case_id, current in current_cases.items():
                prior = baseline_cases.get(case_id)
                current_facets = _case_deterministic_facets(role_e_dir, current)
                prior_facets = (
                    _case_deterministic_facets(baseline_role_e_dir, prior) if prior else {}
                )
                same = bool(prior) and all(
                    (
                        current.get("deterministic_request_id") == prior.get("deterministic_request_id"),
                        (current.get("prospectus_verification") or {}).get("sha256")
                        == (prior.get("prospectus_verification") or {}).get("sha256"),
                        current.get("parsed_chunk_count") == prior.get("parsed_chunk_count"),
                        current_facets.get("market_context_hash")
                        == prior_facets.get("market_context_hash"),
                        current_facets.get("calculation_set_hash")
                        == prior_facets.get("calculation_set_hash"),
                        current_facets.get("calculation_count")
                        == prior_facets.get("calculation_count"),
                        current_facets.get("traceability") == prior_facets.get("traceability"),
                    )
                )
                pairwise_checks.append(
                    {
                        "case_id": case_id,
                        "deterministic_facets_match": same,
                        "request_identity_match": current.get("deterministic_request_id")
                        == (prior or {}).get("deterministic_request_id"),
                        "prospectus_identity_match": (
                            current.get("prospectus_verification") or {}
                        ).get("sha256")
                        == ((prior or {}).get("prospectus_verification") or {}).get("sha256"),
                        "market_context_match": current_facets.get("market_context_hash")
                        == prior_facets.get("market_context_hash"),
                        "calculation_set_match": current_facets.get("calculation_set_hash")
                        == prior_facets.get("calculation_set_hash"),
                        "traceability_match": current_facets.get("traceability")
                        == prior_facets.get("traceability"),
                        "current_calculation_set_hash": current_facets.get("calculation_set_hash"),
                        "baseline_calculation_set_hash": prior_facets.get("calculation_set_hash"),
                    }
                )
                if not same:
                    pairwise = "FAIL"
                    blockers.append(f"{case_id}: deterministic facets differ from the supplied baseline run")

    # Remote LLM prose is not promised byte-for-byte deterministic. The audit
    # proves deterministic identities/facets and preserves provider response
    # hashes instead of making a false reproducibility claim.
    exact_cases = set(current_cases) == set(FINAL_CASE_IDS)
    passed = all(
        (
            len(cases) == 3,
            exact_cases,
            matrix_identity_complete,
            all(case["passed"] for case in cases),
            pairwise == "PASS" if baseline_role_e_dir is not None else True,
        )
    )
    if len(cases) != 3 or not exact_cases:
        blockers.append("determinism audit did not receive the exact frozen 3-case matrix")
    return {
        "schema_version": DETERMINISM_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "definition": (
            "Deterministic request identity and governed deterministic facets must reproduce; "
            "remote LLM text is audited by provider/model/prompt/request/response hash, not by byte-for-byte replay."
        ),
        "cases": cases,
        "matrix_identity": {
            "code_base_sha": summary.get("code_base_sha"),
            "cases_manifest_sha256": summary.get("cases_manifest_sha256"),
            "config_sha256": summary.get("config_sha256"),
            "complete": matrix_identity_complete,
        },
        "pairwise_repeatability": pairwise,
        "pairwise_checks": pairwise_checks,
        "blockers": blockers,
    }


def _artifact_record(
    path: Path,
    *,
    logical_path: str,
    owner: str,
    gate: str,
    required: bool,
) -> dict[str, Any]:
    exists = path.is_file()
    issues = _scan_path_for_sensitive_material(path) if exists else []
    return {
        "logical_path": logical_path,
        "owner": owner,
        "gate": gate,
        "required": required,
        "exists": exists,
        "artifact_type": path.suffix.casefold().lstrip(".") or "file",
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": _sha(path) if exists else None,
        "allowed_in_submission": exists and not issues,
        "rejection_reasons": issues,
    }


def build_artifact_index(
    *,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    runbook_path: Path,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    repo_root = runbook_path.parent.parent

    def add(
        path: Path,
        logical: str,
        owner: str,
        gate: str,
        required: bool = True,
    ) -> None:
        records.append(
            _artifact_record(
                path,
                logical_path=logical,
                owner=owner,
                gate=gate,
                required=required,
            )
        )

    source_logical_paths: set[str] = set()
    for path, logical in _iter_source_files(repo_root):
        add(path, logical, "A", "A1")
        source_logical_paths.add(logical)
    for name in SOURCE_ROOT_FILES:
        logical = f"source/{name}"
        if logical not in source_logical_paths:
            add(repo_root / name, logical, "A", "A1")
    for name in SUBMISSION_DOCS:
        logical = f"source/{name}"
        if logical not in source_logical_paths:
            add(repo_root / name, logical, "A", "A1")

    for name in ROLE_B_REQUIRED:
        add(role_b_dir / name, f"artifacts/role_b/{name}", "B", "B1")
    ai_comparisons = _ai_vs_offline_candidates(role_b_dir, role_d_dir)
    if ai_comparisons:
        for ai_comparison in ai_comparisons:
            add(
                ai_comparison,
                "artifacts/evaluation/ai_vs_offline_report.json",
                "B/D",
                "B1/D1",
            )
    else:
        add(
            role_d_dir / "ai_vs_offline_report.json",
            "artifacts/evaluation/ai_vs_offline_report.json",
            "B/D",
            "B1/D1",
        )
    for name in ROLE_D_REQUIRED:
        if name != "ai_vs_offline_report.json":
            add(role_d_dir / name, f"artifacts/role_d/{name}", "D", "D1")
    summary_path = role_e_dir / "summary.json"
    add(summary_path, "artifacts/role_e/summary.json", "E", "E1/M3")
    add(
        role_e_dir / "market_final_matrix_validation.json",
        "artifacts/role_e/market_final_matrix_validation.json",
        "C",
        "C1",
    )
    add(
        role_e_dir / "explanation_quality.json",
        "artifacts/role_e/explanation_quality.json",
        "E",
        "M4",
    )
    if summary_path.is_file():
        summary = _read_json(summary_path)
        for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
            case_id = str(case.get("case_id") or "")
            for name in ROLE_E_CASE_REQUIRED:
                add(
                    _case_dir(role_e_dir, case) / name,
                    f"artifacts/role_e/{case_id}/{name}",
                    "E",
                    "E1/M3",
                )
    for name in (
        "submission_readiness.json",
        "blind_audit.json",
        "provenance_audit.json",
        "determinism_audit.json",
        "security_audit.json",
        "documentation_consistency_audit.json",
    ):
        add(a_output_dir / name, f"artifacts/role_a/{name}", "A", "A1")
    records.sort(key=lambda item: item["logical_path"])
    logical_paths = [item["logical_path"] for item in records]
    duplicates = sorted({path for path in logical_paths if logical_paths.count(path) > 1})
    missing = [
        item["logical_path"]
        for item in records
        if item["required"] and not item["exists"]
    ]
    rejected = [
        item["logical_path"]
        for item in records
        if item["exists"] and not item["allowed_in_submission"]
    ]
    return {
        "schema_version": ARTIFACT_INDEX_SCHEMA_VERSION,
        "artifact_count": len(records),
        "required_count": sum(1 for item in records if item["required"]),
        "present_count": sum(1 for item in records if item["exists"]),
        "missing_count": len(missing),
        "rejected_count": len(rejected),
        "missing": missing,
        "rejected": rejected,
        "duplicate_logical_paths": duplicates,
        "passed": not missing and not rejected and not duplicates,
        "artifacts": records,
    }


def _record_path(path: Path) -> str:
    """Render a path for an audit record without embedding a local absolute path.

    These audits are themselves packaged and shipped, and the packager refuses
    any artifact carrying a local absolute path -- so the audits must not create
    one, or the tooling refuses its own output.  A path inside the working tree
    is recorded relative to it; anything outside is reduced to its own name,
    which keeps the record readable without pinning it to the machine that
    produced it.  Relative inputs, which is what the CLI defaults pass, are kept
    verbatim.
    """

    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _scan_path_for_sensitive_material(path: Path) -> list[str]:
    issues: list[str] = []
    if path.name.casefold() in {name.casefold() for name in _FORBIDDEN_PACKAGE_NAMES}:
        issues.append(f"forbidden secret-bearing filename: {path.name}")
    if path.suffix.casefold() in _FORBIDDEN_PACKAGE_SUFFIXES:
        issues.append(f"forbidden licensed/secret/model file type: {path.suffix}")
    if path.stat().st_size > 5 * 1024 * 1024:
        issues.append("oversized file rejected from submission allowlist")
        return issues
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return issues
    if _PRIVATE_KEY_RE.search(text):
        issues.append("private-key material detected")
    if _TOKEN_RE.search(text):
        issues.append("token-like secret detected")
    if _BEARER_TOKEN_RE.search(text):
        issues.append("Bearer token-like secret detected")
    if _AWS_ACCESS_KEY_RE.search(text):
        issues.append("cloud access-key-like secret detected")
    # Do not let source-code regex declarations trigger the path scanner that
    # consumes them.  We still scan every non-regex line, including comments,
    # strings and ordinary source literals where an accidental workstation path
    # could leak into the package.
    absolute_path_scan_text = "\n".join(
        line for line in text.splitlines() if "re.compile(" not in line
    )
    if _WINDOWS_ABS_RE.search(absolute_path_scan_text) or _UNIX_LOCAL_ABS_RE.search(
        absolute_path_scan_text
    ):
        issues.append("local absolute path detected")
    return issues


def build_security_audit(
    *,
    repo_root: Path,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
) -> dict[str, Any]:
    """Scan exactly the package allowlist; never traverse licensed/local data roots."""

    candidates = list(_iter_source_files(repo_root)) + list(
        _iter_submission_artifacts(
            role_b_dir=role_b_dir,
            role_d_dir=role_d_dir,
            role_e_dir=role_e_dir,
            a_output_dir=a_output_dir,
            include_a_outputs=False,
        )
    )
    logical_counts: dict[str, int] = {}
    files: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for path, logical in candidates:
        logical_counts[logical] = logical_counts.get(logical, 0) + 1
        issues = _scan_path_for_sensitive_material(path)
        record = {
            "logical_path": logical,
            "size_bytes": path.stat().st_size,
            "sha256": _sha(path),
            "issues": issues,
        }
        files.append(record)
        if issues:
            rejected.append(record)
    duplicates = sorted(path for path, count in logical_counts.items() if count > 1)
    if duplicates:
        rejected.extend(
            {"logical_path": path, "issues": ["duplicate logical artifact path"]}
            for path in duplicates
        )
    return {
        "schema_version": SECURITY_AUDIT_SCHEMA_VERSION,
        "passed": not rejected,
        "scope": "explicit submission source/artifact allowlist only",
        "scanned_file_count": len(files),
        "files": files,
        "duplicates": duplicates,
        "rejected": rejected,
        "licensed_pdf_included": any(
            item["logical_path"].casefold().endswith(".pdf") for item in files
        ),
        "reviewer_work_file_included": any(
            "data/explanation_quality/reviews.json" in item["logical_path"] for item in files
        ),
    }


def build_documentation_consistency_audit(repo_root: Path) -> dict[str, Any]:
    documents = (
        repo_root / "README.md",
        repo_root / "docs/V0.4_RELEASE_ACCEPTANCE.md",
        repo_root / "docs/V045_CURRENT_EXECUTION_PLAN.md",
        repo_root / "docs/ROADMAP.md",
        repo_root / "docs/SUBMISSION_RUNBOOK.md",
    )
    checks: list[dict[str, Any]] = []
    for path in documents:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        current_section = "\n".join(text.splitlines()[:180])
        checks.extend(
            [
                {
                    "source": _record_path(path),
                    "assertion": "document exists",
                    "passed": path.is_file(),
                },
                {
                    "source": _record_path(path),
                    "assertion": "Metric-v2 protocol identity is current",
                    "passed": METRIC_PROTOCOL_VERSION in text,
                },
                {
                    "source": _record_path(path),
                    "assertion": "resolved prospectus-root blocker is not presented as current",
                    "passed": "blocker = IPO_RISK_PROSPECTUS_ROOT is not set" not in current_section,
                },
                {
                    "source": _record_path(path),
                    "assertion": "resolved case_id serialization blocker is not presented as current",
                    "passed": "ValueError: governed result missing case_id" not in current_section,
                },
            ]
        )
    root_readme = documents[0].read_text(encoding="utf-8") if documents[0].is_file() else ""
    acceptance = documents[1].read_text(encoding="utf-8") if documents[1].is_file() else ""
    checks.extend(
        [
            {
                "source": _record_path(documents[0]),
                "assertion": "README does not claim COMPETITION_READY",
                "passed": "尚未标记 `COMPETITION_READY`" in root_readme,
            },
            {
                "source": _record_path(documents[1]),
                "assertion": "Acceptance verdict remains NOT YET COMPETITION_READY",
                "passed": "Current verdict: **NOT YET COMPETITION_READY**" in acceptance,
            },
        ]
    )
    return {
        "schema_version": DOCUMENTATION_AUDIT_SCHEMA_VERSION,
        "passed": bool(checks) and all(item["passed"] for item in checks),
        "checks": checks,
        "blockers": [item["assertion"] for item in checks if not item["passed"]],
    }


def _ai_vs_offline_candidates(role_b_dir: Path, role_d_dir: Path) -> list[Path]:
    return [
        candidate
        for candidate in (
            role_b_dir / "ai_vs_offline_report.json",
            role_d_dir / "ai_vs_offline_report.json",
        )
        if candidate.is_file()
    ]


def _find_ai_vs_offline(role_b_dir: Path, role_d_dir: Path) -> Path | None:
    candidates = _ai_vs_offline_candidates(role_b_dir, role_d_dir)
    return candidates[0] if candidates else None


def build_submission_readiness(
    *,
    repo_root: Path,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    baseline_role_e_dir: Path | None = None,
    latest_main_ci_passed: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    b = audit_role_b(role_b_dir)
    d = audit_role_d(role_d_dir)
    e = audit_role_e(role_e_dir)
    c = audit_market_from_final_matrix(role_e_dir)
    blind = build_blind_audit(role_b_dir, role_d_dir, role_e_dir)
    provenance = build_provenance_audit(role_e_dir, role_b_dir, role_d_dir)
    determinism = build_determinism_audit(role_e_dir, baseline_role_e_dir)
    security = build_security_audit(
        repo_root=repo_root,
        role_b_dir=role_b_dir,
        role_d_dir=role_d_dir,
        role_e_dir=role_e_dir,
        a_output_dir=a_output_dir,
    )
    documentation = build_documentation_consistency_audit(repo_root)
    ai_vs_offline = _find_ai_vs_offline(role_b_dir, role_d_dir)
    runbook = repo_root / "docs/SUBMISSION_RUNBOOK.md"

    a_blockers: list[str] = []
    if not blind["passed"]:
        a_blockers.append("blind audit is not PASS")
    if not provenance["passed"]:
        a_blockers.append("provenance audit is not PASS")
    if not determinism["passed"]:
        a_blockers.append("determinism audit is not PASS")
    if not security["passed"]:
        a_blockers.append("submission allowlist security audit is not PASS")
    if not documentation["passed"]:
        a_blockers.append("documentation consistency audit is not PASS")
    if not runbook.is_file():
        a_blockers.append("docs/SUBMISSION_RUNBOOK.md is missing")
    if ai_vs_offline is None:
        a_blockers.append("ai_vs_offline_report.json is missing from B/D handoff")
    if not latest_main_ci_passed:
        a_blockers.append(CI_ATTESTATION_BLOCKER)
    a_blockers.append(ARTIFACT_INDEX_BLOCKER)
    a = GateResult(
        "A1_final_integration_submission_freeze",
        "A",
        not a_blockers,
        {
            "blind_audit_passed": blind["passed"],
            "provenance_audit_passed": provenance["passed"],
            "determinism_audit_passed": determinism["passed"],
            "security_audit_passed": security["passed"],
            "security_rejected_count": len(security["rejected"]),
            "documentation_consistency_passed": documentation["passed"],
            "documentation_blockers": documentation["blockers"],
            "runbook_present": runbook.is_file(),
            "ai_vs_offline_report": _record_path(ai_vs_offline) if ai_vs_offline else None,
            "latest_main_ci_passed": latest_main_ci_passed,
            "artifact_index_passed": None,
        },
        tuple(a_blockers),
    )

    gates = [b, c, d, e, a]
    blockers = [blocker for gate in gates for blocker in gate.blockers]
    ready = all(gate.passed for gate in gates)
    readiness = {
        "schema_version": READINESS_SCHEMA_VERSION,
        "competition_ready": ready,
        "verdict": "COMPETITION_READY" if ready else "NOT_YET_COMPETITION_READY",
        "gates": [gate.as_dict() for gate in gates],
        "blockers": blockers,
        "rules": {
            "no_missing_gate_may_be_inferred_as_pass": True,
            "model_channel_may_be_explicitly_unavailable": True,
            "2025_blind_y_must_remain_unaccessed": True,
            "remote_llm_text_byte_determinism_claimed": False,
            "packaging_allowed_only_when_competition_ready": True,
        },
        "audits": {
            "security": security,
            "documentation_consistency": documentation,
        },
    }
    return readiness, blind, provenance, determinism


def finalize_readiness_with_artifact_index(
    readiness: dict[str, Any], artifact_index: dict[str, Any]
) -> dict[str, Any]:
    """Bind the final index result into readiness after all audit files exist.

    ``artifact_index.json`` cannot hash itself. Every other package allowlist
    member is indexed, and the packager treats this one explicit self-reference
    as the only permissible difference between the index and ZIP inputs.
    """

    gates = [gate for gate in readiness.get("gates", []) if isinstance(gate, dict)]
    a_gate = next((gate for gate in gates if gate.get("owner") == "A"), None)
    if a_gate is None:
        raise ValueError("submission readiness carries no Role-A Gate")
    blockers = [
        str(blocker)
        for blocker in a_gate.get("blockers", []) or []
        if blocker != ARTIFACT_INDEX_BLOCKER and not str(blocker).startswith("artifact index is not PASS")
    ]
    index_passed = artifact_index.get("passed") is True
    if not index_passed:
        blockers.append(
            "artifact index is not PASS "
            f"(missing={artifact_index.get('missing_count')}, "
            f"rejected={artifact_index.get('rejected_count')}, "
            f"duplicates={len(artifact_index.get('duplicate_logical_paths') or [])})"
        )
    details = dict(a_gate.get("details") or {})
    details.update(
        {
            "artifact_index_passed": index_passed,
            "artifact_index_required_count": artifact_index.get("required_count"),
            "artifact_index_present_count": artifact_index.get("present_count"),
            "artifact_index_missing_count": artifact_index.get("missing_count"),
            "artifact_index_rejected_count": artifact_index.get("rejected_count"),
        }
    )
    a_gate["details"] = details
    a_gate["blockers"] = blockers
    a_gate["passed"] = not blockers
    readiness["blockers"] = [
        str(blocker)
        for gate in gates
        for blocker in gate.get("blockers", []) or []
    ]
    ready = bool(gates) and all(gate.get("passed") is True for gate in gates)
    readiness["competition_ready"] = ready
    readiness["verdict"] = "COMPETITION_READY" if ready else "NOT_YET_COMPETITION_READY"
    readiness["artifact_index"] = {
        "passed": index_passed,
        "artifact_count": artifact_index.get("artifact_count"),
        "required_count": artifact_index.get("required_count"),
        "present_count": artifact_index.get("present_count"),
        "missing_count": artifact_index.get("missing_count"),
        "rejected_count": artifact_index.get("rejected_count"),
        "self_reference_exemption": ARTIFACT_INDEX_LOGICAL_PATH,
    }
    return readiness


def write_submission_audits(
    *,
    output_dir: Path,
    readiness: dict[str, Any],
    blind: dict[str, Any],
    provenance: dict[str, Any],
    determinism: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_payloads: list[tuple[str, dict[str, Any]]] = [
        ("submission_readiness.json", readiness),
        ("blind_audit.json", blind),
        ("provenance_audit.json", provenance),
        ("determinism_audit.json", determinism),
    ]
    embedded_audits = readiness.get("audits") or {}
    for name, key in (
        ("security_audit.json", "security"),
        ("documentation_consistency_audit.json", "documentation_consistency"),
    ):
        payload = embedded_audits.get(key)
        if isinstance(payload, dict):
            audit_payloads.append((name, payload))
    for name, payload in audit_payloads:
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def write_market_final_matrix_validation(path: Path, readiness: dict[str, Any]) -> None:
    gate = next((item for item in readiness.get("gates", []) if item.get("owner") == "C"), None)
    if gate is None:
        raise ValueError("submission readiness carries no Role-C Gate")
    payload = {
        **(gate.get("details") or {}),
        "satisfied": gate.get("passed") is True,
        "unmet_conditions": gate.get("blockers") or [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_artifact_index(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_source_files(repo_root: Path) -> Iterable[tuple[Path, str]]:
    for name in SOURCE_ROOT_FILES:
        path = repo_root / name
        if path.is_file():
            yield path, f"source/{name}"
    for dirname in SOURCE_ROOT_DIRS:
        root = repo_root / dirname
        if not root.is_dir():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(repo_root).as_posix()
            yield path, f"source/{relative}"
    for name in SUBMISSION_DOCS:
        path = repo_root / name
        if path.is_file():
            yield path, f"source/{name}"


def _iter_submission_artifacts(
    *,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    include_a_outputs: bool = True,
) -> Iterable[tuple[Path, str]]:
    for name in ROLE_B_REQUIRED:
        path = role_b_dir / name
        if path.is_file():
            yield path, f"artifacts/role_b/{name}"
    for ai in _ai_vs_offline_candidates(role_b_dir, role_d_dir):
        yield ai, "artifacts/evaluation/ai_vs_offline_report.json"
    for name in ROLE_D_REQUIRED:
        if name == "ai_vs_offline_report.json":
            continue
        path = role_d_dir / name
        if path.is_file():
            yield path, f"artifacts/role_d/{name}"
    summary_path = role_e_dir / "summary.json"
    if summary_path.is_file():
        yield summary_path, "artifacts/role_e/summary.json"
        for name in ("market_final_matrix_validation.json", "explanation_quality.json"):
            path = role_e_dir / name
            if path.is_file():
                yield path, f"artifacts/role_e/{name}"
        summary = _read_json(summary_path)
        for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
            case_id = str(case.get("case_id") or "")
            for name in ROLE_E_CASE_REQUIRED:
                path = _case_dir(role_e_dir, case) / name
                if path.is_file():
                    yield path, f"artifacts/role_e/{case_id}/{name}"
    if include_a_outputs:
        for name in (
            "submission_readiness.json",
            "blind_audit.json",
            "provenance_audit.json",
            "determinism_audit.json",
            "security_audit.json",
            "documentation_consistency_audit.json",
            "artifact_index.json",
        ):
            path = a_output_dir / name
            if path.is_file():
                yield path, f"artifacts/role_a/{name}"


def _verify_artifact_index(index_path: Path, selected: dict[str, Path]) -> None:
    if not index_path.is_file():
        raise RuntimeError("artifact_index.json is missing")
    index = _read_json(index_path)
    if index.get("passed") is not True:
        raise RuntimeError("submission package refused: artifact index is incomplete or rejected")
    if index.get("duplicate_logical_paths"):
        raise RuntimeError("submission package refused: artifact index has duplicate logical paths")
    seen: set[str] = set()
    records = index.get("artifacts", []) or []
    if index.get("artifact_count") != len(records):
        raise RuntimeError("submission package refused: artifact index count is inconsistent")
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError("submission package refused: malformed artifact index record")
        logical = str(record.get("logical_path") or "")
        if logical in seen:
            raise RuntimeError(f"submission package refused: duplicate artifact index entry: {logical}")
        seen.add(logical)
        if record.get("required") is not True:
            continue
        if record.get("exists") is not True or record.get("allowed_in_submission") is not True:
            raise RuntimeError(f"submission package refused: required artifact is unavailable: {logical}")
        path = selected.get(logical)
        if path is None or not path.is_file():
            raise RuntimeError(f"submission package refused: indexed artifact is outside allowlist: {logical}")
        if record.get("sha256") != _sha(path) or record.get("size_bytes") != path.stat().st_size:
            raise RuntimeError(f"submission package refused: artifact index hash/size mismatch: {logical}")
    expected_selected = seen | {ARTIFACT_INDEX_LOGICAL_PATH}
    selected_logicals = set(selected)
    if selected_logicals != expected_selected:
        missing_from_index = sorted(selected_logicals - expected_selected)
        absent_from_package = sorted(expected_selected - selected_logicals)
        raise RuntimeError(
            "submission package refused: artifact index and package allowlist differ "
            f"(unindexed={missing_from_index}, unavailable={absent_from_package})"
        )


def package_submission_bundle(
    *,
    repo_root: Path,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    output_zip: Path,
) -> dict[str, Any]:
    readiness_path = a_output_dir / "submission_readiness.json"
    if not readiness_path.is_file():
        raise RuntimeError("submission_readiness.json is missing; run the readiness audit first")
    readiness = _read_json(readiness_path)
    if readiness.get("competition_ready") is not True:
        raise RuntimeError("submission package refused: COMPETITION_READY is not true")
    a_gate = next(
        (
            gate
            for gate in readiness.get("gates", []) or []
            if isinstance(gate, dict) and gate.get("owner") == "A"
        ),
        None,
    )
    if not a_gate or (a_gate.get("details") or {}).get("artifact_index_passed") is not True:
        raise RuntimeError("submission package refused: readiness is not bound to a passing artifact index")
    if (a_gate.get("details") or {}).get("latest_main_ci_passed") is not True:
        raise RuntimeError("submission package refused: latest-main CI PASS is not attested")

    selected_items = list(_iter_source_files(repo_root)) + list(
        _iter_submission_artifacts(
            role_b_dir=role_b_dir,
            role_d_dir=role_d_dir,
            role_e_dir=role_e_dir,
            a_output_dir=a_output_dir,
        )
    )
    logical_counts: dict[str, int] = {}
    for _, logical in selected_items:
        logical_counts[logical] = logical_counts.get(logical, 0) + 1
    duplicates = sorted(logical for logical, count in logical_counts.items() if count > 1)
    if duplicates:
        raise RuntimeError(
            "submission package refused: duplicate package logical paths: " + ", ".join(duplicates)
        )
    selected = {logical: path for path, logical in selected_items}

    _verify_artifact_index(a_output_dir / "artifact_index.json", selected)

    security_issues: list[dict[str, Any]] = []
    manifest_files: list[dict[str, Any]] = []
    for logical, path in sorted(selected.items()):
        issues = _scan_path_for_sensitive_material(path)
        if issues:
            security_issues.append({"logical_path": logical, "issues": issues})
        manifest_files.append(
            {
                "logical_path": logical,
                "size_bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    if security_issues:
        raise RuntimeError(
            "submission package refused by secret/licensed/local-path audit: "
            + json.dumps(security_issues, ensure_ascii=False)
        )

    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "competition_ready": True,
        "file_count": len(manifest_files),
        "files": manifest_files,
        "security": {
            "licensed_pdf_included": False,
            "secret_file_included": False,
            "local_absolute_path_detected": False,
        },
    }
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for logical, path in sorted(selected.items()):
            info = zipfile.ZipInfo(logical)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("submission_manifest.json")
        info.date_time = (2026, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(
            info,
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    return {
        **manifest,
        "bundle_path": str(output_zip),
        "bundle_size_bytes": output_zip.stat().st_size,
        "bundle_sha256": _sha(output_zip),
    }
