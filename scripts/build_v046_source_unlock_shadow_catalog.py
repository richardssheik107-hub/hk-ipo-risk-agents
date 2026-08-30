"""Build a non-destructive official-edition shadow catalog from HKEX metadata.

The input case selection is operational only.  Source discovery itself sees
stock/listing identity and disclosure date, never Existing-Gold text or pages.
PDF bytes are downloaded for hashing. They are persisted only when the caller
explicitly supplies an isolated ``--materialize-root`` for a shadow benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

import fitz

from ipo_risk.sources.hkex_editions import (
    SOURCE_AUTHORITY,
    HKEXDocument,
    HKEXEditionResolver,
    download_official_pdf,
    sha256_bytes,
)


CATALOG_VERSION = "v046_source_unlock_shadow_catalog_v1"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _document_record(
    case_id: str,
    document: HKEXDocument | None,
    *,
    materialize_path: Path | None = None,
) -> dict[str, object] | None:
    if document is None:
        return None
    payload = download_official_pdf(document.file_url)
    language = document.language
    if materialize_path is not None:
        materialize_path.parent.mkdir(parents=True, exist_ok=True)
        materialize_path.write_bytes(payload)
    with fitz.open(stream=payload, filetype="pdf") as pdf:
        page_count = pdf.page_count
    return {
        "language": language,
        "edition": "official_english" if language == "en" else "official_traditional_chinese",
        "source_authority": SOURCE_AUTHORITY,
        "source_url": document.file_url,
        "release_time": document.release_time.isoformat(),
        "official_category": document.category,
        "official_title": document.title,
        "official_news_id": document.news_id,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
        "pdf_page_count": page_count,
        "retrieval_document_id": (
            f"{case_id}:hkex:{language}:sha256:{sha256_bytes(payload)[:16]}"
        ),
    }


def build(
    manifest_path: Path,
    *,
    case_ids: set[str] | None,
    source_year: int | None,
    materialize_root: Path | None = None,
    shadow_manifest: Path | None = None,
) -> dict[str, object]:
    rows = _load_rows(manifest_path)
    selected = [
        row
        for row in rows
        if (not case_ids or row["case_id"] in case_ids)
        and (source_year is None or int(row["source_year"]) == source_year)
    ]
    resolver = HKEXEditionResolver()
    records: list[dict[str, object]] = []
    shadow_rows: list[dict[str, str]] = []
    for row in selected:
        disclosure = date.fromisoformat(row["disclosure_date"])
        edition_set = resolver.discover(
            stock_code=row["stock_code_raw"], disclosure_date=disclosure
        )
        english_relative_path = Path("source_unlock_shadow") / "en" / f"{row['case_id']}.pdf"
        english = _document_record(
            row["case_id"],
            edition_set.english,
            materialize_path=(
                materialize_root / english_relative_path
                if materialize_root is not None
                else None
            ),
        )
        chinese = _document_record(row["case_id"], edition_set.chinese)
        if english is not None:
            shadow_row = dict(row)
            shadow_row.update(
                {
                    "source_filename": english_relative_path.name,
                    "relative_path": english_relative_path.as_posix(),
                    "file_size_bytes": str(english["size_bytes"]),
                    "sha256": str(english["sha256"]),
                    "pdf_page_count": str(english["pdf_page_count"]),
                    "notes": (
                        "source-unlock shadow catalog; official HKEX English edition; "
                        "production catalog unchanged"
                    ),
                }
            )
            shadow_rows.append(shadow_row)
        records.append(
            {
                "case_id": row["case_id"],
                "stock_code": row["stock_code_wind"],
                "disclosure_date": row["disclosure_date"],
                "listing_identity": edition_set.listing_identity,
                "filing_identity": edition_set.filing_identity,
                "hkex_stock_id": edition_set.stock_identity.stock_id,
                "current_catalog_sha256": row["sha256"],
                "current_catalog_language": "zh-Hant",
                "edition_relationship_confidence": edition_set.relationship_confidence,
                "official_english_found": english is not None,
                "official_chinese_found": chinese is not None,
                "current_catalog_matches_official_chinese": bool(
                    chinese and chinese["sha256"] == row["sha256"]
                ),
                "documents": [item for item in (english, chinese) if item is not None],
            }
        )
    records.sort(key=lambda item: str(item["case_id"]))
    if shadow_manifest is not None:
        if materialize_root is None:
            raise ValueError("shadow manifest requires --materialize-root")
        shadow_manifest.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(rows[0])
        with shadow_manifest.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(shadow_rows)
    return {
        "catalog_version": CATALOG_VERSION,
        "catalog_namespace": "source_unlock_shadow_catalog",
        "catalog_strategy": "language_neutral_all_official_prospectus_editions",
        "source_policy_classification": "SOURCE_POLICY_AMBIGUOUS",
        "source_authority": SOURCE_AUTHORITY,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gold_used_for_discovery": False,
        "gold_text_persisted": False,
        "production_catalog_modified": False,
        "case_count": len(records),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/catalog/ipo_prospectus_manifest.csv"),
    )
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--source-year", type=int)
    parser.add_argument("--materialize-root", type=Path)
    parser.add_argument("--shadow-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        args.manifest,
        case_ids=set(args.case_id) or None,
        source_year=args.source_year,
        materialize_root=args.materialize_root,
        shadow_manifest=args.shadow_manifest,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"case_count={payload['case_count']} "
        f"output={args.output.as_posix()} "
        "production_catalog_modified=false gold_used_for_discovery=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
