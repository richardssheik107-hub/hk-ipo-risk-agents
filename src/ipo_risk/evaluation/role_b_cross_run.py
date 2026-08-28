"""Safe, zero-network comparison of persisted Role-B LLM journals."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ipo_risk.agents.legal_models import ShareholderRightCandidate
from ipo_risk.domain.redemption_rights import RedemptionRightsRiskBuilder
from ipo_risk.extraction.shareholder_rights import ShareholderRightsExtractor
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.schemas import Evidence


_TASK = "shareholder_rights_extract"
_CALL_INPUT_FIELDS = (
    "evidence_content_hash",
    "ordered_allowed_evidence_ids",
    "prompt_hash",
    "prompt_version",
    "provider",
    "model",
    "response_model",
    "response_schema_hash",
    "task_name",
    "transport",
)


def _load_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = payload.get("identity") or {}
        if identity.get("task_name") != _TASK:
            continue
        case_id = str(identity.get("case_id") or "")
        if not case_id or case_id in records:
            raise ValueError(f"duplicate or missing shareholder-rights case identity:{case_id}")
        records[case_id] = payload
    return records


def _load_redemption_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("risk_code") == "redemption_rights"
        ]


def _load_redemption_evidence_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("risk_code") == "redemption_rights"
        ]


def _changed_fields(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field in sorted(set(left) | set(right)):
        if left.get(field) != right.get(field):
            changes.append(
                {"field": field, "run_a": left.get(field), "run_b": right.get(field)}
            )
    return changes


def _replay_builder(record: Mapping[str, Any]) -> dict[str, Any]:
    identity = record["identity"]
    candidate = ShareholderRightCandidate.model_validate(record["structured_payload"])
    evidence = [
        Evidence(
            evidence_id=evidence_id,
            document_id="sanitized-journal-replay",
            chunk_id=f"sanitized:{index}",
            page=index + 1,
            text="Sanitized in-scope shareholder-rights Evidence.",
        )
        for index, evidence_id in enumerate(identity["ordered_allowed_evidence_ids"])
    ]
    fact = ShareholderRightsExtractor(MockLLMProvider()).normalize(candidate, evidence)
    built = RedemptionRightsRiskBuilder().build(
        fact, {item.evidence_id: item for item in evidence}
    )
    return {
        "fact_status": fact.status.value,
        "fact_restoration_clause": fact.restoration_clause,
        "fact_evidence_ids": fact.evidence_ids,
        "builder_status": built.status.value,
        "builder_risk_present": built.risk_item is not None,
        "builder_evidence_ids": (
            [item.evidence_id for item in built.risk_item.evidence]
            if built.risk_item is not None
            else []
        ),
    }


def compare_cross_run(
    *,
    run_a_journal: Path,
    run_b_journal: Path,
    run_a_lifecycle: Path,
    run_b_lifecycle: Path,
    run_a_evidence_units: Path | None = None,
    run_b_evidence_units: Path | None = None,
) -> dict[str, Any]:
    """Compare two journal/lifecycle pairs without network or licensed text output."""

    run_a = _load_records(run_a_journal)
    run_b = _load_records(run_b_journal)
    if set(run_a) != set(run_b):
        raise ValueError("shareholder-rights journal case sets differ")

    comparisons: list[dict[str, Any]] = []
    identity_mismatch_count = 0
    payload_variance_count = 0
    for case_id in sorted(run_a):
        left = run_a[case_id]
        right = run_b[case_id]
        left_identity = left["identity"]
        right_identity = right["identity"]
        identity_differences = [
            field
            for field in _CALL_INPUT_FIELDS
            if left_identity.get(field) != right_identity.get(field)
        ]
        runtime_config_hash_equal = (
            left_identity.get("runtime_config_hash")
            == right_identity.get("runtime_config_hash")
        )
        payload_differences = _changed_fields(
            left.get("structured_payload") or {}, right.get("structured_payload") or {}
        )
        identity_mismatch_count += bool(identity_differences)
        payload_variance_count += bool(payload_differences)
        comparisons.append(
            {
                "case_id": case_id,
                "identity_equal": not identity_differences,
                "identity_differences": identity_differences,
                "runtime_config_hash_equal": runtime_config_hash_equal,
                "payload_equal": not payload_differences,
                "payload_differences": payload_differences,
                "run_a_response_hash": left.get("response_hash"),
                "run_b_response_hash": right.get("response_hash"),
                "run_a_replay": _replay_builder(left),
                "run_b_replay": _replay_builder(right),
            }
        )

    rows_a = _load_redemption_rows(run_a_lifecycle)
    rows_b = _load_redemption_rows(run_b_lifecycle)
    rows_a_by_case = {row["case_id"]: row for row in rows_a}
    rows_b_by_case = {row["case_id"]: row for row in rows_b}
    regressed_cases = sorted(
        case_id
        for case_id, row in rows_a_by_case.items()
        if row.get("m1_correct") == "True"
        and rows_b_by_case.get(case_id, {}).get("m1_correct") != "True"
    )
    m1_a = sum(row.get("m1_correct") == "True" for row in rows_a)
    m1_b = sum(row.get("m1_correct") == "True" for row in rows_b)
    evidence_a = sum(int(row.get("gold_evidence_count") or 0) for row in rows_a)
    evidence_b = sum(int(row.get("gold_evidence_count") or 0) for row in rows_b)

    evidence_rows_a = (
        _load_redemption_evidence_rows(run_a_evidence_units)
        if run_a_evidence_units is not None
        else []
    )
    evidence_rows_b = (
        _load_redemption_evidence_rows(run_b_evidence_units)
        if run_b_evidence_units is not None
        else []
    )
    m2_a = sum(row.get("m2_covered") == "True" for row in evidence_rows_a)
    m2_b = sum(row.get("m2_covered") == "True" for row in evidence_rows_b)
    comparisons_by_case = {item["case_id"]: item for item in comparisons}
    regression_inputs_equal = bool(regressed_cases) and all(
        comparisons_by_case[case_id]["identity_equal"] for case_id in regressed_cases
    )
    classification = (
        "LLM_RESPONSE_VARIANCE"
        if regression_inputs_equal
        and all(
            not comparisons_by_case[case_id]["payload_equal"]
            for case_id in regressed_cases
        )
        else "UNKNOWN"
    )
    return {
        "audit_version": "v046_cross_run_stability_v1",
        "network_calls": 0,
        "licensed_text_persisted": False,
        "task_name": _TASK,
        "case_count": len(comparisons),
        "official_redemption_risk_unit_count": len(rows_a),
        "identity_mismatch_count": identity_mismatch_count,
        "structured_payload_variance_case_count": payload_variance_count,
        "regressed_m1_cases": regressed_cases,
        "regression_call_inputs_equal": regression_inputs_equal,
        "classification": classification,
        "run_a": {
            "redemption_m1_correct": m1_a,
            "redemption_m1_support": len(rows_a),
            "redemption_gold_evidence_support": evidence_a,
            "redemption_m2_covered": m2_a if evidence_rows_a else None,
            "redemption_m2_support": len(evidence_rows_a) if evidence_rows_a else None,
        },
        "run_b": {
            "redemption_m1_correct": m1_b,
            "redemption_m1_support": len(rows_b),
            "redemption_gold_evidence_support": evidence_b,
            "redemption_m2_covered": m2_b if evidence_rows_b else None,
            "redemption_m2_support": len(evidence_rows_b) if evidence_rows_b else None,
        },
        "cases": comparisons,
    }
