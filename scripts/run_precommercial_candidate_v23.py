"""Low-disk development/frozen runner for the precommercial V2.3 experiment."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gc
import hashlib
import json
from math import ceil
from pathlib import Path
import shutil
import statistics
import tempfile
import zipfile

from ipo_risk.evaluation.retrieval_40_annotations import discover_annotation_files, load_annotation
from ipo_risk.evaluation.retrieval_40_benchmark import K_VALUES, _CaseQueryCache
from ipo_risk.parsers.pymupdf_parser import PyMuPDFTableDocumentParser
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.precommercial_v23 import (
    EvidenceIntent, PrecommercialCandidateRetrieverV23, V23_VARIANTS,
    bounded_candidate_union, classify_evidence_intent,
)
from ipo_risk.schemas import DocumentChunk, DocumentParseRequest, Evidence


RISK_CODE = "precommercial_product"
# Frozen after the one development-only A/B/C comparison.  B tied C on every
# development recall metric while retaining four more V2.1 base slots.
FROZEN_VARIANT: str | None = "v23_b"
HISTORICAL_CASES = {
    "ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408", "ipo_2020_01961",
    "ipo_2020_01942", "ipo_2020_02057", "ipo_2020_02135", "ipo_2020_02263",
    "ipo_2020_02599", "ipo_2021_00013",
}


class _StaticBaseline:
    def __init__(self, items: list[Evidence]) -> None:
        self.items = items

    def retrieve_for_risk(self, chunks, risk_code, *, limit=50):
        return self.items[:limit]


def case_split(cases: list[str]) -> dict[str, str]:
    unseen = sorted((case for case in cases if case not in HISTORICAL_CASES),
                    key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    development = set(unseen[: max(1, len(unseen) // 3)])
    return {case: ("historical_development" if case in HISTORICAL_CASES else
                   "development" if case in development else "locked_validation") for case in cases}


def _catalog(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _matrix(path: Path) -> dict[tuple[str, int, str], dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {(row["case_id"], int(row["gold_page"]), row["evidence_id"]): row
                for row in csv.DictReader(handle) if row["risk_code"] == RISK_CODE}


def _v22(path: Path) -> dict[tuple[str, int, str], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {(row["case_id"], int(row["gold_page"]), row["evidence_id"]): row for row in payload["rows"]}


def _applicability(files: list[Path]) -> dict[str, bool]:
    output: dict[str, bool] = {}
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        risk = next((item for item in payload.get("risks", []) if item.get("risk_code") == RISK_CODE), None)
        output[str(payload.get("case_id"))] = bool(risk and risk.get("applicable"))
    return output


def _copy_annual_archive(outer: zipfile.ZipFile, year: str, target: Path) -> None:
    matches = [item for item in outer.infolist() if not item.is_dir() and item.filename.endswith(".zip")
               and Path(item.filename).name.startswith(year)]
    if len(matches) != 1:
        raise FileNotFoundError(f"annual archive for {year}: matches={len(matches)}")
    with outer.open(matches[0]) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _extract_one_pdf(annual: zipfile.ZipFile, filename: str, target: Path) -> None:
    matches = [item for item in annual.infolist() if not item.is_dir() and Path(item.filename).name == filename]
    if len(matches) != 1:
        raise FileNotFoundError(f"PDF member {filename}: matches={len(matches)}")
    with annual.open(matches[0]) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)


def _plain_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    output = []
    for chunk in chunks:
        metadata = {key: value for key, value in chunk.metadata.items()
                    if key not in {"tables", "has_structured_tables"}}
        metadata["parser"] = "pymupdf"
        output.append(chunk.model_copy(update={"metadata": metadata}))
    return output


def _rank(pages: list[int], page: int) -> int | None:
    return pages.index(page) + 1 if page in pages else None


def _old_rank(value) -> int | None:
    return int(value) if value not in (None, "") and str(value).strip() else None


def _family_for_page(items: list[Evidence], page: int) -> str:
    item = next((candidate for candidate in items if candidate.page == page), None)
    return str(item.metadata.get("query_family", "")) if item else ""


def _metric(rows: list[dict], field: str, k: int) -> float:
    return sum(row.get(field) is not None and row[field] <= k for row in rows) / len(rows) if rows else 0.0


def _summary_stats(values: list[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    return {
        "average": sum(ordered) / len(ordered) if ordered else 0.0,
        "median": statistics.median(ordered) if ordered else 0.0,
        "p95": ordered[max(0, ceil(0.95 * len(ordered)) - 1)] if ordered else 0,
        "max": max(ordered) if ordered else 0,
    }


def _variant_summary(rows: list[dict], counts: list[dict], version: str) -> dict:
    selected = [row for row in rows if row["split"] == "development"]
    result = {"gold": len(selected)}
    for k in K_VALUES:
        result[f"r{k}"] = _metric(selected, f"{version}_rank", k)
    result["new_at_20_vs_v22"] = sum((row["v22_rank"] is None or row["v22_rank"] > 20) and row[f"{version}_rank"] is not None and row[f"{version}_rank"] <= 20 for row in selected)
    result["lost_at_20_vs_v22"] = sum(row["v22_rank"] is not None and row["v22_rank"] <= 20 and (row[f"{version}_rank"] is None or row[f"{version}_rank"] > 20) for row in selected)
    result["new_at_50_vs_v22"] = sum((row["v22_rank"] is None or row["v22_rank"] > 50) and row[f"{version}_rank"] is not None and row[f"{version}_rank"] <= 50 for row in selected)
    result["lost_at_50_vs_v22"] = sum(row["v22_rank"] is not None and row["v22_rank"] <= 50 and (row[f"{version}_rank"] is None or row[f"{version}_rank"] > 50) for row in selected)
    result["gain_cases_at_50"] = sorted({row["case_id"] for row in selected if (row["v22_rank"] is None or row["v22_rank"] > 50) and row[f"{version}_rank"] is not None and row[f"{version}_rank"] <= 50})
    result["candidate_count"] = _summary_stats([row[f"{version}_count"] for row in counts if row["split"] == "development"])
    return result


def _metrics(rows: list[dict], frozen: str) -> dict:
    result = {}
    for split in ("historical_development", "development", "locked_validation", "all"):
        selected = rows if split == "all" else [row for row in rows if row["split"] == split]
        values: dict[str, float | int] = {"gold": len(selected)}
        for version in ("v1", "v2", "v21", "v22", "v23"):
            field = f"{frozen}_rank" if version == "v23" else f"{version}_rank"
            values.update({f"{version}_r{k}": _metric(selected, field, k) for k in K_VALUES})
        result[split] = values
    return result


def _intent_summary(rows: list[dict]) -> dict:
    all_intents = Counter(row["intent"] for row in rows)
    misses = Counter(row["intent"] for row in rows if row["v21_rank"] is None or row["v21_rank"] > 50)
    authority: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        authority[row["intent"]][row["source_authority"]] += 1
    return {
        "all_gold": dict(sorted(all_intents.items())),
        "v21_top50_miss": dict(sorted(misses.items())),
        "source_authority_by_intent": {intent: dict(sorted(values.items())) for intent, values in sorted(authority.items())},
        "section_available": False,
    }


def _oracle(rows: list[dict]) -> dict:
    result = {}
    for split in ("historical_development", "development", "locked_validation", "all"):
        selected = rows if split == "all" else [row for row in rows if row["split"] == split]
        result[split] = {
            "gold": len(selected),
            "route_a_hits": sum(row["route_a_raw_hit"] for row in selected),
            "route_b_hits": sum(row["route_b_raw_hit"] for row in selected),
            "both_hits": sum(row["route_a_raw_hit"] and row["route_b_raw_hit"] for row in selected),
            "union_hits": sum(row["route_a_raw_hit"] or row["route_b_raw_hit"] for row in selected),
        }
    return result


def _remaining_reason(row: dict) -> str:
    if row["route_a_raw_hit"] or row["route_b_raw_hit"]:
        return "candidate_merge_problem"
    if row["route_neighbour_hit"]:
        return "page_neighbour_problem"
    if row["intent"] == EvidenceIntent.REVENUE_NATURE.value and row["source_authority"] == "accountants_report":
        return "table_parsing_problem"
    if row["intent"] == EvidenceIntent.SERVICE_REVENUE_EXISTS.value:
        return "section_not_routed"
    if row["intent"] in {EvidenceIntent.PRODUCT_LIFECYCLE.value, EvidenceIntent.PRODUCT_REVENUE_EXISTS.value}:
        return "lexical_mismatch"
    return "intent_not_covered"


def _refresh_analysis_only(output: Path, expert_root: Path) -> None:
    payload = json.loads(output.read_text(encoding="utf-8"))
    files = [path for path in discover_annotation_files(expert_root)
             if path.relative_to(expert_root).parts[0].startswith("ipo_")]
    applicable = _applicability(files)
    rows = payload["rows"]
    for row in rows:
        row["intent"] = classify_evidence_intent(
            row["exact_text_preview"], row["source_authority"], applicable[row["case_id"]],
        ).value
    frozen = payload["frozen_variant"]
    newly = [row for row in rows if (row["v22_rank"] is None or row["v22_rank"] > 50)
             and row[f"{frozen}_rank"] is not None and row[f"{frozen}_rank"] <= 50]
    lost = [row for row in rows if row["v22_rank"] is not None and row["v22_rank"] <= 50
            and (row[f"{frozen}_rank"] is None or row[f"{frozen}_rank"] > 50)]
    for row in newly:
        routes = [name for name, hit in (("route_a", row["route_a_raw_hit"]), ("route_b", row["route_b_raw_hit"])) if hit]
        row["why_recovered"] = f"bounded union retained {','.join(routes)}; family={row['route_a_family'] or row['route_b_family']}"
    payload["intent_summary"] = _intent_summary(rows)
    payload["newly_recovered"] = newly
    payload["lost_previous"] = lost
    payload["locked_top50_remaining_misses"] = [
        dict(row, final_miss_reason=_remaining_reason(row)) for row in rows
        if row["split"] == "locked_validation" and (row[f"{frozen}_rank"] is None or row[f"{frozen}_rank"] > 50)
    ]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"analysis_refreshed": True, "rows": len(rows),
                      "intent_summary": payload["intent_summary"]}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("development", "frozen", "analysis"), required=True)
    parser.add_argument("--outer-zip", type=Path)
    parser.add_argument("--expert-root", type=Path, default=Path("expert_results"))
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--matrix", type=Path, default=Path("reports/retrieval_40_baseline/retrieval_error_matrix.csv"))
    parser.add_argument("--v22", type=Path, default=Path("reports/retrieval_40_baseline/precommercial_product_v22_results.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/retrieval_40_baseline/precommercial_product_v23_results.json"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    args = parser.parse_args()
    if args.phase == "analysis":
        _refresh_analysis_only(args.output, args.expert_root)
        return 0
    if args.outer_zip is None:
        raise ValueError("--outer-zip is required for development/frozen phases")
    if args.phase == "frozen" and FROZEN_VARIANT is None:
        raise ValueError("V23_NOT_FROZEN: run development, select one variant, then set FROZEN_VARIANT")

    root = Path.cwd()
    files = [path for path in discover_annotation_files(args.expert_root)
             if path.relative_to(args.expert_root).parts[0].startswith("ipo_")]
    cases = [load_annotation(path, repository_root=root) for path in files]
    if len(cases) != 40:
        raise ValueError(f"expected 40 IPO cases, found {len(cases)}")
    splits = case_split([case.case_id for case in cases])
    selected_splits = {"historical_development", "development"} if args.phase == "development" else set(splits.values())
    selected_cases = [case for case in cases if splits[case.case_id] in selected_splits]
    catalog = _catalog(args.catalog); matrix = _matrix(args.matrix); v22 = _v22(args.v22)
    applicable = _applicability(files)
    disk_before = shutil.disk_usage(args.temp_parent).free; min_free = disk_before
    rows: list[dict] = []; counts: list[dict] = []; parser_errors = 0; mismatches: list[dict] = []

    with tempfile.TemporaryDirectory(prefix=".tmp_precommercial_v23_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[case.case_id]["source_year"] for case in selected_cases}):
                annual_path = temp / f"{year}.zip"; _copy_annual_archive(outer, year, annual_path)
                min_free = min(min_free, shutil.disk_usage(args.temp_parent).free)
                print(f"[{args.phase} {year}] staged one annual archive")
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        year_cases = [case for case in selected_cases if catalog[case.case_id]["source_year"] == year]
                        for index, case in enumerate(year_cases, 1):
                            pdf_path = temp / "current.pdf"
                            try:
                                _extract_one_pdf(annual, catalog[case.case_id]["source_filename"], pdf_path)
                                min_free = min(min_free, shutil.disk_usage(args.temp_parent).free)
                                parser_impl = PyMuPDFTableDocumentParser()
                                chunks = parser_impl.parse(DocumentParseRequest(document_id=case.case_id, prospectus_path=str(pdf_path)))
                                parser_errors += len(parser_impl.last_errors); plain = _plain_chunks(chunks)
                                old = DomainAwareRetrieverV21(base=_CaseQueryCache()).retrieve_for_risk(plain, RISK_CODE, limit=50)
                                experiment = PrecommercialCandidateRetrieverV23(route_base=KeywordDocumentRetriever(), baseline=_StaticBaseline(old))
                                universe = experiment.candidate_universe(chunks, RISK_CODE, variant="v23_a", baseline_chunks=plain)
                                merged = {name: bounded_candidate_union(universe.base, universe.route_a, universe.route_b,
                                                                        policy=policy, limit=50)
                                          for name, policy in V23_VARIANTS.items()}
                                pages = {name: [item.page for item in items if item.page is not None] for name, items in merged.items()}
                                base_pages = [item.page for item in universe.base if item.page is not None]
                                a_pages = [item.page for item in universe.route_a if item.page is not None]
                                b_pages = [item.page for item in universe.route_b if item.page is not None]
                                counts.append({
                                    "case_id": case.case_id, "split": splits[case.case_id],
                                    "base_count": len(base_pages), "route_a_count": len(a_pages), "route_b_count": len(b_pages),
                                    "raw_union_dedup_count": len(set(base_pages + a_pages + b_pages)),
                                    **{f"{name}_count": len(value) for name, value in pages.items()},
                                })
                                gold = [item for item in case.evidence if item.risk_code == RISK_CODE and item.requirement == "required"]
                                for item in gold:
                                    key = (case.case_id, item.page, item.evidence_id); source = matrix[key]; old_v22 = v22[key]
                                    v21_rank = _rank(base_pages, item.page); matrix_rank = _old_rank(source["v21_rank"])
                                    if v21_rank != matrix_rank:
                                        mismatches.append({"case_id": case.case_id, "gold_page": item.page,
                                                           "matrix_v21_rank": matrix_rank, "rerun_v21_rank": v21_rank})
                                    a_hit = item.page in a_pages; b_hit = item.page in b_pages
                                    route_union = set(a_pages + b_pages)
                                    row = {
                                        "case_id": case.case_id, "split": splits[case.case_id], "gold_page": item.page,
                                        "evidence_id": item.evidence_id, "source_authority": item.source_authority,
                                        "evidence_role": item.evidence_role,
                                        "intent": classify_evidence_intent(item.exact_text, item.source_authority, applicable[case.case_id]).value,
                                        "exact_text_preview": " ".join(item.exact_text.split())[:240],
                                        "v1_rank": _old_rank(source["v1_rank"]), "v2_rank": _old_rank(source["v2_rank"]),
                                        "v21_rank": v21_rank, "v22_rank": _old_rank(old_v22["v22_rank"]),
                                        "route_a_raw_hit": a_hit, "route_b_raw_hit": b_hit,
                                        "route_a_family": _family_for_page(universe.route_a, item.page),
                                        "route_b_family": _family_for_page(universe.route_b, item.page),
                                        "route_neighbour_hit": item.page - 1 in route_union or item.page + 1 in route_union,
                                    }
                                    row.update({f"{name}_rank": _rank(value, item.page) for name, value in pages.items()})
                                    rows.append(row)
                                print(f"[{args.phase} {year} {index}/{len(year_cases)}] {case.case_id}: base={len(base_pages)} A={len(a_pages)} B={len(b_pages)}")
                            finally:
                                pdf_path.unlink(missing_ok=True)
                                for variable in ("chunks", "plain"):
                                    if variable in locals():
                                        del locals()[variable]
                                gc.collect()
                finally:
                    annual_path.unlink(missing_ok=True)

    disk_after = shutil.disk_usage(args.temp_parent).free
    if args.phase == "development":
        print(json.dumps({
            "phase": "development", "variants": {name: _variant_summary(rows, counts, name) for name in V23_VARIANTS},
            "parser_errors": parser_errors, "baseline_mismatches": mismatches,
            "raw_oracle": _oracle(rows), "temporary_directory_removed": True,
            "disk_free_before_bytes": disk_before, "maximum_temporary_bytes": max(0, disk_before - min_free),
            "disk_free_after_bytes": disk_after,
        }, ensure_ascii=False, indent=2))
        return 0

    frozen = FROZEN_VARIANT or ""
    newly = [row for row in rows if (row["v22_rank"] is None or row["v22_rank"] > 50)
             and row[f"{frozen}_rank"] is not None and row[f"{frozen}_rank"] <= 50]
    lost = [row for row in rows if row["v22_rank"] is not None and row["v22_rank"] <= 50
            and (row[f"{frozen}_rank"] is None or row[f"{frozen}_rank"] > 50)]
    for row in newly:
        routes = [name for name, hit in (("route_a", row["route_a_raw_hit"]), ("route_b", row["route_b_raw_hit"])) if hit]
        row["why_recovered"] = f"bounded union retained {','.join(routes)}; family={row['route_a_family'] or row['route_b_family']}"
    remaining_locked = [dict(row, final_miss_reason=_remaining_reason(row)) for row in rows
                        if row["split"] == "locked_validation" and (row[f"{frozen}_rank"] is None or row[f"{frozen}_rank"] > 50)]
    payload = {
        "experiment": "precommercial_product_candidate_v23", "frozen_variant": frozen,
        "variant_policy": V23_VARIANTS[frozen].__dict__, "candidate_generation_only": True,
        "final_candidate_limit": 50, "raw_route_limit_each": 50,
        "metrics": _metrics(rows, frozen), "intent_summary": _intent_summary(rows), "raw_route_oracle": _oracle(rows),
        "candidate_counts": {
            field: _summary_stats([row[field] for row in counts])
            for field in ("base_count", "route_a_count", "route_b_count", "raw_union_dedup_count", f"{frozen}_count")
        },
        "newly_recovered_at_50": len(newly), "locked_newly_recovered_at_50": sum(row["split"] == "locked_validation" for row in newly),
        "locked_gain_cases": sorted({row["case_id"] for row in newly if row["split"] == "locked_validation"}),
        "lost_previous_at_50": len(lost), "net_gold_gain_at_50": len(newly) - len(lost),
        "route_a_newly_recovered": sum(row["route_a_raw_hit"] and not row["route_b_raw_hit"] for row in newly),
        "route_b_newly_recovered": sum(row["route_b_raw_hit"] and not row["route_a_raw_hit"] for row in newly),
        "both_routes_newly_recovered": sum(row["route_a_raw_hit"] and row["route_b_raw_hit"] for row in newly),
        "newly_recovered": newly, "lost_previous": lost, "locked_top50_remaining_misses": remaining_locked,
        "parser_errors": parser_errors, "baseline_mismatches": mismatches,
        "disk_free_before_bytes": disk_before, "maximum_temporary_bytes": max(0, disk_before - min_free),
        "disk_free_after_bytes": disk_after, "temporary_directory_removed": True,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": True, "frozen_variant": frozen, "gold": len(rows),
                      "locked_gains": payload["locked_newly_recovered_at_50"], "lost": len(lost),
                      "baseline_mismatches": len(mismatches), "temporary_directory_removed": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
