"""Pure, deterministic helpers for the Retriever V3 Phase-A audit."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ipo_risk.evaluation.retrieval_40_annotations import GoldEvidence, load_annotation


SPLIT_SALT = "retriever-v3-new20-case-split-v1|2026-08-16"
K_VALUES = (1, 3, 5, 10, 20, 50)
RETRIEVERS = ("v1", "v2", "v21")


@dataclass(frozen=True)
class EffectiveQrel:
    case_id: str
    risk_code: str
    page: int
    evidence_role: str
    requirement: str
    source_authority: str
    confidence: float | None
    evidence_id: str
    gold_label: int
    judgement_status: str
    annotation_source: str
    audit_status: str
    audit_resolution: str


def deterministic_split(case_ids: Iterable[str], *, salt: str = SPLIT_SALT) -> tuple[list[str], list[str]]:
    """Split exactly twenty unseen IPOs 10/10 using stable case-level hashing."""
    unique = sorted(set(case_ids))
    if len(unique) != 20:
        raise ValueError(f"NEW_CASE_COUNT:{len(unique)} expected=20")
    ordered = sorted(unique, key=lambda value: (hashlib.sha256(f"{value}|{salt}".encode()).hexdigest(), value))
    return ordered[:10], ordered[10:]


def validate_case_sets(all_cases: Iterable[str], historical: Iterable[str]) -> tuple[list[str], list[str]]:
    all_set, historical_set = set(all_cases), set(historical)
    if len(all_set) != 60:
        raise ValueError(f"ALL_CASE_COUNT:{len(all_set)} expected=60")
    if len(historical_set) != 40 or not historical_set <= all_set:
        raise ValueError("HISTORICAL_40_NOT_IDENTIFIED")
    new_cases = sorted(all_set - historical_set)
    if len(new_cases) != 20:
        raise ValueError(f"NEW_CASE_COUNT:{len(new_cases)} expected=20")
    return sorted(historical_set), new_cases


def qrel_label(item: GoldEvidence) -> int:
    role = item.evidence_role.lower().strip()
    requirement = item.requirement.lower().strip()
    if requirement == "required":
        return 3 if role == "primary" else 2
    if requirement in {"optional", "alternative", "supporting", "supporting_only"}:
        return 1
    return 1


def candidate_judgement(page: int, qrels: Sequence[EffectiveQrel]) -> tuple[int, str, str]:
    matches = [item for item in qrels if item.page == page]
    if not matches:
        return -1, "UNJUDGED", ""
    best = max(matches, key=lambda item: item.gold_label)
    return best.gold_label, "JUDGED", best.source_authority


def _audit_by_risk(annotation_path: Path) -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    audit_dir = annotation_path.parent.parent / "audit"
    for audit_path in sorted(audit_dir.glob("*.json")) if audit_dir.exists() else []:
        if audit_path.name not in {"financial_resolution_v1.json", "deterministic_corrections_v1.json"}:
            continue
        payload = json.loads(audit_path.read_text(encoding="utf-8-sig"))
        values = payload.get("resolutions", payload.get("corrections", payload.get("entries", payload.get("items", []))))
        if isinstance(values, dict):
            values = list(values.values())
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, dict):
                continue
            risk = str(value.get("risk_code", value.get("code", ""))).strip()
            if not risk:
                continue
            details = [str(value[key]) for key in (
                "closure_status", "action", "policy_code", "resolution_class", "finding", "replacement"
            ) if value.get(key) not in (None, "")]
            output[risk].append(f"{audit_path.name}:{'|'.join(details) or 'available'}")
    return output


def resolve_qrels(annotation_path: Path, *, repository_root: Path) -> list[EffectiveQrel]:
    """Resolve pass1 retrieval qrels; audit metadata never mutates evidence pages."""
    case = load_annotation(annotation_path, repository_root=repository_root)
    audits = _audit_by_risk(annotation_path)
    output = []
    for item in case.evidence:
        details = audits.get(item.risk_code, [])
        output.append(EffectiveQrel(
            case_id=item.case_id, risk_code=item.risk_code, page=item.page,
            evidence_role=item.evidence_role, requirement=item.requirement,
            source_authority=item.source_authority, confidence=item.confidence,
            evidence_id=item.evidence_id, gold_label=qrel_label(item), judgement_status="JUDGED",
            annotation_source=item.annotation_file,
            audit_status="available" if details else "not_available",
            audit_resolution=";".join(details),
        ))
    return output


def recall_at(ranks: Sequence[int | None], k: int) -> float:
    return sum(rank is not None and rank <= k for rank in ranks) / len(ranks) if ranks else 0.0


def completion_at(groups: Mapping[tuple[str, str], Sequence[int | None]], k: int) -> float:
    values = [bool(ranks) and all(rank is not None and rank <= k for rank in ranks) for ranks in groups.values()]
    return sum(values) / len(values) if values else 0.0


def contribution_bucket(flags: Mapping[str, bool]) -> str:
    found = tuple(name for name in RETRIEVERS if flags.get(name, False))
    names = {
        (): "none", ("v1",): "V1_only", ("v2",): "V2_only", ("v21",): "V21_only",
        ("v1", "v2"): "V1_and_V2", ("v1", "v21"): "V1_and_V21",
        ("v2", "v21"): "V2_and_V21", RETRIEVERS: "all_three",
    }
    return names[found]


def unique_contribution(flag_rows: Iterable[Mapping[str, bool]]) -> dict[str, int]:
    counts = Counter(contribution_bucket(row) for row in flag_rows)
    names = ("V1_only", "V2_only", "V21_only", "V1_and_V2", "V1_and_V21", "V2_and_V21", "all_three", "none")
    return {name: counts[name] for name in names}


def oracle_union(flag_rows: Sequence[Mapping[str, bool]], versions: Sequence[str]) -> float:
    return sum(any(row.get(name, False) for name in versions) for row in flag_rows) / len(flag_rows) if flag_rows else 0.0


def rrf_fuse(rankings: Mapping[str, Sequence[int]], *, rrf_k: int = 60, limit: int = 100) -> list[int]:
    """Equal-weight deterministic RRF; no learned or tuned weights."""
    scores: dict[int, float] = defaultdict(float)
    best_rank: dict[int, int] = {}
    for version in sorted(rankings):
        for rank, page in enumerate(rankings[version], 1):
            scores[page] += 1.0 / (rrf_k + rank)
            best_rank[page] = min(best_rank.get(page, rank), rank)
    return [page for page, _ in sorted(scores.items(), key=lambda item: (-item[1], best_rank[item[0]], item[0]))[:limit]]


def classify_failure(*, page_present: bool, native_ranks: Mapping[str, int | None],
                     top20_ranks: Mapping[str, int | None], neighbor_found: bool = False,
                     table_like: bool = False, multipage: bool = False,
                     authority_hint: bool = False) -> tuple[str, str, str]:
    if not page_present:
        return "PARSER_OR_INPUT_MISS", "high", "Gold physical page is absent from parsed input."
    if any(rank is not None for rank in native_ranks.values()) and not any(
        rank is not None and rank <= 20 for rank in top20_ranks.values()
    ):
        return "RANKING_ONLY_MISS", "high", "Gold is in a native candidate universe but below rank 20."
    if neighbor_found:
        return "NEIGHBOR_PAGE_MISS", "high", "An adjacent physical page was retrieved but the Gold page was not."
    if table_like:
        return "TABLE_FRAGMENTATION", "medium", "Gold is table-like and absent from every native candidate universe."
    if multipage:
        return "MULTIPAGE_FRAGMENTATION", "medium", "Another required page in the same evidence bundle was found."
    if authority_hint:
        return "SECTION_AUTHORITY_MISS", "medium", "Gold authority is under-represented in the candidate universes."
    return "QUERY_COVERAGE_MISS", "medium", "No frozen query route produced the Gold page."


def qrels_as_dicts(qrels: Iterable[EffectiveQrel]) -> list[dict[str, Any]]:
    return [asdict(item) for item in qrels]
