"""Evaluation-only raw Retriever audit against Expert Evidence pages."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.parser_preservation import EvidenceAuditStatus, audit_evidence
from ipo_risk.retrieval.keyword import normalize_for_match
from ipo_risk.retrieval.query_families import QUERY_FAMILY_BY_NAME
from ipo_risk.schemas import DocumentChunk, Evidence


TOP_K_VALUES = (1, 3, 5, 10, 20)


class _Retriever(Protocol):
    name: str

    def retrieve(
        self, chunks: list[DocumentChunk], query: str, limit: int = 3
    ) -> list[Evidence]: ...


class RetrievalComposition(StrEnum):
    """Existing production composition behavior for one risk."""

    SINGLE_QUERY = "single_query"
    SEQUENTIAL_UNIQUE_CAP = "sequential_unique_cap"
    PARALLEL_PER_QUERY_UNION = "parallel_per_query_union"


class RetrievalFailure(StrEnum):
    NONE = "NONE"
    RANKING_MISS = "RANKING_MISS"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    TOPK_CUTOFF = "TOPK_CUTOFF"
    QUERY_FAMILY_GAP = "QUERY_FAMILY_GAP"
    NO_QUERY_EXECUTED = "NO_QUERY_EXECUTED"
    EMPTY_RESULT = "EMPTY_RESULT"
    PARSER_REGRESSION = "PARSER_REGRESSION"


@dataclass(frozen=True)
class ProductionQueryPlan:
    """Queries copied from the frozen production Agents without invoking them."""

    family: str
    queries: tuple[str, ...]
    composition: RetrievalComposition


# These values reproduce the frozen v0.3 Agent requests. They are intentionally
# evaluation-local: the audit never imports or calls an Agent and never derives a
# query from Expert exact_text, issuer identity, or physical page.
PRODUCTION_QUERY_PLANS: dict[str, ProductionQueryPlan] = {
    "cash_runway": ProductionQueryPlan(
        family="cash_runway",
        queries=("现金流量表期末现金及现金等价物", "经营活动现金流"),
        composition=RetrievalComposition.PARALLEL_PER_QUERY_UNION,
    ),
    "continuous_loss": ProductionQueryPlan(
        family="continuous_loss",
        queries=(
            "年內虧損", "年内亏损", "期內虧損", "net loss",
            "loss for the year", "年內溢利", "年╱期內溢利", "net profit",
            "profit for the year",
        ),
        composition=RetrievalComposition.SEQUENTIAL_UNIQUE_CAP,
    ),
    "revenue_growth": ProductionQueryPlan(
        family="revenue",
        queries=("收入", "收益", "營業收入", "营业收入", "revenue", "turnover"),
        composition=RetrievalComposition.SEQUENTIAL_UNIQUE_CAP,
    ),
    "customer_concentration": ProductionQueryPlan(
        family="customer_concentration",
        queries=(
            "最大客戶", "最大客户", "五大客戶", "五大客户",
            "largest customer", "top five customers",
        ),
        composition=RetrievalComposition.SEQUENTIAL_UNIQUE_CAP,
    ),
    "supplier_concentration": ProductionQueryPlan(
        family="supplier_concentration",
        queries=(
            "最大供應商", "最大供应商", "五大供應商", "五大供应商",
            "largest supplier", "top five suppliers",
        ),
        composition=RetrievalComposition.SEQUENTIAL_UNIQUE_CAP,
    ),
    "redemption_rights": ProductionQueryPlan(
        family="redemption_rights",
        queries=("redemption_rights",),
        composition=RetrievalComposition.SINGLE_QUERY,
    ),
    "material_litigation_compliance": ProductionQueryPlan(
        family="material_litigation_compliance",
        queries=("material_litigation_compliance",),
        composition=RetrievalComposition.SINGLE_QUERY,
    ),
    "precommercial_product": ProductionQueryPlan(
        family="precommercial_product",
        queries=("commercialization_status", "core_product_pipeline"),
        composition=RetrievalComposition.PARALLEL_PER_QUERY_UNION,
    ),
}


class RankedRetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    page: int | None
    chunk_id: str | None
    relevance_score: float
    query_intent: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    text_excerpt: str = ""


class QueryAuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    risk_code: str
    query_family: str
    query: str
    retriever_name: str
    requested_limit: int
    returned_count: int
    results: list[RankedRetrievalResult]


class GoldRetrievalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    stock_code: str
    risk_code: str
    query_family: str
    queries: list[str]
    evidence_index: int
    gold_page: int
    gold_role: str
    gold_requirement: str
    gold_source_authority: str
    first_hit_rank: int | None = None
    hit_at_1: bool = False
    hit_at_3: bool = False
    hit_at_5: bool = False
    hit_at_10: bool = False
    hit_at_20: bool = False
    primary_failure_code: RetrievalFailure
    secondary_flags: list[RetrievalFailure] = Field(default_factory=list)
    notes: str = ""


class RiskRetrievalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_code: str
    query_family: str
    queries: list[str]
    composition: RetrievalComposition
    gold_required_pages: list[int]
    gold_primary_pages: list[int]
    gold_any_pages: list[int]
    top1_pages: list[int]
    top3_pages: list[int]
    top5_pages: list[int]
    top10_pages: list[int]
    top20_pages: list[int]
    required_hit_at_1: int
    required_hit_at_3: int
    required_hit_at_5: int
    required_hit_at_10: int
    required_hit_at_20: int
    primary_hit_at_1: int
    primary_hit_at_3: int
    primary_hit_at_5: int
    primary_hit_at_10: int
    primary_hit_at_20: int
    any_hit_at_1: bool
    any_hit_at_3: bool
    any_hit_at_5: bool
    any_hit_at_10: bool
    any_hit_at_20: bool
    required_complete_at_1: bool
    required_complete_at_3: bool
    required_complete_at_5: bool
    required_complete_at_10: bool
    required_complete_at_20: bool
    first_valid_hit_rank: int | None = None
    all_required_first_complete_k: int | None = None
    status: str


class RawRetrievalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_gold_evidence: int
    total_required_evidence: int
    total_primary_evidence: int
    unique_gold_pages: int
    evidence_recall_at: dict[int, float]
    primary_evidence_recall_at: dict[int, float]
    required_evidence_recall_at: dict[int, float]
    unique_gold_page_recall_at: dict[int, float]
    any_valid_risk_hit_rate_at: dict[int, float]
    required_evidence_completion_rate_at: dict[int, float]
    failure_taxonomy_counts: dict[str, int]


class RawRetrievalAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    stock_code: str
    company_name: str
    annotation_version: str
    annotation_sha256: str
    pdf_sha256: str
    pdf_page_count: int
    parser_name: str
    parser_chunk_count: int
    parser_error_count: int
    parser_regression: bool
    retriever_name: str
    configured_retriever_name: str
    query_executions: list[QueryAuditRecord]
    records: list[GoldRetrievalRecord]
    risks: list[RiskRetrievalSummary]
    metrics: RawRetrievalMetrics
    raw_retriever_audit_completed: bool = True
    parser_used: bool = True
    retriever_used: bool = True
    llm_used: bool = False
    agent_used: bool = False
    verifier_used: bool = False
    supervisor_used: bool = False
    human_golden_used: bool = False
    market_outcome_used: bool = False
    blind_2025_accessed: bool = False
    production_parser_changed: bool = False
    production_retriever_changed: bool = False
    query_family_changed: bool = False
    agent_changed: bool = False
    verifier_changed: bool = False
    supervisor_changed: bool = False


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _short_excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def _query_execution(
    *,
    case_id: str,
    risk_code: str,
    family: str,
    query: str,
    limit: int,
    chunks: list[DocumentChunk],
    retriever: _Retriever,
) -> QueryAuditRecord:
    evidence = retriever.retrieve(chunks, query, limit=limit)
    results = [
        RankedRetrievalResult(
            rank=rank,
            page=item.page,
            chunk_id=item.chunk_id,
            relevance_score=item.relevance_score,
            query_intent=item.metadata.get("query_intent"),
            matched_terms=list(item.metadata.get("matched_keywords", [])),
            text_excerpt=_short_excerpt(item.text),
        )
        for rank, item in enumerate(evidence, start=1)
    ]
    return QueryAuditRecord(
        case_id=case_id,
        risk_code=risk_code,
        query_family=family,
        query=query,
        retriever_name=getattr(retriever, "name", type(retriever).__name__),
        requested_limit=limit,
        returned_count=len(results),
        results=results,
    )


def _execution_map(
    executions: list[QueryAuditRecord], risk_code: str, limit: int
) -> dict[str, QueryAuditRecord]:
    return {
        item.query: item
        for item in executions
        if item.risk_code == risk_code and item.requested_limit == limit
    }


def _composed_pages(
    plan: ProductionQueryPlan,
    executions: list[QueryAuditRecord],
    risk_code: str,
    limit: int,
) -> list[int]:
    by_query = _execution_map(executions, risk_code, limit)
    if plan.composition is RetrievalComposition.PARALLEL_PER_QUERY_UNION:
        candidates: list[tuple[int, int, int]] = []
        for query_order, query in enumerate(plan.queries):
            for result in by_query[query].results:
                if result.page is not None:
                    candidates.append((result.rank, query_order, result.page))
        pages: list[int] = []
        for _, _, page in sorted(candidates):
            if page not in pages:
                pages.append(page)
        return pages

    pages = []
    for query in plan.queries:
        for result in by_query[query].results:
            if result.page is not None and result.page not in pages:
                pages.append(result.page)
                if len(pages) == limit:
                    return pages
    return pages


def _page_rank(
    plan: ProductionQueryPlan,
    executions: list[QueryAuditRecord],
    risk_code: str,
    page: int,
) -> int | None:
    if plan.composition is RetrievalComposition.PARALLEL_PER_QUERY_UNION:
        ranks = [
            result.rank
            for execution in executions
            if execution.risk_code == risk_code and execution.requested_limit == 20
            for result in execution.results
            if result.page == page
        ]
        return min(ranks) if ranks else None
    pages = _composed_pages(plan, executions, risk_code, 20)
    return pages.index(page) + 1 if page in pages else None


def _family_covers_text(plan: ProductionQueryPlan, exact_text: str) -> bool:
    """Use Gold text for diagnosis only; it never changes retrieval queries/ranks."""
    terms = list(plan.queries)
    for family_name in {plan.family, *plan.queries}:
        family = QUERY_FAMILY_BY_NAME.get(family_name)
        if family is not None:
            terms.extend(family.aliases)
    normalized = normalize_for_match(exact_text)
    compact = normalized.replace(" ", "")
    return any(
        (term_normalized := normalize_for_match(term)) in normalized
        or term_normalized.replace(" ", "") in compact
        for term in terms
        if term.strip()
    )


def _failure(
    *,
    first_rank: int | None,
    parser_failed: bool,
    query_count: int,
    result_count: int,
    family_covers_text: bool,
) -> tuple[RetrievalFailure, list[RetrievalFailure]]:
    if parser_failed:
        return RetrievalFailure.PARSER_REGRESSION, []
    if query_count == 0:
        return RetrievalFailure.NO_QUERY_EXECUTED, []
    if first_rank is not None and first_rank <= 5:
        return RetrievalFailure.NONE, []
    if first_rank is not None:
        return RetrievalFailure.RANKING_MISS, [RetrievalFailure.TOPK_CUTOFF]
    flags: list[RetrievalFailure] = []
    if result_count == 0:
        flags.append(RetrievalFailure.EMPTY_RESULT)
    if not family_covers_text:
        flags.append(RetrievalFailure.QUERY_FAMILY_GAP)
    return RetrievalFailure.RETRIEVAL_MISS, flags


def build_raw_retrieval_audit(
    *,
    bundle: ExpertAnnotationBundle,
    chunks: list[DocumentChunk],
    retriever: _Retriever,
    annotation_sha256: str,
    pdf_sha256: str,
    pdf_page_count: int,
    configured_retriever_name: str,
    parser_error_count: int = 0,
) -> RawRetrievalAudit:
    """Run only Parser-output-to-Retriever evaluation for all eight risks."""
    missing_plans = sorted({risk.risk_code for risk in bundle.risks} - PRODUCTION_QUERY_PLANS.keys())
    if missing_plans:
        raise ValueError(f"production query plan missing for risks: {missing_plans}")

    preservation = audit_evidence(bundle, chunks)
    parser_failed = {
        record.evidence_index: record.final_status is EvidenceAuditStatus.FAIL
        for record in preservation
    }
    executions: list[QueryAuditRecord] = []
    for risk in bundle.risks:
        plan = PRODUCTION_QUERY_PLANS[risk.risk_code]
        for query in plan.queries:
            for limit in TOP_K_VALUES:
                executions.append(_query_execution(
                    case_id=bundle.case_id,
                    risk_code=risk.risk_code,
                    family=plan.family,
                    query=query,
                    limit=limit,
                    chunks=chunks,
                    retriever=retriever,
                ))

    records: list[GoldRetrievalRecord] = []
    for index, gold in enumerate(bundle.evidence):
        plan = PRODUCTION_QUERY_PLANS[gold.risk_code]
        first_rank = _page_rank(plan, executions, gold.risk_code, gold.page)
        result_count = sum(
            item.returned_count
            for item in executions
            if item.risk_code == gold.risk_code and item.requested_limit == 20
        )
        failure, flags = _failure(
            first_rank=first_rank,
            parser_failed=parser_failed[index],
            query_count=len(plan.queries),
            result_count=result_count,
            family_covers_text=_family_covers_text(plan, gold.exact_text),
        )
        hits = {limit: gold.page in _composed_pages(plan, executions, gold.risk_code, limit) for limit in TOP_K_VALUES}
        records.append(GoldRetrievalRecord(
            case_id=bundle.case_id,
            stock_code=bundle.stock_code,
            risk_code=gold.risk_code,
            query_family=plan.family,
            queries=list(plan.queries),
            evidence_index=index,
            gold_page=gold.page,
            gold_role=gold.evidence_role.value,
            gold_requirement=gold.requirement.value,
            gold_source_authority=gold.source_authority.value,
            first_hit_rank=first_rank,
            hit_at_1=hits[1], hit_at_3=hits[3], hit_at_5=hits[5],
            hit_at_10=hits[10], hit_at_20=hits[20],
            primary_failure_code=failure,
            secondary_flags=flags,
            notes=("Gold exact_text was used only for post-retrieval query-family-gap diagnosis."
                   if RetrievalFailure.QUERY_FAMILY_GAP in flags else ""),
        ))

    risks: list[RiskRetrievalSummary] = []
    for risk in bundle.risks:
        plan = PRODUCTION_QUERY_PLANS[risk.risk_code]
        risk_records = [item for item in records if item.risk_code == risk.risk_code]
        required = [item for item in risk_records if item.gold_requirement == "required"]
        primary = [item for item in risk_records if item.gold_role == "primary"]
        hit_counts = {
            "required": {k: sum(getattr(item, f"hit_at_{k}") for item in required) for k in TOP_K_VALUES},
            "primary": {k: sum(getattr(item, f"hit_at_{k}") for item in primary) for k in TOP_K_VALUES},
        }
        any_hit = {k: any(getattr(item, f"hit_at_{k}") for item in risk_records) for k in TOP_K_VALUES}
        complete = {
            k: bool(required) and all(getattr(item, f"hit_at_{k}") for item in required)
            for k in TOP_K_VALUES
        }
        complete_k = next((k for k in TOP_K_VALUES if complete[k]), None)
        first_valid = min(
            (item.first_hit_rank for item in risk_records if item.first_hit_rank is not None),
            default=None,
        )
        status = "PASS" if complete[5] else ("PARTIAL" if any_hit[20] else "FAIL")
        pages_by_k = {k: _composed_pages(plan, executions, risk.risk_code, k) for k in TOP_K_VALUES}
        risks.append(RiskRetrievalSummary(
            risk_code=risk.risk_code,
            query_family=plan.family,
            queries=list(plan.queries),
            composition=plan.composition,
            gold_required_pages=sorted({item.gold_page for item in required}),
            gold_primary_pages=sorted({item.gold_page for item in primary}),
            gold_any_pages=sorted({item.gold_page for item in risk_records}),
            top1_pages=pages_by_k[1], top3_pages=pages_by_k[3], top5_pages=pages_by_k[5],
            top10_pages=pages_by_k[10], top20_pages=pages_by_k[20],
            required_hit_at_1=hit_counts["required"][1], required_hit_at_3=hit_counts["required"][3],
            required_hit_at_5=hit_counts["required"][5], required_hit_at_10=hit_counts["required"][10],
            required_hit_at_20=hit_counts["required"][20],
            primary_hit_at_1=hit_counts["primary"][1], primary_hit_at_3=hit_counts["primary"][3],
            primary_hit_at_5=hit_counts["primary"][5], primary_hit_at_10=hit_counts["primary"][10],
            primary_hit_at_20=hit_counts["primary"][20],
            any_hit_at_1=any_hit[1], any_hit_at_3=any_hit[3], any_hit_at_5=any_hit[5],
            any_hit_at_10=any_hit[10], any_hit_at_20=any_hit[20],
            required_complete_at_1=complete[1], required_complete_at_3=complete[3],
            required_complete_at_5=complete[5], required_complete_at_10=complete[10],
            required_complete_at_20=complete[20],
            first_valid_hit_rank=first_valid,
            all_required_first_complete_k=complete_k,
            status=status,
        ))

    required_records = [item for item in records if item.gold_requirement == "required"]
    primary_records = [item for item in records if item.gold_role == "primary"]
    unique_pages = sorted({item.gold_page for item in records})
    unique_hits = {
        k: {
            item.gold_page
            for item in records
            if getattr(item, f"hit_at_{k}")
        }
        for k in TOP_K_VALUES
    }
    taxonomy = Counter({item.value: 0 for item in RetrievalFailure})
    taxonomy.update(item.primary_failure_code.value for item in records)
    taxonomy.update(flag.value for item in records for flag in item.secondary_flags)
    metrics = RawRetrievalMetrics(
        total_gold_evidence=len(records),
        total_required_evidence=len(required_records),
        total_primary_evidence=len(primary_records),
        unique_gold_pages=len(unique_pages),
        evidence_recall_at={k: _rate(sum(getattr(item, f"hit_at_{k}") for item in records), len(records)) for k in TOP_K_VALUES},
        primary_evidence_recall_at={k: _rate(sum(getattr(item, f"hit_at_{k}") for item in primary_records), len(primary_records)) for k in TOP_K_VALUES},
        required_evidence_recall_at={k: _rate(sum(getattr(item, f"hit_at_{k}") for item in required_records), len(required_records)) for k in TOP_K_VALUES},
        unique_gold_page_recall_at={k: _rate(len(unique_hits[k]), len(unique_pages)) for k in TOP_K_VALUES},
        any_valid_risk_hit_rate_at={k: _rate(sum(getattr(item, f"any_hit_at_{k}") for item in risks), len(risks)) for k in TOP_K_VALUES},
        required_evidence_completion_rate_at={k: _rate(sum(getattr(item, f"required_complete_at_{k}") for item in risks), len(risks)) for k in TOP_K_VALUES},
        failure_taxonomy_counts=dict(sorted(taxonomy.items())),
    )
    return RawRetrievalAudit(
        case_id=bundle.case_id,
        stock_code=bundle.stock_code,
        company_name=bundle.company_name,
        annotation_version=bundle.annotation_version,
        annotation_sha256=annotation_sha256,
        pdf_sha256=pdf_sha256,
        pdf_page_count=pdf_page_count,
        parser_name="PyMuPDFDocumentParser",
        parser_chunk_count=len(chunks),
        parser_error_count=parser_error_count,
        parser_regression=any(parser_failed.values()),
        retriever_name=type(retriever).__name__,
        configured_retriever_name=configured_retriever_name,
        query_executions=executions,
        records=records,
        risks=risks,
        metrics=metrics,
    )


def write_raw_retrieval_outputs(
    audit: RawRetrievalAudit, output_dir: Path
) -> tuple[Path, Path, Path, Path]:
    """Write ignored detailed artifacts with only short retrieval excerpts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "raw_retrieval_audit.json"
    csv_path = output_dir / "raw_retrieval_audit.csv"
    summary_path = output_dir / "raw_retrieval_summary.md"
    top_results_path = output_dir / "top_results_by_risk.json"
    json_path.write_text(audit.model_dump_json(indent=2) + "\n", encoding="utf-8")

    fields = [
        "case_id", "stock_code", "risk_code", "query_family", "query",
        "gold_page", "gold_role", "gold_requirement", "gold_source_authority",
        "first_hit_rank", "hit_at_1", "hit_at_3", "hit_at_5", "hit_at_10",
        "hit_at_20", "failure_code", "secondary_flags",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in audit.records:
            writer.writerow({
                "case_id": record.case_id,
                "stock_code": record.stock_code,
                "risk_code": record.risk_code,
                "query_family": record.query_family,
                "query": " | ".join(record.queries),
                "gold_page": record.gold_page,
                "gold_role": record.gold_role,
                "gold_requirement": record.gold_requirement,
                "gold_source_authority": record.gold_source_authority,
                "first_hit_rank": record.first_hit_rank,
                "hit_at_1": record.hit_at_1,
                "hit_at_3": record.hit_at_3,
                "hit_at_5": record.hit_at_5,
                "hit_at_10": record.hit_at_10,
                "hit_at_20": record.hit_at_20,
                "failure_code": record.primary_failure_code.value,
                "secondary_flags": "|".join(flag.value for flag in record.secondary_flags),
            })

    metrics = audit.metrics
    lines = [
        f"# Raw Retriever Audit — {audit.case_id}", "",
        f"- Retriever: `{audit.retriever_name}` (`{audit.configured_retriever_name}`)",
        f"- Gold / required / primary: `{metrics.total_gold_evidence} / {metrics.total_required_evidence} / {metrics.total_primary_evidence}`",
        f"- Unique Gold pages: `{metrics.unique_gold_pages}`", "",
        "| Metric | @1 | @3 | @5 | @10 | @20 |", "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, values in (
        ("Evidence recall", metrics.evidence_recall_at),
        ("Primary recall", metrics.primary_evidence_recall_at),
        ("Required recall", metrics.required_evidence_recall_at),
        ("Unique-page recall", metrics.unique_gold_page_recall_at),
        ("Any-valid risk hit", metrics.any_valid_risk_hit_rate_at),
        ("Required completion", metrics.required_evidence_completion_rate_at),
    ):
        lines.append(f"| {label} | " + " | ".join(f"{values[k]:.2%}" for k in TOP_K_VALUES) + " |")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    top_results_path.write_text(
        "[\n" + ",\n".join(
            execution.model_dump_json(indent=2)
            for execution in audit.query_executions
            if execution.requested_limit == 20
        ) + "\n]\n",
        encoding="utf-8",
    )
    return json_path, csv_path, summary_path, top_results_path
