"""Experimental, in-memory table-aware candidate lane for Retriever V3."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import re
from typing import Sequence

from ipo_risk.retrieval.bm25_v3 import BM25Config, risk_query_tokens, tokenize
from ipo_risk.schemas import DocumentChunk


FROZEN_BM25 = BM25Config("TABLE-BM25-B", "cjk_bigram", 1.5, 0.75, top_k=50)
_NUMBER = re.compile(r"(?<!\w)[(\-]?\d[\d,.]*(?:%|\))?")
_YEAR = re.compile(r"(?:19|20)\d{2}")
_CURRENCY = re.compile(r"HK\$|US\$|RMB|人民币|人民幣|港元|美元|千元|百萬|million", re.I)


@dataclass(frozen=True)
class TableSignal:
    score: float
    line_count: int
    short_line_ratio: float
    numeric_line_count: int
    numeric_density: float
    percentage_count: int
    currency_count: int
    year_count: int
    is_table_like: bool


@dataclass(frozen=True)
class TableBlock:
    page: int
    block_id: str
    text: str
    signal: TableSignal


@dataclass(frozen=True)
class TableCandidate:
    page: int
    rank: int
    score: float
    table_block_hit_count: int
    heuristic_table_signal: float


@dataclass(frozen=True)
class TableVariant:
    name: str
    aggregation: str

    def __post_init__(self) -> None:
        if self.aggregation not in {"page_filter", "block_max", "block_coverage"}:
            raise ValueError(f"unsupported aggregation: {self.aggregation}")


TABLE_VARIANTS = (
    TableVariant("TABLE-A", "page_filter"),
    TableVariant("TABLE-B", "block_max"),
    TableVariant("TABLE-C", "block_coverage"),
)


def _lines(text: str | None) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines() if line.strip()]


def table_signal(text: str | None) -> TableSignal:
    """Return an explicitly heuristic table signal; this is not a visual detector."""
    lines = _lines(text)
    if not lines:
        return TableSignal(0.0, 0, 0.0, 0, 0.0, 0, 0, 0, False)
    numbers = _NUMBER.findall(text or "")
    numeric_lines = sum(bool(_NUMBER.search(line)) for line in lines)
    short_ratio = sum(len(line) <= 80 for line in lines) / len(lines)
    numeric_density = sum(len(value) for value in numbers) / max(1, len(text or ""))
    percentages = (text or "").count("%")
    currencies = len(_CURRENCY.findall(text or ""))
    years = len(set(_YEAR.findall(text or "")))
    structural = len(lines) >= 8 and short_ratio >= 0.65 and numeric_lines >= 4
    strong_numeric = numeric_lines >= 8 or percentages >= 3 or currencies >= 3 or years >= 3
    prose_penalty = 1.0 if len(lines) < 8 or short_ratio < 0.55 else 0.0
    score = (
        min(numeric_lines / 12.0, 2.0)
        + min(numeric_density * 5.0, 1.5)
        + min(percentages / 5.0, 1.0)
        + min(currencies / 5.0, 1.0)
        + min(years / 3.0, 1.0)
        + short_ratio
        - prose_penalty
    )
    return TableSignal(round(max(0.0, score), 6), len(lines), short_ratio, numeric_lines,
                       numeric_density, percentages, currencies, years, structural and strong_numeric)


def is_table_like_line(line: str) -> bool:
    """Identify a short numeric/header line without treating numeric prose as a table."""
    line = re.sub(r"\s+", " ", line).strip()
    if not line or len(line) > 120:
        return False
    numbers = _NUMBER.findall(line)
    return bool(numbers) and (len(numbers) >= 2 or len(line) <= 35 or "%" in line or bool(_CURRENCY.search(line)))


def build_table_blocks(page: int, text: str | None, *, max_chars: int = 800) -> list[TableBlock]:
    """Build temporary blocks only on heuristic table pages and map them to a physical page."""
    signal = table_signal(text)
    lines = _lines(text)
    if not signal.is_table_like or not lines:
        return []
    anchors = [index for index, line in enumerate(lines) if is_table_like_line(line)]
    if not anchors:
        return []
    ranges: list[tuple[int, int]] = []
    start = max(0, anchors[0] - 4)
    previous = anchors[0]
    for anchor in anchors[1:]:
        if anchor - previous > 7:
            ranges.append((start, min(len(lines), previous + 5)))
            start = max(0, anchor - 4)
        previous = anchor
    ranges.append((start, min(len(lines), previous + 5)))
    blocks: list[TableBlock] = []
    for range_start, range_end in ranges:
        buffer: list[str] = []
        chars = 0
        for line in lines[range_start:range_end]:
            added = len(line) + (1 if buffer else 0)
            if buffer and chars + added > max_chars:
                value = "\n".join(buffer)
                blocks.append(TableBlock(page, f"p{page}:t{len(blocks)}", value, table_signal(value)))
                buffer = buffer[-4:]
                chars = sum(len(item) + 1 for item in buffer)
            buffer.append(line)
            chars += added
        if buffer:
            value = "\n".join(buffer)
            blocks.append(TableBlock(page, f"p{page}:t{len(blocks)}", value, table_signal(value)))
    return blocks


class _BM25Documents:
    def __init__(self, documents: Sequence[tuple[str, str]]) -> None:
        self._terms: dict[str, Counter[str]] = {}
        self._lengths: dict[str, int] = {}
        self._df: Counter[str] = Counter()
        for identifier, text in documents:
            terms = tokenize(text, FROZEN_BM25.tokenizer)
            if not terms:
                continue
            counts = Counter(terms)
            self._terms[identifier] = counts
            self._lengths[identifier] = len(terms)
            self._df.update(counts.keys())
        self._count = len(self._terms)
        self._average = sum(self._lengths.values()) / self._count if self._count else 0.0

    def scores(self, risk_code: str) -> dict[str, float]:
        query = risk_query_tokens(risk_code, FROZEN_BM25.tokenizer)
        output: dict[str, float] = {}
        for identifier, counts in self._terms.items():
            length = self._lengths[identifier]
            score = 0.0
            for term in query:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                df = self._df[term]
                idf = math.log(1.0 + (self._count - df + 0.5) / (df + 0.5))
                norm = tf + FROZEN_BM25.k1 * (1.0 - FROZEN_BM25.b + FROZEN_BM25.b * length / self._average)
                score += idf * tf * (FROZEN_BM25.k1 + 1.0) / norm
            if score > 0:
                output[identifier] = score
        return output


class TableCandidateIndex:
    """One-IPO table views; no page text, blocks, or statistics are persisted."""

    def __init__(self, chunks: Sequence[DocumentChunk], variant: TableVariant) -> None:
        self.variant = variant
        page_text: dict[int, list[str]] = defaultdict(list)
        for chunk in chunks:
            if chunk.page is not None and chunk.text:
                page_text[chunk.page].append(chunk.text)
        self._page_text = {page: "\n".join(values) for page, values in page_text.items()}
        self._signals = {page: table_signal(text) for page, text in self._page_text.items()}
        self._blocks = [block for page, text in self._page_text.items() for block in build_table_blocks(page, text)]

    @property
    def table_page_count(self) -> int:
        return sum(signal.is_table_like for signal in self._signals.values())

    @property
    def table_block_count(self) -> int:
        return len(self._blocks)

    def search(self, risk_code: str, *, top_k: int = 50) -> list[TableCandidate]:
        limit = min(max(top_k, 1), 50)
        if self.variant.aggregation == "page_filter":
            documents = [(str(page), text) for page, text in self._page_text.items() if self._signals[page].is_table_like]
            raw = _BM25Documents(documents).scores(risk_code)
            page_scores = {int(identifier): score for identifier, score in raw.items()}
            hit_counts = {page: 1 for page in page_scores}
        else:
            documents = [(block.block_id, block.text) for block in self._blocks]
            raw = _BM25Documents(documents).scores(risk_code)
            by_page: dict[int, list[float]] = defaultdict(list)
            block_page = {block.block_id: block.page for block in self._blocks}
            for identifier, score in raw.items():
                by_page[block_page[identifier]].append(score)
            hit_counts = {page: len(values) for page, values in by_page.items()}
            if self.variant.aggregation == "block_max":
                page_scores = {page: max(values) for page, values in by_page.items()}
            else:
                page_scores = {page: max(values) + 0.15 * sum(sorted(values, reverse=True)[1:3])
                               for page, values in by_page.items()}
        ordered = sorted(page_scores, key=lambda page: (-page_scores[page], -self._signals[page].score, page))[:limit]
        return [TableCandidate(page, rank, page_scores[page], hit_counts[page], self._signals[page].score)
                for rank, page in enumerate(ordered, 1)]
