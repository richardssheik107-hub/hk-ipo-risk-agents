"""Retriever V3 60-case baseline evaluation helpers.

The module evaluates existing V1/V2/V2.1 retrieval behavior only. It does not
change production queries, scores, parser behavior, or LLM behavior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.evaluation.raw_retrieval_audit import PRODUCTION_QUERY_PLANS, RetrievalComposition
from ipo_risk.evaluation.retriever_v3_dataset import RetrievalGoldRow, evidence_pattern_summary
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.retrieval.query_families import QUERY_FAMILY_BY_NAME
from ipo_risk.schemas import DocumentChunk, Evidence


TOP_K_VALUES = (1, 3, 5, 10, 20, 50, 100)
UNION_DEPTHS = (20, 50, 100)
VARIANTS = ("v1", "v2", "v21")


class PageCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    risk_code: str
    variant: str
    rank: int = Field(ge=1)
    page: int = Field(ge=1)
    chunk_id: str | None
    relevance_score: float
    authority_hint: str
    matched_terms: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    text_excerpt: str = ""


class FailureRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    risk_code: str
    gold_page: int
    source_authority: str
    evidence_roles: list[str]
    first_rank_v1: int | None
    first_rank_v2: int | None
    first_rank_v21: int | None
    primary_failure: str
    secondary_flags: list[str]
    recommended_lane: list[str]


class HardNegativeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    risk_code: str
    variant: str
    rank: int
    page: int
    relevance_score: float
    authority_hint: str
    negative_tier: str
    text_excerpt: str


def _compact_excerpt(text: str, limit: int = 600) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _evidence_to_candidate(case_id: str, risk_code: str, variant: str, rank: int, item: Evidence) -> PageCandidate:
    metadata = item.metadata or {}
    matched = set(metadata.get("matched_keywords", []))
    matched.update(metadata.get("matched_queries", []))
    matched.update(metadata.get("matched_terms", []))
    provenance_keys = (
        "query_intent", "query_family", "query_rounds", "candidate_tier",
        "is_neighbor_only", "is_round2_only", "is_boilerplate", "v1_rank",
        "query_family_multiplicity", "query_multiplicity",
    )
    provenance = {key: metadata.get(key) for key in provenance_keys if key in metadata}
    return PageCandidate(
        case_id=case_id, risk_code=risk_code, variant=variant, rank=rank,
        page=int(item.page), chunk_id=item.chunk_id,
        relevance_score=float(item.relevance_score), authority_hint=authority_hint(item.text),
        matched_terms=sorted(str(value) for value in matched), provenance=provenance,
        text_excerpt=_compact_excerpt(item.text),
    )


def _compose_v1(chunks: list[DocumentChunk], risk_code: str, *, depth: int) -> list[Evidence]:
    base = KeywordDocumentRetriever()
    plan = PRODUCTION_QUERY_PLANS[risk_code]
    runs = [base.retrieve(chunks, query, limit=depth) for query in plan.queries]
    ordered: list[Evidence] = []
    if plan.composition is RetrievalComposition.PARALLEL_PER_QUERY_UNION:
        for source_rank in range(depth):
            for run in runs:
                if source_rank < len(run):
                    ordered.append(run[source_rank])
    else:
        ordered = [item for run in runs for item in run]
    pages: set[int] = set()
    result: list[Evidence] = []
    for item in ordered:
        if item.page is None or item.page in pages:
            continue
        pages.add(item.page)
        result.append(item)
        if len(result) >= depth:
            break
    return result


def retrieve_existing_variants(
    chunks: list[DocumentChunk], *, case_id: str, depth: int = 100,
) -> dict[str, dict[str, list[PageCandidate]]]:
    """Run unchanged V1/V2/V2.1 rankings for all eight risks."""
    v2 = DomainAwareRetrieverV2(candidate_depth=depth)
    v21 = DomainAwareRetrieverV21(candidate_depth=depth)
    output: dict[str, dict[str, list[PageCandidate]]] = {}
    for risk_code in sorted(PRODUCTION_QUERY_PLANS):
        raw = {
            "v1": _compose_v1(chunks, risk_code, depth=depth),
            "v2": v2.retrieve_for_risk(chunks, risk_code, limit=depth),
            "v21": v21.retrieve_for_risk(chunks, risk_code, limit=depth),
        }
        output[risk_code] = {
            variant: [
                _evidence_to_candidate(case_id, risk_code, variant, rank, item)
                for rank, item in enumerate(items, 1) if item.page is not None
            ]
            for variant, items in raw.items()
        }
    return output


def authority_hint(text: str) -> str:
    """Evaluation-only generic page authority hint; never filters retrieval."""
    normalized = normalize_for_match(text)
    rules = (
        ("accountants_report", ("accountants' report", "accountants’ report", "會計師報告", "会计师报告", "歷史財務資料", "历史财务资料")),
        ("financial_information", ("financial information", "財務資料", "财务资料", "財務信息", "财务信息")),
        ("pre_ipo_investment", ("pre-ipo", "pre ipo", "首次公開發售前投資", "首次公开发售前投资", "投資者協議", "投资者协议")),
        ("legal_disclosure", ("litigation", "arbitration", "legal proceedings", "訴訟", "诉讼", "仲裁", "合規", "合规", "licence", "license", "許可證", "许可证")),
        ("business_section", ("business", "業務", "业务", "customers", "suppliers", "客戶", "客户", "供應商", "供应商", "產品", "产品")),
        ("risk_factors", ("risk factors", "風險因素", "风险因素")),
        ("summary", ("summary", "概要", "摘要")),
        ("corporate_structure", ("corporate structure", "股權架構", "股权架构", "公司架構", "公司架构")),
    )
    for label, terms in rules:
        if any(normalize_for_match(term) in normalized for term in terms):
            return label
    return "unknown"


def _required_rows(rows: Iterable[RetrievalGoldRow]) -> list[RetrievalGoldRow]:
    return [row for row in rows if row.requirement == "required"]


def _candidate_pages(candidates: list[PageCandidate], k: int) -> set[int]:
    return {item.page for item in candidates[:k]}


def _first_rank(candidates: list[PageCandidate], page: int) -> int | None:
    return next((item.rank for item in candidates if item.page == page), None)


def variant_metrics(
    rankings: dict[str, dict[str, list[PageCandidate]]], gold_rows: list[RetrievalGoldRow],
) -> dict[str, Any]:
    """Compute evidence recall, page recall, completion and MRR for one case."""
    result: dict[str, Any] = {}
    for variant in VARIANTS:
        required = _required_rows(gold_rows)
        unique_required = {(row.risk_code, row.page) for row in required}
        metrics: dict[str, Any] = {
            "required_evidence_count": len(required), "required_page_count": len(unique_required),
            "required_recall_at": {}, "required_page_recall_at": {},
            "required_completion_at": {}, "mrr": 0.0,
        }
        ranks = [_first_rank(rankings[row.risk_code][variant], row.page) for row in required]
        for k in TOP_K_VALUES:
            metrics["required_recall_at"][str(k)] = sum(rank is not None and rank <= k for rank in ranks) / len(ranks) if ranks else 1.0
            hit_pages = {(risk, page) for risk, page in unique_required if page in _candidate_pages(rankings[risk][variant], k)}
            metrics["required_page_recall_at"][str(k)] = len(hit_pages) / len(unique_required) if unique_required else 1.0
            tasks = sorted({row.risk_code for row in required})
            complete = 0
            for risk_code in tasks:
                risk_pages = {row.page for row in required if row.risk_code == risk_code}
                if risk_pages and risk_pages <= _candidate_pages(rankings[risk_code][variant], k):
                    complete += 1
            metrics["required_completion_at"][str(k)] = complete / len(tasks) if tasks else 1.0
        metrics["mrr"] = sum((1.0 / rank) if rank else 0.0 for rank in ranks) / len(ranks) if ranks else 1.0
        result[variant] = metrics
    return result


def aggregate_variant_metrics(
    all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]], gold_rows: list[RetrievalGoldRow],
) -> dict[str, Any]:
    """Aggregate evidence-level metrics across cases without averaging case rates."""
    by_case_risk: dict[tuple[str, str], list[RetrievalGoldRow]] = defaultdict(list)
    for row in _required_rows(gold_rows):
        by_case_risk[(row.case_id, row.risk_code)].append(row)
    output: dict[str, Any] = {}
    for variant in VARIANTS:
        evidence_ranks: list[int | None] = []
        page_rank: dict[tuple[str, str, int], int | None] = {}
        for (case_id, risk_code), rows in by_case_risk.items():
            candidates = all_rankings[case_id][risk_code][variant]
            for row in rows:
                evidence_ranks.append(_first_rank(candidates, row.page))
                page_rank[(case_id, risk_code, row.page)] = _first_rank(candidates, row.page)
        tasks = list(by_case_risk)
        output[variant] = {
            "required_evidence_count": len(evidence_ranks), "required_page_count": len(page_rank),
            "required_recall_at": {str(k): sum(rank is not None and rank <= k for rank in evidence_ranks) / len(evidence_ranks) if evidence_ranks else 1.0 for k in TOP_K_VALUES},
            "required_page_recall_at": {str(k): sum(rank is not None and rank <= k for rank in page_rank.values()) / len(page_rank) if page_rank else 1.0 for k in TOP_K_VALUES},
            "required_completion_at": {
                str(k): sum(
                    all((_first_rank(all_rankings[case_id][risk_code][variant], row.page) or 10**9) <= k for row in rows)
                    for (case_id, risk_code), rows in by_case_risk.items()
                ) / len(tasks) if tasks else 1.0 for k in TOP_K_VALUES
            },
            "mrr": sum((1.0 / rank) if rank else 0.0 for rank in evidence_ranks) / len(evidence_ranks) if evidence_ranks else 1.0,
        }
    return output


def metrics_by_risk(
    all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]], gold_rows: list[RetrievalGoldRow],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for risk_code in sorted({row.risk_code for row in gold_rows}):
        selected = [row for row in gold_rows if row.risk_code == risk_code and row.requirement == "required"]
        for variant in VARIANTS:
            ranks = [_first_rank(all_rankings[row.case_id][risk_code][variant], row.page) for row in selected]
            record: dict[str, Any] = {
                "risk_code": risk_code, "variant": variant, "required_count": len(ranks),
                "mrr": sum((1 / rank) if rank else 0.0 for rank in ranks) / len(ranks) if ranks else 1.0,
            }
            for k in TOP_K_VALUES:
                record[f"recall_at_{k}"] = sum(rank is not None and rank <= k for rank in ranks) / len(ranks) if ranks else 1.0
            rows.append(record)
    return rows


def unique_coverage(
    all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]], gold_rows: list[RetrievalGoldRow],
) -> dict[str, Any]:
    """Measure complementary Gold coverage without inventing a new union ranking."""
    gold_keys = {(row.case_id, row.risk_code, row.page) for row in _required_rows(gold_rows)}
    output: dict[str, Any] = {}
    for depth in UNION_DEPTHS:
        covered: dict[str, set[tuple[str, str, int]]] = {variant: set() for variant in VARIANTS}
        for case_id, risk_code, page in gold_keys:
            for variant in VARIANTS:
                if page in _candidate_pages(all_rankings[case_id][risk_code][variant], depth):
                    covered[variant].add((case_id, risk_code, page))
        union12 = covered["v1"] | covered["v2"]
        union123 = union12 | covered["v21"]
        output[str(depth)] = {
            "required_gold_pages": len(gold_keys), "v1": len(covered["v1"]), "v2": len(covered["v2"]), "v21": len(covered["v21"]),
            "v1_v2_union": len(union12), "v1_v2_v21_union": len(union123),
            "v1_v2_union_recall": len(union12) / len(gold_keys) if gold_keys else 1.0,
            "v1_v2_v21_union_recall": len(union123) / len(gold_keys) if gold_keys else 1.0,
            "unique_v1": len(covered["v1"] - covered["v2"] - covered["v21"]),
            "unique_v2": len(covered["v2"] - covered["v1"] - covered["v21"]),
            "unique_v21": len(covered["v21"] - covered["v1"] - covered["v2"]),
            "marginal_v2_over_v1": len(union12 - covered["v1"]),
            "marginal_v21_over_v1_v2": len(union123 - union12),
        }
    return output


def _family_covers_text(risk_code: str, exact_text: str) -> bool:
    plan = PRODUCTION_QUERY_PLANS[risk_code]
    terms = list(plan.queries)
    for family_name in {plan.family, *plan.queries}:
        family = QUERY_FAMILY_BY_NAME.get(family_name)
        if family is not None:
            terms.extend(family.aliases)
            terms.extend(family.positive_context)
    normalized = normalize_for_match(exact_text)
    compact = normalized.replace(" ", "")
    return any(
        (term_normalized := normalize_for_match(term)) and (term_normalized in normalized or term_normalized.replace(" ", "") in compact)
        for term in terms
    )


def _table_like(text: str) -> bool:
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    return len(numbers) >= 4 or text.count("%") + text.count("％") >= 2


def _legal_boilerplate(text: str) -> bool:
    normalized = normalize_for_match(text)
    boilerplate = ("articles of association", "組織章程", "组织章程", "cayman companies law", "可贖回股份", "可赎回股份", "share repurchase")
    transaction = ("pre-ipo", "pre ipo", "投資者協議", "投资者协议", "termination", "waiver", "restoration", "終止", "终止", "豁免", "恢復", "恢复", "訴訟", "诉讼", "仲裁", "licence", "license", "許可證", "许可证")
    return any(normalize_for_match(term) in normalized for term in boilerplate) and not any(normalize_for_match(term) in normalized for term in transaction)


def build_failure_rows(
    all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]],
    gold_rows: list[RetrievalGoldRow], chunks_by_case: dict[str, list[DocumentChunk]],
) -> list[FailureRow]:
    """Classify required-page misses after rankings are frozen."""
    grouped: dict[tuple[str, str, int], list[RetrievalGoldRow]] = defaultdict(list)
    for row in _required_rows(gold_rows):
        grouped[(row.case_id, row.risk_code, row.page)].append(row)
    failures: list[FailureRow] = []
    for (case_id, risk_code, page), rows in sorted(grouped.items()):
        ranks = {variant: _first_rank(all_rankings[case_id][risk_code][variant], page) for variant in VARIANTS}
        if any(rank is not None and rank <= 20 for rank in ranks.values()):
            primary = "NONE"
        elif any(rank is not None and rank <= 100 for rank in ranks.values()):
            primary = "RANKING_ONLY_MISS"
        else:
            primary = "QUERY_COVERAGE_MISS"
        flags: list[str] = []
        exact_text = "\n".join(row.exact_text for row in rows)
        page_chunk = next((chunk for chunk in chunks_by_case.get(case_id, []) if chunk.page == page), None)
        if page_chunk is None:
            flags.append("PARSER_PAGE_MISSING")
        else:
            normalized_gold = normalize_for_match(exact_text)
            normalized_page = normalize_for_match(page_chunk.text)
            if normalized_gold and normalized_gold not in normalized_page:
                flags.append("PARSER_TEXT_MISMATCH")
                if _table_like(exact_text):
                    flags.append("TABLE_FRAGMENTATION")
        top100_pages = {item.page for variant in VARIANTS for item in all_rankings[case_id][risk_code][variant][:100]}
        if page not in top100_pages and any(abs(candidate - page) <= 2 for candidate in top100_pages):
            flags.append("NEIGHBOR_PAGE_MISS")
        if not _family_covers_text(risk_code, exact_text):
            flags.append("LEXICAL_VARIATION")
        gold_authorities = {row.source_authority for row in rows}
        top20_authorities = {item.authority_hint for variant in VARIANTS for item in all_rankings[case_id][risk_code][variant][:20]}
        if primary != "NONE" and not (gold_authorities & top20_authorities) and any(authority not in {"other", "summary", "risk_factors"} for authority in gold_authorities):
            flags.append("SOURCE_AUTHORITY_HEURISTIC_MISS")
        if risk_code in {"redemption_rights", "material_litigation_compliance"} and primary != "NONE" and any(
            _legal_boilerplate(item.text_excerpt) for variant in VARIANTS for item in all_rankings[case_id][risk_code][variant][:20]
        ):
            flags.append("BOILERPLATE_DISPLACEMENT")
        recommended: list[str] = []
        if "TABLE_FRAGMENTATION" in flags:
            recommended.extend(["table_lane", "microchunk_lane"])
        if "LEXICAL_VARIATION" in flags:
            recommended.extend(["sparse_bm25_lane", "dense_semantic_lane"])
        if "SOURCE_AUTHORITY_HEURISTIC_MISS" in flags:
            recommended.append("authority_lane")
        if "NEIGHBOR_PAGE_MISS" in flags:
            recommended.append("neighbor_or_microchunk_lane")
        if primary == "RANKING_ONLY_MISS":
            recommended.append("learning_to_rank")
        elif primary == "QUERY_COVERAGE_MISS" and not recommended:
            recommended.extend(["sparse_bm25_lane", "candidate_generation_review"])
        failures.append(FailureRow(
            case_id=case_id, risk_code=risk_code, gold_page=page,
            source_authority=sorted(gold_authorities)[0], evidence_roles=sorted({row.evidence_role for row in rows}),
            first_rank_v1=ranks["v1"], first_rank_v2=ranks["v2"], first_rank_v21=ranks["v21"],
            primary_failure=primary, secondary_flags=sorted(set(flags)), recommended_lane=sorted(set(recommended)),
        ))
    return failures


def build_hard_negatives(
    all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]], gold_rows: list[RetrievalGoldRow], *, depth: int = 50,
) -> list[HardNegativeRow]:
    """Collect high-ranked non-Gold pages for later LTR training."""
    gold_pages: dict[tuple[str, str], set[int]] = defaultdict(set)
    for row in gold_rows:
        gold_pages[(row.case_id, row.risk_code)].add(row.page)
    output: list[HardNegativeRow] = []
    for case_id, by_risk in all_rankings.items():
        for risk_code, by_variant in by_risk.items():
            positives = gold_pages[(case_id, risk_code)]
            for variant, candidates in by_variant.items():
                for item in candidates[:depth]:
                    if item.page in positives:
                        continue
                    tier = "top5" if item.rank <= 5 else ("top20" if item.rank <= 20 else "top50")
                    output.append(HardNegativeRow(
                        case_id=case_id, risk_code=risk_code, variant=variant, rank=item.rank, page=item.page,
                        relevance_score=item.relevance_score, authority_hint=item.authority_hint,
                        negative_tier=tier, text_excerpt=item.text_excerpt,
                    ))
    return output


def failure_summary(rows: list[FailureRow]) -> dict[str, Any]:
    primary = Counter(row.primary_failure for row in rows)
    secondary = Counter(flag for row in rows for flag in row.secondary_flags)
    lanes = Counter(lane for row in rows for lane in row.recommended_lane)
    by_risk: dict[str, dict[str, Any]] = {}
    for risk_code in sorted({row.risk_code for row in rows}):
        selected = [row for row in rows if row.risk_code == risk_code]
        by_risk[risk_code] = {
            "required_pages": len(selected),
            "primary_failures": dict(sorted(Counter(row.primary_failure for row in selected).items())),
            "secondary_flags": dict(sorted(Counter(flag for row in selected for flag in row.secondary_flags).items())),
            "recommended_lanes": dict(sorted(Counter(lane for row in selected for lane in row.recommended_lane).items())),
        }
    return {"primary_failures": dict(sorted(primary.items())), "secondary_flags": dict(sorted(secondary.items())), "recommended_lanes": dict(sorted(lanes.items())), "by_risk": by_risk}


def write_baseline_outputs(
    *, output_dir: Path, all_rankings: dict[str, dict[str, dict[str, list[PageCandidate]]]],
    gold_rows: list[RetrievalGoldRow], chunks_by_case: dict[str, list[DocumentChunk]], split_name: str,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = aggregate_variant_metrics(all_rankings, gold_rows)
    by_risk = metrics_by_risk(all_rankings, gold_rows)
    coverage = unique_coverage(all_rankings, gold_rows)
    failures = build_failure_rows(all_rankings, gold_rows, chunks_by_case)
    hard_negatives = build_hard_negatives(all_rankings, gold_rows)
    patterns = evidence_pattern_summary(gold_rows)

    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps({"split": split_name, "case_count": len(all_rankings), "variant_metrics": aggregate, "unique_coverage": coverage, "failure_summary": failure_summary(failures)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    risk_path = output_dir / "per_risk_metrics.csv"
    fields = ["risk_code", "variant", "required_count", "mrr"] + [f"recall_at_{k}" for k in TOP_K_VALUES]
    with risk_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(by_risk)
    coverage_path = output_dir / "unique_coverage.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failure_path = output_dir / "failure_taxonomy.csv"
    with failure_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = list(FailureRow.model_fields); writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in failures:
            payload = row.model_dump(mode="json"); payload["evidence_roles"] = "|".join(row.evidence_roles); payload["secondary_flags"] = "|".join(row.secondary_flags); payload["recommended_lane"] = "|".join(row.recommended_lane); writer.writerow(payload)
    negatives_path = output_dir / "hard_negatives.jsonl"
    with negatives_path.open("w", encoding="utf-8") as handle:
        for row in hard_negatives: handle.write(row.model_dump_json() + "\n")
    rankings_path = output_dir / "candidate_rankings.jsonl"
    with rankings_path.open("w", encoding="utf-8") as handle:
        for case_id in sorted(all_rankings):
            for risk_code in sorted(all_rankings[case_id]):
                for variant in VARIANTS:
                    for row in all_rankings[case_id][risk_code][variant]: handle.write(row.model_dump_json() + "\n")
    pattern_path = output_dir / "evidence_patterns.json"
    pattern_path.write_text(json.dumps(patterns, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = output_dir / "summary.md"
    summary_path.write_text(_summary_markdown(split_name=split_name, case_count=len(all_rankings), aggregate=aggregate, coverage=coverage, failure=failure_summary(failures), hard_negative_count=len(hard_negatives)), encoding="utf-8")
    return [metrics_path, risk_path, coverage_path, failure_path, negatives_path, rankings_path, pattern_path, summary_path]


def _summary_markdown(*, split_name: str, case_count: int, aggregate: dict[str, Any], coverage: dict[str, Any], failure: dict[str, Any], hard_negative_count: int) -> str:
    lines = [f"# Retriever V3 Baseline — {split_name}", "", f"- Cases: `{case_count}`", f"- Hard negatives: `{hard_negative_count}`", "- Production Retriever modified: `false`", "- LLM used: `false`", "", "## Existing variants", "", "| Variant | Required@3 | @5 | @20 | @50 | @100 | MRR |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for variant in VARIANTS:
        metric = aggregate[variant]; recall = metric["required_recall_at"]
        lines.append(f"| {variant} | {recall['3']:.2%} | {recall['5']:.2%} | {recall['20']:.2%} | {recall['50']:.2%} | {recall['100']:.2%} | {metric['mrr']:.4f} |")
    lines += ["", "## Complementary candidate coverage", "", "| Source depth | V1∪V2 | V1∪V2∪V2.1 | V2 marginal | V2.1 marginal |", "| --- | ---: | ---: | ---: | ---: |"]
    for depth in UNION_DEPTHS:
        row = coverage[str(depth)]
        lines.append(f"| {depth} | {row['v1_v2_union_recall']:.2%} | {row['v1_v2_v21_union_recall']:.2%} | {row['marginal_v2_over_v1']} | {row['marginal_v21_over_v1_v2']} |")
    lines += ["", "## Failure taxonomy", "", "```json", json.dumps(failure, ensure_ascii=False, indent=2), "```", "", "Union values are coverage ceilings at equal per-retriever source depth; they are not a new ranked production Retriever.", ""]
    return "\n".join(lines)
