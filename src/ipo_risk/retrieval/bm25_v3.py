"""Experimental case-local, page-level BM25 candidate lane for Retriever V3."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Iterable, Mapping, Sequence

from ipo_risk.evaluation.raw_retrieval_audit import PRODUCTION_QUERY_PLANS
from ipo_risk.retrieval.domain_aware_v2 import V2_QUERY_PLANS
from ipo_risk.retrieval.query_families import QUERY_FAMILY_BY_NAME
from ipo_risk.schemas import DocumentChunk


_CJK_RUN = re.compile(r"[\u3400-\u9fff]+")
_LATIN_NUMBER = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:[.,]\d+)*%?", re.I)
RRF_K = 60
CV_SALT = "retriever-v3-bm25-group-cv-v1|2026-08-16"


@dataclass(frozen=True)
class BM25Config:
    name: str
    tokenizer: str
    k1: float
    b: float
    top_k: int = 100

    def __post_init__(self) -> None:
        if self.tokenizer not in {"cjk_unigram", "cjk_bigram", "cjk_bigram_trigram"}:
            raise ValueError(f"unsupported tokenizer: {self.tokenizer}")
        if self.k1 <= 0 or not 0 <= self.b <= 1 or not 1 <= self.top_k <= 100:
            raise ValueError("invalid BM25 configuration")


BM25_VARIANTS = (
    BM25Config("BM25-A", "cjk_unigram", 1.2, 0.75),
    BM25Config("BM25-B", "cjk_bigram", 1.5, 0.75),
    BM25Config("BM25-C", "cjk_bigram_trigram", 1.8, 0.50),
)


@dataclass(frozen=True)
class BM25Candidate:
    page: int
    rank: int
    score: float


@dataclass(frozen=True)
class UnionCandidate:
    page: int
    rank: int
    rrf_score: float
    lane_ranks: dict[str, int | None]
    lane_presence: dict[str, bool]
    bm25_score: float | None
    multi_retriever_hit_count: int


_CANONICAL_TERMS: dict[str, tuple[str, ...]] = {
    "cash_runway": ("cash runway", "liquidity runway", "现金跑道", "現金跑道"),
    "continuous_loss": ("continuous loss", "持续亏损", "持續虧損"),
    "revenue_growth": ("revenue growth", "收入增长", "收入增長", "收益增长", "收益增長"),
    "customer_concentration": ("customer concentration", "客户集中度", "客戶集中度"),
    "supplier_concentration": ("supplier concentration", "供应商集中度", "供應商集中度"),
    "redemption_rights": ("redemption rights", "赎回权", "贖回權"),
    "material_litigation_compliance": ("material litigation compliance", "重大诉讼合规", "重大訴訟合規"),
    "precommercial_product": ("precommercial product", "pre-commercial product", "未商业化产品", "未商業化產品"),
}


def tokenize(text: str | None, tokenizer: str) -> list[str]:
    """Tokenize English/number terms and in-memory CJK character n-grams."""
    if not text:
        return []
    normalized = text.lower()
    tokens = _LATIN_NUMBER.findall(normalized)
    n_values = {"cjk_unigram": (1,), "cjk_bigram": (2,), "cjk_bigram_trigram": (2, 3)}[tokenizer]
    for run in _CJK_RUN.findall(normalized):
        for n in n_values:
            if len(run) < n:
                if n == min(n_values):
                    tokens.append(run)
                continue
            tokens.extend(run[index:index + n] for index in range(len(run) - n + 1))
    return tokens


def _expand_existing_phrase(phrase: str) -> tuple[str, ...]:
    family = QUERY_FAMILY_BY_NAME.get(phrase)
    return family.aliases if family else (phrase,)


def risk_query_phrases(risk_code: str) -> tuple[str, ...]:
    """Build only from frozen queries, existing canonical families and risk names."""
    if risk_code not in PRODUCTION_QUERY_PLANS or risk_code not in V2_QUERY_PLANS:
        raise ValueError(f"unsupported risk_code: {risk_code}")
    v1 = PRODUCTION_QUERY_PLANS[risk_code]
    v2 = V2_QUERY_PLANS[risk_code]
    source = [risk_code.replace("_", " "), *_CANONICAL_TERMS[risk_code]]
    if v1.family in QUERY_FAMILY_BY_NAME:
        source.extend(QUERY_FAMILY_BY_NAME[v1.family].aliases)
    for phrase in (*v1.queries, *v2.first_round, *v2.second_round):
        source.extend(_expand_existing_phrase(phrase))
    return tuple(dict.fromkeys(value.strip() for value in source if value and value.strip()))


def risk_query_tokens(risk_code: str, tokenizer: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for phrase in risk_query_phrases(risk_code):
        tokens.extend(tokenize(phrase, tokenizer))
    return tuple(dict.fromkeys(tokens))


def query_policy_sha256() -> str:
    payload = {risk: risk_query_phrases(risk) for risk in sorted(_CANONICAL_TERMS)}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


class PageBM25Index:
    """One IPO's physical pages; all statistics die with this object."""

    def __init__(self, chunks: Sequence[DocumentChunk], config: BM25Config) -> None:
        self.config = config
        page_text: dict[int, list[str]] = defaultdict(list)
        for chunk in chunks:
            if chunk.page is not None and chunk.text:
                page_text[chunk.page].append(chunk.text)
        self._term_frequencies: dict[int, Counter[str]] = {}
        self._lengths: dict[int, int] = {}
        document_frequency: Counter[str] = Counter()
        for page, values in sorted(page_text.items()):
            terms = tokenize("\n".join(values), config.tokenizer)
            if not terms:
                continue
            frequencies = Counter(terms)
            self._term_frequencies[page] = frequencies
            self._lengths[page] = len(terms)
            document_frequency.update(frequencies.keys())
        self._document_frequency = document_frequency
        self._document_count = len(self._term_frequencies)
        self._average_length = sum(self._lengths.values()) / self._document_count if self._document_count else 0.0

    @property
    def page_count(self) -> int:
        return self._document_count

    def search(self, risk_code: str, *, top_k: int | None = None) -> list[BM25Candidate]:
        if self._document_count == 0:
            return []
        limit = min(top_k or self.config.top_k, self.config.top_k, 100)
        query_terms = risk_query_tokens(risk_code, self.config.tokenizer)
        scores: list[tuple[int, float]] = []
        for page, frequencies in self._term_frequencies.items():
            length = self._lengths[page]
            score = 0.0
            for term in query_terms:
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                df = self._document_frequency[term]
                idf = math.log(1.0 + (self._document_count - df + 0.5) / (df + 0.5))
                norm = tf + self.config.k1 * (1.0 - self.config.b + self.config.b * length / self._average_length)
                score += idf * tf * (self.config.k1 + 1.0) / norm
            if score > 0:
                scores.append((page, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return [BM25Candidate(page, rank, score) for rank, (page, score) in enumerate(scores[:limit], 1)]


def deterministic_group_folds(case_ids: Iterable[str], *, salt: str = CV_SALT) -> dict[str, int]:
    unique = sorted(set(case_ids))
    if len(unique) != 50:
        raise ValueError(f"DEVELOPMENT_CASE_COUNT:{len(unique)} expected=50")
    ordered = sorted(unique, key=lambda case: (hashlib.sha256(f"{case}|{salt}".encode()).hexdigest(), case))
    return {case: index // 10 + 1 for index, case in enumerate(ordered)}


def bounded_rrf_union(
    rankings: Mapping[str, Sequence[tuple[int, float | None]]], *, limit: int = 100, rrf_k: int = RRF_K
) -> list[UnionCandidate]:
    if not 1 <= limit <= 100:
        raise ValueError("candidate union limit must be between 1 and 100")
    scores: dict[int, float] = defaultdict(float)
    ranks: dict[int, dict[str, int]] = defaultdict(dict)
    bm25_scores: dict[int, float] = {}
    lanes = tuple(sorted(rankings))
    for lane in lanes:
        seen: set[int] = set()
        for rank, (page, score) in enumerate(rankings[lane], 1):
            if page in seen:
                continue
            seen.add(page)
            ranks[page][lane] = rank
            scores[page] += 1.0 / (rrf_k + rank)
            if lane == "bm25" and score is not None:
                bm25_scores[page] = float(score)
    ordered = sorted(scores, key=lambda page: (-scores[page], min(ranks[page].values()), page))[:limit]
    output = []
    for final_rank, page in enumerate(ordered, 1):
        lane_ranks = {lane: ranks[page].get(lane) for lane in lanes}
        presence = {lane: lane_ranks[lane] is not None for lane in lanes}
        output.append(UnionCandidate(page, final_rank, scores[page], lane_ranks, presence,
                                     bm25_scores.get(page), sum(presence.values())))
    return output
