"""Lightweight, dependency-free reconstruction of borderless financial tables.

The default ``page.get_text("text")`` flattens a financial statement into
newline-separated tokens, destroying the column structure (three fiscal-year
columns collapse onto one line).  This module rebuilds the row/column grid from
**word coordinates only** — the primitives PyMuPDF already exposes via
``page.get_text("words")`` — so downstream extraction can map each value to its
period.

Design notes
------------
* The single public entry point, :func:`reconstruct_page_tables`, takes plain
  word tuples (``x0, y0, x1, y1, text``) rather than a ``fitz`` object, so the
  same algorithm can be fed by a pdfplumber adapter (``page.extract_words``)
  without touching the logic.
* It reuses the extractor's own numeric/year token grammar
  (``_ROW_AMOUNT_TOKEN_RE`` / ``_YEAR_RE``) so a token this module calls a
  "value" is exactly what ``V03FinancialFactExtractor._normalize_amount`` will
  later accept — no grammar drift between parser and extractor.
* Value columns are anchored on the fiscal-year header cells (``2021年`` …),
  which cleanly separates real value columns from note-reference columns
  (e.g. ``18(b)``) that would otherwise pollute the grid.
* Output is JSON-primitive only (str / int / float / list / dict) so it can ride
  in ``DocumentChunk.metadata["tables"]`` and survive repository round-trips.
"""

from __future__ import annotations

from statistics import median
from typing import Sequence

from ipo_risk.extraction.financial import _ROW_AMOUNT_TOKEN_RE, _YEAR_RE

# --- Tunable geometry (points). Exposed as module constants for testing. ---
Y_TOL = 3.0          # words within this vertical distance share a row baseline
X_TOL = 12.0         # x-centres within this distance belong to one column
COL_SNAP = 16.0      # a value token snaps to a year anchor within this distance
LABEL_MARGIN = 18.0  # label tokens must sit this far left of the first value col
SPACE_GAP = 3.0      # horizontal gap above which a space is inserted in a label
HEADER_SPAN = 130.0  # how far above the first data row to scan for period header
MIN_VALUE_COLS = 2   # a data row needs at least this many aligned value cells
MIN_YEAR_ANCHORS = 2 # a table needs at least this many distinct year columns


def _x_center(word: Sequence) -> float:
    return (float(word[0]) + float(word[2])) / 2.0


def _is_value_token(text: str) -> bool:
    """A pure numeric/amount cell (comma groups, parenthesised negatives, dash)."""
    text = text.strip()
    if not text:
        return False
    if _YEAR_RE.fullmatch(text):  # a year header is not a value cell
        return False
    return bool(_ROW_AMOUNT_TOKEN_RE.fullmatch(text))


def _cluster_rows(words: Sequence[Sequence]) -> list[list[Sequence]]:
    """Group words into visual rows by their top y coordinate."""
    rows: list[list[Sequence]] = []
    for word in sorted(words, key=lambda w: (float(w[1]), float(w[0]))):
        if rows and abs(float(word[1]) - float(rows[-1][0][1])) <= Y_TOL:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda w: float(w[0]))
    return rows


def _cluster_1d(values: Sequence[float], tol: float) -> list[float]:
    """Merge sorted 1-D positions into cluster centres."""
    centres: list[float] = []
    bucket: list[float] = []
    for value in sorted(values):
        if bucket and value - bucket[-1] > tol:
            centres.append(sum(bucket) / len(bucket))
            bucket = []
        bucket.append(value)
    if bucket:
        centres.append(sum(bucket) / len(bucket))
    return centres


def _year_anchors(rows: Sequence[Sequence]) -> list[float]:
    """x-centres of fiscal-year header cells define the value columns."""
    xs = [
        _x_center(word)
        for row in rows
        for word in row
        if _YEAR_RE.fullmatch(str(word[4]).strip())
    ]
    return _cluster_1d(xs, X_TOL)


def _row_text(tokens: Sequence[Sequence]) -> str:
    """Join tokens in reading order, inserting a space only across real gaps."""
    parts: list[str] = []
    prev_x1: float | None = None
    for word in sorted(tokens, key=lambda w: float(w[0])):
        text = str(word[4])
        if prev_x1 is not None and float(word[0]) - prev_x1 > SPACE_GAP:
            parts.append(" ")
        parts.append(text)
        prev_x1 = float(word[2])
    return "".join(parts).strip()


def _assemble_row(row: Sequence[Sequence], anchors: Sequence[float]) -> dict | None:
    """Split one visual row into a label and anchor-aligned value cells."""
    value_words: list[tuple[float, Sequence]] = []
    for word in row:
        if _is_value_token(str(word[4])):
            value_words.append((_x_center(word), word))

    cells: list[str] = []
    used_ids: set[int] = set()
    for anchor in anchors:
        best = None
        best_dist = COL_SNAP
        for xc, word in value_words:
            if id(word) in used_ids:
                continue
            dist = abs(xc - anchor)
            if dist <= best_dist:
                best_dist = dist
                best = word
        if best is not None:
            used_ids.add(id(best))
            cells.append(str(best[4]).strip())
        else:
            cells.append("")

    if sum(1 for cell in cells if cell) < MIN_VALUE_COLS:
        return None

    first_anchor = min(anchors)
    label_words = [
        word
        for word in row
        if id(word) not in used_ids and _x_center(word) < first_anchor - LABEL_MARGIN
    ]
    label = _row_text(label_words)
    return {"label": label, "cells": cells, "y": round(float(row[0][1]), 1)}


def reconstruct_page_tables(words: Sequence[Sequence]) -> list[dict]:
    """Reconstruct financial tables from a page's word tuples.

    Parameters
    ----------
    words:
        Sequence of ``(x0, y0, x1, y1, text, ...)`` tuples, e.g. the output of
        ``fitz.Page.get_text("words")`` (extra trailing fields are ignored).

    Returns
    -------
    A list of JSON-primitive table dicts.  Empty when the page shows no
    fiscal-year-anchored numeric grid.
    """
    words = [w for w in words if str(w[4]).strip()]
    if not words:
        return []
    rows = _cluster_rows(words)
    anchors = _year_anchors(rows)
    if len(anchors) < MIN_YEAR_ANCHORS:
        return []

    # Classify each visual row as a value-bearing data row or not.
    assembled: list[tuple[float, dict]] = []
    for row in rows:
        built = _assemble_row(row, anchors)
        if built is not None:
            assembled.append((built["y"], built))
    if not assembled:
        return []

    heights = [float(w[3]) - float(w[1]) for w in words if float(w[3]) > float(w[1])]
    row_height = median(heights) if heights else 10.0
    gap_max = max(row_height * 3.5, Y_TOL * 4)

    # Split data rows into contiguous vertical blocks (separate statements).
    blocks: list[list[dict]] = []
    for y, built in assembled:
        if blocks and y - blocks[-1][-1]["y"] <= gap_max:
            blocks[-1].append(built)
        else:
            blocks.append([built])

    tables: list[dict] = []
    for index, block in enumerate(blocks):
        top_y = block[0]["y"]
        # Header region = words above the first data row, within HEADER_SPAN,
        # emitted one token per line so `_parse_periods` can match years/groups.
        header_words = [
            word
            for row in rows
            for word in row
            if top_y - HEADER_SPAN <= float(word[1]) < top_y - Y_TOL
        ]
        header_lines = [
            str(word[4]).strip()
            for word in sorted(header_words, key=lambda w: (float(w[1]), float(w[0])))
            if str(word[4]).strip()
        ]
        period_header_cells = [line for line in header_lines if _YEAR_RE.fullmatch(line)]
        tables.append(
            {
                "table_id": f"p:t{index}",
                "detector": "word_cluster",
                "n_cols": len(anchors) + 1,
                "n_rows": len(block),
                "value_anchors": [round(a, 1) for a in anchors],
                "header_lines": header_lines,
                "period_header_cells": period_header_cells,
                "rows": [
                    {"label": r["label"], "cells": r["cells"], "y": r["y"]}
                    for r in block
                ],
            }
        )
    return tables
