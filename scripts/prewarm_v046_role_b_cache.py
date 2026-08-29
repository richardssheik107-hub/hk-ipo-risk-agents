#!/usr/bin/env python3
"""Prewarm one content-addressed parser universe for all 79 Development cases."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_SOURCE = _ROOT / "src"
for item in (_ROOT, _SOURCE):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from ipo_risk.parsers.pymupdf_parser import PyMuPDFRoleBRecallParser
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest
from scripts.run_v04_role_e_demo import (
    PROSPECTUS_ROOT_ENV,
    _read_catalog,
    resolve_prospectus,
)


def _hash(payload: Any) -> str:
    return sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _safe_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _development_case_ids(manifest: dict[str, Any]) -> list[str]:
    case_ids = {
        str(row.get("case_id") or "")
        for row in manifest.get("risk_units") or []
        if row.get("split") == "development" and row.get("primary_scope") is True
    }
    case_ids.discard("")
    return sorted(case_ids)


def _pass(
    *,
    case_ids: list[str],
    catalog: dict[str, dict[str, str]],
    prospectus_root: Path,
    cache_root: Path,
) -> tuple[list[dict[str, Any]], float]:
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    for ordinal, case_id in enumerate(case_ids, start=1):
        row = catalog.get(case_id)
        if row is None or row.get("dataset_split") != "development":
            raise RuntimeError(f"Development catalog row unavailable:{case_id}")
        prospectus, verification = resolve_prospectus(dict(row), prospectus_root, None)
        parser = PyMuPDFRoleBRecallParser(
            cache_root=cache_root,
            expected_pdf_sha256=str(verification["sha256"]),
        )
        chunks = parser.parse(
            DocumentParseRequest(document_id=case_id, prospectus_path=str(prospectus))
        )
        retriever = KeywordDocumentRetriever(cache_root=cache_root)
        retrieval = retriever.retrieve(
            chunks, "cash_and_cash_equivalents", limit=20
        )
        semantic_hash = _hash(
            [
                {
                    "page": chunk.page,
                    "section": chunk.section,
                    "text": chunk.text,
                    "bbox": chunk.bbox,
                    "block_type": chunk.block_type,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ]
        )
        records.append(
            {
                "case_id": case_id,
                "pdf_sha256": verification["sha256"],
                "chunk_count": len(chunks),
                "semantic_hash": semantic_hash,
                "cache_metrics": parser.last_cache_metrics,
                "retrieval_semantic_hash": _hash(
                    [item.model_dump(mode="json") for item in retrieval]
                ),
                "retrieval_cache_metrics": retriever.last_cache_metrics,
            }
        )
        print(f"[{ordinal:02d}/{len(case_ids):02d}] {case_id}")
    return records, (time.perf_counter() - started) * 1000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/v045_role_b/existing_gold_evaluable_manifest.json"),
    )
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv")
    )
    parser.add_argument("--cache-root", type=Path, default=Path("data/cache/role_b"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/v046_role_b/cache/dev79_prewarm_summary.json"),
    )
    parser.add_argument("--prospectus-root", type=Path, default=None)
    args = parser.parse_args()

    root = Path.cwd()
    resolved = lambda path: path if path.is_absolute() else root / path
    prospectus_root = args.prospectus_root
    if prospectus_root is None and os.getenv(PROSPECTUS_ROOT_ENV):
        prospectus_root = Path(os.environ[PROSPECTUS_ROOT_ENV])
    if prospectus_root is None or not prospectus_root.is_dir():
        raise RuntimeError("licensed prospectus root is unavailable")

    manifest = json.loads(resolved(args.manifest).read_text(encoding="utf-8"))
    case_ids = _development_case_ids(manifest)
    if len(case_ids) != 79:
        raise RuntimeError(f"expected 79 Development cases, observed {len(case_ids)}")
    catalog = _read_catalog(resolved(args.catalog), "case_id")
    cache_root = resolved(args.cache_root)

    cold, cold_ms = _pass(
        case_ids=case_ids,
        catalog=catalog,
        prospectus_root=prospectus_root,
        cache_root=cache_root,
    )
    warm, warm_ms = _pass(
        case_ids=case_ids,
        catalog=catalog,
        prospectus_root=prospectus_root,
        cache_root=cache_root,
    )
    mismatches = [
        left["case_id"]
        for left, right in zip(cold, warm, strict=True)
        if (
            left["semantic_hash"] != right["semantic_hash"]
            or left["retrieval_semantic_hash"] != right["retrieval_semantic_hash"]
        )
    ]
    if mismatches:
        raise RuntimeError(f"cold/warm semantic mismatch count:{len(mismatches)}")
    summary = {
        "summary_version": "v046_role_b_dev79_cache_prewarm_v2",
        "case_count": len(case_ids),
        "case_set_hash": _hash(case_ids),
        "manifest_hash": manifest.get("manifest_hash"),
        "cold_wall_clock_ms": round(cold_ms, 3),
        "warm_wall_clock_ms": round(warm_ms, 3),
        "speedup_ratio": round(cold_ms / warm_ms, 3) if warm_ms else None,
        "cold_parser_cache_misses": sum(
            int(item["cache_metrics"]["parser_cache_misses"]) for item in cold
        ),
        "warm_parser_cache_hits": sum(
            int(item["cache_metrics"]["parser_cache_hits"]) for item in warm
        ),
        "cold_retrieval_cache_misses": sum(
            int(item["retrieval_cache_metrics"]["retrieval_cache_misses"])
            for item in cold
        ),
        "cold_retrieval_cache_hits": sum(
            int(item["retrieval_cache_metrics"]["retrieval_cache_hits"])
            for item in cold
        ),
        "warm_retrieval_cache_hits": sum(
            int(item["retrieval_cache_metrics"]["retrieval_cache_hits"])
            for item in warm
        ),
        "semantic_mismatch_count": len(mismatches),
        "cache_fingerprints": sorted(
            {
                (
                    item["cache_metrics"]["raw_fingerprint"],
                    item["cache_metrics"]["table_fingerprint"],
                    item["cache_metrics"]["parser_fingerprint"],
                )
                for item in warm
            }
        ),
        "records_hash": _hash(
            [
                {
                    "case_id": item["case_id"],
                    "pdf_sha256": item["pdf_sha256"],
                    "chunk_count": item["chunk_count"],
                    "semantic_hash": item["semantic_hash"],
                    "retrieval_semantic_hash": item["retrieval_semantic_hash"],
                }
                for item in warm
            ]
        ),
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "gold_entered_runtime": False,
        "absolute_paths_persisted": False,
    }
    _safe_write(resolved(args.output), summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
