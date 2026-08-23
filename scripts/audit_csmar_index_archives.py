"""Read-only inventory for delivered CSMAR international/domestic index ZIPs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ipo_risk.market.csmar_hsi import CSMARHSISourceManifest


DAILY_SCHEMAS = {
    "IDX_Gidxtrd.csv": {
        "code": "Indexcd",
        "date": "Trddt",
        "close": "Clsidx",
    },
    "IDX_Idxtrd.csv": {
        "code": "Indexcd",
        "date": "Idxtrd01",
        "close": "Idxtrd05",
    },
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode_text(payload: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return payload.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError("CSMAR text member is neither UTF-8 nor GB18030")


def _parse_decimal(raw: str) -> Decimal | None:
    value = raw.strip().replace(",", "")
    if not value:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _audit_csv(member_name: str, payload: bytes) -> dict[str, Any]:
    text, encoding = _decode_text(payload)
    parse_errors = 0
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        columns = list(reader.fieldnames or ())
        rows = []
        for row in reader:
            if None in row:
                parse_errors += 1
            rows.append(row)
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text))
        columns = list(reader.fieldnames or ())
        rows = list(reader)
        parse_errors += 1

    schema = DAILY_SCHEMAS.get(Path(member_name).name)
    index_codes: list[str] = []
    coverage_start: str | None = None
    coverage_end: str | None = None
    duplicate_key_count = 0
    null_close_count = 0
    invalid_close_count = 0
    if "Indexcd" in columns:
        index_codes = sorted(
            {
                (row.get("Indexcd") or "").strip()
                for row in rows
                if (row.get("Indexcd") or "").strip()
            }
        )
        if Path(member_name).name == "IDX_Gidxinfo.csv":
            code_counts = Counter(
                (row.get("Indexcd") or "").strip() for row in rows
            )
            duplicate_key_count = sum(
                count - 1 for code, count in code_counts.items() if code and count > 1
            )
    if schema is not None:
        keys: list[tuple[str, str]] = []
        valid_dates: list[date] = []
        for row in rows:
            code = (row.get(schema["code"]) or "").strip()
            raw_date = (row.get(schema["date"]) or "").strip()
            keys.append((code, raw_date))
            try:
                valid_dates.append(date.fromisoformat(raw_date))
            except ValueError:
                parse_errors += 1
            raw_close = (row.get(schema["close"]) or "").strip()
            if not raw_close:
                null_close_count += 1
            else:
                close = _parse_decimal(raw_close)
                if close is None or close <= 0:
                    invalid_close_count += 1
        duplicate_key_count = sum(
            count - 1 for count in Counter(keys).values() if count > 1
        )
        if valid_dates:
            coverage_start = min(valid_dates).isoformat()
            coverage_end = max(valid_dates).isoformat()

    return {
        "member_name": member_name,
        "member_sha256": _sha256_bytes(payload),
        "file_type": "CSV",
        "encoding": encoding,
        "byte_count": len(payload),
        "row_count": len(rows),
        "column_names": columns,
        "index_codes": index_codes,
        "min_trading_date": coverage_start,
        "max_trading_date": coverage_end,
        "duplicate_key_count": duplicate_key_count,
        "null_close_count": null_close_count,
        "invalid_close_count": invalid_close_count,
        "parse_errors": parse_errors,
    }


def _audit_text(member_name: str, payload: bytes) -> dict[str, Any]:
    text, encoding = _decode_text(payload)
    return {
        "member_name": member_name,
        "member_sha256": _sha256_bytes(payload),
        "file_type": "TXT",
        "encoding": encoding,
        "byte_count": len(payload),
        "row_count": len(text.splitlines()),
        "column_names": [],
        "index_codes": [],
        "min_trading_date": None,
        "max_trading_date": None,
        "duplicate_key_count": 0,
        "null_close_count": 0,
        "invalid_close_count": 0,
        "parse_errors": 0,
    }


def _audit_binary(member_name: str, payload: bytes) -> dict[str, Any]:
    suffix = Path(member_name).suffix.lower()
    file_type = {".pdf": "PDF", ".xls": "XLS/BIFF8"}.get(
        suffix, "binary"
    )
    return {
        "member_name": member_name,
        "member_sha256": _sha256_bytes(payload),
        "file_type": file_type,
        "encoding": "binary",
        "byte_count": len(payload),
        "row_count": None,
        "column_names": [],
        "index_codes": [],
        "min_trading_date": None,
        "max_trading_date": None,
        "duplicate_key_count": 0,
        "null_close_count": 0,
        "invalid_close_count": 0,
        "parse_errors": 0,
    }


def audit_archive(
    archive_path: Path,
    *,
    hsi_manifest: CSMARHSISourceManifest | None = None,
) -> dict[str, Any]:
    """Inventory one archive without extracting or modifying it."""

    members: list[dict[str, Any]] = []
    archive_sha256 = _sha256_file(archive_path)
    with zipfile.ZipFile(archive_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise zipfile.BadZipFile(f"CRC failure in {bad_member}")
        for info in archive.infolist():
            payload = archive.read(info.filename)
            suffix = Path(info.filename).suffix.lower()
            if suffix == ".csv":
                audit = _audit_csv(info.filename, payload)
            elif suffix == ".txt":
                audit = _audit_text(info.filename, payload)
            else:
                audit = _audit_binary(info.filename, payload)
            audit["compressed_byte_count"] = info.compress_size
            if (
                hsi_manifest is not None
                and archive_path.name == hsi_manifest.source_archive_name
                and archive_sha256 == hsi_manifest.source_archive_sha256
                and info.filename == hsi_manifest.source_file_name
                and audit["member_sha256"] == hsi_manifest.source_file_sha256
            ):
                audit.update(
                    {
                        "row_count": hsi_manifest.row_count,
                        "column_names": [
                            "Indexcd",
                            "Trddt",
                            "Opnidx",
                            "Highidx",
                            "Lowidx",
                            "Clsidx",
                            "Vol",
                            "Value",
                        ],
                        "index_codes": ["HSI"],
                        "min_trading_date": hsi_manifest.coverage_start.isoformat(),
                        "max_trading_date": hsi_manifest.coverage_end.isoformat(),
                        "duplicate_key_count": hsi_manifest.duplicate_count,
                        "null_close_count": hsi_manifest.null_close_count,
                        "invalid_close_count": hsi_manifest.invalid_close_count,
                        "parse_errors": hsi_manifest.parse_error_count,
                        "tabular_reader": "Microsoft Excel hidden/read-only",
                    }
                )
            members.append(audit)
    return {
        "archive_filename": archive_path.name,
        "archive_sha256": archive_sha256,
        "archive_byte_count": archive_path.stat().st_size,
        "zip_crc_check": "PASS",
        "members": members,
    }


def build_inventory(
    archive_paths: list[Path],
    *,
    hsi_manifest: CSMARHSISourceManifest | None = None,
) -> dict[str, Any]:
    archives = [
        audit_archive(path, hsi_manifest=hsi_manifest)
        for path in sorted(archive_paths, key=lambda item: item.name)
    ]
    return {
        "inventory_version": "csmar_index_archive_inventory_v1",
        "archives_audited": len(archives),
        "raw_archives_kept_untouched": True,
        "license_notice": "仅供西安交通大学使用；原始数据不得提交公开仓库",
        "archives": archives,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--hsi-runtime-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = (
        CSMARHSISourceManifest.from_path(args.hsi_runtime_manifest)
        if args.hsi_runtime_manifest is not None
        else None
    )
    inventory = build_inventory(args.archives, hsi_manifest=manifest)
    content = json.dumps(
        inventory,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != content:
        raise ValueError(f"refusing to overwrite conflicting inventory: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="")
    verified = args.output.read_text(encoding="utf-8")
    if "仅供西安交通大学使用" not in verified:
        raise AssertionError("UTF-8 Chinese content verification failed")
    print(_canonical_summary(inventory))
    return 0


def _canonical_summary(inventory: dict[str, Any]) -> str:
    return json.dumps(
        {
            "archives_audited": inventory["archives_audited"],
            "archive_hashes": {
                item["archive_filename"]: item["archive_sha256"]
                for item in inventory["archives"]
            },
            "raw_archives_kept_untouched": True,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
