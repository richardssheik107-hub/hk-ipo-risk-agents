"""Run the frozen precommercial V2.2 candidate experiment with low disk use."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
from math import ceil
from pathlib import Path
import shutil
import tempfile
import zipfile

from ipo_risk.evaluation.retrieval_40_annotations import discover_annotation_files, load_annotation
from ipo_risk.evaluation.retrieval_40_benchmark import K_VALUES, _CaseQueryCache
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.precommercial_v22 import (
    PRECOMMERCIAL_V22_QUERY_FAMILIES,
    PrecommercialCandidateRetrieverV22,
)
from ipo_risk.schemas import DocumentParseRequest


RISK_CODE = "precommercial_product"
HISTORICAL_CASES = {
    "ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408", "ipo_2020_01961",
    "ipo_2020_01942", "ipo_2020_02057", "ipo_2020_02135", "ipo_2020_02263",
    "ipo_2020_02599", "ipo_2021_00013",
}


def case_split(cases: list[str]) -> dict[str, str]:
    """Reproduce the already-published deterministic 40-case split."""
    unseen = sorted(
        (case for case in cases if case not in HISTORICAL_CASES),
        key=lambda value: hashlib.sha256(value.encode()).hexdigest(),
    )
    development = set(unseen[: max(1, len(unseen) // 3)])
    return {
        case: (
            "historical_development" if case in HISTORICAL_CASES
            else "development" if case in development
            else "locked_validation"
        )
        for case in cases
    }


def _catalog(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _matrix(path: Path) -> dict[tuple[str, int, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            (row["case_id"], int(row["gold_page"]), row["evidence_id"]): row
            for row in csv.DictReader(handle)
            if row["risk_code"] == RISK_CODE
        }


def _copy_annual_archive(outer: zipfile.ZipFile, year: str, target: Path) -> None:
    matches = [
        item for item in outer.infolist()
        if not item.is_dir() and item.filename.endswith(".zip")
        and Path(item.filename).name.startswith(year)
    ]
    if len(matches) != 1:
        raise FileNotFoundError(f"annual archive for {year}: matches={len(matches)}")
    with outer.open(matches[0]) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _extract_one_pdf(annual: zipfile.ZipFile, filename: str, target: Path) -> None:
    matches = [
        item for item in annual.infolist()
        if not item.is_dir() and Path(item.filename).name == filename
    ]
    if len(matches) != 1:
        raise FileNotFoundError(f"PDF member {filename}: matches={len(matches)}")
    with annual.open(matches[0]) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _rank(pages: list[int], page: int) -> int | None:
    return pages.index(page) + 1 if page in pages else None


def _old_rank(value: str) -> int | None:
    return int(value) if value.strip() else None


def _metric(rows: list[dict], field: str, k: int) -> float:
    return sum(row[field] is not None and row[field] <= k for row in rows) / len(rows) if rows else 0.0


def _metrics(rows: list[dict]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for split in ("historical_development", "development", "locked_validation", "all"):
        selected = rows if split == "all" else [row for row in rows if row["split"] == split]
        values: dict[str, float | int] = {"gold": len(selected)}
        for version in ("v1", "v2", "v21", "v22"):
            values.update({f"{version}_r{k}": _metric(selected, f"{version}_rank", k) for k in K_VALUES})
        result[split] = values
    return result


def _p95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[max(0, ceil(0.95 * len(ordered)) - 1)] if ordered else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip", required=True, type=Path)
    parser.add_argument("--expert-root", type=Path, default=Path("expert_results"))
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--matrix", type=Path, default=Path("reports/retrieval_40_baseline/retrieval_error_matrix.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/retrieval_40_baseline/precommercial_product_v22_results.json"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    args = parser.parse_args()

    root = Path.cwd()
    files = [
        path for path in discover_annotation_files(args.expert_root)
        if path.relative_to(args.expert_root).parts[0].startswith("ipo_")
    ]
    cases = [load_annotation(path, repository_root=root) for path in files]
    if len(cases) != 40:
        raise ValueError(f"expected 40 IPO cases, found {len(cases)}")
    splits = case_split([case.case_id for case in cases])
    catalog = _catalog(args.catalog)
    matrix = _matrix(args.matrix)
    disk_before = shutil.disk_usage(args.temp_parent).free
    rows: list[dict] = []
    candidate_sizes: list[int] = []
    v21_sizes: list[int] = []
    baseline_mismatches: list[dict] = []
    parser_errors = 0

    with tempfile.TemporaryDirectory(prefix=".tmp_precommercial_v22_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[case.case_id]["source_year"] for case in cases}):
                annual_path = temp / f"{year}.zip"
                print(f"[{year}] staging one annual archive")
                _copy_annual_archive(outer, year, annual_path)
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        year_cases = [case for case in cases if catalog[case.case_id]["source_year"] == year]
                        for index, case in enumerate(year_cases, 1):
                            pdf_path = temp / "current.pdf"
                            try:
                                _extract_one_pdf(annual, catalog[case.case_id]["source_filename"], pdf_path)
                                parser_impl = PyMuPDFDocumentParser()
                                chunks = parser_impl.parse(DocumentParseRequest(
                                    document_id=case.case_id,
                                    prospectus_path=str(pdf_path),
                                ))
                                parser_errors += len(parser_impl.last_errors)
                                base = _CaseQueryCache()
                                baseline = DomainAwareRetrieverV21(base=base)
                                v22 = PrecommercialCandidateRetrieverV22(base=base, baseline=baseline)
                                old_items = baseline.retrieve_for_risk(chunks, RISK_CODE, limit=50)
                                new_items = v22.retrieve_for_risk(chunks, RISK_CODE, limit=50)
                                old_pages = [item.page for item in old_items if item.page is not None]
                                new_pages = [item.page for item in new_items if item.page is not None]
                                by_page = {item.page: item for item in new_items if item.page is not None}
                                candidate_sizes.append(len(new_pages)); v21_sizes.append(len(old_pages))
                                gold = [
                                    item for item in case.evidence
                                    if item.risk_code == RISK_CODE and item.requirement == "required"
                                ]
                                for item in gold:
                                    source = matrix[(case.case_id, item.page, item.evidence_id)]
                                    v21_rank = _rank(old_pages, item.page)
                                    matrix_v21_rank = _old_rank(source["v21_rank"])
                                    if v21_rank != matrix_v21_rank:
                                        baseline_mismatches.append({
                                            "case_id": case.case_id, "gold_page": item.page,
                                            "matrix_v21_rank": matrix_v21_rank, "rerun_v21_rank": v21_rank,
                                        })
                                    v22_rank = _rank(new_pages, item.page)
                                    candidate = by_page.get(item.page)
                                    metadata = candidate.metadata if candidate else {}
                                    rows.append({
                                        "case_id": case.case_id,
                                        "split": splits[case.case_id],
                                        "gold_page": item.page,
                                        "evidence_id": item.evidence_id,
                                        "source_authority": item.source_authority,
                                        "evidence_role": item.evidence_role,
                                        "v1_rank": _old_rank(source["v1_rank"]),
                                        "v2_rank": _old_rank(source["v2_rank"]),
                                        "v21_rank": v21_rank,
                                        "v22_rank": v22_rank,
                                        "v22_candidate_source": metadata.get("retriever", ""),
                                        "v22_query_family": metadata.get("query_family", ""),
                                        "v22_query_text": metadata.get("query_text", ""),
                                        "v22_neighbour_distance": metadata.get("neighbour_distance"),
                                    })
                                print(f"[{year} {index}/{len(year_cases)}] {case.case_id}: old={len(old_pages)} new={len(new_pages)} gold={len(gold)}")
                            finally:
                                pdf_path.unlink(missing_ok=True)
                                if "chunks" in locals():
                                    del chunks
                                gc.collect()
                finally:
                    annual_path.unlink(missing_ok=True)

    disk_after = shutil.disk_usage(args.temp_parent).free
    gains = [
        row for row in rows
        if (row["v21_rank"] is None or row["v21_rank"] > 50)
        and row["v22_rank"] is not None and row["v22_rank"] <= 50
    ]
    regressions = [
        row for row in rows
        if row["v21_rank"] is not None and row["v21_rank"] <= 50
        and (row["v22_rank"] is None or row["v22_rank"] > 50)
    ]
    payload = {
        "experiment": "precommercial_product_candidate_v22_round1",
        "risk_code": RISK_CODE,
        "candidate_generation_only": True,
        "baseline_order_preserved": True,
        "query_families": [
            {"name": family.name, "phrases": list(family.phrases)}
            for family in PRECOMMERCIAL_V22_QUERY_FAMILIES
        ],
        "query_depth": 5,
        "neighbour_radius": 1,
        "candidate_limit": 50,
        "metrics": _metrics(rows),
        "candidate_size": {
            "v21_mean": sum(v21_sizes) / len(v21_sizes),
            "v21_p95": _p95(v21_sizes),
            "v22_mean": sum(candidate_sizes) / len(candidate_sizes),
            "v22_p95": _p95(candidate_sizes),
        },
        "gains_at_50": len(gains),
        "gain_cases_at_50": sorted({row["case_id"] for row in gains}),
        "regressions_at_50": len(regressions),
        "parser_errors": parser_errors,
        "baseline_mismatches": baseline_mismatches,
        "disk_free_before_bytes": disk_before,
        "disk_free_after_bytes": disk_after,
        "temporary_directory_removed": True,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "completed": True,
        "gold": len(rows),
        "gains_at_50": len(gains),
        "regressions_at_50": len(regressions),
        "baseline_mismatches": len(baseline_mismatches),
        "temporary_directory_removed": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
