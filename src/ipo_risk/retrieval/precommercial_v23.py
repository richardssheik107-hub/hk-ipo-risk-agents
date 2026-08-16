"""Research-only V2.3 two-route candidate generation for precommercial risk.

The experiment separates commercialisation/lifecycle evidence (Route A) from
revenue/commercial-activity counterevidence (Route B), then builds a hard-capped
candidate union.  It is deliberately absent from the production registry and
does not alter V2.1 scoring or any public schema.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.schemas import DocumentChunk, Evidence, EvidenceSourceType


class EvidenceIntent(StrEnum):
    NOT_COMMERCIALISED = "NOT_COMMERCIALISED"
    PRODUCT_REVENUE_EXISTS = "PRODUCT_REVENUE_EXISTS"
    SERVICE_REVENUE_EXISTS = "SERVICE_REVENUE_EXISTS"
    REVENUE_NATURE = "REVENUE_NATURE"
    PRODUCT_LIFECYCLE = "PRODUCT_LIFECYCLE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class VariantPolicy:
    name: str
    head_quota: tuple[int, int, int]  # base, route_a, route_b; sums to 20
    total_quota: tuple[int, int, int]  # sums to 50


V23_VARIANTS = {
    "v23_a": VariantPolicy("v23_a_balanced", (14, 3, 3), (34, 8, 8)),
    "v23_b": VariantPolicy("v23_b_revenue", (12, 3, 5), (30, 8, 12)),
    "v23_c": VariantPolicy("v23_c_diverse", (10, 4, 6), (26, 10, 14)),
}


@dataclass
class CandidateUniverse:
    merged: list[Evidence]
    base: list[Evidence]
    route_a: list[Evidence]
    route_b: list[Evidence]


_REVENUE = ("收入", "收益", "營業額", "营业额", "revenue", "turnover", "income")
_PRODUCT = ("產品", "产品", "商品", "貨品", "货品", "軟件", "软件", "車輛", "车辆", "product", "goods", "software", "vehicle")
_SERVICE = ("服務", "服务", "服務費", "服务费", "收費", "收费", "service", "fee")
_SALE = ("銷售", "销售", "出售", "投放市場", "投放市场", "sale", "sales", "sold", "marketed")
_ACTIVITY = ("提供", "從事", "从事", "生產", "生产", "運營", "运营", "業務", "业务", "provide", "engaged", "operate", "manufacture")
_LIFECYCLE = ("研發", "研发", "開發", "开发", "臨床", "临床", "註冊", "注册", "批准", "上市", "推出", "商業化", "商业化", "商業銷售", "商业销售", "development", "clinical", "registration", "approval", "launch", "commercial")
_STATUS = ("尚未", "未有", "仍", "目前", "等待", "待", "預期", "预期", "已", "獲准", "获准", "not yet", "have not", "currently", "pending", "expected", "approved")
_CORE_PRODUCT = ("核心產品", "核心产品", "候選藥物", "候选药物", "候選產品", "候选产品", "core product", "drug candidate", "product candidate")
_NEGATIVE_COMMERCIAL = ("尚未商業化", "尚未商业化", "未獲准商業銷售", "未获准商业销售", "未產生任何產品銷售", "未产生任何产品销售", "沒有產品銷售收入", "没有产品销售收入", "not yet commercial", "not approved for commercial sale", "have not generated revenue from product sales", "no product sales revenue")


def _has(text: str, terms: tuple[str, ...]) -> bool:
    return any(normalize_for_match(term) in text for term in terms)


def _classification_has(text: str, terms: tuple[str, ...]) -> bool:
    """Match fact labels despite per-character PDF spacing; retrieval is unchanged."""
    compact = "".join(char for char in text if not char.isspace())
    return any("".join(char for char in normalize_for_match(term) if not char.isspace()) in compact for term in terms)


def classify_evidence_intent(text: str, source_authority: str, applicable: bool) -> EvidenceIntent:
    """Assign one human-readable primary fact intent for benchmark analysis."""
    normalized = normalize_for_match(text)
    has = lambda terms: _classification_has(normalized, terms)
    if source_authority == "other":
        return EvidenceIntent.OTHER
    if applicable:
        if has(_NEGATIVE_COMMERCIAL) or (has(_REVENUE) and has(("未有", "沒有", "没有", "尚未", "no "))):
            return EvidenceIntent.NOT_COMMERCIALISED
        return EvidenceIntent.PRODUCT_LIFECYCLE
    if has(_LIFECYCLE) and (has((*_CORE_PRODUCT, *_PRODUCT, "註冊申請", "注册申请", "臨床試驗", "临床试验"))) and not has(_REVENUE):
        return EvidenceIntent.PRODUCT_LIFECYCLE
    if has(_PRODUCT) and has((*_SALE, *_REVENUE, "生產及貿易", "生产及贸易")):
        return EvidenceIntent.PRODUCT_REVENUE_EXISTS
    if has(_SERVICE) and has((*_REVENUE, "收取", "產生收入", "产生收入")):
        return EvidenceIntent.SERVICE_REVENUE_EXISTS
    if source_authority in {"accountants_report", "financial_information"} and (
        has((*_REVENUE, "經營分部", "经营分部")) or len(re.findall(r"\d", text)) >= 8
    ):
        return EvidenceIntent.REVENUE_NATURE
    if has(_SERVICE) and (has(_ACTIVITY) or source_authority == "business_section"):
        return EvidenceIntent.SERVICE_REVENUE_EXISTS
    if has(("工程項目", "工程项目", "已完成多個", "已完成多个")) and source_authority == "business_section":
        return EvidenceIntent.SERVICE_REVENUE_EXISTS
    if has(("商業化階段", "商业化阶段")) and len(re.findall(r"\d", text)) >= 4:
        return EvidenceIntent.REVENUE_NATURE
    if has(_REVENUE):
        return EvidenceIntent.REVENUE_NATURE
    return EvidenceIntent.OTHER


def _looks_like_financial_table(text: str) -> bool:
    digits = len(re.findall(r"\d", text))
    columns = len(re.findall(r"(?:19|20)\d{2}|\d{1,2}月\d{1,2}日", text))
    normalized = normalize_for_match(text)
    units = _has(normalized, ("人民幣千元", "人民币千元", "港幣千元", "港币千元", "rmb'000", "hk$'000", "usd'000"))
    return digits >= 30 and (columns >= 2 or units)


def _structured_revenue_row(chunk: DocumentChunk) -> bool:
    tables = chunk.metadata.get("tables") if chunk.metadata else None
    if not isinstance(tables, list):
        return False
    labels = tuple(normalize_for_match(term).replace(" ", "") for term in _REVENUE)
    for table in tables:
        if not isinstance(table, dict):
            continue
        for row in table.get("rows") or []:
            label = normalize_for_match(str(row.get("label", ""))).replace(" ", "")
            if label and any(label.startswith(term) for term in labels):
                return True
    return False


class PrecommercialCandidateRetrieverV23:
    """Generate two raw routes and merge them under a fixed 50-page policy."""

    name = "precommercial_candidate_v23_experiment"
    version = "precommercial_candidate_v23_two_route"

    def __init__(self, *, route_base: Any | None = None, baseline: Any | None = None, raw_route_limit: int = 50) -> None:
        self._route_base = route_base or KeywordDocumentRetriever()
        self._baseline = baseline or DomainAwareRetrieverV21()
        self._raw_route_limit = max(20, min(50, raw_route_limit))

    def retrieve_for_risk(
        self,
        chunks: list[DocumentChunk],
        risk_code: str,
        *,
        limit: int = 50,
        variant: str = "v23_b",
        baseline_chunks: list[DocumentChunk] | None = None,
    ) -> list[Evidence]:
        return self.candidate_universe(
            chunks, risk_code, limit=limit, variant=variant, baseline_chunks=baseline_chunks,
        ).merged

    def candidate_universe(
        self,
        chunks: list[DocumentChunk],
        risk_code: str,
        *,
        limit: int = 50,
        variant: str = "v23_b",
        baseline_chunks: list[DocumentChunk] | None = None,
    ) -> CandidateUniverse:
        if limit <= 0:
            return CandidateUniverse([], [], [], [])
        base = self._baseline.retrieve_for_risk(baseline_chunks or chunks, risk_code, limit=50)
        if risk_code != "precommercial_product":
            return CandidateUniverse(base[:limit], base, [], [])
        try:
            policy = V23_VARIANTS[variant]
        except KeyError as exc:
            raise ValueError(f"unsupported V2.3 variant: {variant}") from exc
        route_a = self._route_a(chunks)
        route_b = self._route_b(chunks)
        merged = bounded_candidate_union(base, route_a, route_b, policy=policy, limit=min(50, limit))
        return CandidateUniverse(merged, base, route_a, route_b)

    def _route_a(self, chunks: list[DocumentChunk]) -> list[Evidence]:
        families: dict[str, list[Evidence]] = {
            "commercialisation_status": self._tag_hits(
                self._route_base.retrieve(chunks, "commercialization_status", limit=self._raw_route_limit),
                "route_a", "commercialisation_status",
            ),
            "product_pipeline": self._tag_hits(
                self._route_base.retrieve(chunks, "core_product_pipeline", limit=self._raw_route_limit),
                "route_a", "product_pipeline",
            ),
            "lifecycle_state": [],
        }
        scored: list[tuple[float, int, DocumentChunk]] = []
        for chunk in chunks:
            text = normalize_for_match(chunk.text)
            negative = _has(text, _NEGATIVE_COMMERCIAL)
            lifecycle = _has(text, _LIFECYCLE)
            product = _has(text, (*_CORE_PRODUCT, *_PRODUCT))
            status = _has(text, _STATUS)
            if not negative and not (lifecycle and product):
                continue
            score = 4.0 * negative + 2.0 * lifecycle + 1.5 * product + 1.0 * status
            scored.append((score, chunk.page, chunk))
        families["lifecycle_state"] = [
            self._from_chunk(chunk, "route_a", "lifecycle_state", score)
            for score, _, chunk in sorted(scored, key=lambda item: (-item[0], item[1]))[:self._raw_route_limit]
        ]
        return _family_round_robin(families, self._raw_route_limit)

    def _route_b(self, chunks: list[DocumentChunk]) -> list[Evidence]:
        families: dict[str, list[Evidence]] = {
            "revenue_family": self._tag_hits(
                self._route_base.retrieve(chunks, "revenue", limit=self._raw_route_limit),
                "route_b", "revenue_family",
            ),
            "structured_revenue": [],
            "commercial_activity": [],
        }
        structured: list[tuple[float, int, DocumentChunk]] = []
        activity: list[tuple[float, int, DocumentChunk]] = []
        for chunk in chunks:
            text = normalize_for_match(chunk.text)
            revenue = _has(text, _REVENUE)
            table = _looks_like_financial_table(chunk.text)
            structured_row = _structured_revenue_row(chunk)
            product_sale = _has(text, _PRODUCT) and _has(text, _SALE)
            service_activity = _has(text, _SERVICE) and _has(text, _ACTIVITY)
            commercial_revenue = revenue and (product_sale or _has(text, _SERVICE))
            if structured_row or (revenue and table):
                score = 5.0 * structured_row + 3.0 * table + 2.0 * revenue
                structured.append((score, chunk.page, chunk))
            if commercial_revenue or product_sale or service_activity:
                score = 3.0 * commercial_revenue + 2.0 * product_sale + 1.5 * service_activity + 1.0 * revenue
                activity.append((score, chunk.page, chunk))
        families["structured_revenue"] = [
            self._from_chunk(chunk, "route_b", "structured_revenue", score)
            for score, _, chunk in sorted(structured, key=lambda item: (-item[0], item[1]))[:self._raw_route_limit]
        ]
        families["commercial_activity"] = [
            self._from_chunk(chunk, "route_b", "commercial_activity", score)
            for score, _, chunk in sorted(activity, key=lambda item: (-item[0], item[1]))[:self._raw_route_limit]
        ]
        return _family_round_robin(families, self._raw_route_limit)

    def _tag_hits(self, hits: list[Evidence], route: str, family: str) -> list[Evidence]:
        return [item.model_copy(update={"metadata": {
            **item.metadata, "retriever": self.name, "retriever_version": self.version,
            "candidate_route": route, "query_family": family, "candidate_generation_only": True,
        }}) for item in hits]

    def _from_chunk(self, chunk: DocumentChunk, route: str, family: str, score: float) -> Evidence:
        evidence_id = str(uuid5(NAMESPACE_URL, f"{self.version}|{chunk.document_id}|{chunk.page}|{route}|{family}"))
        return Evidence(
            evidence_id=evidence_id, document_id=chunk.document_id, chunk_id=chunk.chunk_id,
            page=chunk.page, section=chunk.section, text=" ".join(chunk.text.split())[:1600],
            bbox=chunk.bbox, source_type=EvidenceSourceType.PROSPECTUS,
            relevance_score=max(0.0, min(1.0, score / 10.0)),
            metadata={
                "retriever": self.name, "retriever_version": self.version,
                "risk_code": "precommercial_product", "candidate_route": route,
                "query_family": family, "feature_score": score,
                "candidate_generation_only": True,
            },
        )


def _family_round_robin(families: dict[str, list[Evidence]], limit: int) -> list[Evidence]:
    queues = {name: deque(items) for name, items in families.items()}
    output: list[Evidence] = []
    seen: set[int] = set()
    while len(output) < limit and any(queues.values()):
        for name in families:
            queue = queues[name]
            while queue:
                item = queue.popleft()
                if item.page is not None and item.page not in seen:
                    seen.add(item.page); output.append(item)
                    break
            if len(output) >= limit:
                break
    return output


def bounded_candidate_union(
    base: list[Evidence], route_a: list[Evidence], route_b: list[Evidence],
    *, policy: VariantPolicy, limit: int = 50,
) -> list[Evidence]:
    """Quota-spread three sources without changing any source's own ranking."""
    sources = {"base": base, "route_a": route_a, "route_b": route_b}
    offsets = {name: 0 for name in sources}
    seen: set[int] = set()
    output: list[Evidence] = []

    def take_stage(quotas: tuple[int, int, int], stage_limit: int) -> None:
        names = ("base", "route_a", "route_b")
        used = {name: 0 for name in names}
        while len(output) < stage_limit and any(used[name] < quotas[i] for i, name in enumerate(names)):
            position = sum(used.values()) + 1
            eligible = [
                (quotas[i] * position / max(1, sum(quotas)) - used[name], -i, name)
                for i, name in enumerate(names) if used[name] < quotas[i]
            ]
            _, _, name = max(eligible)
            source = sources[name]
            added = False
            while offsets[name] < len(source):
                item = source[offsets[name]]; offsets[name] += 1
                if item.page is None or item.page in seen:
                    continue
                seen.add(item.page); output.append(item); used[name] += 1; added = True
                break
            if not added:
                used[name] = quotas[names.index(name)]

    head = tuple(min(value, limit) for value in policy.head_quota)
    take_stage(head, min(20, limit))
    tail_quota = tuple(max(0, total - head_value) for total, head_value in zip(policy.total_quota, policy.head_quota))
    take_stage(tail_quota, limit)
    # If dedup or a sparse route leaves quota unused, fill deterministically;
    # base is first so existing candidates receive the preservation fallback.
    for name in ("base", "route_b", "route_a"):
        for item in sources[name][offsets[name]:]:
            if len(output) >= limit:
                break
            if item.page is None or item.page in seen:
                continue
            seen.add(item.page); output.append(item)
    return output[:limit]
