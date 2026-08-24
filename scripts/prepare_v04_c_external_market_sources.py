"""Download and audit public official HSCI and HKEX market sources.

Raw and normalized outputs live below ``data/competition`` and are ignored by
git.  The script never interpolates, forward-fills, or substitutes a proxy.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import requests


HSI_ORIGIN = "https://origin-www.hsi.com.hk"
HKEX_ORIGIN = "https://www.hkex.com.hk"
HSI_DIRECTORY_URL = f"{HSI_ORIGIN}/data/eng/index-series/directory.json"
HSI_METHODOLOGY_URL = (
    "https://www.hsi.com.hk/static/uploads/contents/en/dl_centre/"
    "methodologies/IM_industrye.pdf"
)

TARGET_START = date(2019, 1, 1)
TARGET_END = date(2025, 12, 31)

BENCHMARKS = {
    "HSCIE": ("00011.01", "Energy"),
    "HSCIM": ("00011.02", "Materials"),
    "HSCIIG": ("00011.03", "Industrials"),
    "HSCIT": ("00011.06", "Telecommunications"),
    "HSCIU": ("00011.07", "Utilities"),
    "HSCIF": ("00011.08", "Financials"),
    "HSCIPC": ("00011.09", "Properties & Construction"),
    "HSCIIT": ("00011.10", "Information Technology"),
    "HSCIC": ("00011.11", "Conglomerates"),
    "HSCICD": ("00011.12", "Consumer Discretionary"),
    "HSCICS": ("00011.13", "Consumer Staples"),
    "HSCIH": ("00011.14", "Healthcare"),
}

HKEX_MAIN_FILES = {
    "2015_2019": "/eng/stat/smstat/mthbull/"
    "rpt_data_statistics_archive_trading_data_2015_2019.json",
    "2020_2024": "/eng/stat/smstat/mthbull/"
    "rpt_data_statistics_archive_trading_data_2020_2024.json",
    "2025_2029": "/eng/stat/smstat/mthbull/"
    "rpt_data_statistics_archive_trading_data_2025_2029.json",
}
HKEX_GEM_FILES = {
    "2019_2023": "/eng/stat/smstat/mthbull/"
    "rpt_data_statistics_archive_trading_data_gem_2019_2023.json",
    "2024_2028": "/eng/stat/smstat/mthbull/"
    "rpt_data_statistics_archive_trading_data_gem_2024_2028.json",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_json_bytes(payload: bytes) -> Any:
    return json.loads(payload.decode("utf-8-sig"))


def parse_positive_decimal(raw: object) -> Decimal:
    text = str(raw).strip().replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal: {raw!r}") from exc
    if not value.is_finite() or value <= 0:
        raise ValueError(f"non-positive/non-finite decimal: {raw!r}")
    return value


def _walk_indexes(items: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for item in items:
        yield item
        yield from _walk_indexes(item.get("subIndexList", []))


def validate_hsi_directory(payload: bytes) -> dict[str, dict[str, str]]:
    document = read_json_bytes(payload)
    series = next(
        item
        for item in document["indexSeriesList"]
        if item.get("seriesCode") == "industry"
    )
    by_code = {
        item["indexCode"]: item
        for item in _walk_indexes(series["indexList"])
        if item.get("indexCode")
    }
    verified: dict[str, dict[str, str]] = {}
    for benchmark_id, (internal_code, industry_name) in BENCHMARKS.items():
        item = by_code.get(internal_code)
        if item is None:
            raise ValueError(f"missing HSI directory indexCode {internal_code}")
        index_name = str(item.get("indexName", ""))
        if not index_name.endswith(industry_name):
            raise ValueError(
                f"unexpected HSI name for {benchmark_id}: {index_name!r}"
            )
        if item.get("indexType") != "PI":
            raise ValueError(f"{benchmark_id} is not a price index")
        verified[benchmark_id] = {
            "internal_index_code": internal_code,
            "index_name": index_name,
            "index_short_name": str(item.get("indexShortName", "")),
            "series_type": "price_index",
        }
    return verified


def parse_hsi_chart(
    payload: bytes,
    *,
    benchmark_id: str,
    internal_index_code: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    document = read_json_bytes(payload)
    if document.get("indexCode") != internal_index_code:
        raise ValueError(
            f"unexpected indexCode for {benchmark_id}: {document.get('indexCode')!r}"
        )
    levels = document.get("indexLevels-5y")
    if not isinstance(levels, list) or not levels:
        raise ValueError(f"no 5-year observations for {benchmark_id}")

    rows: list[dict[str, object]] = []
    dates: list[date] = []
    for raw in levels:
        if not isinstance(raw, list) or len(raw) != 2:
            raise ValueError(f"malformed chart row for {benchmark_id}: {raw!r}")
        observed_date = datetime.fromtimestamp(
            int(raw[0]) / 1000, tz=timezone.utc
        ).date()
        close = parse_positive_decimal(raw[1])
        dates.append(observed_date)
        if TARGET_START <= observed_date <= TARGET_END:
            rows.append(
                {
                    "benchmark_id": benchmark_id,
                    "trading_date": observed_date.isoformat(),
                    "close": format(close, "f"),
                    "series_type": "price_index",
                    "source_owner": "Hang Seng Indexes Company Limited",
                }
            )

    duplicate_count = sum(
        count - 1 for count in Counter(dates).values() if count > 1
    )
    if duplicate_count:
        raise ValueError(f"duplicate HSI dates for {benchmark_id}")
    if dates != sorted(dates):
        raise ValueError(f"unsorted HSI dates for {benchmark_id}")
    return rows, {
        "benchmark_id": benchmark_id,
        "row_count_raw_window": len(dates),
        "coverage_start_raw_window": min(dates).isoformat(),
        "coverage_end_raw_window": max(dates).isoformat(),
        "row_count_target_window": len(rows),
        "coverage_start_target_window": rows[0]["trading_date"] if rows else None,
        "coverage_end_target_window": rows[-1]["trading_date"] if rows else None,
        "duplicate_date_count": 0,
        "missing_close_count": 0,
        "invalid_close_count": 0,
    }


_DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def parse_hkex_archive(payload: bytes, *, market_scope: str) -> list[dict[str, object]]:
    document = read_json_bytes(payload)
    tables = document.get("tables", [])
    if len(tables) != 1:
        raise ValueError(f"unexpected HKEX table count: {len(tables)}")
    grouped: dict[int, dict[int, str]] = {}
    for cell in tables[0].get("body", []):
        grouped.setdefault(int(cell["row"]), {})[int(cell["col"])] = str(
            cell.get("text", "")
        ).strip()

    rows: list[dict[str, object]] = []
    for cells in grouped.values():
        raw_date = cells.get(0, "")
        if not _DATE_RE.fullmatch(raw_date):
            continue
        trading_date = date.fromisoformat(raw_date.replace("/", "-"))
        turnover = parse_positive_decimal(cells.get(2, ""))
        volume = parse_positive_decimal(cells.get(3, ""))
        deals = parse_positive_decimal(cells.get(4, ""))
        rows.append(
            {
                "trading_date": trading_date.isoformat(),
                "turnover_hkd": int(turnover),
                "volume_shares": int(volume),
                "number_of_deals": int(deals),
                "market_scope": market_scope,
                "half_day_marker": cells.get(1, ""),
            }
        )
    rows.sort(key=lambda row: str(row["trading_date"]))
    dates = [str(row["trading_date"]) for row in rows]
    if len(dates) != len(set(dates)):
        raise ValueError(f"duplicate HKEX dates for {market_scope}")
    return rows


def combine_hkex_market_scopes(
    main_rows: Iterable[dict[str, object]],
    gem_rows: Iterable[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    main = {str(row["trading_date"]): row for row in main_rows}
    gem = {str(row["trading_date"]): row for row in gem_rows}
    main_dates = {
        value
        for value in main
        if TARGET_START <= date.fromisoformat(value) <= TARGET_END
    }
    gem_dates = {
        value
        for value in gem
        if TARGET_START <= date.fromisoformat(value) <= TARGET_END
    }
    mismatched = sorted(main_dates ^ gem_dates)
    combined: list[dict[str, object]] = []
    for trading_date in sorted(main_dates & gem_dates):
        observed_date = date.fromisoformat(trading_date)
        if not (TARGET_START <= observed_date <= TARGET_END):
            continue
        combined.append(
            {
                "trading_date": trading_date,
                "total_market_turnover": int(main[trading_date]["turnover_hkd"])
                + int(gem[trading_date]["turnover_hkd"]),
                "currency": "HKD",
                "unit": "HKD",
                "market_scope": "Main Board + GEM; all securities in HKEX archive",
                "main_board_turnover_hkd": int(
                    main[trading_date]["turnover_hkd"]
                ),
                "gem_turnover_hkd": int(gem[trading_date]["turnover_hkd"]),
            }
        )
    return combined, {
        "main_only_dates": sorted(main_dates - gem_dates),
        "gem_only_dates": sorted(gem_dates - main_dates),
        "mismatched_calendar_date_count": len(mismatched),
    }


def _download(session: requests.Session, url: str) -> bytes:
    response = session.get(url, timeout=90)
    response.raise_for_status()
    if not response.content:
        raise ValueError(f"empty response from {url}")
    return response.content


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(output_root: Path) -> dict[str, object]:
    raw = output_root / "raw" / "external_sources"
    normalized = output_root / "normalized"
    audit_dir = output_root / "audit"
    session = requests.Session()
    session.headers.update({"User-Agent": "hk-ipo-risk-agents-source-audit/1.0"})
    downloaded_at = datetime.now(timezone.utc).isoformat()
    files: list[dict[str, object]] = []

    def fetch(relative_path: str, url: str) -> bytes:
        payload = _download(session, url)
        destination = raw / relative_path
        _write_bytes(destination, payload)
        files.append(
            {
                "file_name": destination.name,
                "relative_path": destination.relative_to(output_root).as_posix(),
                "source_url": url,
                "download_timestamp_utc": downloaded_at,
                "sha256": sha256_bytes(payload),
                "byte_count": len(payload),
            }
        )
        return payload

    directory_payload = fetch("hsi/directory.json", HSI_DIRECTORY_URL)
    verified = validate_hsi_directory(directory_payload)
    fetch("hsi/IM_industrye.pdf", HSI_METHODOLOGY_URL)

    all_hsi_rows: list[dict[str, object]] = []
    hsi_audits: list[dict[str, object]] = []
    for benchmark_id, (internal_code, _industry_name) in BENCHMARKS.items():
        url = f"{HSI_ORIGIN}/data/eng/indexes/{internal_code}/chart.json"
        payload = fetch(f"hsi/{benchmark_id}_chart.json", url)
        rows, audit = parse_hsi_chart(
            payload,
            benchmark_id=benchmark_id,
            internal_index_code=internal_code,
        )
        all_hsi_rows.extend(rows)
        hsi_audits.append({**verified[benchmark_id], **audit, "source_url": url})
    all_hsi_rows.sort(
        key=lambda row: (str(row["benchmark_id"]), str(row["trading_date"]))
    )
    hsi_csv = normalized / "hsci_industry_daily_close_official_public_5y.csv"
    _write_csv(
        hsi_csv,
        all_hsi_rows,
        [
            "benchmark_id",
            "trading_date",
            "close",
            "series_type",
            "source_owner",
        ],
    )

    main_rows: list[dict[str, object]] = []
    gem_rows: list[dict[str, object]] = []
    for label, endpoint in HKEX_MAIN_FILES.items():
        payload = fetch(f"hkex/main_{label}.json", HKEX_ORIGIN + endpoint)
        main_rows.extend(parse_hkex_archive(payload, market_scope="Main Board"))
    for label, endpoint in HKEX_GEM_FILES.items():
        payload = fetch(f"hkex/gem_{label}.json", HKEX_ORIGIN + endpoint)
        gem_rows.extend(parse_hkex_archive(payload, market_scope="GEM"))
    combined, calendar_audit = combine_hkex_market_scopes(main_rows, gem_rows)
    turnover_csv = normalized / "hkex_total_market_daily_turnover_2019_2025.csv"
    _write_csv(
        turnover_csv,
        combined,
        [
            "trading_date",
            "total_market_turnover",
            "currency",
            "unit",
            "market_scope",
            "main_board_turnover_hkd",
            "gem_turnover_hkd",
        ],
    )

    normalized_files = []
    for path in (hsi_csv, turnover_csv):
        payload = path.read_bytes()
        normalized_files.append(
            {
                "file_name": path.name,
                "relative_path": path.relative_to(output_root).as_posix(),
                "sha256": sha256_bytes(payload),
                "byte_count": len(payload),
            }
        )

    audit = {
        "manifest_version": "v04_c_external_market_source_audit_v1",
        "generated_at_utc": downloaded_at,
        "target_window": {
            "start": TARGET_START.isoformat(),
            "end": TARGET_END.isoformat(),
        },
        "hsi_industry_indexes": {
            "source_owner": "Hang Seng Indexes Company Limited",
            "authoritative_level": "PRIMARY_OFFICIAL",
            "acceptance": "ACCEPT_PARTIAL_COVERAGE",
            "target_count": len(BENCHMARKS),
            "found_count": len(hsi_audits),
            "accepted_count": len(hsi_audits),
            "row_count": len(all_hsi_rows),
            "coverage_start": min(
                row["trading_date"] for row in all_hsi_rows
            ),
            "coverage_end": max(row["trading_date"] for row in all_hsi_rows),
            "series": hsi_audits,
            "pit_safe": True,
            "access_note": (
                "Public chart JSON is a rolling five-year window. Older daily history "
                "is listed by HSIL as a paid historical-data product."
            ),
        },
        "hkex_total_market_turnover": {
            "source_owner": "Hong Kong Exchanges and Clearing Limited",
            "authoritative_level": "PRIMARY_OFFICIAL",
            "acceptance": "ACCEPT",
            "frequency": "daily",
            "row_count": len(combined),
            "coverage_start": combined[0]["trading_date"],
            "coverage_end": combined[-1]["trading_date"],
            "fields": list(combined[0]),
            "currency": "HKD",
            "unit": "HKD",
            "market_scope": "Main Board + GEM; all securities in HKEX archive",
            "series_type": "total_trading_value",
            "pit_safe": True,
            "calendar_audit": calendar_audit,
        },
        "downloaded_files": files,
        "normalized_files": normalized_files,
    }
    audit_path = audit_dir / "v04_c_external_market_source_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/competition/market_reference"),
    )
    args = parser.parse_args()
    run(args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
