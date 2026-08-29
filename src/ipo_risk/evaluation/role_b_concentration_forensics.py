"""Gold-isolated structural classification for concentration fact formation.

The classifier consumes only bounded extractor diagnostics. It never receives
prospectus text, Gold text, expected pages, issuer names, or expected values.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ConcentrationFormationEvidence:
    """Text-free structural evidence emitted by one production replay."""

    status: str
    merged_issues: tuple[str, ...]
    candidate_count: int
    clean_complete_candidate_count: int
    complete_candidate_count: int
    largest_only_candidate_count: int
    top_five_only_candidate_count: int
    candidate_issue_counts: Mapping[str, int]


def _has(evidence: ConcentrationFormationEvidence, *issues: str) -> bool:
    observed = set(evidence.merged_issues) | {
        key for key, count in evidence.candidate_issue_counts.items() if count
    }
    return bool(observed.intersection(issues))


def classify_concentration_formation(
    evidence: ConcentrationFormationEvidence,
) -> dict[str, object]:
    """Classify one unit without using its Gold answer.

    Multiple patterns may coexist. ``primary_pattern`` is the earliest bounded
    structural blocker, while ``source_sufficiency`` prevents an ambiguous or
    genuinely under-supported unit from being counted as safely recoverable.
    """

    patterns: list[str] = []
    if _has(evidence, "concentration_percentage_missing", "percentage_out_of_range"):
        patterns.append("percentage_parsing")
    if _has(evidence, "largest_percentage_exceeds_top_five"):
        patterns.extend(("entity_binding", "top_n_binding"))
    if _has(
        evidence,
        "missing_period",
        "latest_period_months_ambiguous",
        "mixed_period_header_ambiguous",
        "period_months_conflict",
    ):
        patterns.append("period_binding")
    if _has(evidence, "value_period_count_mismatch"):
        patterns.append("companion_series_binding")
    if _has(evidence, "table_row_reconstruction_failed"):
        patterns.append("table_row_reconstruction")
    if evidence.largest_only_candidate_count and evidence.top_five_only_candidate_count:
        patterns.append("aggregation_required")
    if _has(evidence, "conflicting_values_for_same_period", "period_months_conflict"):
        patterns.extend(("multi_occurrence_ambiguity", "genuine_conflict"))
    if evidence.candidate_count == 0 or _has(evidence, "concentration_label_not_found"):
        patterns.append("insufficient_evidence")
    if not patterns:
        patterns.append("other_proven_root")
    patterns = list(dict.fromkeys(patterns))

    if evidence.status == "extracted":
        sufficiency = "source_information_sufficient_fact_formed"
        primary = "fact_formed_downstream_miss"
        recoverable = False
    elif "genuine_conflict" in patterns and evidence.clean_complete_candidate_count:
        sufficiency = "genuine_ambiguity_fail_closed"
        primary = "genuine_conflict"
        recoverable = False
    elif evidence.complete_candidate_count or (
        evidence.largest_only_candidate_count and evidence.top_five_only_candidate_count
    ):
        sufficiency = "source_information_sufficient_pipeline_failed"
        priority = (
            "entity_binding",
            "top_n_binding",
            "companion_series_binding",
            "period_binding",
            "aggregation_required",
            "percentage_parsing",
            "multi_occurrence_ambiguity",
        )
        primary = next((item for item in priority if item in patterns), patterns[0])
        recoverable = primary != "multi_occurrence_ambiguity"
    else:
        sufficiency = "candidate_evidence_insufficient"
        priority = (
            "insufficient_evidence",
            "percentage_parsing",
            "aggregation_required",
            "companion_series_binding",
            "period_binding",
            "entity_binding",
        )
        primary = next((item for item in priority if item in patterns), patterns[0])
        recoverable = False

    return {
        "primary_pattern": primary,
        "patterns": patterns,
        "source_sufficiency": sufficiency,
        "generic_runtime_fix_candidate": recoverable,
    }


def summarize_concentration_matrix(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Return cohort-level counts for a structural unit matrix."""

    return {
        "unit_count": len(rows),
        "primary_pattern_counts": dict(
            sorted(Counter(str(row["primary_pattern"]) for row in rows).items())
        ),
        "source_sufficiency_counts": dict(
            sorted(Counter(str(row["source_sufficiency"]) for row in rows).items())
        ),
        "generic_runtime_fix_candidate_count": sum(
            row.get("generic_runtime_fix_candidate") is True for row in rows
        ),
    }
