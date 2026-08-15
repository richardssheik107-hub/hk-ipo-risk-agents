"""Streaming V1/V2/V2.1 benchmark against expert physical-page evidence."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from ipo_risk.evaluation.raw_retrieval_audit import PRODUCTION_QUERY_PLANS, RetrievalComposition
from ipo_risk.evaluation.retrieval_40_annotations import AnnotationCase, GoldEvidence
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk, Evidence

K_VALUES = (3, 5, 10, 20, 50)
VERSIONS = ("v1", "v2", "v21")


@dataclass
class CaseResult:
    case_id: str
    rows: list[dict[str, Any]]
    risk_metrics: list[dict[str, Any]]
    candidate_sizes: list[dict[str, Any]]
    parser_errors: int


def recall(ranks: list[int | None], k: int) -> float:
    """Evidence-level recall at a global rank cutoff."""
    return sum(rank is not None and rank <= k for rank in ranks) / len(ranks) if ranks else 1.0


def classify_miss(rank: int | None, *, parser_or_input_miss: bool, candidate_limit: int = 50) -> str:
    """Classify the root cause without conflating risk-level completion."""
    if parser_or_input_miss:
        return "parser_or_input_miss"
    if rank is None or rank > candidate_limit:
        return "candidate_miss"
    if rank > 5:
        return "ranking_miss"
    return "hit"


def required_completion(ranks: list[int | None], k: int = 5) -> bool:
    """A risk completes only when every required record is in the head."""
    return bool(ranks) and all(rank is not None and rank <= k for rank in ranks)


class _CaseQueryCache:
    """Share identical deterministic keyword calls across historical variants."""

    name = "keyword_case_memory_cache"

    def __init__(self) -> None:
        self._retriever = _ContextCachedKeywordRetriever()
        self._cache: dict[tuple[str, int], list[Evidence]] = {}

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        key = (query, limit)
        if key not in self._cache:
            reusable = next((items for (cached_query, cached_limit), items in self._cache.items()
                             if cached_query == query and cached_limit >= limit), None)
            self._cache[key] = reusable[:limit] if reusable is not None else self._retriever.retrieve(chunks, query, limit=limit)
        return self._cache[key]


class _ContextCachedKeywordRetriever(KeywordDocumentRetriever):
    """Memoize the immutable page context that production rebuilds per call."""

    def __init__(self) -> None:
        self._cached_contexts: Any = None

    def _build_page_contexts(self, chunks: list[DocumentChunk]) -> Any:
        if self._cached_contexts is None:
            self._cached_contexts = KeywordDocumentRetriever._build_page_contexts(chunks)
        return self._cached_contexts


def _v1_pages(chunks: list[DocumentChunk], risk_code: str, depth: int, base: _CaseQueryCache) -> list[int]:
    plan = PRODUCTION_QUERY_PLANS[risk_code]
    results = [base.retrieve(chunks, query, limit=depth) for query in plan.queries]
    pages: list[int] = []
    if plan.composition is RetrievalComposition.PARALLEL_PER_QUERY_UNION:
        ordered = sorted(
            (rank, query_order, item.page)
            for query_order, items in enumerate(results)
            for rank, item in enumerate(items, 1) if item.page is not None
        )
        source = (page for _, _, page in ordered)
    else:
        source = (item.page for items in results for item in items if item.page is not None)
    for page in source:
        if page not in pages:
            pages.append(page)
            if len(pages) == depth:
                break
    return pages


def _rankings(chunks: list[DocumentChunk], risk_codes: tuple[str, ...], depth: int = 50) -> dict[str, dict[str, list[int]]]:
    base = _CaseQueryCache()
    # Preserve the historical candidates' frozen per-query depth (20).  Asking
    # the global pool for 50 must not silently widen and rerank each query.
    v2 = DomainAwareRetrieverV2(base=base)
    v21 = DomainAwareRetrieverV21(base=base)
    output = {version: {} for version in VERSIONS}
    for risk_code in risk_codes:
        if risk_code not in PRODUCTION_QUERY_PLANS:
            continue
        output["v1"][risk_code] = _v1_pages(chunks, risk_code, depth, base)
        output["v2"][risk_code] = [item.page for item in v2.retrieve_for_risk(chunks, risk_code, limit=depth) if item.page]
        output["v21"][risk_code] = [item.page for item in v21.retrieve_for_risk(chunks, risk_code, limit=depth) if item.page]
    return output


def _preview(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def evaluate_case(case: AnnotationCase, chunks: list[DocumentChunk], *, parser_errors: int = 0) -> CaseResult:
    """Evaluate one case, retaining no page text or candidate dump."""
    rankings = _rankings(chunks, case.risk_codes)
    page_text = {chunk.page: chunk.text for chunk in chunks if chunk.page is not None}
    required = [item for item in case.evidence if item.requirement == "required"]
    rows: list[dict[str, Any]] = []
    by_risk: dict[str, list[GoldEvidence]] = defaultdict(list)
    for item in required:
        by_risk[item.risk_code].append(item)
    rank_cache: dict[tuple[str, str, int], int | None] = {}
    for version in VERSIONS:
        for risk_code, pages in rankings[version].items():
            for item in by_risk[risk_code]:
                rank_cache[(version, risk_code, item.page)] = pages.index(item.page) + 1 if item.page in pages else None
    for item in required:
        page_present = item.page in page_text
        severe_text_miss = page_present and bool(item.exact_text) and _text_overlap(item.exact_text, page_text[item.page]) < 0.15
        parser_miss = not page_present or severe_text_miss
        row: dict[str, Any] = {
            "case_id": case.case_id, "stock_code": case.stock_code, "risk_code": item.risk_code,
            "gold_page": item.page, "evidence_role": item.evidence_role, "requirement": item.requirement,
            "source_authority": item.source_authority, "section": item.section or "",
            "evidence_id": item.evidence_id, "annotation_file": item.annotation_file,
            "exact_text_preview": _preview(item.exact_text), "parser_page_present": page_present,
            "parser_text_severe_miss": severe_text_miss,
        }
        for version in VERSIONS:
            rank = rank_cache.get((version, item.risk_code, item.page))
            row[f"{version}_rank"] = rank
            row[f"{version}_candidate_hit"] = rank is not None and rank <= 50
            row[f"{version}_miss_type"] = classify_miss(rank, parser_or_input_miss=parser_miss)
        ranks = [row[f"{version}_rank"] for version in VERSIONS if row[f"{version}_rank"] is not None]
        row["best_rank"] = min(ranks) if ranks else None
        v21_risk_ranks = [rank_cache.get(("v21", item.risk_code, gold.page)) for gold in by_risk[item.risk_code]]
        row["partial_completion"] = (
            not required_completion(v21_risk_ranks) and any(rank is not None and rank <= 5 for rank in v21_risk_ranks)
        )
        row["miss_type"] = "partial_completion" if row["partial_completion"] and row["v21_miss_type"] != "hit" else row["v21_miss_type"]
        row["underlying_miss_type"] = row["v21_miss_type"]
        rows.append(row)
    risk_metrics: list[dict[str, Any]] = []
    for risk_code in sorted(case.risk_codes):
        gold_items = by_risk[risk_code]
        all_items = [item for item in case.evidence if item.risk_code == risk_code]
        primary = [item for item in all_items if item.evidence_role == "primary"]
        for version in VERSIONS:
            pages = rankings[version].get(risk_code, [])
            ranks = [pages.index(item.page) + 1 if item.page in pages else None for item in gold_items]
            primary_ranks = [pages.index(item.page) + 1 if item.page in pages else None for item in primary]
            any_ranks = [pages.index(item.page) + 1 if item.page in pages else None for item in all_items]
            metric = {"case_id": case.case_id, "risk_code": risk_code, "version": version, "required_count": len(gold_items)}
            metric.update({f"required_recall_at_{k}": recall(ranks, k) for k in K_VALUES})
            metric.update({"primary_count": len(primary),
                           "primary_hit_at_5": sum(rank is not None and rank <= 5 for rank in primary_ranks),
                           "any_valid_hit_at_5": any(rank is not None and rank <= 5 for rank in any_ranks),
                           "required_completion_at_5": required_completion(ranks)})
            risk_metrics.append(metric)
    sizes = [{"case_id": case.case_id, "risk_code": risk, "version": version, "available_candidates": len(pages)}
             for version, risks in rankings.items() for risk, pages in risks.items()]
    return CaseResult(case.case_id, rows, risk_metrics, sizes, parser_errors)


def _text_overlap(gold: str, parsed: str) -> float:
    gold_compact = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", gold.lower())
    parsed_compact = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", parsed.lower())
    if not gold_compact:
        return 1.0
    if gold_compact in parsed_compact:
        return 1.0
    width = min(12, max(4, len(gold_compact) // 20))
    shingles = {gold_compact[index:index + width] for index in range(0, len(gold_compact) - width + 1, width)}
    return sum(shingle in parsed_compact for shingle in shingles) / len(shingles) if shingles else 0.0


def write_matrix(rows: list[dict[str, Any]], csv_path: Path, json_path: Path) -> None:
    """Write the only row-level artifacts; JSON remains compact."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    compact_fields = [field for field in fields if field not in {"exact_text_preview", "parser_text_severe_miss"}]
    json_path.write_text(json.dumps([{key: row[key] for key in compact_fields} for row in rows], ensure_ascii=False,
                                    separators=(",", ":")) + "\n", encoding="utf-8")


def summarize_annotations(cases: list[AnnotationCase]) -> dict[str, Any]:
    evidence = [item for case in cases for item in case.evidence]
    risk_annotations = sum(len(case.risk_codes) for case in cases)
    per_risk: dict[str, list[GoldEvidence]] = defaultdict(list)
    for item in evidence: per_risk[item.risk_code].append(item)
    return {
        "ipo_count": len(cases), "risk_annotation_count": risk_annotations, "evidence_count": len(evidence),
        "required_count": sum(item.requirement == "required" for item in evidence),
        "supporting_count": sum(item.requirement in {"supporting_only", "supporting"} for item in evidence),
        "primary_count": sum(item.evidence_role == "primary" for item in evidence),
        "risk_evidence_counts": dict(sorted(Counter(item.risk_code for item in evidence).items())),
        "risk_average_gold_pages": {risk: len({(item.case_id, item.page) for item in items}) / len({item.case_id for item in items})
                                    for risk, items in sorted(per_risk.items())},
        "source_authority": dict(sorted(Counter(item.source_authority for item in evidence).items())),
        "evidence_role": dict(sorted(Counter(item.evidence_role for item in evidence).items())),
        "requirement": dict(sorted(Counter(item.requirement for item in evidence).items())),
    }


def source_hashes(root: Path) -> dict[str, str]:
    files = {"v1": "src/ipo_risk/retrieval/keyword.py", "v2": "src/ipo_risk/retrieval/domain_aware_v2.py",
             "v21": "src/ipo_risk/retrieval/domain_aware_v21.py"}
    return {key: hashlib.sha256((root / value).read_text(encoding="utf-8").replace("\r\n", "\n").encode()).hexdigest()
            for key, value in files.items()}
