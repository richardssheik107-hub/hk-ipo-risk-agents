"""Evaluation candidate for deterministic domain-aware evidence retrieval.

This module is deliberately not registered as the production default.  It
combines the released keyword retriever with fixed, issuer-independent query
plans, reciprocal-rank fusion, physical-neighbour expansion and at most one
completeness-driven retry round.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


RISK_DOMAINS: dict[str, str] = {
    "cash_runway": "financial",
    "continuous_loss": "financial",
    "revenue_growth": "financial",
    "customer_concentration": "financial",
    "supplier_concentration": "financial",
    "redemption_rights": "legal",
    "material_litigation_compliance": "legal",
    "precommercial_product": "business",
}


@dataclass(frozen=True)
class V2QueryPlan:
    risk_code: str
    first_round: tuple[str, ...]
    second_round: tuple[str, ...] = ()
    completeness_signals: tuple[tuple[str, ...], ...] = ()
    neighbour_radius: int = 2
    fusion_mode: str = "sequential"


# Query phrases describe reusable evidence needs.  They never contain issuer,
# stock-code, document-id, physical-page or Evidence-id information.
V2_QUERY_PLANS: dict[str, V2QueryPlan] = {
    "cash_runway": V2QueryPlan(
        "cash_runway",
        ("现金流量表期末现金及现金等价物", "经营活动现金流"),
        ("現金及現金等價物", "經營活動所得現金淨額", "經營活動所用現金淨額"),
        (("現金及現金等價物", "现金及现金等价物"), ("經營活動", "经营活动")),
        neighbour_radius=0,
        fusion_mode="parallel",
    ),
    "continuous_loss": V2QueryPlan(
        "continuous_loss",
        ("年內虧損", "年内亏损", "期內虧損", "net loss", "loss for the year",
         "年內溢利", "年╱期內溢利", "net profit", "profit for the year"),
        ("綜合損益及其他全面收入表", "綜合全面收益表", "statement of profit or loss"),
        (("綜合損益", "綜合全面收益表", "statement of profit or loss"),),
        neighbour_radius=0,
    ),
    "revenue_growth": V2QueryPlan(
        "revenue_growth",
        ("收入", "收益", "營業收入", "营业收入", "revenue", "turnover"),
        ("尚未從產品銷售產生任何收入", "綜合損益及其他全面收入表", "綜合全面收益表"),
        (("綜合損益", "綜合全面收益表", "statement of profit or loss",
          "尚未從產品銷售產生任何收入"),),
        neighbour_radius=0,
    ),
    "customer_concentration": V2QueryPlan(
        "customer_concentration",
        ("最大客戶", "最大客户", "五大客戶", "五大客户", "largest customer", "top five customers"),
        ("尚未從產品銷售產生任何收入", "綜合損益及其他全面收入表", "綜合全面收益表", "佔總收益"),
        (("客戶", "客户", "customer"),
         ("綜合全面收益表", "綜合損益", "statement of profit or loss",
          "尚未從產品銷售產生任何收入")),
        neighbour_radius=1,
    ),
    "supplier_concentration": V2QueryPlan(
        "supplier_concentration",
        ("最大供應商", "最大供应商", "五大供應商", "五大供应商", "largest supplier", "top five suppliers"),
        ("採購總額", "采购总额", "材料成本", "服務成本"),
        (("供應商", "供应商", "supplier"),
         ("服務成本", "服务成本", "材料成本", "採購總額", "采购总额")),
    ),
    "redemption_rights": V2QueryPlan(
        "redemption_rights",
        ("redemption_rights",),
        ("首次公開發售前投資者", "特別權利", "股權架構", "重組"),
        (("投資者", "investor", "股東", "shareholder", "股權", "shareholding"),),
        neighbour_radius=0,
    ),
    "material_litigation_compliance": V2QueryPlan(
        "material_litigation_compliance",
        ("material_litigation_compliance",),
        ("訴訟及合規事宜", "所有重大方面均已遵守", "牌照", "許可證", "批文"),
        (("訴訟", "诉讼", "litigation", "仲裁", "arbitration"),
         ("合規", "合规", "compliance", "牌照", "licence", "license", "permit")),
    ),
    "precommercial_product": V2QueryPlan(
        "precommercial_product",
        ("commercialization_status", "core_product_pipeline"),
        ("主要業務", "我們是", "我們為", "收益均來自", "研究及開發"),
        (("主要業務", "主要业务", "business overview", "我們為", "我們是"),
         ("收益", "收入", "revenue", "銷售", "销售", "sales", "商業", "商业")),
        neighbour_radius=1,
        fusion_mode="parallel",
    ),
}


def query_plan_sha256() -> str:
    """Return a stable hash used to prove the holdout used a frozen plan."""
    payload = {
        key: {
            "first_round": value.first_round,
            "second_round": value.second_round,
            "completeness_signals": value.completeness_signals,
            "neighbour_radius": value.neighbour_radius,
            "fusion_mode": value.fusion_mode,
        }
        for key, value in sorted(V2_QUERY_PLANS.items())
    }
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class _Candidate:
    chunk: DocumentChunk
    score: float = 0.0
    matched_queries: set[str] | None = None
    query_rounds: set[int] | None = None
    seed_pages: set[int] | None = None
    matched_terms: set[str] | None = None

    def __post_init__(self) -> None:
        self.matched_queries = self.matched_queries or set()
        self.query_rounds = self.query_rounds or set()
        self.seed_pages = self.seed_pages or set()
        self.matched_terms = self.matched_terms or set()


class DomainAwareRetrieverV2:
    """Deterministic research candidate; not wired into the ComponentRegistry."""

    name = "domain_aware_v2_candidate"
    version = "retriever_v2_pilot_1"

    def __init__(self, *, base: KeywordDocumentRetriever | None = None, candidate_depth: int = 20) -> None:
        self._base = base or KeywordDocumentRetriever()
        self._candidate_depth = max(5, candidate_depth)

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        """Meet the existing Retriever shape without changing its Protocol."""
        if query in V2_QUERY_PLANS:
            return self.retrieve_for_risk(chunks, query, limit=limit)
        return self._base.retrieve(chunks, query, limit=limit)

    def retrieve_for_risk(
        self, chunks: list[DocumentChunk], risk_code: str, *, limit: int = 20
    ) -> list[Evidence]:
        if limit <= 0:
            return []
        try:
            plan = V2_QUERY_PLANS[risk_code]
        except KeyError as exc:
            raise ValueError(f"unsupported V2 risk_code: {risk_code}") from exc

        candidates: dict[str, _Candidate] = {}
        by_document_page = {
            (chunk.document_id, chunk.page): chunk
            for chunk in chunks
            if chunk.page is not None
        }
        self._run_round(
            chunks=chunks,
            queries=plan.first_round,
            round_number=1,
            radius=plan.neighbour_radius,
            fusion_mode=plan.fusion_mode,
            by_document_page=by_document_page,
            candidates=candidates,
        )
        first_round_top = sorted(
            candidates.values(), key=lambda item: (-item.score, item.chunk.page or 0, item.chunk.chunk_id)
        )[:5]
        first_round_text = " ".join(item.chunk.text for item in first_round_top)
        missing_groups = self._missing_signal_groups(first_round_text, plan.completeness_signals)
        second_round_triggered = bool(missing_groups and plan.second_round)
        if second_round_triggered:
            self._run_round(
                chunks=chunks,
                queries=plan.second_round,
                round_number=2,
                radius=plan.neighbour_radius,
                fusion_mode="sequential",
                by_document_page=by_document_page,
                candidates=candidates,
            )

        ranked = sorted(
            candidates.values(),
            key=lambda item: (-item.score, item.chunk.page or 0, item.chunk.chunk_id),
        )
        return [
            self._to_evidence(
                item,
                risk_code=risk_code,
                rank=rank,
                second_round_triggered=second_round_triggered,
                missing_groups=missing_groups,
            )
            for rank, item in enumerate(ranked[:limit], start=1)
        ]

    def _run_round(
        self,
        *,
        chunks: list[DocumentChunk],
        queries: tuple[str, ...],
        round_number: int,
        radius: int,
        fusion_mode: str,
        by_document_page: dict[tuple[str, int | None], DocumentChunk],
        candidates: dict[str, _Candidate],
    ) -> None:
        round_weight = 1.0 if round_number == 1 else 0.28
        query_results = [self._base.retrieve(chunks, query, limit=self._candidate_depth) for query in queries]
        ordered: list[tuple[str, Evidence]] = []
        if fusion_mode == "parallel":
            for source_rank in range(self._candidate_depth):
                for query, results in zip(queries, query_results):
                    if source_rank < len(results):
                        ordered.append((query, results[source_rank]))
        else:
            ordered = [
                (query, evidence)
                for query, results in zip(queries, query_results)
                for evidence in results
            ]

        seen_seed_chunks: set[str] = set()
        global_position = 0
        for query, evidence in ordered:
            if evidence.chunk_id is None or evidence.chunk_id in seen_seed_chunks:
                continue
            seen_seed_chunks.add(evidence.chunk_id)
            global_position += 1
            source_rank = global_position
            if evidence.page is None:
                continue
            seed = by_document_page.get((evidence.document_id, evidence.page))
            if seed is None:
                continue
            for distance in range(-radius, radius + 1):
                chunk = by_document_page.get((evidence.document_id, evidence.page + distance))
                if chunk is None:
                    continue
                candidate = candidates.setdefault(chunk.chunk_id, _Candidate(chunk=chunk))
                proximity = 1.0 if distance == 0 else (0.40 if abs(distance) == 1 else 0.20)
                contribution = round_weight * proximity / source_rank
                candidate.score = max(candidate.score, contribution)
                candidate.matched_queries.add(query)
                candidate.query_rounds.add(round_number)
                candidate.seed_pages.add(evidence.page)
                candidate.matched_terms.update(evidence.metadata.get("matched_keywords", []))

    @staticmethod
    def _missing_signal_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> list[int]:
        normalized = normalize_for_match(text)
        return [
            index
            for index, group in enumerate(groups)
            if not any(normalize_for_match(term) in normalized for term in group)
        ]

    def _to_evidence(
        self,
        item: _Candidate,
        *,
        risk_code: str,
        rank: int,
        second_round_triggered: bool,
        missing_groups: list[int],
    ) -> Evidence:
        chunk = item.chunk
        excerpt = " ".join(chunk.text.split())[:1600]
        evidence_id = str(uuid5(
            NAMESPACE_URL,
            f"{self.version}|{risk_code}|{chunk.document_id}|{chunk.chunk_id}",
        ))
        return Evidence(
            evidence_id=evidence_id,
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            page=chunk.page,
            section=chunk.section,
            text=excerpt,
            bbox=chunk.bbox,
            source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=max(0.0, min(1.0, item.score)),
            metadata={
                "retriever": self.name,
                "retriever_version": self.version,
                "risk_code": risk_code,
                "domain": RISK_DOMAINS[risk_code],
                "global_rank": rank,
                "fusion": "weighted_global_rank_fusion",
                "matched_queries": sorted(item.matched_queries),
                "query_rounds": sorted(item.query_rounds),
                "seed_pages": sorted(item.seed_pages),
                "matched_keywords": sorted(item.matched_terms),
                "neighbour_expansion": any(page != chunk.page for page in item.seed_pages),
                "second_round_triggered": second_round_triggered,
                "missing_signal_groups_after_round_1": missing_groups,
                "query_plan_sha256": query_plan_sha256(),
            },
        )
