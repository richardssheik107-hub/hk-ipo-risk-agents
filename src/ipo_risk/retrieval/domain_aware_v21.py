"""Research-only deterministic Retriever V2.1 ranking candidate."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.domain_aware_v2 import RISK_DOMAINS, V2_QUERY_PLANS
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


RRF_K = 60


class Specificity(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    BROAD = "BROAD"


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    text: str
    family: str
    specificity: Specificity
    round_number: int


_FAMILY_LAYOUT: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "cash_runway": (("CASH_BALANCE", "OPERATING_CASH_FLOW"),
                     ("CASH_BALANCE", "OPERATING_CASH_FLOW", "OPERATING_CASH_FLOW")),
    "continuous_loss": (("PROFIT_LOSS",) * 9, ("INCOME_STATEMENT",) * 3),
    "revenue_growth": (("REVENUE",) * 6,
                       ("ZERO_REVENUE", "INCOME_STATEMENT", "INCOME_STATEMENT")),
    "customer_concentration": (("LARGEST_CUSTOMER",) * 2 + ("TOP_FIVE_CUSTOMER",) * 4,
                               ("ZERO_REVENUE", "INCOME_STATEMENT", "INCOME_STATEMENT", "REVENUE_DENOMINATOR")),
    "supplier_concentration": (("LARGEST_SUPPLIER",) * 2 + ("TOP_FIVE_SUPPLIER",) * 4,
                               ("PURCHASE_DENOMINATOR",) * 4),
    "redemption_rights": (("SPECIAL_RIGHTS",),
                          ("PRE_IPO_INVESTOR", "SPECIAL_RIGHTS", "CORPORATE_STRUCTURE", "CORPORATE_STRUCTURE")),
    "material_litigation_compliance": (("LITIGATION_COMPLIANCE",),
                                       ("LITIGATION_ARBITRATION", "COMPLIANCE", "LICENCE_PERMIT", "LICENCE_PERMIT", "LICENCE_PERMIT")),
    "precommercial_product": (("COMMERCIALIZATION", "CORE_PRODUCT"),
                              ("BUSINESS_OVERVIEW", "ISSUER_IDENTITY", "ISSUER_IDENTITY", "PRODUCT_REVENUE", "DEVELOPMENT_STAGE")),
}

_HIGH = {
    "CASH_BALANCE", "OPERATING_CASH_FLOW", "PROFIT_LOSS", "ZERO_REVENUE",
    "LARGEST_CUSTOMER", "TOP_FIVE_CUSTOMER", "LARGEST_SUPPLIER", "TOP_FIVE_SUPPLIER",
    "PRE_IPO_INVESTOR", "SPECIAL_RIGHTS", "LITIGATION_ARBITRATION", "LICENCE_PERMIT",
    "CORE_PRODUCT", "DEVELOPMENT_STAGE", "COMMERCIALIZATION", "PRODUCT_REVENUE",
}
_MEDIUM = {
    "INCOME_STATEMENT", "REVENUE_DENOMINATOR", "PURCHASE_DENOMINATOR",
    "LITIGATION_COMPLIANCE", "COMPLIANCE",
}

_LEGAL_BOILERPLATE = (
    "articles of association", "memorandum and articles", "cayman companies law",
    "bvi business companies act", "redeemable shares", "share repurchase",
    "capital reduction", "組織章程", "組織章程細則", "公司法", "可贖回股份",
)
_LEGAL_TRANSACTION = (
    "pre-ipo", "pre ipo", "investor agreement", "specific holder", "redemption trigger",
    "termination", "waiver", "restoration", "current status", "pending proceeding",
    "首次公開發售前投資", "投資者協議", "終止", "豁免", "恢復", "現時狀況",
    "訴訟", "仲裁", "牌照", "許可證", "批文",
)


def _specificity(family: str) -> Specificity:
    if family in _HIGH:
        return Specificity.HIGH
    if family in _MEDIUM:
        return Specificity.MEDIUM
    return Specificity.BROAD


def query_specs(risk_code: str) -> tuple[tuple[QuerySpec, ...], tuple[QuerySpec, ...]]:
    """Return the frozen issuer-independent query-family mapping."""
    plan = V2_QUERY_PLANS[risk_code]
    first_families, second_families = _FAMILY_LAYOUT[risk_code]
    if len(first_families) != len(plan.first_round) or len(second_families) != len(plan.second_round):
        raise RuntimeError(f"query-family layout mismatch: {risk_code}")
    first = tuple(QuerySpec(f"{risk_code}:r1:{i}", text, family, _specificity(family), 1)
                  for i, (text, family) in enumerate(zip(plan.first_round, first_families), 1))
    second = tuple(QuerySpec(f"{risk_code}:r2:{i}", text, family, _specificity(family), 2)
                   for i, (text, family) in enumerate(zip(plan.second_round, second_families), 1))
    return first, second


def policy_hashes() -> dict[str, str]:
    """Return stable hashes for freeze enforcement."""
    query_payload = {risk: [spec.text for group in query_specs(risk) for spec in group]
                     for risk in sorted(V2_QUERY_PLANS)}
    family_payload = {risk: [[spec.family for spec in group] for group in query_specs(risk)]
                      for risk in sorted(V2_QUERY_PLANS)}
    specificity_payload = {family: _specificity(family).value
                           for layouts in _FAMILY_LAYOUT.values() for group in layouts for family in group}
    ranking_payload = {
        "rrf_k": RRF_K,
        "tiers": ["high_direct", "v1_anchor_or_medium_direct", "other_direct", "round2_only", "neighbor_broad_boilerplate"],
        "neighbor_top3": False, "neighbor_top5_cap": 1, "round2_only_top3": False,
        "legal_boilerplate": list(_LEGAL_BOILERPLATE), "legal_transaction": list(_LEGAL_TRANSACTION),
        "business_v1_head_anchor": True,
    }
    digest = lambda value: sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {
        "query_plan_sha256": digest(query_payload),
        "query_family_mapping_sha256": digest(family_payload),
        "specificity_policy_sha256": digest(specificity_payload),
        "ranking_policy_sha256": digest(ranking_payload),
    }


@dataclass
class _Hit:
    spec: QuerySpec
    local_rank: int
    base_score: float
    matched_terms: tuple[str, ...]


@dataclass
class _Candidate:
    chunk: DocumentChunk
    hits: list[_Hit] = field(default_factory=list)
    neighbor_seed_pages: set[int] = field(default_factory=set)
    v1_rank: int | None = None

    @property
    def direct(self) -> bool:
        return bool(self.hits)

    @property
    def neighbor_only(self) -> bool:
        return bool(self.neighbor_seed_pages) and not self.hits

    @property
    def round2_only(self) -> bool:
        return bool(self.hits) and all(hit.spec.round_number == 2 for hit in self.hits)

    @property
    def specificity(self) -> Specificity:
        values = {hit.spec.specificity for hit in self.hits}
        return Specificity.HIGH if Specificity.HIGH in values else (Specificity.MEDIUM if Specificity.MEDIUM in values else Specificity.BROAD)

    @property
    def family_contributions(self) -> dict[str, float]:
        values: dict[str, float] = {}
        for hit in self.hits:
            values[hit.spec.family] = max(values.get(hit.spec.family, 0.0), 1.0 / (RRF_K + hit.local_rank))
        return values

    @property
    def family_rrf(self) -> float:
        return sum(self.family_contributions.values())

    @property
    def direct_quality(self) -> float:
        return max((hit.base_score for hit in self.hits), default=0.0)


class DomainAwareRetrieverV21:
    """Family-capped RRF candidate; deliberately absent from the registry."""

    name = "domain_aware_v21_candidate"
    version = "retriever_v21_ten_case_1"

    def __init__(self, *, base: KeywordDocumentRetriever | None = None, candidate_depth: int = 20) -> None:
        self._base = base or KeywordDocumentRetriever()
        self._candidate_depth = max(20, candidate_depth)

    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        if query in V2_QUERY_PLANS:
            return self.retrieve_for_risk(chunks, query, limit=limit)
        return self._base.retrieve(chunks, query, limit=limit)

    def retrieve_for_risk(self, chunks: list[DocumentChunk], risk_code: str, *, limit: int = 20) -> list[Evidence]:
        return self._retrieve(chunks, risk_code, limit=limit, mode="v21", neighbor=True, second_round=True)

    def retrieve_ablation(self, chunks: list[DocumentChunk], risk_code: str, *, variant: str, limit: int = 20) -> list[Evidence]:
        settings = {
            "v2_direct_only": ("union", False, False),
            "v2_direct_current_fusion": ("current_max", False, False),
            "v2_plus_neighbor": ("current_max", True, False),
            "v2_direct_family_rrf": ("family_rrf", False, False),
        }
        try:
            mode, neighbor, second = settings[variant]
        except KeyError as exc:
            raise ValueError(f"unsupported ablation: {variant}") from exc
        return self._retrieve(chunks, risk_code, limit=limit, mode=mode, neighbor=neighbor, second_round=second)

    def _retrieve(self, chunks: list[DocumentChunk], risk_code: str, *, limit: int, mode: str, neighbor: bool, second_round: bool) -> list[Evidence]:
        if limit <= 0:
            return []
        plan = V2_QUERY_PLANS[risk_code]
        first, second = query_specs(risk_code)
        by_key = {(chunk.document_id, chunk.page): chunk for chunk in chunks if chunk.page is not None}
        candidates: dict[str, _Candidate] = {}
        ordered_first = self._run_specs(chunks, first, candidates)
        v1_pages = self._compose_v1_pages(ordered_first, plan.fusion_mode)
        for rank, page in enumerate(v1_pages[:20], 1):
            chunk = by_key.get((chunks[0].document_id, page)) if chunks else None
            if chunk:
                candidates.setdefault(chunk.chunk_id, _Candidate(chunk)).v1_rank = rank
        if neighbor:
            self._add_neighbors(candidates, by_key, radius=plan.neighbour_radius)
        top_text = " ".join(item.chunk.text for item in self._rank(candidates, risk_code, mode)[:5])
        missing = self._missing_signal_groups(top_text, plan.completeness_signals)
        if second_round and missing and second:
            self._run_specs(chunks, second, candidates)
            if neighbor:
                self._add_neighbors(candidates, by_key, radius=plan.neighbour_radius)
        ranked = self._rank(candidates, risk_code, mode)
        ranked_pages = {item.chunk.page for item in ranked}
        missing_v1_pages = [page for page in v1_pages[:20] if page not in ranked_pages]
        return [
            self._to_evidence(item, risk_code, rank, missing, missing_v1_pages)
            for rank, item in enumerate(ranked[:limit], 1)
        ]

    def _run_specs(self, chunks: list[DocumentChunk], specs: tuple[QuerySpec, ...], candidates: dict[str, _Candidate]) -> list[list[Evidence]]:
        ordered: list[list[Evidence]] = []
        by_chunk = {chunk.chunk_id: chunk for chunk in chunks}
        for spec in specs:
            results = self._base.retrieve(chunks, spec.text, limit=self._candidate_depth)
            ordered.append(results)
            for rank, evidence in enumerate(results, 1):
                if evidence.chunk_id is None or evidence.page is None:
                    continue
                chunk = by_chunk.get(evidence.chunk_id)
                if chunk is None:
                    continue
                candidate = candidates.setdefault(chunk.chunk_id, _Candidate(chunk))
                candidate.hits.append(_Hit(spec, rank, evidence.relevance_score, tuple(evidence.metadata.get("matched_keywords", []))))
        return ordered

    @staticmethod
    def _compose_v1_pages(results: list[list[Evidence]], mode: str) -> list[int]:
        ordered: list[Evidence]
        if mode == "parallel":
            ordered = [items[i] for i in range(20) for items in results if i < len(items)]
        else:
            ordered = [item for items in results for item in items]
        pages: list[int] = []
        for item in ordered:
            if item.page is not None and item.page not in pages:
                pages.append(item.page)
                if len(pages) == 20:
                    break
        return pages

    @staticmethod
    def _add_neighbors(candidates: dict[str, _Candidate], by_key: dict[tuple[str, int | None], DocumentChunk], *, radius: int) -> None:
        if radius <= 0:
            return
        seeds = [item for item in candidates.values() if item.direct]
        for seed in seeds:
            if seed.chunk.page is None:
                continue
            for distance in range(-radius, radius + 1):
                if distance == 0:
                    continue
                chunk = by_key.get((seed.chunk.document_id, seed.chunk.page + distance))
                if chunk:
                    candidates.setdefault(chunk.chunk_id, _Candidate(chunk)).neighbor_seed_pages.add(seed.chunk.page)

    def _rank(self, candidates: dict[str, _Candidate], risk_code: str, mode: str) -> list[_Candidate]:
        def current_score(item: _Candidate) -> float:
            return max((1 / hit.local_rank for hit in item.hits), default=0.0)

        def union_rank(item: _Candidate) -> int:
            return min((hit.local_rank for hit in item.hits), default=9999)

        def tier(item: _Candidate) -> int:
            if mode != "v21":
                return 1 if item.direct else 5
            boilerplate = self._legal_boilerplate(item.chunk.text) if RISK_DOMAINS[risk_code] == "legal" else False
            if boilerplate or item.neighbor_only or item.specificity == Specificity.BROAD:
                return 5
            if risk_code == "precommercial_product" and item.v1_rank is not None and item.v1_rank <= 5:
                return 1
            if item.specificity == Specificity.HIGH:
                return 1
            if (item.v1_rank is not None and item.v1_rank <= 5) or item.specificity == Specificity.MEDIUM:
                return 2
            if item.direct and not item.round2_only:
                return 3
            if item.round2_only:
                return 4
            return 5

        def key(item: _Candidate) -> tuple[object, ...]:
            score = item.family_rrf if mode in {"family_rrf", "v21"} else current_score(item)
            if mode == "union":
                score = 1 / union_rank(item)
            return (tier(item), -score, -item.direct_quality, item.v1_rank or 9999,
                    item.chunk.page or 0, item.chunk.chunk_id)

        ranked = sorted(candidates.values(), key=key)
        if mode == "v21":
            ranked = self._enforce_tail_caps(ranked)
        return ranked

    @staticmethod
    def _enforce_tail_caps(ranked: list[_Candidate]) -> list[_Candidate]:
        head, tail = [], []
        neighbor_in_top5 = 0
        for item in ranked:
            position = len(head) + 1
            blocked = (position <= 3 and (item.neighbor_only or (item.round2_only and item.specificity != Specificity.HIGH)))
            if position <= 5 and item.neighbor_only and neighbor_in_top5 >= 1:
                blocked = True
            if blocked:
                tail.append(item)
                continue
            head.append(item)
            if len(head) <= 5 and item.neighbor_only:
                neighbor_in_top5 += 1
        return head + tail

    @staticmethod
    def _missing_signal_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> list[int]:
        normalized = normalize_for_match(text)
        return [i for i, group in enumerate(groups) if not any(normalize_for_match(term) in normalized for term in group)]

    @staticmethod
    def _legal_boilerplate(text: str) -> bool:
        normalized = normalize_for_match(text)
        boilerplate = any(normalize_for_match(term) in normalized for term in _LEGAL_BOILERPLATE)
        transaction = any(normalize_for_match(term) in normalized for term in _LEGAL_TRANSACTION)
        return boilerplate and not transaction

    def _to_evidence(
        self,
        item: _Candidate,
        risk_code: str,
        rank: int,
        missing: list[int],
        missing_v1_pages: list[int],
    ) -> Evidence:
        families = item.family_contributions
        evidence_id = str(uuid5(NAMESPACE_URL, f"{self.version}|{risk_code}|{item.chunk.document_id}|{item.chunk.chunk_id}"))
        query_rows = [{
            "query_id": hit.spec.query_id, "query_text": hit.spec.text, "query_family": hit.spec.family,
            "specificity": hit.spec.specificity.value, "round": hit.spec.round_number,
            "local_query_rank": hit.local_rank, "base_relevance_score": hit.base_score,
            "rrf_contribution": 1 / (RRF_K + hit.local_rank),
        } for hit in item.hits]
        return Evidence(
            evidence_id=evidence_id, document_id=item.chunk.document_id, chunk_id=item.chunk.chunk_id,
            page=item.chunk.page, section=item.chunk.section, text=" ".join(item.chunk.text.split())[:1600],
            bbox=item.chunk.bbox, source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=max(0.0, min(1.0, item.family_rrf)),
            metadata={
                "retriever": self.name, "retriever_version": self.version, "risk_code": risk_code,
                "domain": RISK_DOMAINS[risk_code], "case_id": item.chunk.document_id,
                "final_rank": rank, "candidate_tier": self._tier_label(item, risk_code),
                "query_provenance": query_rows, "family_contributions": families, "final_family_rrf": item.family_rrf,
                "query_multiplicity": len(item.hits), "query_family_multiplicity": len(families),
                "v1_rank": item.v1_rank, "is_v1_head_anchor": item.v1_rank is not None and item.v1_rank <= 5,
                "is_direct": item.direct, "is_neighbor_only": item.neighbor_only, "is_round2_only": item.round2_only,
                "is_boilerplate": self._legal_boilerplate(item.chunk.text) if RISK_DOMAINS[risk_code] == "legal" else False,
                "neighbor_seed_pages": sorted(item.neighbor_seed_pages), "missing_facets_after_round1": missing,
                "matched_terms": sorted({term for hit in item.hits for term in hit.matched_terms}),
                "v1_candidate_universe_missing_pages": missing_v1_pages,
                "policy_hashes": policy_hashes(), "rrf_k": RRF_K,
            },
        )

    def _tier_label(self, item: _Candidate, risk_code: str) -> str:
        if RISK_DOMAINS[risk_code] == "legal" and self._legal_boilerplate(item.chunk.text):
            return "TIER_5"
        if item.neighbor_only or item.specificity == Specificity.BROAD:
            return "TIER_5"
        if (risk_code == "precommercial_product" and item.v1_rank is not None and item.v1_rank <= 5) or item.specificity == Specificity.HIGH:
            return "TIER_1"
        if (item.v1_rank is not None and item.v1_rank <= 5) or item.specificity == Specificity.MEDIUM:
            return "TIER_2"
        if item.direct and not item.round2_only:
            return "TIER_3"
        return "TIER_4" if item.round2_only else "TIER_5"
