"""Read-only Role-B waterfall and monotonicity artifact construction.

This module intentionally does not run retrieval, call an LLM, or reinterpret
Existing Gold.  It combines the frozen coverage manifest, the rows already
produced by the Existing-Gold evaluator, and an optional post-run pipeline
trace.  Missing trace data remains explicitly unavailable; it is never counted
as a miss.

The returned objects are safe, compact report payloads.  Only identifiers,
hashes, enum-like values, pages, booleans, and counts are retained.  Prospectus
text, Gold text, prompts, and raw model responses are never copied into the
artifacts.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


REPORT_VERSION = "v046_role_b_waterfall_v1"
TRACE_VERSION = "v046_role_b_pipeline_trace_v1"
NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_PROVEN = "NOT_PROVEN"

_CASE_YEAR = re.compile(r"^ipo_(\d{4})_")
_TOP_K = (1, 3, 5, 10, 20)
_TRACE_FIELDS = (
    "deterministic_candidate_present",
    "llm_request_success",
    "llm_structured_valid",
    "llm_scope_valid",
    "llm_candidate_present",
    "llm_abstained",
    "candidate_conflict",
    "normalization_success",
    "reconciliation_success",
    "candidate_after_reconciliation",
    "verifier_outcome",
)
_COMMON_IDENTITY_KEYS = (
    "code_fingerprint",
    "subset_hash",
    "gold_manifest_hash",
    "evaluator_version",
)
_LLM_IDENTITY_KEYS = (
    "provider",
    "model",
    "transport",
    "prompt_set_hash",
    "schema_set_hash",
    "llm_journal_hash",
)


class RoleBWaterfallError(ValueError):
    """Raised when a diagnostic input violates the frozen Development scope."""


def read_evaluator_csv(path: Path) -> list[dict[str, str]]:
    """Read one evaluator CSV without changing or re-scoring its contents."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no", ""}:
            return False
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    raise RoleBWaterfallError(f"expected_boolean:{value!r}")


def _optional_positive_int(value: Any, *, field: str) -> int | None:
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        raise RoleBWaterfallError(f"invalid_{field}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RoleBWaterfallError(f"invalid_{field}") from exc
    if parsed <= 0:
        raise RoleBWaterfallError(f"invalid_{field}")
    return parsed


def _nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool):
        raise RoleBWaterfallError(f"invalid_{field}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise RoleBWaterfallError(f"invalid_{field}") from exc
    if parsed < 0:
        raise RoleBWaterfallError(f"invalid_{field}")
    return parsed


def _development_case(case_id: str, split: str, *, source: str) -> None:
    if split != "development":
        raise RoleBWaterfallError(f"non_development_{source}:{case_id or 'missing'}")
    match = _CASE_YEAR.match(case_id)
    if not match:
        raise RoleBWaterfallError(f"invalid_case_id_{source}:{case_id or 'missing'}")
    if int(match.group(1)) >= 2024:
        raise RoleBWaterfallError(f"validation_or_blind_{source}:{case_id}")


def _manifest_indexes(
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    risk_rows = manifest.get("risk_units")
    evidence_rows = manifest.get("evidence_units")
    if not isinstance(risk_rows, list) or not isinstance(evidence_rows, list):
        raise RoleBWaterfallError("coverage_manifest_units_missing")
    risk_index = {
        str(row.get("risk_unit_id") or ""): row
        for row in risk_rows
        if isinstance(row, Mapping) and row.get("risk_unit_id")
    }
    evidence_index = {
        str(row.get("evidence_unit_id") or ""): row
        for row in evidence_rows
        if isinstance(row, Mapping) and row.get("evidence_unit_id")
    }
    if len(risk_index) != sum(
        isinstance(row, Mapping) and bool(row.get("risk_unit_id")) for row in risk_rows
    ):
        raise RoleBWaterfallError("duplicate_manifest_risk_unit_id")
    if len(evidence_index) != sum(
        isinstance(row, Mapping) and bool(row.get("evidence_unit_id"))
        for row in evidence_rows
    ):
        raise RoleBWaterfallError("duplicate_manifest_evidence_unit_id")
    return risk_index, evidence_index


def _validated_evaluator_rows(
    rows: Sequence[Mapping[str, Any]],
    manifest_index: Mapping[str, Mapping[str, Any]],
    *,
    unit_key: str,
) -> list[Mapping[str, Any]]:
    validated: list[Mapping[str, Any]] = []
    observed: set[str] = set()
    for row in rows:
        unit_id = str(row.get(unit_key) or "")
        if not unit_id or unit_id in observed:
            raise RoleBWaterfallError(f"invalid_or_duplicate_{unit_key}:{unit_id or 'missing'}")
        observed.add(unit_id)
        source = manifest_index.get(unit_id)
        if source is None:
            raise RoleBWaterfallError(f"unknown_{unit_key}:{unit_id}")
        case_id = str(row.get("case_id") or "")
        split = str(row.get("split") or "")
        _development_case(case_id, split, source=unit_key)
        if case_id != str(source.get("case_id") or "") or split != str(source.get("split") or ""):
            raise RoleBWaterfallError(f"manifest_identity_mismatch:{unit_id}")
        validated.append(row)
    return validated


def _trace_index(
    trace: Sequence[Mapping[str, Any]] | None,
    *,
    kind: str,
    unit_key: str,
) -> dict[str, Mapping[str, Any]]:
    if trace is None:
        return {}
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in trace:
        row_kind = str(row.get("trace_kind") or "")
        if row_kind and row_kind != kind:
            continue
        if not row_kind and unit_key not in row:
            continue
        if row.get("trace_version") not in {None, TRACE_VERSION}:
            raise RoleBWaterfallError("unexpected_pipeline_trace_version")
        unit_id = str(row.get(unit_key) or "")
        if not unit_id or unit_id in indexed:
            raise RoleBWaterfallError(f"invalid_or_duplicate_trace_{unit_key}:{unit_id or 'missing'}")
        case_id = str(row.get("case_id") or "")
        split = str(row.get("split") or "")
        _development_case(case_id, split, source="pipeline_trace")
        if row.get("blind_2025_outcome_accessed") not in {None, False}:
            raise RoleBWaterfallError("pipeline_trace_blind_access_flagged")
        indexed[unit_id] = row
    return indexed


def _trace_status(observed: int, expected: int, *, missing_reason: str) -> str:
    if observed == 0:
        return missing_reason
    if observed < expected:
        return "PARTIAL_TRACE"
    return "AVAILABLE"


def _monotone_counts(stages: Sequence[Mapping[str, Any]]) -> None:
    values = [item.get("count") for item in stages]
    numeric = [item for item in values if isinstance(item, int)]
    if any(left < right for left, right in zip(numeric, numeric[1:])):
        raise RoleBWaterfallError("waterfall_stage_counts_not_monotone")


def build_retrieval_waterfall(
    coverage_manifest: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
    pipeline_trace: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a Gold-unit retrieval waterfall without re-running retrieval.

    Candidate ranks are accepted only from an explicit post-run trace.  When
    that trace is absent, candidate/ranking fields are ``NOT_AVAILABLE`` while
    final evaluator coverage remains available.
    """

    _, manifest_evidence = _manifest_indexes(coverage_manifest)
    rows = _validated_evaluator_rows(
        evidence_rows, manifest_evidence, unit_key="evidence_unit_id"
    )
    traces = _trace_index(
        pipeline_trace, kind="retrieval", unit_key="evidence_unit_id"
    )
    unknown = set(traces) - {str(row["evidence_unit_id"]) for row in rows}
    if unknown:
        raise RoleBWaterfallError(f"trace_contains_unknown_evidence_units:{sorted(unknown)}")

    units: list[dict[str, Any]] = []
    candidate_top20_count = 0
    consumed_count = 0
    consumed_observed = 0
    final_covered_count = 0
    anomalies: list[dict[str, str]] = []

    for row in rows:
        unit_id = str(row["evidence_unit_id"])
        trace_row = traces.get(unit_id)
        final_covered = _bool(row.get("covered"))
        final_rank = _optional_positive_int(row.get("rank"), field="final_rank")
        final_covered_count += int(final_covered)
        unit: dict[str, Any] = {
            "case_id": str(row.get("case_id") or ""),
            "risk_code": str(row.get("source_risk_code") or ""),
            "gold_unit_id": unit_id,
            "page": _nonnegative_int(row.get("page"), field="page"),
            "exact_text_hash": str(row.get("exact_text_hash") or ""),
            "final_evidence_covered": final_covered,
            "final_evidence_rank": final_rank,
        }
        if trace_row is None:
            unit.update(
                {
                    "retrieval_query_family": NOT_AVAILABLE,
                    "candidate_count": NOT_AVAILABLE,
                    "first_gold_rank": NOT_AVAILABLE,
                    **{f"gold_evidence_in_top{k}": NOT_AVAILABLE for k in _TOP_K},
                    "agent_consumed": NOT_AVAILABLE,
                    "candidate_generation_miss": NOT_AVAILABLE,
                    "ranking_miss": NOT_AVAILABLE,
                }
            )
            units.append(unit)
            continue

        if str(trace_row.get("case_id") or "") != unit["case_id"]:
            raise RoleBWaterfallError(f"trace_case_mismatch:{unit_id}")
        first_rank = _optional_positive_int(
            trace_row.get("first_gold_rank"), field="first_gold_rank"
        )
        candidate_count = _nonnegative_int(
            trace_row.get("candidate_count"), field="candidate_count"
        )
        if first_rank is not None and first_rank > candidate_count:
            raise RoleBWaterfallError(f"first_gold_rank_exceeds_candidate_count:{unit_id}")
        candidate_top20 = first_rank is not None and first_rank <= 20
        candidate_top20_count += int(candidate_top20)
        consumed_value = trace_row.get("agent_consumed", NOT_AVAILABLE)
        if consumed_value == NOT_AVAILABLE or consumed_value is None:
            consumed: bool | str = NOT_AVAILABLE
            ranking_miss: bool | str = NOT_AVAILABLE
        else:
            consumed = _bool(consumed_value)
            consumed_observed += 1
            consumed_count += int(candidate_top20 and consumed)
            ranking_miss = bool(candidate_top20 and not consumed)
            if final_covered and not consumed:
                anomalies.append(
                    {"gold_unit_id": unit_id, "reason": "final_covered_without_consumed_trace"}
                )
        query_family = trace_row.get("retrieval_query_family", NOT_AVAILABLE)
        if isinstance(query_family, list):
            query_family = sorted({str(item) for item in query_family if str(item)})
        elif query_family != NOT_AVAILABLE and not isinstance(query_family, str):
            raise RoleBWaterfallError(f"invalid_retrieval_query_family:{unit_id}")
        unit.update(
            {
                "retrieval_query_family": query_family,
                "candidate_count": candidate_count,
                "first_gold_rank": first_rank,
                **{
                    f"gold_evidence_in_top{k}": first_rank is not None and first_rank <= k
                    for k in _TOP_K
                },
                "agent_consumed": consumed,
                "candidate_generation_miss": not candidate_top20,
                "ranking_miss": ranking_miss,
            }
        )
        units.append(unit)

    observed = len(traces)
    trace_status = _trace_status(
        observed,
        len(rows),
        missing_reason="NOT_AVAILABLE_WITHOUT_CANDIDATE_TRACE",
    )
    if observed == len(rows):
        candidate_stage: int | str = candidate_top20_count
    else:
        candidate_stage = NOT_AVAILABLE
    if observed == len(rows) and consumed_observed == len(rows):
        consumed_stage: int | str = consumed_count
    else:
        consumed_stage = NOT_AVAILABLE

    stages = [
        {"stage": "existing_gold_evidence_units", "count": len(rows)},
        {"stage": "candidate_top20_hit", "count": candidate_stage},
        {"stage": "agent_consumed_hit", "count": consumed_stage},
        {
            "stage": "final_evidence_covered",
            "count": (
                final_covered_count
                if isinstance(consumed_stage, int) and final_covered_count <= consumed_stage
                else NOT_AVAILABLE
            ),
        },
    ]
    _monotone_counts(stages)
    return {
        "report_version": REPORT_VERSION,
        "trace_status": trace_status,
        "split": "development",
        "unit_count": len(rows),
        "observed_candidate_trace_count": observed,
        "observed_consumed_trace_count": consumed_observed,
        "candidate_hit_at_20_count_observed": candidate_top20_count,
        "candidate_recall_at_20_observed_only": (
            candidate_top20_count / observed if observed else NOT_AVAILABLE
        ),
        "final_covered_count": final_covered_count,
        "waterfall": stages,
        "trace_anomalies": anomalies,
        "units": units,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _final_first_failure(row: Mapping[str, Any]) -> str | None:
    if not _bool(row.get("predicted_present")):
        return "final_risk_absent"
    if not _bool(row.get("predicted_positive")):
        return "verifier_or_final_bucket"
    if not _bool(row.get("status_match")):
        return "status_normalization"
    if not _bool(row.get("level_match")):
        return "level_normalization"
    if not _bool(row.get("calculation_match")):
        return "calculation"
    if not _bool(row.get("evidence_hit")):
        return "evidence_binding"
    return None


def build_risk_pipeline_waterfall(
    coverage_manifest: Mapping[str, Any],
    risk_rows: Sequence[Mapping[str, Any]],
    pipeline_trace: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a cumulative final-only risk waterfall, enriched by optional trace."""

    manifest_risks, _ = _manifest_indexes(coverage_manifest)
    rows = _validated_evaluator_rows(risk_rows, manifest_risks, unit_key="risk_unit_id")
    traces = _trace_index(pipeline_trace, kind="risk_pipeline", unit_key="risk_unit_id")
    unknown = set(traces) - {str(row["risk_unit_id"]) for row in rows}
    if unknown:
        raise RoleBWaterfallError(f"trace_contains_unknown_risk_units:{sorted(unknown)}")

    stage_names = (
        "existing_gold_positive_units",
        "final_risk_present",
        "final_risk_positive",
        "status_match",
        "level_match",
        "calculation_match",
        "final_evidence_match",
        "risk_match",
    )
    counts = Counter({stage_names[0]: len(rows)})
    units: list[dict[str, Any]] = []
    for row in rows:
        present = _bool(row.get("predicted_present"))
        positive = present and _bool(row.get("predicted_positive"))
        status = positive and _bool(row.get("status_match"))
        level = status and _bool(row.get("level_match"))
        calculation = level and _bool(row.get("calculation_match"))
        evidence = calculation and _bool(row.get("evidence_hit"))
        correct = evidence and _bool(row.get("correct"))
        for name, value in zip(
            stage_names[1:],
            (present, positive, status, level, calculation, evidence, correct),
        ):
            counts[name] += int(value)

        unit_id = str(row["risk_unit_id"])
        trace_row = traces.get(unit_id)
        trace_fields: dict[str, Any] = {}
        for field in _TRACE_FIELDS:
            if trace_row is None or field not in trace_row:
                trace_fields[field] = NOT_AVAILABLE
            elif field == "verifier_outcome":
                value = trace_row[field]
                if not isinstance(value, str) or not value:
                    raise RoleBWaterfallError(f"invalid_verifier_outcome:{unit_id}")
                trace_fields[field] = value
            else:
                trace_fields[field] = _bool(trace_row[field])
        unit: dict[str, Any] = {
            "case_id": str(row.get("case_id") or ""),
            "risk_code": str(row.get("source_risk_code") or ""),
            "gold_unit_id": unit_id,
            **trace_fields,
            "final_risk_present": present,
            "final_risk_positive": positive,
            "final_bucket": str(row.get("predicted_bucket") or ""),
            "final_evidence_ids": (
                sorted({str(item) for item in trace_row.get("final_evidence_ids", [])})
                if trace_row is not None
                and isinstance(trace_row.get("final_evidence_ids", []), list)
                else NOT_AVAILABLE
            ),
            "risk_match": correct,
            "evidence_match": _bool(row.get("evidence_hit")),
            "first_failure_stage": (
                trace_row.get("first_failure_stage")
                if trace_row is not None and trace_row.get("first_failure_stage")
                else _final_first_failure(row)
            ),
        }
        if trace_row is not None and str(trace_row.get("case_id") or "") != unit["case_id"]:
            raise RoleBWaterfallError(f"trace_case_mismatch:{unit_id}")
        units.append(unit)

    stages = [{"stage": name, "count": int(counts[name])} for name in stage_names]
    _monotone_counts(stages)
    return {
        "report_version": REPORT_VERSION,
        "trace_status": _trace_status(
            len(traces),
            len(rows),
            missing_reason="FINAL_ONLY_WITHOUT_PIPELINE_TRACE",
        ),
        "split": "development",
        "unit_count": len(rows),
        "waterfall": stages,
        "units": units,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _metric(summary: Mapping[str, Any], name: str) -> float | None:
    direct = summary.get(name)
    if isinstance(direct, (int, float)) and not isinstance(direct, bool):
        return float(direct)
    if name == "m1":
        nested = (summary.get("risk_extraction") or {}).get("official_aligned_accuracy")
    else:
        nested = (summary.get("evidence_coverage") or {}).get("coverage_recall")
    return float(nested) if isinstance(nested, (int, float)) and not isinstance(nested, bool) else None


def _per_risk(summary: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = summary.get("per_risk")
    if isinstance(direct, Mapping):
        return direct
    nested = (summary.get("risk_extraction") or {}).get("per_risk")
    return nested if isinstance(nested, Mapping) else {}


def _mode_unit_indexes(
    mode: Mapping[str, Any],
    manifest_risks: Mapping[str, Mapping[str, Any]],
    manifest_evidence: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    risk_rows = mode.get("risk_rows")
    evidence_rows = mode.get("evidence_rows")
    if not isinstance(risk_rows, list) or not isinstance(evidence_rows, list):
        raise RoleBWaterfallError("mode_evaluator_rows_missing")
    validated_risks = _validated_evaluator_rows(
        risk_rows, manifest_risks, unit_key="risk_unit_id"
    )
    validated_evidence = _validated_evaluator_rows(
        evidence_rows, manifest_evidence, unit_key="evidence_unit_id"
    )
    risk_index = {str(row["risk_unit_id"]): row for row in validated_risks}
    evidence_index = {
        str(row["evidence_unit_id"]): row for row in validated_evidence
    }
    return risk_index, evidence_index


def _not_proven(reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "status": NOT_PROVEN,
        "satisfied": NOT_PROVEN,
        "reasons": list(dict.fromkeys(reasons)),
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def build_monotonicity_report(
    mode_results: Mapping[str, Mapping[str, Any]],
    coverage_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare offline/shadow/gated rows only when identities are provably aligned."""

    required_modes = ("offline", "shadow", "gated")
    missing_modes = [mode for mode in required_modes if mode not in mode_results]
    if missing_modes:
        return _not_proven([f"missing_mode:{mode}" for mode in missing_modes])
    if coverage_manifest is None:
        return _not_proven(["coverage_manifest_missing"])
    try:
        manifest_risks, manifest_evidence = _manifest_indexes(coverage_manifest)
    except RoleBWaterfallError as exc:
        return _not_proven([str(exc)])

    reasons: list[str] = []
    identities: dict[str, Mapping[str, Any]] = {}
    for mode in required_modes:
        identity = mode_results[mode].get("identity")
        if not isinstance(identity, Mapping):
            reasons.append(f"identity_missing:{mode}")
            identity = {}
        identities[mode] = identity
        if identity.get("split") != "development":
            reasons.append(f"non_development_identity:{mode}")
        if identity.get("validation_opened") not in {None, False}:
            reasons.append(f"validation_opened:{mode}")
        if identity.get("blind_2025_outcome_accessed") not in {None, False}:
            reasons.append(f"blind_accessed:{mode}")
        for key in _COMMON_IDENTITY_KEYS:
            if not identity.get(key):
                reasons.append(f"identity_key_missing:{mode}:{key}")

    reference = identities["offline"]
    manifest_hash = str(coverage_manifest.get("manifest_hash") or "")
    if not manifest_hash:
        reasons.append("coverage_manifest_hash_missing")
    elif reference.get("gold_manifest_hash") != manifest_hash:
        reasons.append("coverage_manifest_hash_mismatch")
    for mode in ("shadow", "gated"):
        for key in _COMMON_IDENTITY_KEYS:
            if reference.get(key) and identities[mode].get(key) != reference.get(key):
                reasons.append(f"identity_mismatch:{mode}:{key}")
    for key in _LLM_IDENTITY_KEYS:
        shadow_value = identities["shadow"].get(key)
        gated_value = identities["gated"].get(key)
        if not shadow_value or not gated_value:
            reasons.append(f"llm_identity_key_missing:{key}")
        elif shadow_value != gated_value:
            reasons.append(f"llm_identity_mismatch:{key}")

    canonical_hashes: dict[str, Mapping[str, Any]] = {}
    for mode in required_modes:
        hashes = mode_results[mode].get("canonical_result_hashes")
        if not isinstance(hashes, Mapping) or not hashes:
            reasons.append(f"canonical_result_hashes_missing:{mode}")
            hashes = {}
        canonical_hashes[mode] = hashes
    if reasons:
        return _not_proven(reasons)

    shadow_matches_offline = canonical_hashes["shadow"] == canonical_hashes["offline"]

    try:
        indexes = {
            mode: _mode_unit_indexes(
                mode_results[mode], manifest_risks, manifest_evidence
            )
            for mode in required_modes
        }
    except RoleBWaterfallError as exc:
        return _not_proven([str(exc)])
    offline_risks, offline_evidence = indexes["offline"]
    gated_risks, gated_evidence = indexes["gated"]
    for mode in ("shadow", "gated"):
        if set(indexes[mode][0]) != set(offline_risks):
            reasons.append(f"risk_unit_identity_mismatch:{mode}")
        if set(indexes[mode][1]) != set(offline_evidence):
            reasons.append(f"evidence_unit_identity_mismatch:{mode}")
    if reasons:
        return _not_proven(reasons)

    summaries = {
        mode: mode_results[mode].get("summary")
        for mode in required_modes
    }
    if any(not isinstance(summary, Mapping) for summary in summaries.values()):
        return _not_proven(["mode_summary_missing"])
    metrics = {
        mode: {"m1": _metric(summaries[mode], "m1"), "m2": _metric(summaries[mode], "m2")}
        for mode in required_modes
    }
    if any(value is None for pair in metrics.values() for value in pair.values()):
        return _not_proven(["mode_metric_missing"])

    removed_risk_units = sorted(
        unit_id
        for unit_id, offline in offline_risks.items()
        if _bool(offline.get("predicted_present"))
        and not _bool(gated_risks[unit_id].get("predicted_present"))
    )
    removed_evidence_units = sorted(
        unit_id
        for unit_id, offline in offline_evidence.items()
        if _bool(offline.get("covered"))
        and not _bool(gated_evidence[unit_id].get("covered"))
    )
    gained_valid = sorted(
        unit_id
        for unit_id, offline in offline_risks.items()
        if not _bool(offline.get("correct")) and _bool(gated_risks[unit_id].get("correct"))
    )
    new_invalid = sorted(
        unit_id
        for unit_id, offline in offline_risks.items()
        if not _bool(offline.get("predicted_present"))
        and _bool(gated_risks[unit_id].get("predicted_present"))
        and not _bool(gated_risks[unit_id].get("correct"))
    )
    regressions = sorted(
        unit_id
        for unit_id, offline in offline_risks.items()
        if _bool(offline.get("correct")) and not _bool(gated_risks[unit_id].get("correct"))
    )

    per_risk: dict[str, dict[str, float | None]] = {}
    families = sorted(
        set(_per_risk(summaries["offline"]))
        | set(_per_risk(summaries["shadow"]))
        | set(_per_risk(summaries["gated"]))
    )
    for family in families:
        values: dict[str, float | None] = {}
        for mode in required_modes:
            raw = (_per_risk(summaries[mode]).get(family) or {}).get(
                "official_aligned_accuracy"
            )
            values[mode] = (
                float(raw)
                if isinstance(raw, (int, float)) and not isinstance(raw, bool)
                else None
            )
        values["gated_minus_offline"] = (
            values["gated"] - values["offline"]
            if values["gated"] is not None and values["offline"] is not None
            else None
        )
        per_risk[family] = values

    gated_m1_delta = metrics["gated"]["m1"] - metrics["offline"]["m1"]
    gated_m2_delta = metrics["gated"]["m2"] - metrics["offline"]["m2"]
    satisfied = (
        shadow_matches_offline
        and gated_m1_delta >= 0
        and gated_m2_delta >= 0
        and not removed_risk_units
        and not removed_evidence_units
        and not regressions
    )
    return {
        "report_version": REPORT_VERSION,
        "status": "PROVEN",
        "satisfied": satisfied,
        "identity": {key: reference[key] for key in _COMMON_IDENTITY_KEYS},
        "llm_journal_hash": identities["gated"]["llm_journal_hash"],
        "modes": metrics,
        "offline_vs_shadow": {
            "canonical_results_equal": shadow_matches_offline,
            "m1_delta": metrics["shadow"]["m1"] - metrics["offline"]["m1"],
            "m2_delta": metrics["shadow"]["m2"] - metrics["offline"]["m2"],
        },
        "offline_vs_gated": {
            "m1_delta": gated_m1_delta,
            "m2_delta": gated_m2_delta,
            "per_risk": per_risk,
        },
        "shadow_vs_gated": {
            "m1_delta": metrics["gated"]["m1"] - metrics["shadow"]["m1"],
            "m2_delta": metrics["gated"]["m2"] - metrics["shadow"]["m2"],
        },
        "deterministic_risks_removed_by_llm_count": len(removed_risk_units),
        "deterministic_risk_unit_ids_removed": removed_risk_units,
        "deterministic_evidence_removed_by_llm_count": len(removed_evidence_units),
        "deterministic_evidence_unit_ids_removed": removed_evidence_units,
        "new_valid_risks_added_by_llm_count": len(gained_valid),
        "new_valid_risk_unit_ids": gained_valid,
        "new_invalid_risks_added_by_llm_count": len(new_invalid),
        "new_invalid_risk_unit_ids": new_invalid,
        "per_risk_regressions": regressions,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def build_role_b_waterfall_artifacts(
    *,
    coverage_manifest: Mapping[str, Any],
    risk_rows: Sequence[Mapping[str, Any]],
    evidence_rows: Sequence[Mapping[str, Any]],
    pipeline_trace: Sequence[Mapping[str, Any]] | None = None,
    mode_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build all three in-memory artifact payloads without writing any file."""

    return {
        "retrieval_waterfall": build_retrieval_waterfall(
            coverage_manifest, evidence_rows, pipeline_trace
        ),
        "risk_pipeline_waterfall": build_risk_pipeline_waterfall(
            coverage_manifest, risk_rows, pipeline_trace
        ),
        "monotonicity_report": build_monotonicity_report(
            mode_results or {}, coverage_manifest
        ),
    }


__all__ = [
    "REPORT_VERSION",
    "TRACE_VERSION",
    "NOT_AVAILABLE",
    "NOT_PROVEN",
    "RoleBWaterfallError",
    "read_evaluator_csv",
    "build_retrieval_waterfall",
    "build_risk_pipeline_waterfall",
    "build_monotonicity_report",
    "build_role_b_waterfall_artifacts",
]
