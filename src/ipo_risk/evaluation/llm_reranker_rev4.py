"""Post-freeze evaluation helpers for the Phase 0.6C Revision-4 pilot.

This module consumes frozen rankings and Expert Gold only.  It has no network
or Provider dependency and deliberately cannot issue LLM calls.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.raw_retrieval_audit import RawRetrievalAudit, TOP_K_VALUES
from ipo_risk.retrieval.domain_aware_v2 import RISK_DOMAINS
from ipo_risk.retrieval.llm_reranker import rerank
from ipo_risk.retrieval.llm_reranker_prompts import RISK_FACETS
from ipo_risk.retrieval.llm_reranker_schemas import (
    CandidateEvidenceView,
    LLMCandidateJudgmentBundle,
)


VARIANT_NAMES = ("v1", "v2", "v21", "stage1_union", "llm_rev4")
MAIN_METRICS = (
    "required_recall_at_3",
    "required_recall_at_5",
    "required_completion_at_5",
    "mrr",
)


@dataclass(frozen=True)
class GoldEvidenceRecord:
    """One frozen Expert-Gold Evidence row."""

    case_id: str
    runtime_case_id: str
    stock_code: str
    risk_code: str
    evidence_index: int
    page: int
    requirement: str
    evidence_role: str
    source_authority: str

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.case_id, self.risk_code, self.evidence_index)

    @property
    def task(self) -> tuple[str, str]:
        return (self.case_id, self.risk_code)


def runtime_case_aliases(
    canonical_cases: Sequence[str], runtime_cases: Sequence[str]
) -> dict[str, str]:
    """Map runtime IDs to canonical IDs without changing either source."""
    canonical_set = set(canonical_cases)
    by_suffix: dict[str, list[str]] = defaultdict(list)
    for case_id in canonical_cases:
        by_suffix[case_id.rsplit("_", 1)[-1]].append(case_id)
    aliases: dict[str, str] = {}
    for runtime_case in runtime_cases:
        if runtime_case in canonical_set:
            aliases[runtime_case] = runtime_case
            continue
        suffix = runtime_case.rsplit("_", 1)[-1]
        matches = by_suffix.get(suffix, [])
        if len(matches) != 1:
            raise ValueError(f"RUNTIME_CASE_ID_CANNOT_BE_RESOLVED:{runtime_case}")
        aliases[runtime_case] = matches[0]
    if set(aliases.values()) != canonical_set:
        raise ValueError("RUNTIME_AND_CANONICAL_CASE_SETS_DIFFER")
    return aliases


def gold_records(
    bundles: Sequence[ExpertAnnotationBundle], runtime_aliases: Mapping[str, str]
) -> list[GoldEvidenceRecord]:
    """Flatten Gold bundles while preserving canonical evidence indexes."""
    canonical_to_runtime = {canonical: runtime for runtime, canonical in runtime_aliases.items()}
    records: list[GoldEvidenceRecord] = []
    for bundle in bundles:
        runtime_case = canonical_to_runtime[bundle.case_id]
        for index, evidence in enumerate(bundle.evidence):
            records.append(
                GoldEvidenceRecord(
                    case_id=bundle.case_id,
                    runtime_case_id=runtime_case,
                    stock_code=bundle.stock_code,
                    risk_code=evidence.risk_code,
                    evidence_index=index,
                    page=evidence.page,
                    requirement=evidence.requirement.value,
                    evidence_role=evidence.evidence_role.value,
                    source_authority=evidence.source_authority.value,
                )
            )
    return records


def ranks_from_audits(audits: Sequence[RawRetrievalAudit]) -> dict[tuple[str, str, int], int | None]:
    """Extract frozen first-hit ranks from a historical Retriever audit."""
    return {
        (record.case_id, record.risk_code, record.evidence_index): record.first_hit_rank
        for audit in audits
        for record in audit.records
    }


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_ranks(
    records: Sequence[GoldEvidenceRecord],
    ranks: Mapping[tuple[str, str, int], int | None],
    *,
    task_filter: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Evaluate one frozen ranking with the historical PR-46 definitions."""
    selected = [record for record in records if task_filter is None or record.task in task_filter]
    missing_keys = [record.key for record in selected if record.key not in ranks]
    if missing_keys:
        raise ValueError(f"RANKS_MISSING_GOLD_KEYS:{missing_keys[:3]}")
    required = [record for record in selected if record.requirement == "required"]
    primary = [record for record in selected if record.evidence_role == "primary"]
    primary_or_required = [
        record
        for record in selected
        if record.evidence_role == "primary" or record.requirement == "required"
    ]
    tasks = sorted({record.task for record in selected})
    by_task = {task: [record for record in selected if record.task == task] for task in tasks}
    unique_pages = {(record.case_id, record.page) for record in selected}

    def recall(rows: Sequence[GoldEvidenceRecord], k: int) -> float:
        return _rate(sum((ranks[row.key] or 10**9) <= k for row in rows), len(rows))

    evidence_recall = {k: recall(selected, k) for k in TOP_K_VALUES}
    required_recall = {k: recall(required, k) for k in TOP_K_VALUES}
    primary_recall = {k: recall(primary, k) for k in TOP_K_VALUES}
    primary_or_required_recall = {k: recall(primary_or_required, k) for k in TOP_K_VALUES}
    unique_page_recall = {
        k: _rate(
            len(
                {
                    (record.case_id, record.page)
                    for record in selected
                    if (ranks[record.key] or 10**9) <= k
                }
            ),
            len(unique_pages),
        )
        for k in TOP_K_VALUES
    }
    any_valid = {
        k: _rate(
            sum(any((ranks[row.key] or 10**9) <= k for row in rows) for rows in by_task.values()),
            len(tasks),
        )
        for k in TOP_K_VALUES
    }
    completion = {}
    first_required_rank: dict[str, int | None] = {}
    for task, rows in by_task.items():
        needed = [row for row in rows if row.requirement == "required"]
        available = [ranks[row.key] for row in needed if ranks[row.key] is not None]
        first_required_rank[f"{task[0]}:{task[1]}"] = min(available) if available else None
    for k in TOP_K_VALUES:
        completion[k] = _rate(
            sum(
                bool(needed := [row for row in rows if row.requirement == "required"])
                and all((ranks[row.key] or 10**9) <= k for row in needed)
                for rows in by_task.values()
            ),
            len(tasks),
        )
    mrr = _rate(
        sum((1.0 / ranks[row.key]) if ranks[row.key] else 0.0 for row in required),
        len(required),
    )
    return {
        "evidence_count": len(selected),
        "required_count": len(required),
        "primary_count": len(primary),
        "unique_gold_page_count": len(unique_pages),
        "risk_task_count": len(tasks),
        "evidence_recall_at": evidence_recall,
        "required_recall_at": required_recall,
        "primary_recall_at": primary_recall,
        "primary_or_required_recall_at": primary_or_required_recall,
        "unique_gold_page_recall_at": unique_page_recall,
        "any_valid_risk_hit_at": any_valid,
        "required_completion_at": completion,
        "mrr": mrr,
        "first_required_rank_by_task": first_required_rank,
    }


def stage1_and_llm_ranks(
    records: Sequence[GoldEvidenceRecord],
    candidate_rows: Sequence[dict[str, Any]],
    judgments: Mapping[tuple[str, str], dict[str, Any]],
    runtime_aliases: Mapping[str, str],
) -> tuple[
    dict[tuple[str, str, int], int | None],
    dict[tuple[str, str, int], int | None],
    dict[tuple[str, str], list[CandidateEvidenceView]],
    dict[tuple[str, str], LLMCandidateJudgmentBundle | None],
]:
    """Build D/E ranks; failed official tasks deterministically use D."""
    stage1_pages: dict[tuple[str, str], list[int]] = {}
    llm_pages: dict[tuple[str, str], list[int]] = {}
    llm_order: dict[tuple[str, str], list[CandidateEvidenceView]] = {}
    bundles: dict[tuple[str, str], LLMCandidateJudgmentBundle | None] = {}
    for row in candidate_rows:
        runtime_case = row["case_id"]
        canonical_case = runtime_aliases[runtime_case]
        task = (canonical_case, row["risk_code"])
        pool = [CandidateEvidenceView.model_validate(item) for item in row["candidates"]]
        stage1_pages[task] = [item.page for item in pool]
        frozen = judgments[(runtime_case, row["risk_code"])]
        if frozen["status"] == "completed":
            bundle = LLMCandidateJudgmentBundle.model_validate(frozen["bundle"])
            order = rerank(pool, bundle, row["risk_code"])
            bundles[task] = bundle
        elif frozen["status"] == "failed" and frozen.get("fallback") == "stage1_union_order":
            order = pool
            bundles[task] = None
        else:
            raise ValueError(f"INVALID_OFFICIAL_JUDGMENT:{runtime_case}:{row['risk_code']}")
        llm_order[task] = order
        llm_pages[task] = [item.page for item in order]

    def locate(page_map: Mapping[tuple[str, str], list[int]]) -> dict[tuple[str, str, int], int | None]:
        output: dict[tuple[str, str, int], int | None] = {}
        for record in records:
            pages = page_map[record.task]
            output[record.key] = pages.index(record.page) + 1 if record.page in pages else None
        return output

    return locate(stage1_pages), locate(llm_pages), llm_order, bundles


def breakdown(
    records: Sequence[GoldEvidenceRecord],
    variants: Mapping[str, Mapping[tuple[str, str, int], int | None]],
    *,
    group_by: str,
) -> list[dict[str, Any]]:
    """Return domain, risk or case slices for every variant."""
    if group_by not in {"domain", "risk", "case"}:
        raise ValueError(f"unsupported breakdown: {group_by}")
    groups: dict[str, list[GoldEvidenceRecord]] = defaultdict(list)
    for record in records:
        key = (
            RISK_DOMAINS[record.risk_code]
            if group_by == "domain"
            else record.risk_code
            if group_by == "risk"
            else record.case_id
        )
        groups[key].append(record)
    rows = []
    for group, selected in sorted(groups.items()):
        for variant, ranks in variants.items():
            metrics = evaluate_ranks(selected, ranks)
            rows.append(
                {
                    group_by: group,
                    "variant": variant,
                    "gold_evidence_count": metrics["evidence_count"],
                    "required_count": metrics["required_count"],
                    "required_at_3": metrics["required_recall_at"][3],
                    "required_at_5": metrics["required_recall_at"][5],
                    "required_at_20": metrics["required_recall_at"][20],
                    "completion_at_5": metrics["required_completion_at"][5],
                    "mrr": metrics["mrr"],
                }
            )
    return rows


def promotion_matrix(
    records: Sequence[GoldEvidenceRecord],
    variants: Mapping[str, Mapping[tuple[str, str, int], int | None]],
    task_status: Mapping[tuple[str, str], str],
) -> list[dict[str, Any]]:
    """Classify Stage1-to-LLM movement for every required Gold row."""
    rows = []
    for record in records:
        if record.requirement != "required":
            continue
        d = variants["stage1_union"][record.key]
        e = variants["llm_rev4"][record.key]
        if d is None:
            classification = "NOT_IN_STAGE1"
        elif d > 10 and e is not None and e <= 5:
            classification = "DEEP_GAIN"
        elif d > 3 and e is not None and e <= 3:
            classification = "RECOVERED_TO_TOP3"
        elif d > 5 and e is not None and e <= 5:
            classification = "RECOVERED_TO_TOP5"
        elif d <= 3 and (e is None or e > 3):
            classification = "DEMOTED_FROM_TOP3"
        elif d <= 5 and (e is None or e > 5):
            classification = "DEMOTED_FROM_TOP5"
        else:
            classification = "UNCHANGED_HEAD"
        rows.append(
            {
                "case_id": record.case_id,
                "risk_code": record.risk_code,
                "gold_page": record.page,
                "requirement": record.requirement,
                "evidence_role": record.evidence_role,
                "source_authority": record.source_authority,
                "v1_rank": variants["v1"][record.key],
                "v2_rank": variants["v2"][record.key],
                "v21_rank": variants["v21"][record.key],
                "stage1_rank": d,
                "llm_rank": e,
                "delta_stage1_to_llm": None if d is None or e is None else d - e,
                "official_task_status": task_status[record.task],
                "classification": classification,
            }
        )
    return rows


def facet_coverage(
    llm_order: Mapping[tuple[str, str], Sequence[CandidateEvidenceView]],
    bundles: Mapping[tuple[str, str], LLMCandidateJudgmentBundle | None],
) -> dict[str, Any]:
    """Measure frozen semantic-facet coverage on completed tasks only."""
    rows = []
    for task, order in sorted(llm_order.items()):
        bundle = bundles[task]
        if bundle is None:
            continue
        by_id = {item.candidate_id: item for item in bundle.judgments}
        expected = set(RISK_FACETS[task[1]])
        values = {}
        for k in (3, 5, 10):
            found = {
                facet
                for candidate in order[:k]
                for facet in by_id[candidate.candidate_id].completeness_facets
            }
            values[k] = _rate(len(found & expected), len(expected))
        rows.append({"case_id": task[0], "risk_code": task[1], "coverage": values})
    by_risk = {}
    for risk_code in sorted(RISK_FACETS):
        selected = [row for row in rows if row["risk_code"] == risk_code]
        by_risk[risk_code] = {
            "completed_tasks": len(selected),
            "coverage_at": {
                k: _rate(sum(row["coverage"][k] for row in selected), len(selected))
                for k in (3, 5, 10)
            },
        }
    return {
        "diagnostic_only": True,
        "completed_tasks": len(rows),
        "coverage_at": {
            k: _rate(sum(row["coverage"][k] for row in rows), len(rows))
            for k in (3, 5, 10)
        },
        "by_risk": by_risk,
        "tasks": rows,
    }


def reliability_analysis(task_status: Mapping[tuple[str, str], str]) -> dict[str, Any]:
    """Break official structured-output reliability down by domain and risk."""
    def summarize(tasks: Iterable[tuple[str, str]]) -> dict[str, Any]:
        items = list(tasks)
        completed = sum(task_status[item] == "completed" for item in items)
        fallback = len(items) - completed
        return {
            "task_count": len(items),
            "completed": completed,
            "fallback": fallback,
            "fallback_rate": _rate(fallback, len(items)),
        }

    return {
        "overall": summarize(task_status),
        "by_domain": {
            domain: summarize(task for task in task_status if RISK_DOMAINS[task[1]] == domain)
            for domain in sorted(set(RISK_DOMAINS.values()))
        },
        "by_risk": {
            risk: summarize(task for task in task_status if task[1] == risk)
            for risk in sorted(RISK_DOMAINS)
        },
    }


def semantic_error_taxonomy(
    records: Sequence[GoldEvidenceRecord],
    stage1_ranks: Mapping[tuple[str, str, int], int | None],
    llm_ranks: Mapping[tuple[str, str, int], int | None],
    task_status: Mapping[tuple[str, str], str],
    llm_order: Mapping[tuple[str, str], Sequence[CandidateEvidenceView]],
    bundles: Mapping[tuple[str, str], LLMCandidateJudgmentBundle | None],
) -> dict[str, Any]:
    """Classify post-Gold Top-5 misses without changing the frozen policy."""
    required_by_task: dict[tuple[str, str], list[GoldEvidenceRecord]] = defaultdict(list)
    for record in records:
        if record.requirement == "required":
            required_by_task[record.task].append(record)
    rows = []
    for record in records:
        if record.requirement != "required" or (llm_ranks[record.key] or 10**9) <= 5:
            continue
        d, e = stage1_ranks[record.key], llm_ranks[record.key]
        task_rows = required_by_task[record.task]
        some_task_hit = any((llm_ranks[row.key] or 10**9) <= 5 for row in task_rows)
        if d is None:
            category = "CANDIDATE_COVERAGE_MISS"
        elif task_status[record.task] == "failed":
            category = "FALLBACK_NO_LLM"
        elif d <= 5:
            category = "LLM_HEAD_DEMOTION"
        elif len(task_rows) > 1 and some_task_hit and RISK_DOMAINS[record.risk_code] == "financial":
            category = "FINANCIAL_MULTIPAGE_FRAGMENTATION"
        elif len(task_rows) > 1 and some_task_hit:
            category = "MULTIPAGE_COMPLETION_FAILURE"
        else:
            bundle = bundles[record.task]
            top = llm_order[record.task][:5]
            judged = {item.candidate_id: item for item in bundle.judgments} if bundle else {}
            top_judgments = [judged[item.candidate_id] for item in top if item.candidate_id in judged]
            if record.risk_code == "material_litigation_compliance" and any(
                item.boilerplate or item.evidence_role == "boilerplate" for item in top_judgments
            ):
                category = "GENERIC_BOILERPLATE_CONFUSION"
            elif record.risk_code in {"redemption_rights", "material_litigation_compliance"} and any(
                item.current_status_relevance in {"none", "indirect"} for item in top_judgments
            ):
                category = "CURRENT_STATUS_CONFUSION"
            elif any(item.source_authority in {"weak", "unknown"} for item in top_judgments):
                category = "AUTHORITY_CONFUSION"
            else:
                category = "LLM_INSUFFICIENT_PROMOTION"
        rows.append(
            {
                "case_id": record.case_id,
                "risk_code": record.risk_code,
                "gold_page": record.page,
                "stage1_rank": d,
                "llm_rank": e,
                "task_status": task_status[record.task],
                "category": category,
            }
        )
    counts = Counter(row["category"] for row in rows)
    for name in (
        "CANDIDATE_COVERAGE_MISS",
        "LLM_HEAD_DEMOTION",
        "LLM_INSUFFICIENT_PROMOTION",
        "FALLBACK_NO_LLM",
        "MULTIPAGE_COMPLETION_FAILURE",
        "AUTHORITY_CONFUSION",
        "GENERIC_BOILERPLATE_CONFUSION",
        "FINANCIAL_MULTIPAGE_FRAGMENTATION",
        "CURRENT_STATUS_CONFUSION",
        "OTHER",
    ):
        counts.setdefault(name, 0)
    return {"top5_required_miss_count": len(rows), "counts": dict(sorted(counts.items())), "rows": rows}
