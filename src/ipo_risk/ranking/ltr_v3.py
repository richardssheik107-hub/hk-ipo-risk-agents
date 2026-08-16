"""Leakage-controlled feature and metric utilities for experimental V3 LTR."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import math
from typing import Iterable, Mapping, Sequence


LANES = ("v1", "v2", "v21", "bm25", "table")
RISKS = (
    "cash_runway", "continuous_loss", "customer_concentration", "material_litigation_compliance",
    "precommercial_product", "redemption_rights", "revenue_growth", "supplier_concentration",
)
RRF_K = 60
MISSING_RANK = 1000.0
WEAK_NEGATIVE_SALT = "retriever-v3-ltr-weak-negative-v1|2026-08-16"
FORBIDDEN_FEATURE_PARTS = (
    "gold", "label", "annotation", "exact_text", "requirement", "evidence_role", "case_id",
    "company", "stock", "source_authority", "confidence", "primary", "supporting",
)


@dataclass(frozen=True)
class CandidateRow:
    case_id: str
    risk_code: str
    page: int
    fold: int
    gold_label: int
    judgement_status: str
    features: dict[str, float]
    rrf_rank: int


def minmax_scores(values: Mapping[int, float | None]) -> dict[int, float]:
    present = {page: float(score) for page, score in values.items() if score is not None}
    if not present:
        return {page: 0.0 for page in values}
    low, high = min(present.values()), max(present.values())
    if high == low:
        return {page: (1.0 if page in present else 0.0) for page in values}
    return {page: ((present[page] - low) / (high - low) if page in present else 0.0) for page in values}


def score_percentiles(values: Mapping[int, float | None]) -> dict[int, float]:
    present = sorted(((float(score), page) for page, score in values.items() if score is not None),
                     key=lambda item: (item[0], -item[1]))
    denominator = max(1, len(present) - 1)
    result = {page: 0.0 for page in values}
    for index, (_, page) in enumerate(present):
        result[page] = index / denominator if len(present) > 1 else 1.0
    return result


def rrf_order(lane_ranks: Mapping[int, Mapping[str, int | None]]) -> tuple[dict[int, int], dict[int, float]]:
    scores = {page: sum(1.0 / (RRF_K + rank) for rank in ranks.values() if rank is not None)
              for page, ranks in lane_ranks.items()}
    ordered = sorted(scores, key=lambda page: (-scores[page], min(
        rank for rank in lane_ranks[page].values() if rank is not None), page))
    return ({page: index for index, page in enumerate(ordered, 1)}, scores)


def build_feature_rows(
    *, case_id: str, risk_code: str, fold: int,
    lane_rankings: Mapping[str, Sequence[tuple[int, float | None, Mapping[str, float] | None]]],
    page_structures: Mapping[int, Mapping[str, float]], judgements: Mapping[int, int],
) -> list[CandidateRow]:
    """Deduplicate a pre-cap union and create features without identity or Gold-derived inputs."""
    if risk_code not in RISKS:
        raise ValueError(f"unsupported risk: {risk_code}")
    pages = sorted({page for rows in lane_rankings.values() for page, _, _ in rows})
    ranks: dict[int, dict[str, int | None]] = {page: {lane: None for lane in LANES} for page in pages}
    scores: dict[str, dict[int, float | None]] = {lane: {page: None for page in pages} for lane in LANES}
    table_metadata: dict[int, Mapping[str, float]] = {}
    for lane in LANES:
        seen: set[int] = set()
        for rank, (page, score, metadata) in enumerate(lane_rankings.get(lane, ()), 1):
            if page in seen:
                continue
            seen.add(page); ranks[page][lane] = rank; scores[lane][page] = score
            if lane == "table" and metadata:
                table_metadata[page] = metadata
    rrf_ranks, rrf_scores = rrf_order(ranks)
    bm_norm, bm_pct = minmax_scores(scores["bm25"]), score_percentiles(scores["bm25"])
    tb_norm, tb_pct = minmax_scores(scores["table"]), score_percentiles(scores["table"])
    output = []
    for page in pages:
        values: dict[str, float] = {}
        for lane in LANES:
            rank = ranks[page][lane]
            values[f"{lane}_present"] = float(rank is not None)
            values[f"{lane}_rank"] = float(rank if rank is not None else MISSING_RANK)
            values[f"{lane}_rr"] = 1.0 / (RRF_K + rank) if rank is not None else 0.0
        values["retriever_hit_count"] = sum(values[f"{lane}_present"] for lane in LANES)
        values["equal_rrf_score"] = rrf_scores[page]
        values["rrf_rank"] = float(rrf_ranks[page])
        values.update({"bm25_score_norm": bm_norm[page], "bm25_score_percentile": bm_pct[page],
                       "table_score_norm": tb_norm[page], "table_score_percentile": tb_pct[page],
                       "table_block_hit_count": float(table_metadata.get(page, {}).get("table_block_hit_count", 0.0)),
                       "table_candidate_signal": float(table_metadata.get(page, {}).get("heuristic_table_signal", 0.0))})
        structure = page_structures.get(page, {})
        values.update({"page_text_length_log": math.log1p(float(structure.get("page_text_length", 0.0))),
                       "page_numeric_density": float(structure.get("numeric_density", 0.0)),
                       "page_percentage_count_log": math.log1p(float(structure.get("percentage_count", 0.0))),
                       "page_currency_count_log": math.log1p(float(structure.get("currency_count", 0.0))),
                       "page_year_count": float(structure.get("year_count", 0.0)),
                       "page_table_signal": float(structure.get("heuristic_table_signal", 0.0))})
        values.update({f"risk_{risk}": float(risk_code == risk) for risk in RISKS})
        label = int(judgements.get(page, -1))
        output.append(CandidateRow(case_id, risk_code, page, fold, label,
                                   "JUDGED" if page in judgements else "UNJUDGED", values, rrf_ranks[page]))
    return output


FEATURE_VARIANTS = {
    "LTR-A": tuple([f"{lane}_{suffix}" for lane in LANES for suffix in ("present", "rank", "rr")]
                   + ["retriever_hit_count", "equal_rrf_score", "rrf_rank"]),
    "LTR-B": tuple([f"{lane}_{suffix}" for lane in LANES for suffix in ("present", "rank", "rr")]
                   + ["retriever_hit_count", "equal_rrf_score", "rrf_rank", "bm25_score_norm",
                      "bm25_score_percentile", "table_score_norm", "table_score_percentile",
                      "table_block_hit_count", "table_candidate_signal"]),
    "LTR-C": tuple([f"{lane}_{suffix}" for lane in LANES for suffix in ("present", "rank", "rr")]
                   + ["retriever_hit_count", "equal_rrf_score", "rrf_rank", "bm25_score_norm",
                      "bm25_score_percentile", "table_score_norm", "table_score_percentile",
                      "table_block_hit_count", "table_candidate_signal", "page_text_length_log",
                      "page_numeric_density", "page_percentage_count_log", "page_currency_count_log",
                      "page_year_count", "page_table_signal"] + [f"risk_{risk}" for risk in RISKS]),
}


def audit_feature_names(names: Iterable[str]) -> None:
    bad = [name for name in names if any(part in name.lower() for part in FORBIDDEN_FEATURE_PARTS)]
    if bad:
        raise ValueError(f"FEATURE_LEAKAGE:{bad}")


def sample_training_rows(rows: Sequence[CandidateRow], *, weak_limit: int) -> list[tuple[CandidateRow, int, str]]:
    """Keep every judged row and deterministically sample conservative UNJUDGED weak zeros."""
    if weak_limit not in {20, 40}:
        raise ValueError("weak_limit must be 20 or 40")
    positives = [row for row in rows if row.gold_label > 0]
    judged = [row for row in rows if row.gold_label >= 0]
    positive_pages = {row.page for row in positives}
    eligible = [row for row in rows if row.gold_label < 0 and all(abs(row.page - gold) > 1 for gold in positive_pages)]
    strata = (range(1, 21), range(21, 61), range(61, 10_000))
    selected: list[CandidateRow] = []
    targets = [weak_limit // 3, weak_limit // 3, weak_limit - 2 * (weak_limit // 3)]
    for positions, target in zip(strata, targets):
        pool = [row for row in eligible if row.rrf_rank in positions]
        pool.sort(key=lambda row: hashlib.sha256(
            f"{row.case_id}|{row.risk_code}|{row.page}|{WEAK_NEGATIVE_SALT}".encode()).hexdigest())
        selected.extend(pool[:target])
    if len(selected) < weak_limit:
        remaining = [row for row in eligible if row not in selected]
        remaining.sort(key=lambda row: hashlib.sha256(
            f"{row.case_id}|{row.risk_code}|{row.page}|{WEAK_NEGATIVE_SALT}|fill".encode()).hexdigest())
        selected.extend(remaining[:weak_limit - len(selected)])
    result = []
    for row in judged:
        source = {3: "GOLD_PRIMARY", 2: "GOLD_SUPPORTING", 1: "GOLD_OPTIONAL", 0: "EXPLICIT_NEGATIVE"}[row.gold_label]
        result.append((row, row.gold_label, source))
    result.extend((row, 0, "WEAK_UNJUDGED_ZERO") for row in selected)
    return sorted(result, key=lambda item: (item[0].rrf_rank, item[0].page))


def rank_scores(rows: Sequence[CandidateRow], scores: Sequence[float], *, cap: int = 100) -> dict[int, int]:
    if len(rows) != len(scores) or cap < 1 or cap > 100:
        raise ValueError("invalid ranking input")
    ordered = sorted(zip(rows, scores), key=lambda item: (-float(item[1]), item[0].rrf_rank, item[0].page))[:cap]
    return {row.page: rank for rank, (row, _) in enumerate(ordered, 1)}


def evidence_recall(evidence: Sequence[Mapping], ranks: Mapping[tuple[str, str, int], int], k: int) -> float:
    return sum((rank := ranks.get((row["case_id"], row["risk_code"], int(row["page"])))) is not None and rank <= k
               for row in evidence) / len(evidence)


def completion_at(evidence: Sequence[Mapping], ranks: Mapping[tuple[str, str, int], int], k: int) -> float:
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in evidence:
        groups[(row["case_id"], row["risk_code"])].append(int(row["page"]))
    return sum(all((rank := ranks.get((case, risk, page))) is not None and rank <= k for page in pages)
               for (case, risk), pages in groups.items()) / len(groups)


def mrr_ndcg(rows_by_query: Mapping[tuple[str, str], Sequence[CandidateRow]],
             ranks: Mapping[tuple[str, str, int], int], k_values: Sequence[int] = (5, 10, 20)) -> tuple[float, dict[int, float]]:
    reciprocal, ndcg = [], {k: [] for k in k_values}
    for (case, risk), rows in rows_by_query.items():
        relevant = {row.page: max(0, row.gold_label) for row in rows if row.gold_label > 0}
        ordered = sorted(((ranks.get((case, risk, page)), grade) for page, grade in relevant.items()),
                         key=lambda item: item[0] if item[0] is not None else 10_000)
        first = next((rank for rank, _ in ordered if rank is not None), None)
        reciprocal.append(1.0 / first if first else 0.0)
        ideal = sorted(relevant.values(), reverse=True)
        for k in k_values:
            dcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in ordered if rank is not None and rank <= k)
            idcg = sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal[:k]))
            ndcg[k].append(dcg / idcg if idcg else 0.0)
    return sum(reciprocal) / len(reciprocal), {k: sum(values) / len(values) for k, values in ndcg.items()}
