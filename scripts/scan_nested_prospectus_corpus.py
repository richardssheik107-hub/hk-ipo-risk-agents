"""Low-disk health scan for prospectus PDFs stored in nested ZIP archives.

Only metadata and counts are persisted.  PDF bytes are held one document at a
time and opened from memory; no ZIP member, page image, or extracted text is
written to disk.
"""

from __future__ import annotations

import argparse
import csv
import gc
import io
import json
import statistics
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


def _real_members(infos: list[zipfile.ZipInfo], suffix: str) -> list[zipfile.ZipInfo]:
    return [
        item
        for item in infos
        if not item.is_dir()
        and item.filename.casefold().endswith(suffix)
        and "__macosx" not in item.filename.casefold()
        and not PurePosixPath(item.filename).name.startswith("._")
    ]


def scan(outer_path: Path, csv_path: Path, summary_path: Path) -> dict[str, Any]:
    import pymupdf

    rows: list[dict[str, Any]] = []
    outer_member_count = 0
    nested_archives: list[zipfile.ZipInfo] = []
    with zipfile.ZipFile(outer_path) as outer:
        outer_member_count = len(outer.infolist())
        nested_archives = _real_members(outer.infolist(), ".zip")
        for archive_index, archive_info in enumerate(nested_archives, start=1):
            with outer.open(archive_info) as nested_stream:
                with zipfile.ZipFile(nested_stream) as nested:
                    pdfs = _real_members(nested.infolist(), ".pdf")
                    for pdf_index, info in enumerate(pdfs, start=1):
                        row: dict[str, Any] = {
                            "archive": PurePosixPath(archive_info.filename).name,
                            "file": info.filename,
                            "size": info.file_size,
                            "compressed_size": info.compress_size,
                            "parse_status": "failed",
                            "page_count": 0,
                            "chunk_count": 0,
                            "blank_page_count": 0,
                            "error_type": "",
                        }
                        try:
                            payload = nested.read(info)
                            with pymupdf.open(stream=payload, filetype="pdf") as document:
                                row["page_count"] = int(document.page_count)
                                nonblank = 0
                                for page in document:
                                    if page.get_text("text").strip():
                                        nonblank += 1
                                row["chunk_count"] = nonblank
                                row["blank_page_count"] = row["page_count"] - nonblank
                                row["parse_status"] = "success"
                            del payload
                        except Exception as exc:  # health scan must inventory every member
                            row["error_type"] = type(exc).__name__
                        rows.append(row)
                        if len(rows) % 25 == 0:
                            print(f"scanned={len(rows)} archive={archive_index}/{len(nested_archives)}")
                        gc.collect()

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "archive", "file", "size", "compressed_size", "parse_status",
        "page_count", "chunk_count", "blank_page_count", "error_type",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    successful = [row for row in rows if row["parse_status"] == "success"]
    pages = [int(row["page_count"]) for row in successful]
    suspicious = [
        row["file"]
        for row in rows
        if row["parse_status"] != "success"
        or int(row["page_count"]) == 0
        or (int(row["page_count"]) and int(row["chunk_count"]) / int(row["page_count"]) < 0.1)
    ]
    summary = {
        "outer_member_count": outer_member_count,
        "nested_archive_count": len(nested_archives),
        "pdf_total": len(rows),
        "compressed_size": sum(int(row["compressed_size"]) for row in rows),
        "uncompressed_size": sum(int(row["size"]) for row in rows),
        "parse_success": len(successful),
        "parse_failure": len(rows) - len(successful),
        "median_pages": statistics.median(pages) if pages else None,
        "max_pages": max(pages) if pages else None,
        "zero_page": sum(int(row["page_count"]) == 0 for row in rows),
        "suspicious_pdf_count": len(suspicious),
        "suspicious_pdfs": suspicious,
        "exceptions": {
            name: sum(row["error_type"] == name for row in rows)
            for name in sorted({row["error_type"] for row in rows if row["error_type"]})
        },
        "pdfs_extracted": 0,
        "text_persisted": False,
        "page_images_persisted": False,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outer_zip", type=Path)
    parser.add_argument(
        "--csv", type=Path,
        default=Path("reports/experiments/CORPUS_HEALTH_SUMMARY.csv"),
    )
    parser.add_argument(
        "--summary", type=Path,
        default=Path("reports/experiments/CORPUS_HEALTH_SUMMARY.json"),
    )
    args = parser.parse_args()
    print(json.dumps(scan(args.outer_zip, args.csv, args.summary), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
