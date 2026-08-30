#!/usr/bin/env python3
"""Replay a frozen Development concentration cohort and emit a text-free matrix."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
for item in (_ROOT, _SRC):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from ipo_risk.evaluation.role_b_concentration_forensics import (  # noqa: E402
    ConcentrationFormationEvidence,
    classify_concentration_formation,
    summarize_concentration_matrix,
)
from ipo_risk.extraction import TableAwareV03FinancialFactExtractor  # noqa: E402
from ipo_risk.parsers.pymupdf_parser import PyMuPDFRoleBRecallParser  # noqa: E402
from ipo_risk.retrieval.role_b_financial_v046 import (  # noqa: E402
    RoleBFinancialHighRecallRetriever,
)
from ipo_risk.schemas import DocumentParseRequest  # noqa: E402
from scripts.run_v04_role_e_demo import _read_catalog, resolve_prospectus  # noqa: E402


def _hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _seed_units(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = sorted(
        {
            (str(row.get("case_id") or ""), str(row.get("risk_family") or ""))
            for row in rows
            if row.get("classification") == "parser_text_missing"
            and row.get("risk_family")
            in {"customer_concentration", "supplier_concentration"}
        }
    )
    if not selected or any(not case_id for case_id, _ in selected):
        raise RuntimeError("frozen concentration seed cohort is empty or invalid")
    return selected


def _candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    largest = candidate.get("largest_counterparty_pct")
    top_five = candidate.get("top_five_pct")
    return {
        "status": candidate.get("status"),
        "issues": sorted(str(item) for item in candidate.get("issues") or []),
        "period_end": candidate.get("period_end"),
        "period_months": candidate.get("period_months"),
        "largest_present": largest is not None,
        "top_five_present": top_five is not None,
        "value_pair_hash": _hash({"largest": largest, "top_five": top_five}),
        # Numeric-only lifecycle diagnostics are safe to persist locally and
        # make multi-period loss visible without retaining prospectus text.
        "percentage_occurrences": candidate.get("percentage_occurrences", {}),
        "percentage_occurrence_selection": candidate.get(
            "percentage_occurrence_selection", {}
        ),
        "concentration_period_selection": candidate.get(
            "concentration_period_selection"
        ),
        "raw_percentages": candidate.get("raw_percentages", {}),
        "period_candidates": candidate.get("period_candidates", []),
    }


def _classify_fact(case_id: str, risk_code: str, evidence_count: int, fact: Any) -> dict[str, Any]:
    candidates = [
        _candidate_summary(item)
        for item in fact.metadata.get("candidate_diagnostics", [])
        if isinstance(item, Mapping)
    ]
    issue_counts: dict[str, int] = {}
    for candidate in candidates:
        for issue in candidate["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    complete = [
        item for item in candidates if item["largest_present"] and item["top_five_present"]
    ]
    clean_complete = [
        item for item in complete if item["status"] == "extracted" and not item["issues"]
    ]
    structural = ConcentrationFormationEvidence(
        status=fact.status.value,
        merged_issues=tuple(str(item) for item in fact.issues),
        candidate_count=len(candidates),
        clean_complete_candidate_count=len(clean_complete),
        complete_candidate_count=len(complete),
        largest_only_candidate_count=sum(
            item["largest_present"] and not item["top_five_present"] for item in candidates
        ),
        top_five_only_candidate_count=sum(
            item["top_five_present"] and not item["largest_present"] for item in candidates
        ),
        candidate_issue_counts=issue_counts,
    )
    classification = classify_concentration_formation(structural)
    return {
        "case_id": case_id,
        "risk_family": risk_code,
        "retrieved_evidence_count": evidence_count,
        "extraction_status": fact.status.value,
        "merged_issues": sorted(str(item) for item in fact.issues),
        "candidate_count": len(candidates),
        "clean_complete_candidate_count": len(clean_complete),
        "complete_candidate_count": len(complete),
        "largest_only_candidate_count": structural.largest_only_candidate_count,
        "top_five_only_candidate_count": structural.top_five_only_candidate_count,
        "candidate_issue_counts": dict(sorted(issue_counts.items())),
        "candidate_diagnostics": candidates,
        "merge_value_basis": fact.metadata.get("merge_value_basis"),
        **classification,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-audit", type=Path, required=True)
    parser.add_argument("--prospectus-root", type=Path, required=True)
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv")
    )
    parser.add_argument("--cache-root", type=Path, default=Path("data/cache/role_b"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    units = _seed_units(args.seed_audit)
    catalog = _read_catalog(args.catalog, "case_id")
    by_case: dict[str, list[str]] = {}
    for case_id, risk_code in units:
        by_case.setdefault(case_id, []).append(risk_code)

    retriever = RoleBFinancialHighRecallRetriever(cache_root=args.cache_root)
    # Match the frozen Role-B experiment profile. Using the regex extractor
    # here would diagnose a different execution path than the ALL79 run.
    extractor = TableAwareV03FinancialFactExtractor()
    rows: list[dict[str, Any]] = []
    for ordinal, (case_id, risk_codes) in enumerate(sorted(by_case.items()), start=1):
        catalog_row = catalog.get(case_id)
        if catalog_row is None or catalog_row.get("dataset_split") != "development":
            raise RuntimeError(f"Development catalog row unavailable:{case_id}")
        prospectus, verification = resolve_prospectus(
            dict(catalog_row), args.prospectus_root, None
        )
        parser_instance = PyMuPDFRoleBRecallParser(
            cache_root=args.cache_root,
            expected_pdf_sha256=str(verification["sha256"]),
        )
        chunks = parser_instance.parse(
            DocumentParseRequest(document_id=case_id, prospectus_path=str(prospectus))
        )
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        for risk_code in sorted(risk_codes):
            evidence = list(retriever.retrieve_for_risk(chunks, risk_code, limit=20))
            result = extractor.extract_v03(
                net_result_candidates=[],
                revenue_candidates=[],
                customer_concentration_candidates=(
                    evidence if risk_code == "customer_concentration" else []
                ),
                supplier_concentration_candidates=(
                    evidence if risk_code == "supplier_concentration" else []
                ),
                chunks_by_id=chunks_by_id,
            )
            fact = (
                result.customer_concentration
                if risk_code == "customer_concentration"
                else result.supplier_concentration
            )
            rows.append(_classify_fact(case_id, risk_code, len(evidence), fact))
        print(f"[{ordinal:02d}/{len(by_case):02d}] {case_id}")

    summary = {
        "audit_version": "v046_role_b_concentration_formation_v1",
        "source_revision": _git_revision(),
        "seed_unit_count": len(units),
        "seed_hash": _hash(units),
        **summarize_concentration_matrix(rows),
        "gold_used_at_runtime": False,
        "gold_join_stage": "post_run_case_selection_only",
        "network_calls": 0,
        "validation_opened": False,
        "blind_2025_accessed": False,
        "raw_prospectus_text_persisted": False,
        "raw_gold_text_persisted": False,
        "absolute_paths_persisted": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "concentration_formation_matrix.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "concentration_formation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
