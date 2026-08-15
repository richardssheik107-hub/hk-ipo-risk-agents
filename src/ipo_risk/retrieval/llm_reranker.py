"""Frozen Stage-1 union and deterministic Stage-2 LLM judgment ordering."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.evaluation.raw_retrieval_audit import PRODUCTION_QUERY_PLANS, RetrievalComposition
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.retrieval.llm_reranker_prompts import PROMPT_VERSION, RISK_FACETS, instruction, task_name
from ipo_risk.retrieval.llm_reranker_schemas import CandidateEvidenceView, LLMCandidateJudgment, LLMCandidateJudgmentBundle
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


class StructuredProvider(Protocol):
    def generate_structured(self, *, task_name: str, prompt_version: str, evidence: list[Evidence], response_model: type[LLMCandidateJudgmentBundle]) -> LLMCandidateJudgmentBundle: ...


def _v1(chunks: list[DocumentChunk], risk: str, base: KeywordDocumentRetriever) -> list[Evidence]:
    plan = PRODUCTION_QUERY_PLANS[risk]
    runs = [base.retrieve(chunks, q, limit=20) for q in plan.queries]
    ordered: list[Evidence] = []
    if plan.composition is RetrievalComposition.PARALLEL_PER_QUERY_UNION:
        for i in range(20):
            ordered.extend(run[i] for run in runs if i < len(run))
    else:
        ordered = [item for run in runs for item in run]
    result: list[Evidence] = []
    pages: set[int] = set()
    for item in ordered:
        if item.page is not None and item.page not in pages:
            pages.add(item.page); result.append(item)
        if len(result) == 20: break
    return result


def _excerpt(text: str, terms: list[str], limit: int = 2400) -> tuple[str, int, int, bool]:
    compact = " ".join(text.split())
    if len(compact) <= limit: return compact, 0, len(compact), False
    normalized = normalize_for_match(compact)
    positions = [normalized.find(normalize_for_match(t)) for t in terms if t and normalized.find(normalize_for_match(t)) >= 0]
    center = min(positions) if positions else 0
    start = max(0, min(center - limit // 3, len(compact) - limit))
    return compact[start:start + limit], start, start + limit, True


def build_candidate_pool(chunks: list[DocumentChunk], risk_code: str) -> list[CandidateEvidenceView]:
    base = KeywordDocumentRetriever(); v1 = _v1(chunks, risk_code, base)
    v2 = DomainAwareRetrieverV2(base=base).retrieve_for_risk(chunks, risk_code, limit=20)
    by_page: dict[int, dict[str, object]] = {}
    for origin, values in (("v1", v1), ("v2", v2)):
        for rank, item in enumerate(values, 1):
            if item.page is None: continue
            row = by_page.setdefault(item.page, {"item": item, "origin": [], "terms": set(), "families": set()})
            row["origin"].append(origin); row[f"{origin}_rank"] = rank; row[f"{origin}_score"] = item.relevance_score
            row["terms"].update(item.metadata.get("matched_keywords", [])); row["terms"].update(item.metadata.get("matched_queries", []))
            row["families"].add(risk_code)
    priority: list[int] = []
    for item in (v1[:5] + v2[:10]):
        if item.page is not None and item.page not in priority: priority.append(item.page)
    rest = sorted((p for p in by_page if p not in priority), key=lambda p: (min(int(by_page[p].get("v1_rank", 999)), int(by_page[p].get("v2_rank", 999))), p))
    pages = (priority + rest)[:20]
    output = []
    for page in pages:
        row = by_page[page]; item = row["item"]; terms = sorted(row["terms"]); excerpt, start, end, truncated = _excerpt(item.text, terms)
        cid = str(uuid5(NAMESPACE_URL, f"llm-reranker|{risk_code}|{item.document_id}|{item.chunk_id}|{page}"))
        output.append(CandidateEvidenceView(candidate_id=cid, document_id=item.document_id or "", page=page, chunk_id=item.chunk_id or "", section=item.section, v1_rank=row.get("v1_rank"), v2_rank=row.get("v2_rank"), v1_score=row.get("v1_score"), v2_score=row.get("v2_score"), origin=sorted(row["origin"]), matched_query_terms=terms, matched_query_families=sorted(row["families"]), excerpt=excerpt, excerpt_start=start, excerpt_end=end, truncated=truncated))
    return output


_AUTH = {"primary": 0, "strong_supporting": 1, "supporting": 2, "weak": 3, "unknown": 4}
_SPEC = {"high": 0, "medium": 1, "broad": 2}
_STATUS = {"direct": 0, "indirect": 1, "none": 2, "not_applicable": 3}


def judgment_tier(j: LLMCandidateJudgment) -> int:
    if j.risk_relevance == "irrelevant" or j.evidence_role == "irrelevant": return 6
    if j.boilerplate or j.evidence_role == "boilerplate" or j.risk_relevance == "low": return 5
    if j.risk_relevance == "high" and j.source_authority in {"primary", "strong_supporting"} and j.evidence_specificity == "high": return 1
    if j.risk_relevance == "high" and j.supports_risk_assessment: return 2
    if j.risk_relevance == "medium" and j.supports_risk_assessment: return 3
    return 4


def rerank(pool: list[CandidateEvidenceView], judgments: LLMCandidateJudgmentBundle, risk_code: str) -> list[CandidateEvidenceView]:
    expected = {x.candidate_id for x in pool}; actual = {x.candidate_id for x in judgments.judgments}
    if expected != actual: raise ValueError("LLM judgment candidate coverage mismatch")
    allowed = set(RISK_FACETS[risk_code]); by_id = {x.candidate_id: x for x in judgments.judgments}
    if any(set(x.completeness_facets) - allowed for x in judgments.judgments): raise ValueError("unknown completeness facet")
    return sorted(pool, key=lambda c: (judgment_tier(by_id[c.candidate_id]), _AUTH[by_id[c.candidate_id].source_authority], _SPEC[by_id[c.candidate_id].evidence_specificity], _STATUS[by_id[c.candidate_id].current_status_relevance], -len(set(by_id[c.candidate_id].completeness_facets)), -by_id[c.candidate_id].confidence, min(c.v1_rank or 999, c.v2_rank or 999), c.page, c.chunk_id))


def judge_pool(provider: StructuredProvider, pool: list[CandidateEvidenceView], risk_code: str) -> LLMCandidateJudgmentBundle:
    payload = [Evidence(evidence_id=c.candidate_id, document_id=c.document_id, chunk_id=c.chunk_id, page=c.page, section=c.section, text=json.dumps({"instruction": instruction(risk_code), "candidate": c.model_dump()}, ensure_ascii=False), source_type=EvidenceSourceType.PROSPECTUS) for c in pool]
    return provider.generate_structured(task_name=task_name(risk_code), prompt_version=PROMPT_VERSION, evidence=payload, response_model=LLMCandidateJudgmentBundle)


def pool_sha256(pool: list[CandidateEvidenceView]) -> str:
    return sha256(json.dumps([x.model_dump(mode="json") for x in pool], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
