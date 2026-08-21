"""Build a governed filtered EOD store for the official 2020-2024 IPO cohort.

The cohort is selected from the authoritative ``official_listed_date`` in the
catalog bridge. ``source_year`` is a document/prospectus attribute and must not
be used as the modeling cohort because it can differ from the true listing year.

This script is deliberately a streaming filter: it does not load the raw EOD
file into memory and it never treats per-security ``S_DQ_AMOUNT`` as total-market
turnover.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Iterable

FILTER_SCHEMA_VERSION = "v04_ipo_eod_filter_v2"
OFFICIAL_LISTING_YEARS = frozenset({2020, 2021, 2022, 2023, 2024})
EXPECTED_OFFICIAL_CASE_COUNT = 438
OUTPUT_COLUMNS = (
    "OBJECT_ID",
    "S_INFO_WINDCODE",
    "TRADE_DT",
    "S_DQ_OPEN",
    "S_DQ_HIGH",
    "S_DQ_LOW",
    "S_DQ_CLOSE",
    "S_DQ_VOLUME",
    "S_DQ_AMOUNT",
    "S_DQ_PRECLOSE",
    "S_DQ_ADJCLOSE",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_official_listing_year(raw: str) -> int | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value).year
    except ValueError as exc:
        raise ValueError(f"invalid official_listed_date: {raw!r}") from exc


def load_official_target_codes(
    bridge_path: Path,
    *,
    allowed_years: Iterable[int] = OFFICIAL_LISTING_YEARS,
    expected_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
) -> tuple[set[str], tuple[str, ...]]:
    """Return target Wind codes/cases using authoritative official listing year.

    The function is intentionally independent from the raw EOD payload so the
    cohort selection rule can be regression-tested without a large market file.
    """

    years = frozenset(allowed_years)
    target_codes: set[str] = set()
    target_cases: list[str] = []
    seen_cases: set[str] = set()

    with bridge_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "case_id",
            "stock_code_wind",
            "official_match_status",
            "official_listed_date",
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "official bridge missing fields: " + ", ".join(sorted(missing))
            )

        for row in reader:
            if (row.get("official_match_status") or "").strip() != "matched":
                continue
            listing_year = _parse_official_listing_year(
                row.get("official_listed_date") or ""
            )
            if listing_year not in years:
                continue
            case_id = (row.get("case_id") or "").strip()
            stock_code = (row.get("stock_code_wind") or "").strip()
            if not case_id or not stock_code:
                raise ValueError(
                    "matched official cohort row requires case_id and stock_code_wind"
                )
            if case_id in seen_cases:
                raise ValueError(f"duplicate official case_id in bridge: {case_id}")
            seen_cases.add(case_id)
            target_cases.append(case_id)
            target_codes.add(stock_code)

    target_cases.sort()
    if expected_case_count is not None and len(target_cases) != expected_case_count:
        raise ValueError(
            "official target cohort drift: "
            f"expected {expected_case_count}, found {len(target_cases)}"
        )
    return target_codes, tuple(target_cases)


def _cache_is_compatible(
    manifest: dict[str, object], *, raw_hash: str, bridge_hash: str
) -> bool:
    return (
        manifest.get("raw_eod_sha256") == raw_hash
        and manifest.get("bridge_sha256") == bridge_hash
        and manifest.get("filter_schema_version") == FILTER_SCHEMA_VERSION
        and manifest.get("selection_policy")
        == "official_match_status=matched + official_listed_date.year in 2020-2024"
    )


def build_store(
    *,
    data_root: Path,
    catalog_dir: Path,
    cache_dir: Path,
    rebuild: bool = False,
    expected_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
) -> dict[str, object]:
    bridge = catalog_dir / "ipo_official_master_bridge.csv"
    raw = data_root / "hkshareeodprices.csv"
    output = cache_dir / "v04_ipo_eod.csv"
    manifest_path = cache_dir / "v04_ipo_eod.manifest.json"

    if not bridge.is_file():
        raise FileNotFoundError(bridge)
    if not raw.is_file():
        raise FileNotFoundError(raw)

    bridge_hash = sha256_file(bridge)
    raw_hash = sha256_file(raw)
    target_codes, target_cases = load_official_target_codes(
        bridge,
        expected_case_count=expected_case_count,
    )

    if manifest_path.exists() and output.exists() and not rebuild:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if _cache_is_compatible(
            existing, raw_hash=raw_hash, bridge_hash=bridge_hash
        ):
            return existing
        raise RuntimeError(
            "cache conflict; source/cohort provenance changed. "
            "Use --rebuild only after reviewing the source change."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    row_count = 0
    dates: list[str] = []
    seen_codes: set[str] = set()

    with raw.open("r", encoding="gb18030", newline="") as source, output.open(
        "w", encoding="utf-8", newline=""
    ) as destination:
        reader = csv.DictReader(source)
        required = {"OBJECT_ID", "S_INFO_WINDCODE", "TRADE_DT"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(
                "raw EOD source missing fields: " + ", ".join(sorted(missing))
            )
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in reader:
            stock_code = (row.get("S_INFO_WINDCODE") or "").strip()
            if stock_code not in target_codes:
                continue
            writer.writerow({column: row.get(column, "") for column in OUTPUT_COLUMNS})
            row_count += 1
            seen_codes.add(stock_code)
            trade_date = (row.get("TRADE_DT") or "").strip()
            if trade_date:
                dates.append(trade_date)

    manifest: dict[str, object] = {
        "filter_schema_version": FILTER_SCHEMA_VERSION,
        "selection_policy": (
            "official_match_status=matched + "
            "official_listed_date.year in 2020-2024"
        ),
        "official_listing_years": sorted(OFFICIAL_LISTING_YEARS),
        "expected_official_case_count": expected_case_count,
        "target_case_count": len(target_cases),
        "target_case_ids_sha256": hashlib.sha256(
            json.dumps(target_cases, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "raw_eod_sha256": raw_hash,
        "bridge_sha256": bridge_hash,
        "row_count": row_count,
        "distinct_target_securities": len(seen_codes),
        "target_security_count": len(target_codes),
        "min_trading_date": min(dates) if dates else None,
        "max_trading_date": max(dates) if dates else None,
        "source_record_id_column": "OBJECT_ID",
        "s_dq_amount_semantics": (
            "retained as per-security source column only; never total-market turnover"
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root", type=Path, default=Path("data/competition")
    )
    parser.add_argument(
        "--catalog-dir", type=Path, default=Path("data/catalog")
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    manifest = build_store(
        data_root=args.data_root,
        catalog_dir=args.catalog_dir,
        cache_dir=args.cache_dir,
        rebuild=args.rebuild,
    )
    print(
        "cache_valid=true "
        f"rows={manifest.get('row_count')} "
        f"targets={manifest.get('target_case_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
