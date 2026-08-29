"""Fast, deterministic issuer lookup over the committed official IPO bridge.

This module is deliberately UI-free.  The Streamlit intake can search the same
catalog identity that Market-X and the governed runtime use without duplicating
identity rules in the presentation layer.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


_CODE_DIGITS = re.compile(r"\d+")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class IssuerCatalogRecord:
    case_id: str
    company_name: str
    stock_code: str
    listing_date: date

    @property
    def label(self) -> str:
        return f"{self.company_name} · {self.stock_code} · {self.listing_date.isoformat()}"


def _clean_text(value: object) -> str:
    return _SPACE.sub(" ", str(value or "").strip()).casefold()


def normalize_stock_code(value: object) -> str:
    """Map 02460 / 2460 / 2460.HK to one searchable HK code identity."""

    raw = str(value or "").strip().upper().replace(" ", "")
    if raw.endswith(".HK"):
        raw = raw[:-3]
    digits = "".join(_CODE_DIGITS.findall(raw))
    if not digits:
        return ""
    # HKEX display codes are zero-padded in some sources and not in others.
    return str(int(digits))


def load_issuer_catalog(path: str | Path) -> tuple[IssuerCatalogRecord, ...]:
    """Load matched official identities that are usable by the runtime."""

    records: list[IssuerCatalogRecord] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "case_id",
            "stock_code_wind",
            "official_listed_date",
            "selected_name",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "official issuer bridge missing fields: " + ", ".join(sorted(missing))
            )
        for row in reader:
            if row.get("official_match_status") not in (None, "", "matched"):
                continue
            case_id = str(row.get("case_id") or "").strip()
            company_name = str(row.get("selected_name") or "").strip()
            stock_code = str(row.get("stock_code_wind") or "").strip()
            listed = str(row.get("official_listed_date") or "").strip()
            if not all((case_id, company_name, stock_code, listed)):
                continue
            try:
                listing_date = date.fromisoformat(listed)
            except ValueError:
                continue
            records.append(
                IssuerCatalogRecord(
                    case_id=case_id,
                    company_name=company_name,
                    stock_code=stock_code,
                    listing_date=listing_date,
                )
            )
    return tuple(records)


def _match_score(record: IssuerCatalogRecord, query: str) -> int | None:
    q = _clean_text(query)
    if not q:
        return None

    company = _clean_text(record.company_name)
    case_id = _clean_text(record.case_id)
    stock = _clean_text(record.stock_code)
    listing = record.listing_date.isoformat()
    q_code = normalize_stock_code(query)
    record_code = normalize_stock_code(record.stock_code)

    if q == case_id:
        return 140
    if q_code and q_code == record_code:
        return 135
    if q == listing:
        return 130
    if q == company:
        return 125
    if q in company:
        # Prefer a tighter name match without introducing fuzzy/non-deterministic
        # ranking dependencies.
        return 100 + min(20, len(q))
    if q in stock:
        return 90
    if q_code and record_code.startswith(q_code):
        return 80
    if q in listing:
        return 70
    if q in case_id:
        return 60
    return None


def search_issuer_catalog(
    records: Iterable[IssuerCatalogRecord],
    query: str,
    *,
    limit: int = 12,
) -> tuple[IssuerCatalogRecord, ...]:
    """Search by issuer name, HK stock code, case id or listing date."""

    if limit < 1:
        return ()
    scored: list[tuple[int, IssuerCatalogRecord]] = []
    for record in records:
        score = _match_score(record, query)
        if score is not None:
            scored.append((score, record))
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].listing_date,
            item[1].stock_code,
            item[1].company_name,
        )
    )
    return tuple(record for _, record in scored[:limit])
