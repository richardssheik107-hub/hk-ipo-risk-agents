"""Replay fixed-10 cash-runway retrieval without LLM or runtime Gold access.

The retriever sees parsed Development prospectus pages only. Existing Gold is
joined after retrieval solely to calculate page/anchor ranks. Persisted output
contains hashes and ranks, never prospectus or Gold text or local paths.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import re
import subprocess
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from run_fixed10_zip_offline_baseline import YEAR_ARCHIVES, load_subset
    from run_v045_role_b_offline_pdf_benchmark import (
        exact_member,
        stream_member,
        validate_archive_members,
        validate_pdf_identity,
    )
except ModuleNotFoundError:  # imported as ``scripts.*`` by tests
    from scripts.run_fixed10_zip_offline_baseline import YEAR_ARCHIVES, load_subset
    from scripts.run_v045_role_b_offline_pdf_benchmark import (
        exact_member,
        stream_member,
        validate_archive_members,
        validate_pdf_identity,
    )

from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.role_b_financial_v046 import RoleBFinancialHighRecallRetriever
from ipo_risk.schemas import DocumentParseRequest


class CashRunwayAuditError(RuntimeError):
    """A governed replay invariant failed."""


def _canonical_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"\s+", "", text)


def _text_anchor_matches(gold_text: str, candidate_text: str) -> bool:
    """Mirror the frozen v0.4.6 evaluator's 12-character anchor rule."""
    gold = _canonical_text(gold_text)
    candidate = _canonical_text(candidate_text)
    if not gold or not candidate:
        return False
    if min(len(gold), len(candidate)) < 12:
        return gold == candidate
    return gold in candidate or candidate in gold


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def load_catalog(path: Path, case_ids: Iterable[str]) -> dict[str, dict[str, str]]:
    requested = set(case_ids)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = {
            row["case_id"]: row
            for row in csv.DictReader(handle)
            if row.get("case_id") in requested
        }
    if set(rows) != requested:
        raise CashRunwayAuditError("one or more fixed-10 catalog rows are missing")
    for case_id, row in rows.items():
        if row.get("dataset_split") != "development":
            raise CashRunwayAuditError(f"non-Development case rejected:{case_id}")
        if int(row["source_year"]) not in YEAR_ARCHIVES:
            raise CashRunwayAuditError(f"disallowed source year:{case_id}")
    return rows


def load_cash_units(path: Path, case_ids: Iterable[str]) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("blind_2025_outcome_accessed") is not False:
        raise CashRunwayAuditError("Existing-Gold manifest blind guard is not false")
    selected = set(case_ids)
    units = [
        row
        for row in payload.get("evidence_units", [])
        if row.get("case_id") in selected
        and row.get("split") == "development"
        and row.get("source_risk_code") == "cash_runway"
        and row.get("primary_scope") is True
    ]
    if not units:
        raise CashRunwayAuditError("no fixed-10 cash-runway Evidence units found")
    if any(not row.get("exact_text") or not row.get("exact_text_hash") for row in units):
        raise CashRunwayAuditError("cash-runway Evidence unit lacks anchor provenance")
    return units


def rank_units(
    *,
    case_id: str,
    units: Iterable[dict[str, Any]],
    candidates: Iterable[Any],
) -> list[dict[str, Any]]:
    materialized = list(candidates)
    rows: list[dict[str, Any]] = []
    for unit in units:
        expected_page = int(unit["page"])
        page_rank = next(
            (rank for rank, value in enumerate(materialized, start=1) if value.page == expected_page),
            None,
        )
        anchor_rank = next(
            (
                rank
                for rank, value in enumerate(materialized, start=1)
                if value.page == expected_page
                and _text_anchor_matches(str(unit["exact_text"]), value.text)
            ),
            None,
        )
        rows.append(
            {
                "case_id": case_id,
                "evidence_unit_id": str(unit["evidence_unit_id"]),
                "exact_text_hash": str(unit["exact_text_hash"]),
                "expected_page": expected_page,
                "candidate_count": len(materialized),
                "first_gold_page_rank": page_rank,
                "first_gold_anchor_rank": anchor_rank,
                "page_hit_at_20": page_rank is not None and page_rank <= 20,
                "anchor_hit_at_20": anchor_rank is not None and anchor_rank <= 20,
            }
        )
    return rows


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    count = len(materialized)
    page_hits = sum(bool(row["page_hit_at_20"]) for row in materialized)
    anchor_hits = sum(bool(row["anchor_hit_at_20"]) for row in materialized)
    return {
        "evidence_unit_count": count,
        "case_count": len({row["case_id"] for row in materialized}),
        "page_hit_at_20_count": page_hits,
        "page_recall_at_20": page_hits / count if count else None,
        "anchor_hit_at_20_count": anchor_hits,
        "anchor_recall_at_20": anchor_hits / count if count else None,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    case_ids = load_subset(args.subset)
    subset_payload = json.loads(args.subset.read_text(encoding="utf-8"))
    catalog = load_catalog(args.catalog, case_ids)
    units = load_cash_units(args.gold_manifest, case_ids)
    units_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        units_by_case[str(unit["case_id"])].append(unit)

    parser = PyMuPDFDocumentParser()
    retriever = RoleBFinancialHighRecallRetriever()
    result_rows: list[dict[str, Any]] = []
    parsed_cases: list[str] = []
    args.temp_parent.mkdir(parents=True, exist_ok=True)
    pdf_path = args.temp_parent / "current.pdf"
    if pdf_path.exists():
        raise CashRunwayAuditError("refusing to overwrite existing temporary current.pdf")
    try:
        with zipfile.ZipFile(args.outer_zip) as outer:
            outer_infos = validate_archive_members(outer.infolist())
            relevant_cases = [case_id for case_id in case_ids if case_id in units_by_case]
            for year in sorted({int(catalog[case_id]["source_year"]) for case_id in relevant_cases}):
                annual_info = exact_member(outer_infos, basename=YEAR_ARCHIVES[year])
                with outer.open(annual_info) as annual_stream, zipfile.ZipFile(annual_stream) as annual:
                    annual_infos = validate_archive_members(annual.infolist())
                    for case_id in [
                        value
                        for value in relevant_cases
                        if int(catalog[value]["source_year"]) == year
                    ]:
                        row = catalog[case_id]
                        try:
                            info = exact_member(annual_infos, basename=row["source_filename"])
                            stream_member(annual, info, pdf_path)
                            validate_pdf_identity(pdf_path, row)
                            chunks = parser.parse(
                                DocumentParseRequest(
                                    document_id=case_id,
                                    prospectus_path=str(pdf_path),
                                )
                            )
                            candidates = retriever.retrieve_for_risk(
                                chunks, "cash_runway", limit=20
                            )
                            result_rows.extend(
                                rank_units(
                                    case_id=case_id,
                                    units=units_by_case[case_id],
                                    candidates=candidates,
                                )
                            )
                            parsed_cases.append(case_id)
                            print(
                                f"case={case_id} pages={len(chunks)} "
                                f"candidates={len(candidates)} status=completed"
                            )
                        finally:
                            if pdf_path.exists():
                                pdf_path.unlink()
                            gc.collect()
    finally:
        if pdf_path.exists():
            pdf_path.unlink()

    if len(result_rows) != len(units):
        raise CashRunwayAuditError(
            f"result coverage mismatch:{len(result_rows)} != {len(units)}"
        )
    result_rows.sort(key=lambda row: (row["case_id"], row["evidence_unit_id"]))
    summary = summarize(result_rows)
    payload = {
        "audit_id": "v046_fixed10_cash_runway_trace_replay_v1",
        "source_revision": _git_revision(),
        "trace_contract_fix_applied": True,
        "retriever": retriever.name,
        "retriever_version": retriever.version,
        "query_risk_code": "cash_runway",
        "candidate_limit": 20,
        "fixed10_manifest_sha256": _sha256(args.subset),
        "fixed10_subset_hash": str(subset_payload.get("subset_hash") or ""),
        "existing_gold_manifest_sha256": _sha256(args.gold_manifest),
        "catalog_sha256": _sha256(args.catalog),
        "selected_case_count": len(case_ids),
        "parsed_case_count": len(parsed_cases),
        "parsed_cases": sorted(parsed_cases),
        "summary": summary,
        "evidence_units": result_rows,
        "runtime_gold_accessed": False,
        "gold_join_stage": "post_retrieval_metric_only",
        "llm_calls": 0,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "prospectus_text_persisted": False,
        "gold_text_persisted": False,
        "local_paths_persisted": False,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["audit_payload_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outer_zip", type=Path)
    parser.add_argument(
        "--subset",
        type=Path,
        default=Path("reports/v045_role_b/fixed10_development_subset.json"),
    )
    parser.add_argument(
        "--gold-manifest",
        type=Path,
        default=Path("reports/v045_role_b/existing_gold_evaluable_manifest.json"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/catalog/ipo_prospectus_manifest.csv"),
    )
    parser.add_argument("--temp-parent", type=Path, default=Path("reports/experiments"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/experiments/V046_CASH_RUNWAY_TRACE_REPLAY.json"),
    )
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
