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
  (e.g. ``18(b)``) that would otherwise pollute the grid.  A token is assigned to
  the column whose x-interval contains it, never by distance to the anchor: the
  columns are right-aligned, so the offset between a token's centre and its
  anchor is a function of how long the token is (see :func:`_column_bounds`).
* Output is JSON-primitive only (str / int / float / list / dict) so it can ride
  in ``DocumentChunk.metadata["tables"]`` and survive repository round-trips.

Mixed-period tables
-------------------
A Hong Kong track-record statement routinely puts **two different period bases
side by side** — e.g. three full years under 「截至12月31日止年度」 followed by two
nine-month stubs under 「截至9月30日止九個月」.  The same year label then appears
twice (``2024年`` as both a full year and a nine-month stub), and the column
count no longer matches a uniform three-period series.

Two structural facts make that recoverable, and this module now emits both:

``period_columns``
    One entry per value column, carrying the year label *and* the period-group
    caption that governs that column.  Downstream this makes the annual/interim
    split explicit instead of leaving it to be re-inferred from a flat list of
    year strings, and it guarantees ``len(period_columns) == len(row["cells"])``.

``period_header_source``
    A statement is split into several vertical blocks whenever a subtotal rule
    opens a gap, but only the topmost block sits under the caption; the rest
    would otherwise scan the *previous block's data rows* as their header.  All
    blocks on a page share one set of ``value_anchors``, hence one column
    geometry, so a block without a period header of its own inherits the nearest
    preceding one and is marked ``carried_forward``.
"""

from __future__ import annotations

import re
from statistics import median
from typing import Mapping, Sequence

from ipo_risk.extraction.financial import _ROW_AMOUNT_TOKEN_RE, _YEAR_RE

# --- Tunable geometry (points). Exposed as module constants for testing. ---
Y_TOL = 3.0          # words within this vertical distance share a row baseline
X_TOL = 12.0         # x-centres within this distance belong to one column
HEADER_SNAP = 16.0   # a year header cell snaps to a column anchor within this distance
LABEL_MARGIN = 18.0  # label tokens must sit this far left of the first value col
SPACE_GAP = 3.0      # horizontal gap above which a space is inserted in a label
HEADER_SPAN = 130.0  # how far above the first data row to scan for period header
MIN_VALUE_COLS = 2   # a data row needs at least this many aligned value cells
MIN_YEAR_ANCHORS = 2 # a table needs at least this many distinct year columns
LABEL_WRAP_PITCH = 1.6  # a wrapped label line sits within this many line heights

# Mirrors ``V03FinancialFactExtractor._is_period_group``; the equivalence is
# pinned by a unit test so the two cannot drift apart.
_PERIOD_GROUP_RE = re.compile(r"截至.*(?:止|ended)|(?:year|months?).*ended", re.I)


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


def _column_bounds(anchors: Sequence[float]) -> tuple[list[float], list[float]]:
    """Half-open ``[lower, upper)`` x-interval owned by each value column.

    Financial statement columns are **right-aligned**, so a token's x-centre sits
    a width-dependent distance from the year label centred above it: a bare dash
    centres well right of the anchor, a seven-digit figure well left of it.  A
    single centre-distance tolerance therefore has to be loose enough for the dash
    and tight enough to exclude the neighbouring column, and on the 2020-2023
    development cohort no such value exists — 22.2% of the cells whose column is
    unambiguous (553,488 cells on rows carrying exactly one value per anchor) sit
    further than the old 16pt tolerance from their own anchor, and the short cells
    that overshot were dropped outright.

    Splitting the axis at the midpoints between adjacent anchors asks instead the
    question that does have a stable answer — which column box does this token sit
    in — and needs no tolerance.  Development cohort, on those same forced-pairing
    rows: 68.8% of rows reconstructed exactly under the tolerance, 93.3% under the
    intervals.  The two outer bounds mirror the adjacent gap, which keeps the
    note-reference column (printed a full column further left) outside the first
    box.  ``anchors`` is ascending, as :func:`_year_anchors` returns it.
    """
    mids = [(left + right) / 2.0 for left, right in zip(anchors, anchors[1:])]
    lower = [anchors[0] - (mids[0] - anchors[0]), *mids]
    upper = [*mids, anchors[-1] + (anchors[-1] - mids[-1])]
    return lower, upper


def _assemble_row(row: Sequence[Sequence], anchors: Sequence[float]) -> dict | None:
    """Split one visual row into a label and column-aligned value cells."""
    lower, upper = _column_bounds(anchors)
    columns: list[Sequence | None] = [None] * len(anchors)
    used_ids: set[int] = set()
    for word in row:  # rows arrive in reading order from ``_cluster_rows``
        if not _is_value_token(str(word[4])):
            continue
        centre = _x_center(word)
        for index in range(len(anchors)):
            if lower[index] <= centre < upper[index]:
                # A column box holding two value tokens is a printed pair, not
                # two columns: a 「金額／佔收益百分比」 summary prints the amount
                # and its percentage inside one year's box, and keeping the
                # first in reading order is what keeps the amount rather than
                # the percentage.  Dropping the surplus — rather than spilling it
                # into an empty neighbour — is also what stops a page footer such
                # as ``I-5`` from passing as a two-cell data row; on the
                # development cohort spilling bought 0.7pp of exact rows, and on
                # the rows where the pairing is forced the four candidate
                # tie-breaks were indistinguishable.
                if columns[index] is None:
                    columns[index] = word
                    used_ids.add(id(word))
                break

    cells = ["" if word is None else str(word[4]).strip() for word in columns]
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


def _repeated_year_group_counts(labels: Sequence[str], group_count: int) -> list[int] | None:
    """Split the year sequence where a year label repeats.

    A track-record table restates the same year under the next period basis
    (``2024年`` closing the full year, then ``2024年`` again as the nine-month
    comparative), so a repeat is a period-basis boundary.  This is the strongest
    available cue and is preferred over geometry whenever it fires.
    """
    column_count = len(labels)
    if group_count <= 0 or column_count < group_count:
        return None
    if group_count == 1:
        return [column_count]
    boundaries = [
        index for index in range(1, column_count) if labels[index] == labels[index - 1]
    ]
    if len(boundaries) != group_count - 1:
        return None
    points = [0, *boundaries, column_count]
    counts = [points[index + 1] - points[index] for index in range(group_count)]
    return counts if all(count > 0 for count in counts) else None


def _nearest_caption_group_counts(
    year_centres: Sequence[float], caption_centres: Sequence[float]
) -> list[int] | None:
    """Assign each year cell to the horizontally nearest period-group caption.

    The fallback for headers the repeat cue cannot split — notably a table whose
    interim stub carries a year that never appears as a full year (``2022/2023/
    2024`` annual plus a lone ``2025`` nine-month column).  Captions and columns
    both run left to right and each caption governs a contiguous run, so the
    assignment is forced to be non-decreasing.
    """
    if not caption_centres or not year_centres:
        return None
    assignment: list[int] = []
    lowest = 0
    for centre in year_centres:
        index = min(
            range(len(caption_centres)),
            key=lambda candidate: abs(centre - caption_centres[candidate]),
        )
        lowest = max(lowest, index)
        assignment.append(lowest)
    counts = [assignment.count(index) for index in range(len(caption_centres))]
    return counts if all(count > 0 for count in counts) else None


def _period_group_captions(header_words: Sequence[Sequence]) -> list[tuple[float, str]]:
    """Return complete period captions, including narrowly wrapped Chinese ones.

    Some summary tables wrap a caption between the month number and the rest of
    the date (for example ``截至8`` / ``月31日止八個月``).  Neither visual line is a
    valid period caption on its own, so treating words independently silently
    assigns every year column to the neighbouring annual caption.  Rejoin only
    the strongly delimited Chinese form: an ``截至`` prefix without ``止`` and
    the nearest lower, horizontally overlapping suffix that contains ``止``.
    This keeps the repair structural and prevents unrelated header prose from
    being combined merely because it is nearby.
    """

    captions: list[tuple[float, str]] = [
        (_x_center(word), str(word[4]).strip())
        for word in header_words
        if _PERIOD_GROUP_RE.search(str(word[4]).strip())
    ]
    incomplete_prefixes = [
        word
        for word in header_words
        if str(word[4]).strip().startswith("截至")
        and "止" not in str(word[4]).strip()
    ]
    for prefix in incomplete_prefixes:
        lower_candidates = []
        for suffix in header_words:
            suffix_text = str(suffix[4]).strip()
            vertical_gap = float(suffix[1]) - float(prefix[3])
            horizontal_overlap = min(float(prefix[2]), float(suffix[2])) - max(
                float(prefix[0]), float(suffix[0])
            )
            horizontal_gap = float(suffix[0]) - float(prefix[2])
            same_line_continuation = (
                abs(float(suffix[1]) - float(prefix[1])) <= Y_TOL
                and 0.0 <= horizontal_gap <= SPACE_GAP
            )
            wrapped_continuation = (
                0.0 <= vertical_gap <= 18.0 and horizontal_overlap >= 0.0
            )
            if (
                "止" in suffix_text
                and not suffix_text.startswith("截至")
                and (same_line_continuation or wrapped_continuation)
            ):
                distance = abs(float(suffix[1]) - float(prefix[1])) + max(
                    horizontal_gap, 0.0
                )
                lower_candidates.append((distance, suffix))
        if not lower_candidates:
            continue
        _, suffix = min(lower_candidates, key=lambda item: item[0])
        caption = f"{str(prefix[4]).strip()}{str(suffix[4]).strip()}"
        if _PERIOD_GROUP_RE.search(caption):
            centre = (min(float(prefix[0]), float(suffix[0])) + max(
                float(prefix[2]), float(suffix[2])
            )) / 2.0
            captions.append((centre, caption))

    return sorted(dict.fromkeys(captions), key=lambda item: item[0])


def _period_columns(
    header_words: Sequence[Sequence], anchors: Sequence[float]
) -> list[dict] | None:
    """Map every value column to its year label and governing period caption.

    Returns one entry per anchor (so it stays index-aligned with ``row["cells"]``)
    or ``None`` when the header carries no fiscal-year cell at all — the signal
    that this block must inherit a preceding block's header.
    """
    year_by_column: dict[int, Sequence] = {}
    for word in header_words:
        if not _YEAR_RE.fullmatch(str(word[4]).strip()):
            continue
        centre = _x_center(word)
        distances = [(abs(centre - anchor), index) for index, anchor in enumerate(anchors)]
        distance, column = min(distances)
        if distance > HEADER_SNAP:
            continue
        # Multi-row headers repeat the year; the line nearest the data wins.
        previous = year_by_column.get(column)
        if previous is None or float(word[1]) > float(previous[1]):
            year_by_column[column] = word
    if not year_by_column:
        return None

    captions = _period_group_captions(header_words)

    ordered_columns = sorted(year_by_column)
    labels = [str(year_by_column[column][4]).strip() for column in ordered_columns]
    centres = [_x_center(year_by_column[column]) for column in ordered_columns]

    counts: list[int] | None
    if not captions:
        counts = None
    else:
        counts = _repeated_year_group_counts(labels, len(captions))
        if counts is None:
            counts = _nearest_caption_group_counts(centres, [c for c, _ in captions])

    group_by_column: dict[int, str] = {}
    if counts is not None:
        offset = 0
        for (_, caption), count in zip(captions, counts, strict=True):
            for column in ordered_columns[offset : offset + count]:
                group_by_column[column] = caption
            offset += count
    elif len(captions) == 1:
        group_by_column = {column: captions[0][1] for column in ordered_columns}

    return [
        {
            "column": index,
            "anchor": round(float(anchor), 1),
            "year_label": (
                str(year_by_column[index][4]).strip() if index in year_by_column else None
            ),
            "group_line": group_by_column.get(index),
        }
        for index, anchor in enumerate(anchors)
    ]


def _join_label(prefix: str, label: str) -> str:
    """Rejoin a wrapped label, inserting a space only between Latin fragments."""
    if prefix and label and (prefix[-1].isascii() and prefix[-1].isalnum()) and (
        label[0].isascii() and label[0].isalnum()
    ):
        return f"{prefix} {label}"
    return f"{prefix}{label}"


def _wrapped_label_prefix(
    rows: Sequence[Sequence],
    index: int,
    anchors: Sequence[float],
    row_height: float,
    data_rows: Mapping[int, dict],
) -> str:
    """Text of the label lines a long row label wrapped onto, above its values.

    A statement prints a long caption over several lines and puts the figures on
    the last one only ("年內利潤及全面" / "收入總額  31,155 …").  Reading a single
    visual row therefore hands the extractor the caption's *tail*, and a tail can
    match a completely different metric than the whole: ``收入總額`` reads as
    revenue, while ``年內利潤及全面收入總額`` is the net result — so the row's net
    profit would be extracted as the company's revenue.  On the 2020-2023
    development cohort 2,718 of 17,501 data rows wrap this way; rejoining them
    changes which metric 46 rows match, and every one of those is a correction
    (``出售物業、廠房及設備的收益`` — a disposal gain — stops reading as revenue,
    and 31 total-comprehensive-income rows start reading as the net result).

    A line is part of the label only when it sits directly above (no wider than a
    line pitch), carries no value token, and lies entirely in the label zone left
    of the first value column — which is what keeps the column captions and the
    unit line, both of which reach into the value columns, out of the label.
    """
    label_zone = min(anchors) - LABEL_MARGIN
    parts: list[str] = []
    cursor = index - 1
    while cursor >= 0 and cursor not in data_rows:
        row = rows[cursor]
        if float(rows[cursor + 1][0][1]) - float(row[0][1]) > row_height * LABEL_WRAP_PITCH:
            break
        if any(_is_value_token(str(word[4])) for word in row):
            break
        if not all(_x_center(word) < label_zone for word in row):
            break
        parts.append(_row_text(row))
        cursor -= 1
    # ``parts`` was collected walking upwards, so reverse it back into reading
    # order and append: a caption wrapping over three or more lines is otherwise
    # reassembled with its middle lines transposed.
    prefix = ""
    for part in reversed(parts):
        prefix = _join_label(prefix, part)
    return prefix


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
    assembled_by_index: dict[int, dict] = {}
    for index, row in enumerate(rows):
        built = _assemble_row(row, anchors)
        if built is not None:
            assembled_by_index[index] = built
    if not assembled_by_index:
        return []

    heights = [float(w[3]) - float(w[1]) for w in words if float(w[3]) > float(w[1])]
    row_height = median(heights) if heights else 10.0
    gap_max = max(row_height * 3.5, Y_TOL * 4)

    # Re-attach labels that wrapped onto the lines above their values.
    for index, built in assembled_by_index.items():
        prefix = _wrapped_label_prefix(
            rows, index, anchors, row_height, assembled_by_index
        )
        if prefix:
            built["label"] = _join_label(prefix, built["label"])

    assembled = [(built["y"], built) for built in assembled_by_index.values()]

    # Split data rows into contiguous vertical blocks (separate statements).
    blocks: list[list[dict]] = []
    for y, built in assembled:
        if blocks and y - blocks[-1][-1]["y"] <= gap_max:
            blocks[-1].append(built)
        else:
            blocks.append([built])

    tables: list[dict] = []
    carried: dict | None = None  # nearest preceding block header on this page
    previous_bottom = float("-inf")
    for index, block in enumerate(blocks):
        top_y = block[0]["y"]
        # Header region = words above the first data row, within HEADER_SPAN and
        # below the previous block's last data row, so a block never mistakes the
        # rows above it for a period header.
        floor_y = max(top_y - HEADER_SPAN, previous_bottom + row_height / 2.0)
        header_words = [
            word
            for row in rows
            for word in row
            if floor_y <= float(word[1]) < top_y - Y_TOL
        ]
        header_words.sort(key=lambda w: (float(w[1]), float(w[0])))
        local_header_lines = [
            str(word[4]).strip() for word in header_words if str(word[4]).strip()
        ]
        columns = _period_columns(header_words, anchors)

        if columns is not None:
            header_lines = local_header_lines
            header_source = "block"
            carried = {"columns": columns, "header_lines": header_lines}
        elif carried is not None:
            columns = carried["columns"]
            header_lines = carried["header_lines"]
            header_source = "carried_forward"
        else:
            header_lines = local_header_lines
            header_source = "none"

        period_header_cells = [line for line in header_lines if _YEAR_RE.fullmatch(line)]
        group_lines = [
            column["group_line"] for column in (columns or []) if column["group_line"]
        ]
        tables.append(
            {
                "table_id": f"p:t{index}",
                "detector": "word_cluster",
                "n_cols": len(anchors) + 1,
                "n_rows": len(block),
                "value_anchors": [round(a, 1) for a in anchors],
                "header_lines": header_lines,
                "local_header_lines": local_header_lines,
                "period_header_cells": period_header_cells,
                "period_header_source": header_source,
                "period_columns": columns or [],
                "period_group_lines": list(dict.fromkeys(group_lines)),
                "period_basis_mixed": len(set(group_lines)) > 1,
                "rows": [
                    {"label": r["label"], "cells": r["cells"], "y": r["y"]}
                    for r in block
                ],
            }
        )
        previous_bottom = block[-1]["y"]
    return tables
