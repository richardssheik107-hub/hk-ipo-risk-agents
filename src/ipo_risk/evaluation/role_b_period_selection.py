"""Gold-isolated helpers for auditing deterministic Financial period selection.

This module is evaluation-only.  It classifies already-produced extractor
diagnostics; it is never imported by a runtime Agent, Retriever, or selector.
"""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PeriodSelectionEvidence:
    """Minimum evidence required to call a failure a selector bug."""

    retrieved_candidate_present: bool
    parser_text_present: bool
    correct_period_candidate_present: bool
    correct_value_candidate_present: bool
    currency_unit_compatible: bool
    compatible_pair_exists: bool
    same_period_conflict_detected: bool
    selected_period_matches: bool | None


def classify_period_selection(evidence: PeriodSelectionEvidence) -> str:
    """Return the earliest proven failure without guessing missing facts.

    A selector bug is deliberately the last remaining explanation: the correct
    period and value must both exist, be compatible and conflict-free, while the
    production selection must demonstrably choose another period.
    """

    if not evidence.retrieved_candidate_present:
        return "deterministic_fact_missing"
    if not evidence.parser_text_present:
        return "parser_text_missing"
    if not evidence.correct_period_candidate_present:
        return "period_candidate_missing"
    if not evidence.correct_value_candidate_present:
        return "numeric_extraction_miss"
    if not evidence.currency_unit_compatible:
        return "deterministic_fact_missing"
    if evidence.same_period_conflict_detected:
        return "conflict_fail_closed"
    if not evidence.compatible_pair_exists:
        return "deterministic_fact_missing"
    if evidence.selected_period_matches is False:
        return "period_selection_bug"
    if evidence.selected_period_matches is True:
        return "correct"
    return "deterministic_fact_missing"


def extract_component_metadata(serialized: str, risk_code: str) -> dict[str, Any] | None:
    """Extract one literal metadata mapping from the legacy diagnostic repr.

    The persisted analysis contract currently stores ``ComponentDiagnostic``
    values as a repr string.  Only the balanced ``metadata={...}`` literal is
    decoded, with ``ast.literal_eval``; no executable input is evaluated.
    """

    marker = f"ComponentDiagnostic(risk_code='{risk_code}'"
    start = serialized.find(marker)
    if start < 0:
        return None
    metadata_start = serialized.find("metadata=", start)
    if metadata_start < 0:
        return None
    brace = serialized.find("{", metadata_start)
    if brace < 0:
        return None
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(brace, len(serialized)):
        character = serialized[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                value = ast.literal_eval(serialized[brace : index + 1])
                return dict(value) if isinstance(value, dict) else None
    return None


def value_hash(value: object) -> str | None:
    """Hash a diagnostic value so safe artifacts do not persist financial text."""

    if value is None:
        return None
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def period_candidates(metadata: Mapping[str, Any], risk_code: str) -> list[dict[str, Any]]:
    """Return bounded, text-free period candidates from persisted diagnostics."""

    if risk_code == "cash_runway":
        conversion = metadata.get("financial_conversion")
        if not isinstance(conversion, Mapping):
            return []
        result: list[dict[str, Any]] = []
        for metric in ("cash", "operating_cash_flow"):
            item = conversion.get(metric)
            if not isinstance(item, Mapping):
                continue
            result.append(
                {
                    "metric": metric,
                    "period_end": item.get("period_end"),
                    "period_months": item.get("period_months"),
                    "value_present": item.get("value") is not None,
                    "value_hash": value_hash(item.get("value")),
                    "currency": item.get("currency"),
                    "unit": item.get("unit"),
                    "status": item.get("status"),
                }
            )
        return result

    candidates = metadata.get("candidate_diagnostics")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        return []
    result = []
    for item in candidates:
        if not isinstance(item, Mapping):
            continue
        values = {
            "largest": item.get("largest_counterparty_pct"),
            "top_five": item.get("top_five_pct"),
        }
        result.append(
            {
                "period_end": item.get("period_end"),
                "period_months": item.get("period_months"),
                "value_present": any(value is not None for value in values.values()),
                "value_hash": value_hash(values),
                "status": item.get("status"),
                "issues": list(item.get("issues") or []),
                "selected": item.get("selected_for_merge") is True,
            }
        )
    return result


def summarize_candidates(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Produce the bounded fields permitted in a committed audit artifact."""

    periods = sorted(
        {
            (str(item.get("period_end")), item.get("period_months"))
            for item in candidates
            if item.get("period_end")
        },
        key=lambda item: (item[0], -1 if item[1] is None else int(item[1])),
    )
    return {
        "candidate_count": len(candidates),
        "parsed_period_candidate_count": len(periods),
        "parsed_period_candidates": [
            {"period_end": period_end, "period_months": months}
            for period_end, months in periods
        ],
        "parsed_value_candidate_count": sum(
            item.get("value_present") is True for item in candidates
        ),
        "selected_value_hashes": sorted(
            {
                str(item["value_hash"])
                for item in candidates
                if item.get("value_hash")
                and (item.get("selected") is True or len(candidates) <= 2)
            }
        ),
    }
