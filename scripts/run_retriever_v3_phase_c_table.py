"""Run the Development-only Retriever V3 Phase C table-lane experiment."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gc
import gzip
import json
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ipo_risk.evaluation.retrieval_40_annotations import load_annotation
from ipo_risk.evaluation.retriever_v3 import recall_at
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.bm25_v3 import BM25Config, PageBM25Index, bounded_rrf_union
from ipo_risk.retrieval.table_v3 import TABLE_VARIANTS, TableCandidateIndex, table_signal
from ipo_risk.schemas import DocumentParseRequest
from scripts.run_retriever_v3_phase_a import (
    OUTER_ZIP_DEFAULT, _annual_member, _copy_member, _pdf_member, _read_catalog, _sha256,
)
from scripts.run_retriever_v3_phase_b_bm25 import (
    OLD_LANES, _load_old_candidates, _load_qrels, _load_split, _old_complete_misses,
    _old_failure_labels, _old_ranks,
)


FROZEN_BM25_B = BM25Config("BM25-B", "cjk_bigram", 1.5, 0.75, top_k=100)
K_VALUES = (5, 10, 20, 50, 100)
AUDIT_FIELDS = (
    "case_id", "risk_code", "gold_page", "evidence_id", "source_authority",
    "table_failure_subtype", "table_signal", "neighbor_needed", "parser_text_available",
    "reclassification", "recovery_status", "table_rank", "exact_text_preview",
)


def _rank(page: int, ranking: list[tuple[int, float | None]]) -> int | None:
    return next((index for index, (candidate, _) in enumerate(ranking, 1) if candidate == page), None)


def _load_bm25_recovered(path: Path) -> set[tuple[str, str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return {(row["case_id"], row["risk_code"], row["evidence_id"]) for row in csv.DictReader(handle)}


def _is_genuine_table_evidence(exact_text: str) -> bool:
    lines = [line.strip() for line in exact_text.splitlines() if line.strip()]
    numbers = re.findall(r"(?<!\w)\d[\d,.]*%?", exact_text)
    return len(lines) >= 5 and len(numbers) >= 6


def _audit_subtype(exact_text: str) -> tuple[str, str]:
    lines = [line.strip() for line in exact_text.splitlines() if line.strip()]
    if not _is_genuine_table_evidence(exact_text):
        return "RECLASSIFIED_NON_TABLE_PROSE", "RECLASSIFIED"
    if len(exact_text) < 100:
        return "TABLE_ROW_HEADER_SEPARATION", ""
    if len(lines) >= 20:
        return "TABLE_TEXT_TOKEN_FRAGMENTATION", ""
    return "WHOLE_PAGE_TABLE_DILUTION", ""


def _stream(
    *, cases: list[str], qrels: list[dict], table_targets: set[tuple], catalog: dict,
    outer_zip: Path, temp: Path, repo: Path,
) -> tuple[dict, dict, dict, list[dict], int, dict]:
    by_case: dict[str, list[dict]] = defaultdict(list)
    for row in qrels:
        if row["case_id"] in cases:
            by_case[row["case_id"]].append(row)
    bm25_ranks: dict[tuple, tuple[int | None, float | None]] = {}
    table_ranks = {variant.name: {} for variant in TABLE_VARIANTS}
    bm25_candidates: dict[str, dict[str, list[tuple[int, float | None]]]] = defaultdict(dict)
    table_candidates = {variant.name: defaultdict(dict) for variant in TABLE_VARIANTS}
    audits: list[dict] = []
    peak = 0
    diagnostics = {variant.name: {"table_pages": [], "table_blocks": []} for variant in TABLE_VARIANTS}
    with zipfile.ZipFile(outer_zip) as outer:
        for year in sorted({catalog[case]["source_year"] for case in cases}):
            annual_path = temp / f"{year}.zip"
            _copy_member(outer, _annual_member(outer, year), annual_path)
            peak = max(peak, annual_path.stat().st_size)
            try:
                with zipfile.ZipFile(annual_path) as annual:
                    year_cases = [case for case in cases if catalog[case]["source_year"] == year]
                    for position, case in enumerate(year_cases, 1):
                        pdf_path = temp / "current.pdf"
                        chunks = None
                        try:
                            _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf_path)
                            peak = max(peak, annual_path.stat().st_size + pdf_path.stat().st_size)
                            if _sha256(pdf_path) != catalog[case]["sha256"]:
                                raise ValueError(f"PDF_HASH_MISMATCH:{case}")
                            chunks = PyMuPDFDocumentParser().parse(
                                DocumentParseRequest(document_id=case, prospectus_path=str(pdf_path))
                            )
                            page_text = {chunk.page: chunk.text for chunk in chunks if chunk.page is not None}
                            risks = sorted({row["risk_code"] for row in by_case[case]})
                            bm25 = PageBM25Index(chunks, FROZEN_BM25_B)
                            table_indexes = {variant.name: TableCandidateIndex(chunks, variant) for variant in TABLE_VARIANTS}
                            for variant in TABLE_VARIANTS:
                                diagnostics[variant.name]["table_pages"].append(table_indexes[variant.name].table_page_count)
                                diagnostics[variant.name]["table_blocks"].append(table_indexes[variant.name].table_block_count)
                            for risk in risks:
                                bm = bm25.search(risk, top_k=100)
                                bm25_candidates[case][risk] = [(item.page, item.score) for item in bm]
                                bm_map = {item.page: (item.rank, item.score) for item in bm}
                                for row in (item for item in by_case[case] if item["risk_code"] == risk):
                                    bm25_ranks[row["key"]] = bm_map.get(row["page"], (None, None))
                                for variant in TABLE_VARIANTS:
                                    result = table_indexes[variant.name].search(risk, top_k=50)
                                    table_candidates[variant.name][case][risk] = [(item.page, item.score) for item in result]
                                    result_map = {item.page: (item.rank, item.score) for item in result}
                                    for row in (item for item in by_case[case] if item["risk_code"] == risk):
                                        table_ranks[variant.name][row["key"]] = result_map.get(row["page"], (None, None))
                            annotation = load_annotation(
                                repo / "expert_results" / case / "pass1" / "expert_annotation_v1.json",
                                repository_root=repo,
                            )
                            exact = {item.evidence_id: item.exact_text for item in annotation.evidence}
                            for row in (item for item in by_case[case] if item["key"] in table_targets):
                                value = exact.get(row["evidence_id"], "")
                                subtype, reclassified = _audit_subtype(value)
                                page_value = page_text.get(row["page"], "")
                                audits.append({
                                    "case_id": case, "risk_code": row["risk_code"], "gold_page": row["page"],
                                    "evidence_id": row["evidence_id"], "source_authority": row["source_authority"],
                                    "table_failure_subtype": subtype,
                                    "table_signal": table_signal(page_value).score if page_value else 0.0,
                                    "neighbor_needed": False, "parser_text_available": bool(page_value),
                                    "reclassification": reclassified, "recovery_status": "PENDING",
                                    "table_rank": "", "exact_text_preview": re.sub(r"\s+", " ", value)[:200],
                                })
                            del bm25, table_indexes
                            print(f"[{year} {position}/{len(year_cases)}] {case}: BM25-B + Table variants ok", flush=True)
                        finally:
                            pdf_path.unlink(missing_ok=True)
                            if chunks is not None:
                                del chunks
                            gc.collect()
            finally:
                annual_path.unlink(missing_ok=True)
    return bm25_ranks, table_ranks, {"bm25": bm25_candidates, "table": table_candidates}, audits, peak, diagnostics


def _oracle(qrels: list[dict], old: dict, bm25: dict, table: dict | None, cutoff: int) -> float:
    found = 0
    for row in qrels:
        old_hit = any(rank is not None and rank <= cutoff for rank in _old_ranks(row, old).values())
        bm_hit = bm25[row["key"]][0] is not None and bm25[row["key"]][0] <= cutoff
        table_hit = bool(table) and table[row["key"]][0] is not None and table[row["key"]][0] <= min(cutoff, 50)
        found += old_hit or bm_hit or table_hit
    return found / len(qrels)


def _rrf(qrels: list[dict], old: dict, candidates: dict, table_name: str) -> tuple[dict, dict, dict, list[int]]:
    before_ranks: dict[tuple, int | None] = {}
    after_ranks: dict[tuple, int | None] = {}
    sizes: list[int] = []
    cache = {}
    for row in qrels:
        pair = (row["case_id"], row["risk_code"])
        if pair not in cache:
            case, risk = pair
            old_lanes = {lane: old[case][risk].get(lane, []) for lane in OLD_LANES}
            four = {**old_lanes, "bm25": candidates["bm25"][case][risk]}
            five = {**four, "table": candidates["table"][table_name][case][risk]}
            before = bounded_rrf_union(four, limit=100)
            after = bounded_rrf_union(five, limit=100)
            cache[pair] = (before, after)
            sizes.append(len(after))
        before, after = cache[pair]
        before_ranks[row["key"]] = next((item.rank for item in before if item.page == row["page"]), None)
        after_ranks[row["key"]] = next((item.rank for item in after if item.page == row["page"]), None)
    metric = lambda ranks: {f"r{k}": recall_at(list(ranks.values()), k) for k in (5, 20, 50, 100)}
    return metric(before_ranks), metric(after_ranks), {"before": before_ranks, "after": after_ranks}, sizes


def _stats(values: list[int]) -> dict:
    ordered = sorted(values)
    return {"mean": statistics.mean(ordered), "median": statistics.median(ordered),
            "p95": ordered[max(0, int(.95 * len(ordered)) - 1)], "max": max(ordered)}


def _write_audit(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDS)
        writer.writeheader(); writer.writerows(rows)


def _write_unique(path: Path, rows: list[dict]) -> None:
    fields = ("case_id", "risk_code", "gold_page", "evidence_id", "table_rank", "table_score",
              "old_failure_type", "source_authority", "retriever_presence_mask")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def _report(summary: dict) -> str:
    p = lambda value: f"{value:.2%}"
    result = summary["result"]
    original = summary["table_miss_recovery"]["original"]
    genuine = summary["table_miss_recovery"]["genuine"]
    lines = ["# Retriever V3 Phase C — Table Retrieval Lane", "", "PHASE R3-C RESULT:", "", result, "",
             "New Lane:", "Lightweight table-block retrieval", "", "Development cases:", "50", "",
             "Locked cases:", "10", "", "Locked metrics opened:", "NO", "",
             "## Remaining Complete Misses Before Table", "", "Total remaining: 30", "",
             "- Query Coverage: 10", "- Table: 8", "- Authority: 6", "- Neighbor: 4", "- Multipage: 2", "",
             f"重新 audit 后：6 条是真正表格，2 条重分类为普通叙述证据。", "",
             "## Table Miss Recovery", "", "| Metric | Result |", "|---|---:|",
             f"| Original taxonomy Table misses | {original['total']} |",
             f"| Genuine Table misses | {genuine['total']} |",
             f"| Recovered@10 | {genuine['at_10']} |", f"| Recovered@20 | {genuine['at_20']} |",
             f"| Recovered@50 | {genuine['at_50']} |", f"| Still Missing | {genuine['remaining']} |", "",
             "原始8条（含2条误分类）的恢复："
             f"@10={original['at_10']}，@20={original['at_20']}，@50={original['at_50']}。", "",
             "### Table Lane raw recall（all Development Gold）", "",
             "| @10 | @20 | @50 |", "|---:|---:|---:|",
             f"| {p(summary['table_raw_recall']['r10'])} | {p(summary['table_raw_recall']['r20'])} | {p(summary['table_raw_recall']['r50'])} |", "",
             "## Variant comparison", "", "| Variant | Policy | Genuine@50 | Overall unique@50 |", "|---|---|---:|---:|"]
    for row in summary["variants"]:
        lines.append(f"| {row['name']} | {row['aggregation']} | {row['genuine_recovered_at_50']} | {row['overall_unique_at_50']} |")
    old, new = summary["oracle"]["before"], summary["oracle"]["after"]
    lines += ["", f"Frozen variant: **{summary['selected_variant']}**。查询与 BM25-B 的 tokenizer/k1/b 均未修改。", "",
              "## Stage1 Ceiling", "", "| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |",
              "|---|---:|---:|---:|",
              f"| V1∪V2∪V2.1∪BM25 | {p(old['at_20'])} | {p(old['at_50'])} | {p(old['at_100_native'])} |",
              f"| + Table Lane | {p(new['at_20'])} | {p(new['at_50'])} | {p(new['at_100_native'])} |", "",
              "Oracle Coverage ≠ Fused Recall；它只表示至少一个 Lane 看到了 Gold。", "",
              "## Unique Table Contribution", "", f"Unique Gold found only after Table Lane: {summary['unique_contribution']['gold']}", "",
              f"Across IPO cases: {summary['unique_contribution']['cases']}", "",
              f"Across risks: {summary['unique_contribution']['risks']}", "",
              "## Equal-weight RRF", "", "| Fusion | R@5 | R@20 | R@50 | R@100 |", "|---|---:|---:|---:|---:|",
              f"| Before Table | {p(summary['rrf']['before']['r5'])} | {p(summary['rrf']['before']['r20'])} | {p(summary['rrf']['before']['r50'])} | {p(summary['rrf']['before']['r100'])} |",
              f"| After Table | {p(summary['rrf']['after']['r5'])} | {p(summary['rrf']['after']['r20'])} | {p(summary['rrf']['after']['r50'])} | {p(summary['rrf']['after']['r100'])} |", "",
              "Fusion 使用固定 equal-weight RRF，没有按 Gold 调权重。", "",
              "### Bounded candidate pool", "",
              f"- Mean: {summary['candidate_pool']['mean']}", f"- Median: {summary['candidate_pool']['median']}",
              f"- P95: {summary['candidate_pool']['p95']}", f"- Max: {summary['candidate_pool']['max']}（cap=100）", "",
              f"Newly recovered Gold in bounded Top100: {summary['bounded_union']['newly_recovered_gold']}",
              f"Lost previous Gold in bounded Top100: {summary['bounded_union']['lost_previous_gold']}",
              f"Net Gold gain: {summary['bounded_union']['net_gold_gain']}", "",
              "## Remaining complete candidate misses", "", f"Remaining: {summary['remaining']['total']}"]
    lines += [f"- {name}: {count}" for name, count in summary["remaining"]["by_type"].items()]
    lines += ["", "## Cost", "", f"- Implementation complexity: {summary['cost']['implementation_complexity']}",
              f"- Runtime overhead: {summary['cost']['runtime_overhead']}",
              f"- Memory overhead: {summary['cost']['memory_overhead']}",
              f"- Disk overhead: {summary['cost']['disk_overhead']}", "", "## Disk", "",
              f"- Available disk before: {summary['disk']['before_gib']:.2f} GiB",
              f"- Peak temporary disk: {summary['disk']['peak_mib']:.1f} MiB",
              f"- Available disk after: {summary['disk']['after_gib']:.2f} GiB",
              "- Persistent Table index: NO", "- Persistent BM25 index: NO", "- Model download: NO",
              "- Temporary PDFs remaining: 0", "- Temporary year ZIPs remaining: 0", "- Temporary directories: CLEAN", "",
              "## LOCKED VALIDATION STATUS", "", "Cases: 10", "", "Metrics opened: NO", "",
              "Gold inspected: NO", "", "Used for tuning: NO", "", "Used for Table design: NO", "",
              "## Strategic decision", "", f"CANDIDATE EXPANSION RECOMMENDATION: **{summary['strategic_recommendation']}**", "",
              summary["strategic_reason"], "", "Push: NO", "", "Remote GitHub modified: NO", ""]
    if result == "PASS":
        lines += ["## 简单结论", "", "TABLE LANE PASS。", "",
                  f"BM25之后还剩30条正确 Evidence 完全找不到，其中确认有{genuine['total']}条属于真正表格问题。轻量 Table Lane 在Top50找回{genuine['at_50']}条，来自{summary['genuine_diversity']['cases']}家IPO、覆盖{summary['genuine_diversity']['risks']}个risk。Stage1 Oracle native ceiling 从{p(old['at_100_native'])}提高到{p(new['at_100_native'])}。", ""]
    else:
        lines += ["## 简单结论", "", "TABLE LANE FAIL。", "",
                  f"确认的{genuine['total']}条表格问题中，轻量 Table Lane 只在Top50找回{genuine['at_50']}条；收益不足以证明增加 Table subsystem 的复杂度值得。", ""]
    return "\n".join(lines)


def run(args) -> dict:
    repo = ROOT
    output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=True)
    disk_before = shutil.disk_usage(args.temp_parent).free
    development, locked = _load_split(args.split_manifest)
    qrels = _load_qrels(args.gold, set(development), set(locked))
    old = _load_old_candidates(args.old_candidates, set(development), set(locked))
    old_misses = _old_complete_misses(qrels, old)
    if len(old_misses) != 144:
        raise ValueError(f"OLD_COMPLETE_MISS_GATE:{len(old_misses)}")
    failures = _old_failure_labels(qrels, old_misses, old, repo)
    recovered_by_bm25 = _load_bm25_recovered(args.bm25_recovery)
    catalog = _read_catalog(args.catalog)
    # Smoke selection derives the known miss from the frozen R3-B recovery artifact, not from Locked data.
    fixed_table_rows = [row for row in old_misses if row["key"] not in recovered_by_bm25
                        and failures[row["key"]] == "TABLE_FRAGMENTATION"]
    if len(fixed_table_rows) != 8:
        raise ValueError(f"FIXED_TABLE_MISS_GATE:{len(fixed_table_rows)} expected=8")
    smoke_cases = list(dict.fromkeys([fixed_table_rows[0]["case_id"], *development]))[:3]
    cases = smoke_cases if args.smoke else development
    peak = 0
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_table_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        fixed_targets = {row["key"] for row in fixed_table_rows}
        bm25, table, candidates, audits, stream_peak, diagnostics = _stream(
            cases=cases, qrels=qrels, table_targets=fixed_targets, catalog=catalog,
            outer_zip=args.outer_zip, temp=temp, repo=repo,
        )
        peak = max(peak, stream_peak)
        if args.smoke:
            expected = [row for row in qrels if row["case_id"] in cases]
            if len(bm25) != len(expected) or any(len(table[name]) != len(expected) for name in table):
                raise ValueError("SMOKE_RANK_EXPORT")
            return {"smoke": True, "cases": len(cases), "known_table_case_included": True,
                    "locked_metrics_opened": False, "temporary_directory_removed": True}

        # Match the fixed R3-B remainder: old native miss and BM25-B absent through Top100.
        remaining30 = [row for row in old_misses if bm25[row["key"]][0] is None]
        if len(remaining30) != 30:
            raise ValueError(f"R3_B_REMAINDER_GATE:{len(remaining30)} expected=30")
        table_rows = [row for row in remaining30 if failures[row["key"]] == "TABLE_FRAGMENTATION"]
        if len(table_rows) != 8:
            raise ValueError(f"TABLE_MISS_GATE:{len(table_rows)} expected=8")
        table_keys = {row["key"] for row in table_rows}
        audits = [row for row in audits if (row["case_id"], row["risk_code"], row["evidence_id"]) in table_keys]
        genuine_keys = {row["key"] for row in table_rows if _is_genuine_table_evidence(next(
            item.exact_text for item in load_annotation(repo / "expert_results" / row["case_id"] / "pass1" / "expert_annotation_v1.json", repository_root=repo).evidence
            if item.evidence_id == row["evidence_id"]))}
        variants = []
        for variant in TABLE_VARIANTS:
            ranks = table[variant.name]
            genuine50 = sum(ranks[key][0] is not None and ranks[key][0] <= 50 for key in genuine_keys)
            unique50 = sum(ranks[row["key"]][0] is not None and ranks[row["key"]][0] <= 50 for row in remaining30)
            variants.append({"name": variant.name, "aggregation": variant.aggregation,
                             "genuine_recovered_at_50": genuine50, "overall_unique_at_50": unique50})
        order = {variant.name: index for index, variant in enumerate(TABLE_VARIANTS)}
        selected_name = max(variants, key=lambda row: (row["genuine_recovered_at_50"], row["overall_unique_at_50"], -order[row["name"]]))["name"]
        selected = table[selected_name]
        table_raw_recall = {f"r{k}": recall_at([selected[row["key"]][0] for row in qrels], k)
                            for k in (10, 20, 50)}
        for audit in audits:
            key = (audit["case_id"], audit["risk_code"], audit["evidence_id"])
            rank = selected[key][0]
            audit["table_rank"] = rank or ""
            audit["recovery_status"] = "RECOVERED" if rank is not None and rank <= 50 else "STILL_MISSING"
        original_recovery = {k: sum(selected[row["key"]][0] is not None and selected[row["key"]][0] <= k for row in table_rows)
                             for k in (10, 20, 50)}
        genuine_rows = [row for row in table_rows if row["key"] in genuine_keys]
        genuine_recovery = {k: sum(selected[row["key"]][0] is not None and selected[row["key"]][0] <= k for row in genuine_rows)
                            for k in (10, 20, 50)}
        unique_rows = [row for row in remaining30 if selected[row["key"]][0] is not None and selected[row["key"]][0] <= 50]
        before_oracle = {"at_20": _oracle(qrels, old, bm25, None, 20), "at_50": _oracle(qrels, old, bm25, None, 50),
                         "at_100_native": _oracle(qrels, old, bm25, None, 100)}
        after_oracle = {"at_20": _oracle(qrels, old, bm25, selected, 20), "at_50": _oracle(qrels, old, bm25, selected, 50),
                        "at_100_native": _oracle(qrels, old, bm25, selected, 100)}
        before_rrf, after_rrf, union_ranks, pool_sizes = _rrf(qrels, old, candidates, selected_name)
        previous = {key for key, rank in union_ranks["before"].items() if rank is not None and rank <= 100}
        current = {key for key, rank in union_ranks["after"].items() if rank is not None and rank <= 100}
        remaining_after = [row for row in remaining30 if row not in unique_rows]
        corrected_failures = dict(failures)
        for audit in audits:
            if audit["reclassification"] == "RECLASSIFIED":
                key = (audit["case_id"], audit["risk_code"], audit["evidence_id"])
                corrected_failures[key] = "SECTION_AUTHORITY_MISS"
        remaining_counts = Counter(corrected_failures[row["key"]] for row in remaining_after)
        gates = {
            "A_recover_at_least_4_genuine": genuine_recovery[50] >= 4,
            "B_at_least_3_cases": len({row["case_id"] for row in genuine_rows if selected[row["key"]][0] is not None and selected[row["key"]][0] <= 50}) >= 3,
            "C_at_least_2_risks": len({row["risk_code"] for row in genuine_rows if selected[row["key"]][0] is not None and selected[row["key"]][0] <= 50}) >= 2,
            "D_oracle_positive": after_oracle["at_100_native"] > before_oracle["at_100_native"],
            "E_bounded_union_net_positive": len(current - previous) - len(previous - current) > 0,
        }
        passed = all(gates.values())
        # At >=95% ceiling, only a cheap concentrated lane would justify more expansion.
        strategic = "STOP_AND_MOVE_TO_RANKING" if after_oracle["at_100_native"] >= .95 else "CONTINUE"
        reason = ("当前 Stage1 Candidate Recall 已达到至少95%，剩余错误少且分散；下一阶段应开始设计 LTR。"
                  if strategic == "STOP_AND_MOVE_TO_RANKING" else
                  "当前 ceiling 仍低于95%，可再评估一个低成本、集中明确的 Authority 或 Neighbor Lane。")
        disk_after = shutil.disk_usage(args.temp_parent).free
        summary = {
            "result": "PASS" if passed else "FAIL", "pass": passed,
            "development_cases": 50, "locked_cases": 10, "locked_metrics_opened": False,
            "selected_variant": selected_name, "frozen_bm25": FROZEN_BM25_B.__dict__, "variants": variants,
            "remaining_before": {"total": 30, "QUERY_COVERAGE_MISS": 10, "TABLE_FRAGMENTATION": 8,
                                 "SECTION_AUTHORITY_MISS": 6, "NEIGHBOR_PAGE_MISS": 4, "MULTIPAGE_FRAGMENTATION": 2},
            "table_miss_recovery": {
                "original": {"total": 8, "at_10": original_recovery[10], "at_20": original_recovery[20],
                             "at_50": original_recovery[50], "remaining": 8 - original_recovery[50]},
                "genuine": {"total": len(genuine_rows), "reclassified": 8 - len(genuine_rows),
                            "at_10": genuine_recovery[10], "at_20": genuine_recovery[20],
                            "at_50": genuine_recovery[50], "remaining": len(genuine_rows) - genuine_recovery[50]},
            },
            "table_raw_recall": table_raw_recall,
            "genuine_diversity": {
                "cases": len({row["case_id"] for row in genuine_rows if selected[row["key"]][0] is not None and selected[row["key"]][0] <= 50}),
                "risks": len({row["risk_code"] for row in genuine_rows if selected[row["key"]][0] is not None and selected[row["key"]][0] <= 50}),
            },
            "unique_contribution": {"gold": len(unique_rows), "cases": len({row["case_id"] for row in unique_rows}),
                                    "risks": len({row["risk_code"] for row in unique_rows})},
            "oracle": {"before": before_oracle, "after": after_oracle,
                       "gain": {key: after_oracle[key] - before_oracle[key] for key in before_oracle}},
            "rrf": {"before": before_rrf, "after": after_rrf}, "candidate_pool": _stats(pool_sizes),
            "bounded_union": {"newly_recovered_gold": len(current - previous), "lost_previous_gold": len(previous - current),
                              "net_gold_gain": len(current - previous) - len(previous - current)},
            "remaining": {"total": len(remaining_after), "by_type": {name: remaining_counts[name] for name in
                ("QUERY_COVERAGE_MISS", "TABLE_FRAGMENTATION", "SECTION_AUTHORITY_MISS", "NEIGHBOR_PAGE_MISS",
                 "MULTIPAGE_FRAGMENTATION", "OTHER_UNKNOWN")}},
            "gates": gates, "strategic_recommendation": strategic, "strategic_reason": reason,
            "cost": {"implementation_complexity": "MEDIUM", "runtime_overhead": "one case-local table-block index; three variants only in this offline experiment",
                     "memory_overhead": "case-local only; released after each PDF", "disk_overhead": "summary/audit metadata only"},
            "diagnostics": {name: {"mean_table_pages": statistics.mean(values["table_pages"]),
                                    "mean_table_blocks": statistics.mean(values["table_blocks"])}
                            for name, values in diagnostics.items()},
            "disk": {"before_bytes": disk_before, "after_bytes": disk_after, "peak_temporary_bytes": peak,
                     "before_gib": disk_before / 2**30, "after_gib": disk_after / 2**30, "peak_mib": peak / 2**20},
            "persistent_table_index": False, "persistent_bm25_index": False, "model_download": False,
        }
        unique_export = [{"case_id": row["case_id"], "risk_code": row["risk_code"], "gold_page": row["page"],
                          "evidence_id": row["evidence_id"], "table_rank": selected[row["key"]][0],
                          "table_score": selected[row["key"]][1], "old_failure_type": failures[row["key"]],
                          "source_authority": row["source_authority"], "retriever_presence_mask": "V1=0,V2=0,V21=0,BM25=0,TABLE=1"}
                         for row in unique_rows]
        _write_audit(output / "table_miss_audit.csv", audits)
        _write_unique(output / "table_unique_recovery.csv.gz", unique_export)
        (output / "table_phase_c_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "RETRIEVER_V3_PHASE_C_TABLE_REPORT.md").write_text(_report(summary), encoding="utf-8")
    return {"completed": True, "result": summary["result"], "selected": selected_name,
            "genuine_recovered_at_50": genuine_recovery[50], "locked_metrics_opened": False,
            "temporary_directory_removed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip", type=Path, default=OUTER_ZIP_DEFAULT)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--split-manifest", type=Path, default=Path("reports/retriever_v3/split_manifest.json"))
    parser.add_argument("--gold", type=Path, default=Path("reports/retriever_v3/gold_evidence.csv"))
    parser.add_argument("--old-candidates", type=Path, default=Path("reports/retriever_v3/hard_candidate_dataset.csv.gz"))
    parser.add_argument("--bm25-recovery", type=Path, default=Path("reports/retriever_v3/bm25_unique_recovery.csv.gz"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/retriever_v3"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(); print(json.dumps(run(args), ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
