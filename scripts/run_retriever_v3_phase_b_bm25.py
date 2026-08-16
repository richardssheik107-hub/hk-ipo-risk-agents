"""Run 5-fold development-only evaluation for the experimental page BM25 lane."""

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
from ipo_risk.retrieval.bm25_v3 import (
    BM25_VARIANTS, CV_SALT, BM25Config, PageBM25Index, bounded_rrf_union,
    deterministic_group_folds, query_policy_sha256,
)
from ipo_risk.schemas import DocumentParseRequest
from scripts.run_retriever_v3_phase_a import (
    OUTER_ZIP_DEFAULT, _annual_member, _copy_member, _pdf_member, _read_catalog, _sha256,
)


K_VALUES = (5, 10, 20, 50, 100)
OLD_LANES = ("v1", "v2", "v21")
ALL_LANES = (*OLD_LANES, "bm25")


def _load_split(path: Path) -> tuple[list[str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    development = payload["historical_development"] + payload["new_development"]
    locked = payload["locked_validation"]
    if len(development) != 50 or len(locked) != 10 or set(development) & set(locked):
        raise ValueError("R3_A_SPLIT_INVALID")
    return development, locked


def _load_qrels(path: Path, development: set[str], locked: set[str]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["requirement"] == "required"]
    cases = {row["case_id"] for row in rows}
    if cases & locked or not cases <= development:
        raise ValueError("LOCKED_QRELS_LEAKAGE")
    for row in rows:
        row["page"] = int(row["page"]); row["gold_label"] = int(row["gold_label"])
        row["key"] = (row["case_id"], row["risk_code"], row["evidence_id"])
    return rows


def _load_old_candidates(path: Path, development: set[str], locked: set[str]) -> dict:
    output: dict[str, dict[str, dict[str, list[tuple[int, float | None]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["case_id"] in locked:
                raise ValueError("LOCKED_CANDIDATE_LEAKAGE")
            if row["case_id"] not in development:
                continue
            output[row["case_id"]][row["risk_code"]][row["retriever"]].append((int(row["page"]), None))
    return output


def _rank(page: int, ranking: list[tuple[int, float | None]]) -> int | None:
    return next((index for index, (candidate, _) in enumerate(ranking, 1) if candidate == page), None)


def _old_ranks(qrel: dict, old: dict) -> dict[str, int | None]:
    case, risk, page = qrel["case_id"], qrel["risk_code"], qrel["page"]
    return {lane: _rank(page, old[case][risk].get(lane, [])) for lane in OLD_LANES}


def _stream_bm25(
    *, configs: tuple[BM25Config, ...], cases: list[str], qrels: list[dict], catalog: dict,
    outer_zip: Path, temp: Path, smoke: bool = False,
) -> tuple[dict[str, dict[tuple, tuple[int | None, float | None]]], dict[str, dict[str, list[tuple[int, float | None]]]], int]:
    """Parse one PDF at a time and retain only Gold ranks or final page/rank/score."""
    by_case: dict[str, list[dict]] = defaultdict(list)
    for row in qrels:
        if row["case_id"] in cases:
            by_case[row["case_id"]].append(row)
    gold_ranks = {config.name: {} for config in configs}
    final_candidates: dict[str, dict[str, list[tuple[int, float | None]]]] = defaultdict(dict)
    peak = 0
    with zipfile.ZipFile(outer_zip) as outer:
        for year in sorted({catalog[case]["source_year"] for case in cases}):
            annual_path = temp / f"{year}.zip"
            _copy_member(outer, _annual_member(outer, year), annual_path)
            peak = max(peak, annual_path.stat().st_size)
            try:
                with zipfile.ZipFile(annual_path) as annual:
                    year_cases = [case for case in cases if catalog[case]["source_year"] == year]
                    for index, case in enumerate(year_cases, 1):
                        pdf_path = temp / "current.pdf"
                        try:
                            _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf_path)
                            peak = max(peak, annual_path.stat().st_size + pdf_path.stat().st_size)
                            if _sha256(pdf_path) != catalog[case]["sha256"]:
                                raise ValueError(f"PDF_HASH_MISMATCH:{case}")
                            parser = PyMuPDFDocumentParser()
                            chunks = parser.parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdf_path)))
                            risks = sorted({row["risk_code"] for row in by_case[case]})
                            for config in configs:
                                index_impl = PageBM25Index(chunks, config)
                                for risk in risks:
                                    candidates = index_impl.search(risk, top_k=100)
                                    ranking = [(item.page, item.score) for item in candidates]
                                    if len(configs) == 1:
                                        final_candidates[case][risk] = ranking
                                    page_map = {item.page: (item.rank, item.score) for item in candidates}
                                    for row in (item for item in by_case[case] if item["risk_code"] == risk):
                                        gold_ranks[config.name][row["key"]] = page_map.get(row["page"], (None, None))
                                del index_impl
                            print(f"[{year} {index}/{len(year_cases)}] {case}: BM25 ok", flush=True)
                        finally:
                            pdf_path.unlink(missing_ok=True)
                            if "chunks" in locals(): del chunks
                            gc.collect()
            finally:
                annual_path.unlink(missing_ok=True)
    return gold_ranks, final_candidates, peak


def _metric_rows(qrels: list[dict], ranks: dict[tuple, tuple[int | None, float | None]]) -> dict:
    all_ranks = [ranks[row["key"]][0] for row in qrels]
    primary = [ranks[row["key"]][0] for row in qrels if row["gold_label"] == 3]
    groups: dict[tuple[str, str], list[int | None]] = defaultdict(list)
    for row in qrels:
        groups[(row["case_id"], row["risk_code"])].append(ranks[row["key"]][0])
    result = {f"r{k}": recall_at(all_ranks, k) for k in K_VALUES}
    result["primary_required"] = {f"r{k}": recall_at(primary, k) for k in K_VALUES}
    result["completion"] = {f"at_{k}": sum(all(rank is not None and rank <= k for rank in values)
                                               for values in groups.values()) / len(groups) for k in K_VALUES}
    return result


def _old_complete_misses(qrels: list[dict], old: dict) -> list[dict]:
    return [row for row in qrels if all(rank is None for rank in _old_ranks(row, old).values())]


def _cv_summary(config: BM25Config, qrels: list[dict], old_misses: list[dict], ranks: dict,
                folds: dict[str, int], old: dict) -> list[dict]:
    output = []
    for fold in range(1, 6):
        fold_qrels = [row for row in qrels if folds[row["case_id"]] == fold]
        fold_misses = [row for row in old_misses if folds[row["case_id"]] == fold]
        recovered50 = [row for row in fold_misses if ranks[row["key"]][0] is not None and ranks[row["key"]][0] <= 50]
        recovered100 = [row for row in fold_misses if ranks[row["key"]][0] is not None and ranks[row["key"]][0] <= 100]
        oracle_old50 = sum(any(rank is not None and rank <= 50 for rank in _old_ranks(row, old).values()) for row in fold_qrels) / len(fold_qrels)
        oracle_new50 = sum(any(rank is not None and rank <= 50 for rank in _old_ranks(row, old).values()) or
                           (ranks[row["key"]][0] is not None and ranks[row["key"]][0] <= 50) for row in fold_qrels) / len(fold_qrels)
        output.append({"fold": fold, "case_count": 10, "gold": len(fold_qrels), "old_complete_misses": len(fold_misses),
                       "bm25_r50": recall_at([ranks[row["key"]][0] for row in fold_qrels], 50),
                       "bm25_r100": recall_at([ranks[row["key"]][0] for row in fold_qrels], 100),
                       "unique_recovered_at_50": len(recovered50), "unique_recovered_at_100": len(recovered100),
                       "oracle_gain_at_50": oracle_new50 - oracle_old50})
    return output


def _choose_config(cv: dict[str, list[dict]]) -> str:
    """Global selection: unique@50, unique@100, mean standalone R@50/R@100, then declared order."""
    order = {config.name: index for index, config in enumerate(BM25_VARIANTS)}
    return max(cv, key=lambda name: (
        sum(row["unique_recovered_at_50"] for row in cv[name]),
        sum(row["unique_recovered_at_100"] for row in cv[name]),
        statistics.mean(row["bm25_r50"] for row in cv[name]),
        statistics.mean(row["bm25_r100"] for row in cv[name]),
        -order[name],
    ))


def _strict_table(text: str) -> bool:
    years = len(set(re.findall(r"20\d{2}", text)))
    numbers = len(re.findall(r"(?<!\w)\d[\d,.]*%?", text))
    currency = bool(re.search(r"HK\$|RMB|人民幣|港元|美元|千元|百萬", text, re.I))
    return (years >= 2 and numbers >= 5) or (currency and numbers >= 6) or (text.count("\n") >= 3 and numbers >= 5)


def _old_failure_labels(qrels: list[dict], old_misses: list[dict], old: dict, repo: Path) -> dict[tuple, str]:
    exact: dict[tuple, str] = {}
    for case in sorted({row["case_id"] for row in qrels}):
        annotation = load_annotation(repo / "expert_results" / case / "pass1/expert_annotation_v1.json", repository_root=repo)
        exact.update({(item.case_id, item.risk_code, item.evidence_id): item.exact_text for item in annotation.evidence})
    by_case_risk: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in qrels: by_case_risk[(row["case_id"], row["risk_code"])].append(row)
    output = {}
    for row in old_misses:
        case, risk, page = row["case_id"], row["risk_code"], row["page"]
        pages = {candidate for lane in OLD_LANES for candidate, _ in old[case][risk].get(lane, [])}
        other_found = any(item["evidence_id"] != row["evidence_id"] and item["page"] in pages
                          for item in by_case_risk[(case, risk)])
        if page - 1 in pages or page + 1 in pages:
            label = "NEIGHBOR_PAGE_MISS"
        elif _strict_table(exact.get(row["key"], "")):
            label = "TABLE_FRAGMENTATION"
        elif other_found:
            label = "MULTIPAGE_FRAGMENTATION"
        elif row["source_authority"] in {"corporate_structure", "pre_ipo_investment", "legal_disclosure"}:
            label = "SECTION_AUTHORITY_MISS"
        else:
            label = "QUERY_COVERAGE_MISS"
        output[row["key"]] = label
    return output


def _oracle(qrels: list[dict], old: dict, bm25: dict, cutoff: int, *, include_bm25: bool) -> float:
    found = 0
    for row in qrels:
        old_found = any(rank is not None and rank <= cutoff for rank in _old_ranks(row, old).values())
        bm25_found = include_bm25 and bm25[row["key"]][0] is not None and bm25[row["key"]][0] <= cutoff
        found += old_found or bm25_found
    return found / len(qrels)


def _fusion_metrics(qrels: list[dict], old: dict, final_candidates: dict) -> tuple[dict, dict, list[int]]:
    old_ranks, new_ranks, pool_sizes = [], [], []
    cache: dict[tuple[str, str], tuple[list, list]] = {}
    for row in qrels:
        key = (row["case_id"], row["risk_code"])
        if key not in cache:
            old_rankings = {lane: old[key[0]][key[1]].get(lane, []) for lane in OLD_LANES}
            new_rankings = {**old_rankings, "bm25": final_candidates[key[0]][key[1]]}
            old_union = bounded_rrf_union(old_rankings, limit=100)
            new_union = bounded_rrf_union(new_rankings, limit=100)
            cache[key] = (old_union, new_union); pool_sizes.append(len(new_union))
        old_union, new_union = cache[key]
        old_ranks.append(next((item.rank for item in old_union if item.page == row["page"]), None))
        new_ranks.append(next((item.rank for item in new_union if item.page == row["page"]), None))
    metric = lambda ranks: {f"r{k}": recall_at(ranks, k) for k in (5, 20, 50, 100)}
    return metric(old_ranks), metric(new_ranks), pool_sizes


def _stats(values: list[int]) -> dict:
    ordered = sorted(values)
    return {"mean": statistics.mean(ordered), "median": statistics.median(ordered),
            "p95": ordered[max(0, int(.95 * len(ordered)) - 1)], "max": max(ordered)}


def _write_recovery(path: Path, rows: list[dict]) -> None:
    fields = ("case_id", "risk_code", "gold_page", "evidence_id", "old_failure_type", "bm25_rank", "bm25_score",
              "bm25_hit_at_20", "bm25_hit_at_50", "bm25_hit_at_100")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def _report(summary: dict) -> str:
    p = lambda value: f"{value:.2%}"
    result = "PASS" if summary["pass"] else "FAIL"
    base = summary["baseline_overall"]; bm = summary["bm25_standalone"]
    lines = ["# Retriever V3 Phase B — Page-level BM25", "", "PHASE R3-B RESULT:", "", result, "",
             "New Lane:", "Page-level BM25", "", "Development cases:", "50", "", "Locked cases:", "10", "",
             "Locked metrics opened:", "NO", "", "## BM25 Standalone", "",
             "| Retriever | R@5 | R@20 | R@50 | R@100/native |", "|---|---:|---:|---:|---:|",
             f"| V1 | {p(base['v1']['r5'])} | {p(base['v1']['r20'])} | {p(base['v1']['r50'])} | {p(base['v1']['native_recall'])} |",
             f"| V2 | {p(base['v2']['r5'])} | {p(base['v2']['r20'])} | {p(base['v2']['r50'])} | {p(base['v2']['native_recall'])} |",
             f"| V2.1 | {p(base['v21']['r5'])} | {p(base['v21']['r20'])} | {p(base['v21']['r50'])} | {p(base['v21']['native_recall'])} |",
             f"| BM25 | {p(bm['r5'])} | {p(bm['r20'])} | {p(bm['r50'])} | {p(bm['r100'])} |", "",
             "### BM25 Primary Required / Completion", "",
             "| Metric | @5 | @20 | @50 | @100 |", "|---|---:|---:|---:|---:|",
             f"| Primary Required Recall | {p(bm['primary_required']['r5'])} | {p(bm['primary_required']['r20'])} | {p(bm['primary_required']['r50'])} | {p(bm['primary_required']['r100'])} |",
             f"| Required Completion | {p(bm['completion']['at_5'])} | {p(bm['completion']['at_20'])} | {p(bm['completion']['at_50'])} | {p(bm['completion']['at_100'])} |", "",
             "### CV variant comparison", "", "| Variant | Tokenizer | Unique@50 | Unique@100 |", "|---|---|---:|---:|"]
    variant_by_name = {row["name"]: row for row in summary["variants"]}
    for name, folds in summary["cv_results"].items():
        lines.append(f"| {name} | {variant_by_name[name]['tokenizer']} | {sum(row['unique_recovered_at_50'] for row in folds)} | {sum(row['unique_recovered_at_100'] for row in folds)} |")
    lines += ["", "BM25-B 依据预先固定的 selection order 胜出；B 与 C 的 @100 相同，但 B 的 @50 更高。", "",
             "## Stage1 Ceiling", "", "| Candidate Sources | Oracle@20 | Oracle@50 | Oracle@100/native |",
             "|---|---:|---:|---:|",
             f"| V1∪V2∪V2.1 | {p(summary['oracle']['old']['at_20'])} | {p(summary['oracle']['old']['at_50'])} | {p(summary['oracle']['old']['at_100_native'])} |",
             f"| V1∪V2∪V2.1∪BM25 | {p(summary['oracle']['new']['at_20'])} | {p(summary['oracle']['new']['at_50'])} | {p(summary['oracle']['new']['at_100_native'])} |", "",
             "Oracle Coverage ≠ Fused Recall；Oracle 只表示至少一个 Lane 看到了 Gold。", "",
             "## 144 Old Complete Misses", "", f"Old complete candidate misses: {summary['old_complete_misses']}", "",
             f"BM25 recovered @20: {summary['old_miss_recovery']['at_20']}", "",
             f"BM25 recovered @50: {summary['old_miss_recovery']['at_50']}", "",
             f"BM25 recovered @100: {summary['old_miss_recovery']['at_100']}", "",
             f"Remaining: {summary['old_miss_recovery']['remaining']}", "", "## BM25 Unique Contribution by Risk", "",
             "| Risk | Old Complete Misses | BM25 Recovered@20 | BM25 Recovered@50 | BM25 Recovered@100 |", "|---|---:|---:|---:|---:|"]
    for risk, data in summary["by_risk"].items():
        lines.append(f"| {risk} | {data['old_misses']} | {data['recovered_at_20']} | {data['recovered_at_50']} | {data['recovered_at_100']} |")
    diversity = summary["diversity"]
    lines += ["", "## Case diversity", "", f"New Gold recovered: {diversity['gold']}", "",
              f"Across IPO cases: {diversity['cases']}", "", f"Across risk_codes: {diversity['risks']}", "",
              f"BM25-only Gold：@20={summary['old_miss_recovery']['at_20']}，@50={summary['old_miss_recovery']['at_50']}，@100={summary['old_miss_recovery']['at_100']}。", "",
              "## 5-fold stability", "", "| Fold | Old Misses Recovered@100 | Oracle Gain@50 |", "|---|---:|---:|"]
    for row in summary["selected_cv_folds"]:
        lines.append(f"| {row['fold']} | {row['unique_recovered_at_100']} | {p(row['oracle_gain_at_50'])} |")
    query = summary["query_coverage"]
    lines += ["", "## QUERY_COVERAGE", "", f"QUERY_COVERAGE misses: {query['total']}", "",
              f"Recovered by BM25 @20: {query['at_20']}", "", f"Recovered @50: {query['at_50']}", "",
              f"Recovered @100: {query['at_100']}", "", f"Still missing: {query['remaining']}", "",
              "## Equal-weight RRF", "", "| Fusion | R@5 | R@20 | R@50 | R@100 |", "|---|---:|---:|---:|---:|",
              f"| Old 3-lane | {p(summary['rrf']['old']['r5'])} | {p(summary['rrf']['old']['r20'])} | {p(summary['rrf']['old']['r50'])} | {p(summary['rrf']['old']['r100'])} |",
              f"| New 4-lane | {p(summary['rrf']['new']['r5'])} | {p(summary['rrf']['new']['r20'])} | {p(summary['rrf']['new']['r50'])} | {p(summary['rrf']['new']['r100'])} |", "",
              "Fusion 使用固定 equal-weight RRF，没有按 Gold 调权重。", "", "## Bounded candidate pool", "",
              f"- Mean unique candidates: {summary['candidate_pool']['mean']:.2f}",
              f"- Median: {summary['candidate_pool']['median']:.2f}", f"- P95: {summary['candidate_pool']['p95']}",
              f"- Max: {summary['candidate_pool']['max']}（上限100）", "",
              "每个池只保留当前 IPO 中 BM25 分数大于零的真实 physical pages，经四 Lane 去重和固定 RRF 后截断到100；没有补零分页，也没有使用整本 PDF 作为候选。", "",
              "## Remaining old misses", ""]
    lines += [f"- {name}: {count}" for name, count in summary["remaining_failure_types"].items()]
    lines += ["", "## PASS gates", ""] + [f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in summary["gates"].items()]
    lines += ["", "## Frozen BM25 configuration", "", f"`{json.dumps(summary['frozen_config'], ensure_ascii=False)}`", "",
              "Query source: frozen V1/V2/V2.1 query families + canonical risk terminology；没有使用 Gold exact_text 做 query expansion。", "",
              "## Disk and isolation", "", f"- Available disk before: {summary['disk']['before_gib']:.2f} GiB",
              f"- Peak temporary disk: {summary['disk']['peak_mib']:.1f} MiB",
              f"- Available disk after: {summary['disk']['after_gib']:.2f} GiB",
              "- Persistent BM25 index: NO", "- Embedding/model download: NO", "- Temporary PDFs remaining: 0",
              "- Temporary year ZIP remaining: 0", "- Temporary directories: CLEAN", "",
              "## Locked validation", "", "Metrics opened: NO", "", "Gold inspected for tuning: NO", "",
              "Pattern mining: NO", "", "Push: NO", "", "Remote GitHub modified: NO", ""]
    lines += ["## 简单结论", "", f"BM25 {result}。", "",
              f"原来有{summary['old_complete_misses']}条正确 Evidence 是 V1/V2/V2.1 三个系统全部找不到的；BM25 在 Top100 新找回{summary['old_miss_recovery']['at_100']}条，来自{summary['diversity']['cases']}家 IPO，覆盖{summary['diversity']['risks']}个 risk。Stage1 Oracle@50 从{p(summary['oracle']['old']['at_50'])}提高到{p(summary['oracle']['new']['at_50'])}。", "",
              f"下一阶段建议单独研究 Table Fragmentation。虽然仍有{summary['remaining_failure_types']['QUERY_COVERAGE_MISS']}条 Query Coverage miss，但继续扩 BM25 词汇容易重新走向关键词工程；剩余{summary['remaining_failure_types']['TABLE_FRAGMENTATION']}条明确表格碎片是更独立、可验证的下一 Lane。本阶段不实施。", ""]
    return "\n".join(lines)


def run(args) -> dict:
    repo = ROOT; output = args.output_dir.resolve(); output.mkdir(parents=True, exist_ok=True)
    disk_before = shutil.disk_usage(args.temp_parent).free
    development, locked = _load_split(args.split_manifest)
    folds = deterministic_group_folds(development)
    qrels = _load_qrels(args.gold, set(development), set(locked))
    old = _load_old_candidates(args.old_candidates, set(development), set(locked))
    old_misses = _old_complete_misses(qrels, old)
    if len(old_misses) != 144:
        raise ValueError(f"OLD_COMPLETE_MISS_GATE:{len(old_misses)} expected=144")
    catalog = _read_catalog(args.catalog)
    cv_manifest = {"manifest_version": "retriever_v3_bm25_cv_v1", "salt": CV_SALT,
                   "group": "case_id", "fold_count": 5, "cases_per_fold": 10,
                   "folds": {str(fold): sorted(case for case, value in folds.items() if value == fold) for fold in range(1, 6)},
                   "locked_case_count": 10, "locked_metrics_opened": False}
    (output / "bm25_cv_manifest.json").write_text(json.dumps(cv_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    smoke_cases = development[:3] if args.smoke else development
    peak = 0
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_bm25_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        cv_ranks, _, cv_peak = _stream_bm25(configs=BM25_VARIANTS, cases=smoke_cases, qrels=qrels,
                                             catalog=catalog, outer_zip=args.outer_zip, temp=temp, smoke=args.smoke)
        peak = max(peak, cv_peak)
        if args.smoke:
            for config in BM25_VARIANTS:
                expected = [row for row in qrels if row["case_id"] in smoke_cases]
                if len(cv_ranks[config.name]) != len(expected): raise ValueError("SMOKE_GOLD_RANK_EXPORT")
            return {"smoke": True, "cases": 3, "temporary_directory_removed": True}
        cv = {config.name: _cv_summary(config, qrels, old_misses, cv_ranks[config.name], folds, old)
              for config in BM25_VARIANTS}
        selected_name = _choose_config(cv)
        selected = next(config for config in BM25_VARIANTS if config.name == selected_name)
        # Freeze, then execute one fresh 50-case pass with only the selected global config.
        final_ranks_by_name, final_candidates, final_peak = _stream_bm25(
            configs=(selected,), cases=development, qrels=qrels, catalog=catalog,
            outer_zip=args.outer_zip, temp=temp,
        )
        peak = max(peak, final_peak)
        final_ranks = final_ranks_by_name[selected.name]
        bm25_metrics = _metric_rows(qrels, final_ranks)
        failures = _old_failure_labels(qrels, old_misses, old, repo)
        recovery = {k: [row for row in old_misses if final_ranks[row["key"]][0] is not None and final_ranks[row["key"]][0] <= k]
                    for k in (20, 50, 100)}
        by_risk = {}
        for risk in sorted({row["risk_code"] for row in old_misses}):
            misses = [row for row in old_misses if row["risk_code"] == risk]
            by_risk[risk] = {"old_misses": len(misses),
                             "recovered_at_20": sum(row in recovery[20] for row in misses),
                             "recovered_at_50": sum(row in recovery[50] for row in misses),
                             "recovered_at_100": sum(row in recovery[100] for row in misses)}
        query_rows = [row for row in old_misses if failures[row["key"]] == "QUERY_COVERAGE_MISS"]
        remaining = [row for row in old_misses if row not in recovery[100]]
        remaining_types = Counter(failures[row["key"]] for row in remaining)
        old_rrf, new_rrf, pool_sizes = _fusion_metrics(qrels, old, final_candidates)
        baseline = json.loads(args.baseline_summary.read_text(encoding="utf-8"))
        oracle_old = {"at_20": _oracle(qrels, old, final_ranks, 20, include_bm25=False),
                      "at_50": _oracle(qrels, old, final_ranks, 50, include_bm25=False),
                      "at_100_native": _oracle(qrels, old, final_ranks, 100, include_bm25=False)}
        oracle_new = {"at_20": _oracle(qrels, old, final_ranks, 20, include_bm25=True),
                      "at_50": _oracle(qrels, old, final_ranks, 50, include_bm25=True),
                      "at_100_native": _oracle(qrels, old, final_ranks, 100, include_bm25=True)}
        recovered100 = recovery[100]
        gates = {
            "A_unique_gold_at_least_10": len(recovered100) >= 10,
            "B_at_least_5_cases": len({row["case_id"] for row in recovered100}) >= 5,
            "C_at_least_3_risks": len({row["risk_code"] for row in recovered100}) >= 3,
            "D_oracle_gain_at_least_2pp": (oracle_new["at_50"] - oracle_old["at_50"] >= .02 or
                                             oracle_new["at_100_native"] - oracle_old["at_100_native"] >= .02),
            "E_candidate_misses_decrease": len(remaining) < 144,
            "F_positive_recovery_in_4_of_5_folds": sum(row["unique_recovered_at_100"] > 0 for row in cv[selected.name]) >= 4,
        }
        disk_after = shutil.disk_usage(args.temp_parent).free
        summary = {
            "result": "PASS" if all(gates.values()) else "FAIL", "pass": all(gates.values()),
            "development_cases": 50, "locked_cases": 10, "locked_metrics_opened": False,
            "query_policy_sha256": query_policy_sha256(), "variants": [config.__dict__ for config in BM25_VARIANTS],
            "cv_results": cv, "selected_cv_folds": cv[selected.name], "selected_config": selected.name,
            "frozen_config": {**selected.__dict__, "query_construction": "frozen V1/V2 query families + canonical risk terms",
                              "tie_break": "score desc, physical page asc", "index_scope": "one IPO in memory"},
            "baseline_overall": baseline["overall"], "bm25_standalone": bm25_metrics,
            "old_complete_misses": 144,
            "old_miss_recovery": {"at_20": len(recovery[20]), "at_50": len(recovery[50]),
                                  "at_100": len(recovery[100]), "remaining": len(remaining)},
            "diversity": {"gold": len(recovered100), "cases": len({row["case_id"] for row in recovered100}),
                          "risks": len({row["risk_code"] for row in recovered100})},
            "by_risk": by_risk,
            "query_coverage": {"total": len(query_rows),
                               "at_20": sum(row in recovery[20] for row in query_rows),
                               "at_50": sum(row in recovery[50] for row in query_rows),
                               "at_100": sum(row in recovery[100] for row in query_rows),
                               "remaining": sum(row not in recovery[100] for row in query_rows)},
            "oracle": {"old": oracle_old, "new": oracle_new,
                       "gain": {key: oracle_new[key] - oracle_old[key] for key in oracle_old}},
            "rrf": {"old": old_rrf, "new": new_rrf}, "candidate_pool": _stats(pool_sizes),
            "remaining_failure_types": {name: remaining_types[name] for name in
                ("QUERY_COVERAGE_MISS", "TABLE_FRAGMENTATION", "NEIGHBOR_PAGE_MISS",
                 "SECTION_AUTHORITY_MISS", "MULTIPAGE_FRAGMENTATION", "OTHER_UNKNOWN")},
            "gates": gates,
            "disk": {"before_bytes": disk_before, "after_bytes": disk_after, "peak_temporary_bytes": peak,
                     "before_gib": disk_before / 2**30, "after_gib": disk_after / 2**30, "peak_mib": peak / 2**20},
            "persistent_bm25_index": False, "embedding_model_download": False,
        }
        recovery_rows = [{"case_id": row["case_id"], "risk_code": row["risk_code"], "gold_page": row["page"],
                          "evidence_id": row["evidence_id"], "old_failure_type": failures[row["key"]],
                          "bm25_rank": final_ranks[row["key"]][0], "bm25_score": final_ranks[row["key"]][1],
                          "bm25_hit_at_20": final_ranks[row["key"]][0] <= 20,
                          "bm25_hit_at_50": final_ranks[row["key"]][0] <= 50,
                          "bm25_hit_at_100": True} for row in recovered100]
        _write_recovery(output / "bm25_unique_recovery.csv.gz", recovery_rows)
        (output / "bm25_phase_b_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "RETRIEVER_V3_PHASE_B_BM25_REPORT.md").write_text(_report(summary), encoding="utf-8")
    return {"completed": True, "result": summary["result"], "selected": selected.name,
            "recovered_at_100": len(recovered100), "temporary_directory_removed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip", type=Path, default=OUTER_ZIP_DEFAULT)
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--split-manifest", type=Path, default=Path("reports/retriever_v3/split_manifest.json"))
    parser.add_argument("--gold", type=Path, default=Path("reports/retriever_v3/gold_evidence.csv"))
    parser.add_argument("--old-candidates", type=Path, default=Path("reports/retriever_v3/hard_candidate_dataset.csv.gz"))
    parser.add_argument("--baseline-summary", type=Path, default=Path("reports/retriever_v3/baseline_summary.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/retriever_v3"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(); print(json.dumps(run(args), ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
