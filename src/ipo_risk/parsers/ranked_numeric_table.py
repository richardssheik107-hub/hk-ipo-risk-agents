"""Recover bounded ranked-table bodies from flattened page text.

This module is deliberately document-generic.  It recognises only a complete
``1..5`` row sequence whose rows each end in an amount and percentage and whose
reported total agrees with the five row percentages.  No issuer, case, page, or
Gold value participates in detection.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any


_RANK_RE = re.compile(r"^[1-5]$")
_NUMBER_RE = re.compile(
    r"^\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?%?$|^\(?-?\d+(?:\.\d+)?\)?%?$"
)
_PERIOD_RE = re.compile(
    r"截至.{0,30}(?:止|年度|期間)|(?:year|months?).{0,30}ended",
    re.I,
)
_TOTAL_RE = re.compile(r"總\s*計|合\s*計|小\s*計|total", re.I)
_CUSTOMER_RE = re.compile(r"客\s*[戶户]|customer", re.I)
_SUPPLIER_RE = re.compile(r"供\s*[應应]\s*商|supplier", re.I)


def _number(value: str) -> Decimal | None:
    text = value.strip().rstrip("%").replace(",", "")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return -parsed if negative else parsed


def _numeric_lines(lines: list[str]) -> list[tuple[int, Decimal]]:
    output: list[tuple[int, Decimal]] = []
    for index, line in enumerate(lines):
        if not _NUMBER_RE.fullmatch(line):
            continue
        value = _number(line)
        if value is not None:
            output.append((index, value))
    return output


def _counterparty_type(text: str) -> str | None:
    customer = len(_CUSTOMER_RE.findall(text))
    supplier = len(_SUPPLIER_RE.findall(text))
    if customer >= 2 and customer > supplier:
        return "customer"
    if supplier >= 2 and supplier > customer:
        return "supplier"
    return None


def recover_ranked_numeric_table(text: str) -> dict[str, Any] | None:
    """Return one complete ranked counterparty table, otherwise ``None``.

    The detector is intentionally strict: five standalone ranks must occur in
    order, every row must end in an amount/percentage pair, a following total
    amount/percentage pair must be present, and the disclosed total percentage
    must agree with the row sum within ordinary printed-rounding tolerance.
    """

    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return None

    rank_positions: list[int] = []
    cursor = 0
    for expected in range(1, 6):
        position = next(
            (
                index
                for index in range(cursor, len(lines))
                if _RANK_RE.fullmatch(lines[index])
                and int(lines[index]) == expected
            ),
            None,
        )
        if position is None:
            return None
        rank_positions.append(position)
        cursor = position + 1

    rows: list[dict[str, Any]] = []
    for offset, start in enumerate(rank_positions):
        end = rank_positions[offset + 1] if offset < 4 else len(lines)
        numeric = _numeric_lines(lines[start + 1 : end])
        if len(numeric) < 2:
            return None
        amount_index, amount = numeric[0]
        percentage_index, percentage = numeric[1]
        if amount <= 0 or percentage < 0 or percentage > 100:
            return None
        rows.append(
            {
                "rank": offset + 1,
                "amount": str(amount),
                "percentage": str(percentage),
                "segment_end": start + 1 + percentage_index,
                "amount_line": start + 1 + amount_index,
            }
        )

    tail_start = rank_positions[-1] + 1
    tail_numeric = _numeric_lines(lines[tail_start:])
    if len(tail_numeric) < 4:
        return None
    total_amount_line, total_amount = tail_numeric[2]
    total_percentage_line, total_percentage = tail_numeric[3]
    if total_amount <= 0 or total_percentage < 0 or total_percentage > 100:
        return None
    percentages = [Decimal(row["percentage"]) for row in rows]
    if abs(sum(percentages) - total_percentage) > Decimal("0.2"):
        return None

    period_index = next(
        (
            index
            for index in range(rank_positions[0] - 1, -1, -1)
            if _PERIOD_RE.search(lines[index])
        ),
        None,
    )
    if period_index is None:
        return None

    type_probe = "\n".join(lines[max(0, period_index - 12) : total_percentage_line + tail_start + 1])
    counterparty_type = _counterparty_type(type_probe)
    if counterparty_type is None:
        return None

    total_end = tail_start + total_percentage_line
    body = "\n".join([lines[period_index], *lines[rank_positions[0] : total_end + 1]])
    return {
        "detector": "ranked_numeric_1_to_5_v1",
        "counterparty_type": counterparty_type,
        "period_text": lines[period_index],
        "rank_rows": [
            {
                "rank": row["rank"],
                "amount": row["amount"],
                "percentage": row["percentage"],
            }
            for row in rows
        ],
        "largest_counterparty_pct": str(max(percentages)),
        "top_five_pct": str(total_percentage),
        "total_amount": str(total_amount),
        "body_text": body,
        "rounding_delta": str(abs(sum(percentages) - total_percentage)),
    }
