"""Existing-Gold-only M1/M2 audit and evaluator for competition metric protocol v2.

This module is deliberately read-only with respect to Expert Annotation / Oracle Gold.
It verifies the current annotation inventory against the frozen Oracle-v2 source hash,
builds a deterministic evaluable-unit manifest, and evaluates governed analysis JSONL
without adding or modifying any manual labels.

Primary M1/M2 scope follows the competition-priority mappings that are actually
supported by pre-existing Gold. Other pre-existing risk families remain diagnostics.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from ipo_risk.evaluation.expert_annotation import validate_expert_annotation_payload
from ipo_risk.modeling.oracle_document import load_risk_gold
from ipo_risk.modeling.oracle_document_v2 import annotation_inventory
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.market import expected_market_split


METRIC_PROTOCOL_VERSION = "v045_competition_metric_protocol_v2_existing_gold_only"
COVERAGE_MANIFEST_VERSION = "v045_existing_gold_evaluable_manifest_v1"
EVALUATOR_VERSION = "v045_existing_gold_evaluator_v1"
FROZEN_ORACLE_MANIFEST = Path("reports/frozen/v04_oracle_v2_manifest.json")

COMPETITION_PRIORITY_FAMILIES = (
    "redemption_rights",
    "related_party_transaction",
    "customer_concentration",
    "supplier_concentration",
    "cash_burn_pressure",
)

_EXISTING_TO_COMPETITION = {
    "redemption_rights": "redemption_rights",
    "customer_concentration": "customer_concentration",
    "supplier_concentration": "supplier_concentration",
    "cash_runway": "cash_burn_pressure",
}
_COMPETITION_TO_EXISTING = {value: key for key, value in _EXISTING_TO_COMPETITION.items()}

_CALCULATION_RESULT_KEYS = {
    "cash_runway": "months",
    "customer_concentration": "ratio_pct",
    "supplier_concentration": "ratio_pct",
    "revenue_growth": "growth_pct",
    "continuous_loss": "loss_period_count",
}
_CASE_YEAR = re.compile(r"^ipo_(\d{4})_")
_MIN_ANCHOR_CHARS = 12


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json:{path.as_posix()}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected_object:{path.as_posix()}")
    return payload


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"\s+", "", text)


def _text_anchor_matches(gold_text: str, predicted_text: str) -> bool:
    gold = _canonical_text(gold_text)
    predicted = _canonical_text(predicted_text)
    if not gold or not predicted:
        return False
    if min(len(gold), len(predicted)) < _MIN_ANCHOR_CHARS:
        return gold == predicted
    return gold in predicted or predicted in gold


def _evidence_unit_id(case_id: str, risk_code: str, page: int, exact_text: str) -> str:
    return _sha256_text(
        json.dumps(
            [case_id, risk_code, page, _canonical_text(exact_text)],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )


def _risk_unit_id(case_id: str, risk_code: str) -> str:
    return _sha256_text(f"{case_id}|{risk_code}")


def _case_year(case_id: str) -> int:
    match = _CASE_YEAR.match(case_id)
    if not match:
        raise ValueError(f"noncanonical_case_id:{case_id}")
    return int(match.group(1))


def _source_bundle(root: Path, case_id: str, inventory_entry: dict[str, Any]):
    """Load the same effective annotation semantics used by frozen Oracle v2."""
    pass1 = root / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json"
    metadata_path = (
        root
        / "docs"
        / "annotation"
        / "gpt_expert_v1_1"
        / "case_packets"
        / case_id
        / "case_metadata.json"
    )
    if not pass1.is_file() or not metadata_path.is_file():
        raise ValueError(f"missing_existing_gold_source:{case_id}")
    if inventory_entry.get("audit_status") == "fresh":
        return load_risk_gold(root, case_id).bundle

    metadata = _read_json(metadata_path)
    payload = _read_json(pass1)
    bundle, issues = validate_expert_annotation_payload(
        payload, page_count=int(metadata["page_count"])
    )
    if bundle is None or issues:
        codes = ",".join(issue.code for issue in issues)
        raise ValueError(f"invalid_existing_gold:{case_id}:{codes}")
    return bundle


def _official_metadata(root: Path) -> dict[str, Any]:
    provider = CompetitionCSVMarketDataProvider(
        root, catalog_dir=root / "data" / "catalog"
    )
    official = {item.case_id: item for item in provider.iter_listing_metadata()}
    for case_id, item in official.items():
        if int(item.cohort_year) >= 2025:
            raise ValueError(f"blind_case_in_official_gold_universe:{case_id}")
    return official


def _required_calculation(risk: Any) -> dict[str, Any] | None:
    if not risk.calculation_required or not isinstance(risk.calculation_result, dict):
        return None
    key = _CALCULATION_RESULT_KEYS.get(risk.risk_code)
    if key is None or key not in risk.calculation_result:
        return None
    value = risk.calculation_result.get(key)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return {"key": key, "value": numeric}


def _manifest_hash(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "manifest_hash"}
    return canonical_hash(body)


def verify_coverage_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("manifest_version") != COVERAGE_MANIFEST_VERSION:
        raise ValueError("unexpected_existing_gold_manifest_version")
    if manifest.get("metric_protocol_version") != METRIC_PROTOCOL_VERSION:
        raise ValueError("unexpected_metric_protocol_version")
    if manifest.get("manifest_hash") != _manifest_hash(manifest):
        raise ValueError("existing_gold_manifest_hash_mismatch")
    governance = manifest.get("source_governance") or {}
    if governance.get("source_inventory_matches_frozen") is not True:
        raise ValueError("existing_gold_source_not_frozen")
    if manifest.get("new_manual_annotations_added") is not False:
        raise ValueError("new_manual_annotation_flag_must_be_false")
    if manifest.get("existing_gold_modified") is not False:
        raise ValueError("existing_gold_modified_flag_must_be_false")
    if manifest.get("blind_2025_outcome_accessed") is not False:
        raise ValueError("blind_2025_outcome_accessed")


def build_existing_gold_coverage(root: Path) -> dict[str, Any]:
    """Audit frozen Expert Gold and create the deterministic evaluable-unit manifest."""
    root = root.resolve()
    frozen = _read_json(root / FROZEN_ORACLE_MANIFEST)
    if frozen.get("manifest_version") != "v04_oracle_v2_freeze_manifest_v1":
        raise ValueError("unexpected_frozen_oracle_manifest")
    if frozen.get("blind_2025_y_accessed") is not False:
        raise ValueError("frozen_oracle_manifest_blind_violation")

    inventory = annotation_inventory(root)
    expected_inventory_hash = frozen.get("source_annotation_inventory_hash")
    source_matches = (
        inventory.get("inventory_hash") == expected_inventory_hash
        and inventory.get("count") == frozen.get("source_annotation_inventory_count")
        and inventory.get("valid_count") == frozen.get("valid_annotation_count")
    )
    if not source_matches:
        raise ValueError(
            "existing_gold_inventory_drift:"
            f"current={inventory.get('inventory_hash')}:"
            f"frozen={expected_inventory_hash}"
        )

    official = _official_metadata(root)
    valid_entries = [
        item for item in inventory["entries"] if item.get("status") == "valid"
    ]

    risk_units: list[dict[str, Any]] = []
    evidence_units: list[dict[str, Any]] = []
    official_source_cases = 0
    ignored_non_official: list[str] = []

    for entry in valid_entries:
        case_id = str(entry["case_id"])
        meta = official.get(case_id)
        if meta is None:
            ignored_non_official.append(case_id)
            continue
        official_source_cases += 1
        year = int(meta.cohort_year)
        if year >= 2025:
            raise ValueError(f"blind_existing_gold_case:{case_id}")
        split = expected_market_split(year).value
        bundle = _source_bundle(root, case_id, entry)
        if bundle.case_id != case_id:
            raise ValueError(f"existing_gold_identity_mismatch:{case_id}")

        source_key = canonical_hash(
            {
                "case_id": case_id,
                "base_pass_hash": entry.get("base_pass_hash"),
                "audit_hash": entry.get("audit_hash"),
                "audit_status": entry.get("audit_status"),
                "inventory_hash": inventory["inventory_hash"],
            }
        )

        evidence_by_risk: dict[str, list[Any]] = defaultdict(list)
        applicable_by_risk = {risk.risk_code: bool(risk.applicable) for risk in bundle.risks}
        for evidence in bundle.evidence:
            evidence_by_risk[evidence.risk_code].append(evidence)

        for risk in bundle.risks:
            competition_family = _EXISTING_TO_COMPETITION.get(risk.risk_code)
            existing_evidence = evidence_by_risk.get(risk.risk_code, [])
            risk_units.append(
                {
                    "risk_unit_id": _risk_unit_id(case_id, risk.risk_code),
                    "case_id": case_id,
                    "stock_code": str(meta.stock_code),
                    "cohort_year": year,
                    "split": split,
                    "source_manifest_key": source_key,
                    "source_annotation_hash": entry.get("base_pass_hash"),
                    "source_audit_hash": entry.get("audit_hash"),
                    "source_audit_status": entry.get("audit_status"),
                    "source_risk_code": risk.risk_code,
                    "competition_risk_family": competition_family,
                    "primary_scope": competition_family is not None,
                    "explicit_gold_judgment": True,
                    "applicable": bool(risk.applicable),
                    "expected_status": risk.expected_status.value,
                    "expected_level": (
                        risk.expected_level.value if risk.expected_level is not None else None
                    ),
                    "calculation_requirement": _required_calculation(risk),
                    "gold_evidence_unit_count": len(existing_evidence),
                    "evaluable_positive": bool(risk.applicable),
                }
            )

        seen_evidence: set[tuple[str, int, str]] = set()
        for evidence in bundle.evidence:
            normalized = _canonical_text(evidence.exact_text)
            dedupe_key = (evidence.risk_code, int(evidence.page), normalized)
            if dedupe_key in seen_evidence:
                continue
            seen_evidence.add(dedupe_key)
            competition_family = _EXISTING_TO_COMPETITION.get(evidence.risk_code)
            evidence_units.append(
                {
                    "evidence_unit_id": _evidence_unit_id(
                        case_id,
                        evidence.risk_code,
                        int(evidence.page),
                        evidence.exact_text,
                    ),
                    "case_id": case_id,
                    "stock_code": str(meta.stock_code),
                    "cohort_year": year,
                    "split": split,
                    "source_manifest_key": source_key,
                    "source_annotation_hash": entry.get("base_pass_hash"),
                    "source_audit_hash": entry.get("audit_hash"),
                    "source_audit_status": entry.get("audit_status"),
                    "source_risk_code": evidence.risk_code,
                    "competition_risk_family": competition_family,
                    "gold_risk_applicable": applicable_by_risk.get(evidence.risk_code, False),
                    "primary_scope": (
                        competition_family is not None
                        and applicable_by_risk.get(evidence.risk_code, False)
                    ),
                    "page": int(evidence.page),
                    "exact_text_hash": _sha256_text(normalized),
                    "exact_text": evidence.exact_text,
                    "evidence_role": evidence.evidence_role.value,
                    "requirement": evidence.requirement.value,
                    "source_authority": evidence.source_authority.value,
                }
            )

    if official_source_cases != int(frozen.get("materialized_count", -1)):
        raise ValueError(
            "official_existing_gold_case_count_drift:"
            f"current={official_source_cases}:"
            f"frozen={frozen.get('materialized_count')}"
        )

    risk_units.sort(key=lambda item: (item["case_id"], item["source_risk_code"]))
    evidence_units.sort(
        key=lambda item: (
            item["case_id"],
            item["source_risk_code"],
            item["page"],
            item["evidence_unit_id"],
        )
    )

    primary_support: dict[str, dict[str, Any]] = {}
    for family in COMPETITION_PRIORITY_FAMILIES:
        source_code = _COMPETITION_TO_EXISTING.get(family)
        units = [
            row for row in risk_units if row.get("competition_risk_family") == family
        ]
        positives = [row for row in units if row["applicable"]]
        primary_support[family] = {
            "source_risk_code": source_code,
            "explicit_judgment_count": len(units),
            "positive_count": len(positives),
            "negative_count": len(units) - len(positives),
            "status": (
                "EVALUABLE_FROM_EXISTING_GOLD"
                if positives
                else "NOT_EVALUABLE_FROM_EXISTING_GOLD"
            ),
        }

    def _evaluable_case_count(selected_split: str) -> int:
        return len(
            {
                row["case_id"]
                for row in risk_units
                if row["split"] == selected_split and row["primary_scope"]
            }
        )

    def _positive_case_count(selected_split: str) -> int:
        return len(
            {
                row["case_id"]
                for row in risk_units
                if row["split"] == selected_split
                and row["primary_scope"]
                and row["evaluable_positive"]
            }
        )

    manifest: dict[str, Any] = {
        "manifest_version": COVERAGE_MANIFEST_VERSION,
        "metric_protocol_version": METRIC_PROTOCOL_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "existing_gold_source": "frozen Expert Annotation / Oracle v2 source inventory",
        "source_governance": {
            "frozen_manifest_path": FROZEN_ORACLE_MANIFEST.as_posix(),
            "frozen_manifest_hash": frozen.get("freeze_manifest_hash"),
            "frozen_source_git_revision": frozen.get("source_git_revision"),
            "frozen_inventory_count": frozen.get("source_annotation_inventory_count"),
            "frozen_valid_annotation_count": frozen.get("valid_annotation_count"),
            "frozen_official_materialized_count": frozen.get("materialized_count"),
            "frozen_inventory_hash": expected_inventory_hash,
            "current_inventory_hash": inventory.get("inventory_hash"),
            "source_inventory_matches_frozen": True,
            "ignored_non_official_case_ids": sorted(ignored_non_official),
        },
        "official_existing_gold_case_count": official_source_cases,
        "evaluable_development_case_count": _evaluable_case_count("development"),
        "evaluable_validation_case_count": _evaluable_case_count("validation"),
        "positive_development_case_count": _positive_case_count("development"),
        "positive_validation_case_count": _positive_case_count("validation"),
        "primary_risk_support": primary_support,
        "risk_unit_count": len(risk_units),
        "positive_risk_unit_count": sum(row["evaluable_positive"] for row in risk_units),
        "primary_positive_risk_unit_count": sum(
            row["evaluable_positive"] and row["primary_scope"] for row in risk_units
        ),
        "evidence_unit_count": len(evidence_units),
        "primary_evidence_unit_count": sum(row["primary_scope"] for row in evidence_units),
        "risk_units": risk_units,
        "evidence_units": evidence_units,
        "new_manual_annotations_added": False,
        "existing_gold_modified": False,
        "blind_2025_outcome_accessed": False,
    }
    manifest["manifest_hash"] = _manifest_hash(manifest)
    verify_coverage_manifest(manifest)
    return manifest


def _result_case_id(result: dict[str, Any]) -> str:
    metadata = result.get("metadata") or {}
    return str(metadata.get("case_id") or result.get("case_id") or "")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid_results_jsonl_line:{line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"results_jsonl_line_not_object:{line_number}")
            results.append(payload)
    return results


def _provider_mode(result: dict[str, Any]) -> str:
    metadata = result.get("metadata") or {}
    modes = metadata.get("component_modes") or {}
    provider = str(modes.get("llm_provider") or "").casefold()
    status = str(modes.get("llm_status") or "").casefold()
    use_mock = (metadata.get("configuration") or {}).get("use_mock")
    if use_mock is True:
        return "mock"
    if provider in {"openai_compatible", "openai_responses"} and status == "available":
        return "real_external_llm"
    if provider == "unavailable" or status == "offline_unavailable":
        return "unavailable/offline"
    return provider or status or "not_recorded"


def _predicted_risk_index(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        rows = result.get(bucket, [])
        if not isinstance(rows, list):
            raise ValueError(f"invalid_prediction_bucket:{bucket}")
        for risk in rows:
            if not isinstance(risk, dict):
                raise ValueError(f"invalid_prediction_risk:{bucket}")
            code = str(risk.get("risk_code") or "")
            if not code:
                continue
            if code in index:
                raise ValueError(f"duplicate_predicted_risk_code:{code}")
            index[code] = {"bucket": bucket.removesuffix("_risks"), "risk": risk}
    return index


def _verification_status(predicted: dict[str, Any]) -> str:
    risk = predicted["risk"]
    raw = str(risk.get("verification_status") or predicted["bucket"]).casefold()
    return {
        "pending": "needs_review",
        "verified": "verified",
        "rejected": "rejected",
        "needs_review": "needs_review",
    }.get(raw, raw)


def _predicted_evidence(risk: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = risk.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("predicted_evidence_not_array")
    rows = [item for item in evidence if isinstance(item, dict)]
    rows.sort(
        key=lambda item: float(item.get("relevance_score") or 0.0),
        reverse=True,
    )
    return rows


def _evidence_match(gold: dict[str, Any], predicted: dict[str, Any]) -> bool:
    page = predicted.get("page")
    if not isinstance(page, int) or isinstance(page, bool):
        return False
    if page != int(gold["page"]):
        return False
    return _text_anchor_matches(str(gold["exact_text"]), str(predicted.get("text") or ""))


def _evidence_rank(
    gold: dict[str, Any], predicted_rows: Sequence[dict[str, Any]]
) -> int | None:
    for index, predicted in enumerate(predicted_rows, start=1):
        if _evidence_match(gold, predicted):
            return index
    return None


def _calculation_match(
    requirement: dict[str, Any] | None,
    risk: dict[str, Any],
) -> tuple[bool, str]:
    if requirement is None:
        return True, "NOT_REQUIRED_BY_EXISTING_GOLD"
    calculation = risk.get("calculation")
    if not isinstance(calculation, dict) or calculation.get("result") is None:
        return False, "MISSING_PREDICTED_CALCULATION"
    try:
        predicted = float(calculation.get("result"))
        gold = float(requirement["value"])
    except (TypeError, ValueError):
        return False, "NON_NUMERIC_PREDICTED_CALCULATION"
    matched = math.isclose(predicted, gold, rel_tol=1e-6, abs_tol=1e-6)
    return matched, "MATCH" if matched else "VALUE_MISMATCH"


def _risk_failure_reason(
    *,
    predicted: dict[str, Any] | None,
    status_match: bool,
    level_match: bool,
    calculation_match: bool,
    evidence_hit: bool,
) -> str:
    if predicted is None:
        return "semantic_extraction_miss"
    if predicted["bucket"] == "rejected":
        return "verifier_rejection"
    if not status_match or not level_match or not calculation_match:
        return "schema_normalization_or_riskitem_reconciliation_miss"
    if not evidence_hit:
        return "evidence_not_retained_in_final_risk"
    return ""


def _metric_status(value: float | None, threshold: float) -> bool | None:
    return None if value is None else value >= threshold


def evaluate_existing_gold(
    manifest: dict[str, Any],
    results: Sequence[dict[str, Any]],
    *,
    split: str = "development",
    open_validation: bool = False,
    case_ids: set[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate analysis results against a verified Existing-Gold coverage manifest."""
    verify_coverage_manifest(manifest)
    if split not in {"development", "validation"}:
        raise ValueError("split must be development or validation")
    if split == "validation" and not open_validation:
        raise ValueError("Validation evaluation requires explicit open_validation=True")

    full_expected_case_ids = {
        row["case_id"]
        for row in manifest["risk_units"]
        if row["split"] == split and row["primary_scope"]
    }
    if case_ids is None:
        expected_case_ids = set(full_expected_case_ids)
        evaluation_scope = "full_split"
    else:
        unknown = set(case_ids) - full_expected_case_ids
        if unknown:
            raise ValueError(f"debug_subset_contains_non_evaluable_cases:{sorted(unknown)}")
        expected_case_ids = set(case_ids)
        evaluation_scope = "debug_subset"

    results_by_case: dict[str, dict[str, Any]] = {}
    for result in results:
        case_id = _result_case_id(result)
        if case_id.startswith("ipo_2025_") or (
            _CASE_YEAR.match(case_id) and _case_year(case_id) >= 2025
        ):
            raise ValueError(f"2025 Blind result rejected:{case_id}")
        if not case_id:
            raise ValueError("governed result missing case_id")
        if case_id in results_by_case:
            raise ValueError(f"duplicate governed result:{case_id}")
        results_by_case[case_id] = result

    risk_units = [
        row
        for row in manifest["risk_units"]
        if row["split"] == split
        and row["primary_scope"]
        and row["evaluable_positive"]
        and row["case_id"] in expected_case_ids
    ]
    all_explicit_primary = [
        row
        for row in manifest["risk_units"]
        if row["split"] == split
        and row["primary_scope"]
        and row["explicit_gold_judgment"]
        and row["case_id"] in expected_case_ids
    ]
    evidence_units = [
        row
        for row in manifest["evidence_units"]
        if row["split"] == split
        and row["primary_scope"]
        and row["case_id"] in expected_case_ids
    ]
    evidence_by_case_risk: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence_units:
        evidence_by_case_risk[(row["case_id"], row["source_risk_code"])].append(row)

    risk_rows: list[dict[str, Any]] = []
    for gold in risk_units:
        result = results_by_case.get(gold["case_id"])
        predicted = None
        if result is not None:
            predicted = _predicted_risk_index(result).get(gold["source_risk_code"])

        predicted_positive = bool(predicted and predicted["bucket"] in {"verified", "pending"})
        predicted_status = _verification_status(predicted) if predicted else ""
        status_match = predicted_status == gold["expected_status"] if predicted_positive else False
        predicted_level = (
            str(predicted["risk"].get("level") or "").casefold()
            if predicted_positive
            else ""
        )
        gold_level = str(gold.get("expected_level") or "").casefold()
        level_match = (
            True if not gold_level else predicted_level == gold_level
        ) if predicted_positive else False
        calc_match, calc_reason = (
            _calculation_match(gold.get("calculation_requirement"), predicted["risk"])
            if predicted_positive
            else (False, "RISK_NOT_POSITIVE")
        )
        predicted_evidence = (
            _predicted_evidence(predicted["risk"]) if predicted_positive else []
        )
        gold_evidence = evidence_by_case_risk.get(
            (gold["case_id"], gold["source_risk_code"]), []
        )
        evidence_hit = (
            any(_evidence_rank(item, predicted_evidence) is not None for item in gold_evidence)
            if gold_evidence
            else True
        )
        correct = (
            predicted_positive
            and status_match
            and level_match
            and calc_match
            and evidence_hit
        )
        risk_rows.append(
            {
                **{
                    key: gold[key]
                    for key in (
                        "risk_unit_id",
                        "case_id",
                        "stock_code",
                        "split",
                        "source_manifest_key",
                        "source_annotation_hash",
                        "source_risk_code",
                        "competition_risk_family",
                    )
                },
                "gold_status": gold["expected_status"],
                "gold_level": gold["expected_level"],
                "predicted_present": predicted is not None,
                "predicted_positive": predicted_positive,
                "predicted_bucket": predicted["bucket"] if predicted else "",
                "predicted_status": predicted_status,
                "predicted_level": predicted_level,
                "status_match": status_match,
                "level_match": level_match,
                "calculation_match": calc_match,
                "calculation_match_reason": calc_reason,
                "evidence_required": bool(gold_evidence),
                "evidence_hit": evidence_hit,
                "correct": correct,
                "failure_reason": _risk_failure_reason(
                    predicted=predicted,
                    status_match=status_match,
                    level_match=level_match,
                    calculation_match=calc_match,
                    evidence_hit=evidence_hit,
                ),
            }
        )

    evidence_rows: list[dict[str, Any]] = []
    for gold in evidence_units:
        result = results_by_case.get(gold["case_id"])
        predicted_rows: list[dict[str, Any]] = []
        if result is not None:
            predicted = _predicted_risk_index(result).get(gold["source_risk_code"])
            if predicted and predicted["bucket"] in {"verified", "pending"}:
                predicted_rows = _predicted_evidence(predicted["risk"])
        rank = _evidence_rank(gold, predicted_rows)
        evidence_rows.append(
            {
                **{
                    key: gold[key]
                    for key in (
                        "evidence_unit_id",
                        "case_id",
                        "stock_code",
                        "split",
                        "source_manifest_key",
                        "source_annotation_hash",
                        "source_risk_code",
                        "competition_risk_family",
                        "page",
                        "exact_text_hash",
                        "evidence_role",
                        "requirement",
                        "source_authority",
                    )
                },
                "covered": rank is not None,
                "rank": rank,
                "predicted_evidence_count": len(predicted_rows),
            }
        )

    positive_total = len(risk_rows)
    correct_total = sum(bool(row["correct"]) for row in risk_rows)
    accuracy = correct_total / positive_total if positive_total else None

    predicted_positive_pairs: set[tuple[str, str]] = set()
    for case_id in {row["case_id"] for row in all_explicit_primary}:
        result = results_by_case.get(case_id)
        if result is None:
            continue
        for code, predicted in _predicted_risk_index(result).items():
            if code in _EXISTING_TO_COMPETITION and predicted["bucket"] in {"verified", "pending"}:
                predicted_positive_pairs.add((case_id, code))
    explicit_positive_pairs = {
        (row["case_id"], row["source_risk_code"])
        for row in all_explicit_primary
        if row["applicable"]
    }
    tp_existence = len(predicted_positive_pairs & explicit_positive_pairs)
    precision = tp_existence / len(predicted_positive_pairs) if predicted_positive_pairs else 0.0
    existence_recall = (
        tp_existence / len(explicit_positive_pairs) if explicit_positive_pairs else None
    )
    existence_f1 = (
        2 * precision * existence_recall / (precision + existence_recall)
        if existence_recall is not None and precision + existence_recall
        else 0.0 if existence_recall is not None else None
    )

    per_risk: dict[str, dict[str, Any]] = {}
    family_f1_values: list[float] = []
    for family in COMPETITION_PRIORITY_FAMILIES:
        source_code = _COMPETITION_TO_EXISTING.get(family)
        if source_code is None:
            per_risk[family] = {
                "status": "NOT_EVALUABLE_FROM_EXISTING_GOLD",
                "support": 0,
                "correct": 0,
                "recall": None,
                "precision": None,
                "f1": None,
            }
            continue
        positives = [row for row in risk_rows if row["competition_risk_family"] == family]
        support = len(positives)
        correct = sum(bool(row["correct"]) for row in positives)
        family_explicit = [
            row for row in all_explicit_primary if row["competition_risk_family"] == family
        ]
        family_gold_positive = {
            (row["case_id"], row["source_risk_code"])
            for row in family_explicit
            if row["applicable"]
        }
        family_pred_positive = {
            pair for pair in predicted_positive_pairs if pair[1] == source_code
        }
        family_tp = len(family_pred_positive & family_gold_positive)
        family_precision = family_tp / len(family_pred_positive) if family_pred_positive else 0.0
        family_existence_recall = (
            family_tp / len(family_gold_positive) if family_gold_positive else None
        )
        family_f1 = (
            2 * family_precision * family_existence_recall
            / (family_precision + family_existence_recall)
            if family_existence_recall is not None and family_precision + family_existence_recall
            else 0.0 if family_existence_recall is not None else None
        )
        if family_f1 is not None:
            family_f1_values.append(family_f1)
        per_risk[family] = {
            "status": (
                "EVALUABLE_FROM_EXISTING_GOLD"
                if support
                else "NOT_EVALUABLE_FROM_EXISTING_GOLD"
            ),
            "support": support,
            "correct": correct,
            "official_aligned_accuracy": correct / support if support else None,
            "existence_precision": family_precision,
            "existence_recall": family_existence_recall,
            "existence_f1": family_f1,
        }

    macro_f1 = sum(family_f1_values) / len(family_f1_values) if family_f1_values else None

    evidence_total = len(evidence_rows)
    evidence_covered = sum(bool(row["covered"]) for row in evidence_rows)
    coverage_recall = evidence_covered / evidence_total if evidence_total else None
    recall_at: dict[str, float | None] = {}
    for k in (1, 3, 5, 10, 20):
        hits = sum(
            row["rank"] is not None and int(row["rank"]) <= k
            for row in evidence_rows
        )
        recall_at[f"recall_at_{k}"] = hits / evidence_total if evidence_total else None

    # Completeness is a case-level runtime fact, not a positive-Gold fact.
    # Some governed Development cases intentionally contain only explicit
    # negative/unjudged primary units and therefore emit no ``risk_rows``.
    # Counting through the scored positive rows would silently drop those
    # negative-control cases from ``evaluated_case_count`` and
    # ``real_llm_cases`` even when their governed result is present.
    evaluated_case_ids = expected_case_ids & set(results_by_case)
    missing_case_ids = sorted(expected_case_ids - set(results_by_case))
    real_llm_cases = sum(
        _provider_mode(results_by_case[case_id]) == "real_external_llm"
        for case_id in evaluated_case_ids
    )

    failures = Counter(row["failure_reason"] for row in risk_rows if row["failure_reason"])
    summary = {
        "metric_protocol_version": METRIC_PROTOCOL_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "coverage_manifest_version": manifest["manifest_version"],
        "existing_gold_source": manifest["existing_gold_source"],
        "existing_gold_source_hash_or_manifest": manifest["manifest_hash"],
        "split": split,
        "evaluation_scope": evaluation_scope,
        "evaluable_development_case_count": manifest["evaluable_development_case_count"],
        "evaluable_validation_case_count": manifest["evaluable_validation_case_count"],
        "expected_case_count_for_split": len(expected_case_ids),
        "evaluated_case_count": len(evaluated_case_ids),
        "missing_case_ids": missing_case_ids,
        "real_llm_cases": real_llm_cases,
        "external_llm_called": real_llm_cases > 0,
        "risk_extraction": {
            "evaluable_positive_count": positive_total,
            "correct_positive_count": correct_total,
            "official_aligned_accuracy": accuracy,
            "official_threshold": 0.80,
            "official_threshold_met": _metric_status(accuracy, 0.80),
            "project_target": 0.85,
            "project_target_met": _metric_status(accuracy, 0.85),
            "existence_precision": precision,
            "existence_recall": existence_recall,
            "existence_f1": existence_f1,
            "precision_status": "AVAILABLE_FROM_EXPLICIT_EXISTING_GOLD_JUDGMENTS",
            "macro_f1": macro_f1,
            "macro_f1_status": "AVAILABLE_FOR_EXISTING_GOLD_MAPPED_FAMILIES",
            "per_risk": per_risk,
        },
        "evidence_coverage": {
            "evaluable_existing_gold_count": evidence_total,
            "covered_existing_gold_count": evidence_covered,
            "coverage_recall": coverage_recall,
            "official_threshold": 0.85,
            "official_threshold_met": _metric_status(coverage_recall, 0.85),
            "project_target": 0.88,
            "project_target_met": _metric_status(coverage_recall, 0.88),
        },
        "retrieval_diagnostics": {
            **recall_at,
            "candidate_retrieval_recall_at_20": "NOT_AVAILABLE_WITHOUT_CANDIDATE_TRACE",
            "reranked_recall_at_10": "NOT_AVAILABLE_WITHOUT_RERANK_TRACE",
        },
        "failure_taxonomy": dict(sorted(failures.items())),
        "measurement_gate": {
            "all_expected_cases_present": not missing_case_ids and bool(expected_case_ids),
            "real_llm_measurement_present": real_llm_cases > 0,
            "full_split_scope": evaluation_scope == "full_split",
            "competition_pass_claim_eligible": (
                evaluation_scope == "full_split"
                and not missing_case_ids
                and bool(expected_case_ids)
                and real_llm_cases > 0
            ),
            "official_m1_pass": _metric_status(accuracy, 0.80),
            "official_m2_pass": _metric_status(coverage_recall, 0.85),
        },
        "new_manual_annotations_added": False,
        "existing_gold_modified": False,
        "blind_2025_outcome_accessed": False,
    }
    return summary, risk_rows, evidence_rows


def write_existing_gold_coverage(output_dir: Path, manifest: dict[str, Any]) -> None:
    verify_coverage_manifest(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "existing_gold_evaluable_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    risk_fields = [
        "risk_unit_id",
        "case_id",
        "stock_code",
        "cohort_year",
        "split",
        "source_manifest_key",
        "source_annotation_hash",
        "source_audit_hash",
        "source_audit_status",
        "source_risk_code",
        "competition_risk_family",
        "primary_scope",
        "explicit_gold_judgment",
        "applicable",
        "expected_status",
        "expected_level",
        "gold_evidence_unit_count",
        "evaluable_positive",
    ]
    with (output_dir / "existing_gold_risk_units.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=risk_fields)
        writer.writeheader()
        for row in manifest["risk_units"]:
            writer.writerow({key: row.get(key) for key in risk_fields})

    evidence_fields = [
        "evidence_unit_id",
        "case_id",
        "stock_code",
        "cohort_year",
        "split",
        "source_manifest_key",
        "source_annotation_hash",
        "source_audit_hash",
        "source_audit_status",
        "source_risk_code",
        "competition_risk_family",
        "gold_risk_applicable",
        "primary_scope",
        "page",
        "exact_text_hash",
        "evidence_role",
        "requirement",
        "source_authority",
    ]
    with (output_dir / "existing_gold_evidence_units.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=evidence_fields)
        writer.writeheader()
        for row in manifest["evidence_units"]:
            writer.writerow({key: row.get(key) for key in evidence_fields})

    summary = {
        key: value for key, value in manifest.items() if key not in {"risk_units", "evidence_units"}
    }
    (output_dir / "existing_gold_coverage_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_existing_gold_evaluation(
    output_dir: Path,
    summary: dict[str, Any],
    risk_rows: Sequence[dict[str, Any]],
    evidence_rows: Sequence[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "document_benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    risk_fields = [
        "risk_unit_id",
        "case_id",
        "stock_code",
        "split",
        "source_manifest_key",
        "source_annotation_hash",
        "source_risk_code",
        "competition_risk_family",
        "gold_status",
        "gold_level",
        "predicted_present",
        "predicted_positive",
        "predicted_bucket",
        "predicted_status",
        "predicted_level",
        "status_match",
        "level_match",
        "calculation_match",
        "calculation_match_reason",
        "evidence_required",
        "evidence_hit",
        "correct",
        "failure_reason",
    ]
    with (output_dir / "risk_benchmark.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=risk_fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in risk_fields} for row in risk_rows)

    evidence_fields = [
        "evidence_unit_id",
        "case_id",
        "stock_code",
        "split",
        "source_manifest_key",
        "source_annotation_hash",
        "source_risk_code",
        "competition_risk_family",
        "page",
        "exact_text_hash",
        "evidence_role",
        "requirement",
        "source_authority",
        "covered",
        "rank",
        "predicted_evidence_count",
    ]
    with (output_dir / "evidence_benchmark.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=evidence_fields)
        writer.writeheader()
        writer.writerows(
            {key: row.get(key) for key in evidence_fields} for row in evidence_rows
        )


__all__ = [
    "METRIC_PROTOCOL_VERSION",
    "COVERAGE_MANIFEST_VERSION",
    "EVALUATOR_VERSION",
    "COMPETITION_PRIORITY_FAMILIES",
    "build_existing_gold_coverage",
    "evaluate_existing_gold",
    "verify_coverage_manifest",
    "write_existing_gold_coverage",
    "write_existing_gold_evaluation",
    "_load_jsonl",
]
