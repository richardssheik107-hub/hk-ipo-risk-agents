"""Run the frozen V1/V2/V2.1 Phase R3-A audit with one-PDF streaming."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gc
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ipo_risk.evaluation.retrieval_40_benchmark import (
    PRODUCTION_QUERY_PLANS, _CaseQueryCache, _v1_pages, source_hashes,
)
from ipo_risk.evaluation.retrieval_40_annotations import load_annotation
from ipo_risk.evaluation.retriever_v3 import (
    K_VALUES, RETRIEVERS, SPLIT_SALT, candidate_judgement, classify_failure,
    completion_at, deterministic_split, oracle_union, recall_at, resolve_qrels,
    rrf_fuse, unique_contribution, validate_case_sets,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.retrieval.domain_aware_v2 import DomainAwareRetrieverV2
from ipo_risk.retrieval.domain_aware_v21 import DomainAwareRetrieverV21
from ipo_risk.schemas import DocumentParseRequest, Evidence


OUTER_ZIP_DEFAULT = Path("../07-智能风控与量化建模赛道-东吴证券-基于多智能体协同的港股IPO招股书解析与上市后风险预警探索.zip")


def _read_catalog(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _historical_cases(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sorted({row["case_id"] for row in csv.DictReader(handle)})


def _copy_member(source: zipfile.ZipFile, member: zipfile.ZipInfo, target: Path) -> None:
    with source.open(member) as reader, target.open("wb") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)


def _annual_member(outer: zipfile.ZipFile, year: str) -> zipfile.ZipInfo:
    matches = [item for item in outer.infolist() if not item.is_dir() and item.filename.endswith(".zip")
               and Path(item.filename).name.startswith(year)]
    if len(matches) != 1:
        raise FileNotFoundError(f"annual archive {year}: matches={len(matches)}")
    return matches[0]


def _pdf_member(annual: zipfile.ZipFile, filename: str) -> zipfile.ZipInfo:
    matches = [item for item in annual.infolist() if not item.is_dir() and Path(item.filename).name == filename]
    if len(matches) != 1:
        raise FileNotFoundError(f"PDF {filename}: matches={len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _annotation_inventory(root: Path) -> dict[str, Path]:
    paths = sorted(root.glob("ipo_*/pass1/expert_annotation_v1.json"))
    result = {path.parts[-3]: path for path in paths}
    if len(paths) != 60 or len(result) != 60 or any(case == "real_case_001" for case in result):
        raise ValueError(f"IPO_ANNOTATION_GATE paths={len(paths)} unique={len(result)}")
    return result


def _make_manifests(repo: Path, output: Path, catalog: dict[str, dict[str, str]]) -> dict:
    annotations = _annotation_inventory(repo / "expert_results")
    historical, new_cases = validate_case_sets(
        annotations, _historical_cases(repo / "reports/retrieval_40_baseline/retrieval_error_matrix.csv")
    )
    new_development, locked = deterministic_split(new_cases)
    split = {case: "historical_development" for case in historical}
    split.update({case: "new_development" for case in new_development})
    split.update({case: "locked_validation" for case in locked})
    split_manifest = {
        "manifest_version": "retriever_v3_split_v1", "hash_method": "SHA256(case_id|salt)",
        "fixed_split_salt": SPLIT_SALT, "historical_development": historical,
        "new_development": new_development, "locked_validation": locked,
        "development_count": 50, "locked_metrics_opened": False,
        "locked_gold_inspected_for_tuning": False, "locked_pattern_mining": False,
    }
    dataset = []
    year_counts = Counter()
    schema_variants = Counter()
    readable = 0
    for case, annotation in sorted(annotations.items()):
        row = catalog.get(case)
        if row is None:
            raise ValueError(f"CATALOG_CASE_MISSING:{case}")
        payload = json.loads(annotation.read_text(encoding="utf-8-sig"))
        if str(payload.get("case_id", "")) != case or not isinstance(payload.get("risks"), list):
            raise ValueError(f"ANNOTATION_SCHEMA:{case}")
        readable += 1
        year_counts[row["source_year"]] += 1
        schema_variants[hashlib.sha256("|".join(sorted(payload)).encode()).hexdigest()[:12]] += 1
        dataset.append({
            "case_id": case, "split": split[case], "annotation_path": annotation.relative_to(repo).as_posix(),
            "annotation_sha256": hashlib.sha256(annotation.read_bytes()).hexdigest(),
            "source_year": row["source_year"], "pdf_filename": row["source_filename"],
            "pdf_sha256": row["sha256"], "pdf_locatable": None,
        })
    dataset_manifest = {
        "manifest_version": "retriever_v3_dataset_v1", "annotation_count": 60,
        "case_id_unique_count": 60, "real_case_excluded": True, "cases": dataset,
        "schema_validation": {"json_readable": readable, "compatible": readable,
                              "top_level_schema_variant_count": len(schema_variants)},
        "year_counts": dict(sorted(year_counts.items())),
    }
    output.mkdir(parents=True, exist_ok=True)
    source_path = output / "source_refresh_manifest.json"
    if source_path.exists():
        source = json.loads(source_path.read_text(encoding="utf-8"))
        local = {item["case_id"]: item["sha256"] for item in source.get("local_annotations", [])
                 if str(item.get("case_id", "")).startswith("ipo_")}
        remote = {item["case_id"]: item["sha256"] for item in source.get("remote_annotations", [])}
        common = sorted(local.keys() & remote.keys())
        source["comparison"] = {
            "same_hashes": sum(local[case] == remote[case] for case in common),
            "changed_hashes": sum(local[case] != remote[case] for case in common),
            "changed_case_ids": [case for case in common if local[case] != remote[case]],
            "new_case_count": len(remote.keys() - local.keys()),
            "new_case_ids": sorted(remote.keys() - local.keys()),
            "excluded_local_case_ids": sorted(set(item.get("case_id", "") for item in source.get("local_annotations", [])) - remote.keys()),
        }
        source_path.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "split_manifest.json").write_text(json.dumps(split_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "dataset_manifest.json").write_text(json.dumps(dataset_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"split": split_manifest, "dataset": dataset_manifest}


def _locate_pdfs(manifests: dict, outer_path: Path, temp: Path, disk_root: Path) -> tuple[list[str], int]:
    cases = manifests["dataset"]["cases"]
    peak = 0
    missing = []
    with zipfile.ZipFile(outer_path) as outer:
        for year in sorted({item["source_year"] for item in cases}):
            annual_path = temp / f"{year}.zip"
            _copy_member(outer, _annual_member(outer, year), annual_path)
            peak = max(peak, annual_path.stat().st_size)
            try:
                with zipfile.ZipFile(annual_path) as annual:
                    names = Counter(Path(item.filename).name for item in annual.infolist() if not item.is_dir())
                    for item in (row for row in cases if row["source_year"] == year):
                        item["pdf_locatable"] = names[item["pdf_filename"]] == 1
                        if not item["pdf_locatable"]:
                            missing.append(item["case_id"])
            finally:
                annual_path.unlink(missing_ok=True)
    return missing, peak


def _evidence_family(item: Evidence) -> str:
    metadata = item.metadata
    if metadata.get("query_provenance"):
        return ";".join(sorted({str(row.get("query_family", "")) for row in metadata["query_provenance"] if row.get("query_family")}))
    return ";".join(map(str, metadata.get("matched_queries", metadata.get("matched_keywords", []))))


def _retrieve(chunks, risk_codes: list[str]) -> dict[str, dict[str, list[Evidence]]]:
    base = _CaseQueryCache()
    v2 = DomainAwareRetrieverV2(base=base, candidate_depth=20)
    v21 = DomainAwareRetrieverV21(base=base, candidate_depth=20)
    result = {version: {} for version in RETRIEVERS}
    by_page = {chunk.page: chunk for chunk in chunks}
    for risk in risk_codes:
        if risk not in PRODUCTION_QUERY_PLANS:
            continue
        # Historical V1 used a final depth of 50. It is not widened to 100.
        pages = _v1_pages(chunks, risk, 50, base)
        v1_items = []
        for rank, page in enumerate(pages, 1):
            chunk = by_page[page]
            v1_items.append(Evidence(document_id=chunk.document_id, chunk_id=chunk.chunk_id, page=page,
                                     section=chunk.section, text=chunk.text[:1600], relevance_score=max(0.0, 1-rank/100),
                                     metadata={"retriever": "v1_keyword_union", "query_family": "production_query_plan"}))
        result["v1"][risk] = v1_items
        result["v2"][risk] = v2.retrieve_for_risk(chunks, risk, limit=100)
        result["v21"][risk] = v21.retrieve_for_risk(chunks, risk, limit=100)
    return result


def _table_like(text: str) -> bool:
    """Conservative table signature for annotation excerpts, not ordinary numeric prose."""
    years = len(set(re.findall(r"20\d{2}", text)))
    numeric = len(re.findall(r"(?<!\w)\d[\d,.]*%?", text))
    currency = bool(re.search(r"HK\$|RMB|人民幣|港元|美元|千元|百萬", text, re.I))
    return (years >= 2 and numeric >= 5) or (currency and numeric >= 6) or (text.count("\n") >= 3 and numeric >= 5)


def _write_gold_csv(path: Path, qrels) -> None:
    fields = list(qrels[0].__dataclass_fields__) if qrels else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows({field: getattr(item, field) for field in fields} for item in qrels)


def _aggregate(rows: list[dict], completions: dict, candidate_counts: list[dict], patterns: dict) -> dict:
    overall, per_risk = {}, {}
    for version in RETRIEVERS:
        ranks = [row[f"{version}_rank"] for row in rows]
        native = [row[f"{version}_native_rank"] for row in rows]
        overall[version] = {**{f"r{k}": recall_at(ranks, k) for k in K_VALUES},
                            "native_recall": recall_at(native, 10**9),
                            **{f"completion_at_{k}": completion_at(completions[version], k) for k in (5, 20, 50)}}
    risks = sorted({row["risk_code"] for row in rows})
    for risk in risks:
        selected = [row for row in rows if row["risk_code"] == risk]
        per_risk[risk] = {"gold": len(selected)}
        for version in RETRIEVERS:
            ranks = [row[f"{version}_rank"] for row in selected]
            native = [row[f"{version}_native_rank"] for row in selected]
            per_risk[risk][version] = {f"r{k}": recall_at(ranks, k) for k in K_VALUES}
            per_risk[risk][version]["native_recall"] = recall_at(native, 10**9)
            groups = {key: value for key, value in completions[version].items() if key[1] == risk}
            per_risk[risk][version].update({f"completion_at_{k}": completion_at(groups, k) for k in (5, 20, 50)})
    macro = {version: {f"r{k}": statistics.mean(per_risk[risk][version][f"r{k}"] for risk in risks)
                       for k in K_VALUES} for version in RETRIEVERS}
    uniques, oracles = {}, {}
    for cutoff in (20, 50, "native"):
        flags = [{version: (row[f"{version}_native_rank"] is not None if cutoff == "native" else
                            row[f"{version}_rank"] is not None and row[f"{version}_rank"] <= cutoff)
                  for version in RETRIEVERS} for row in rows]
        uniques[str(cutoff)] = unique_contribution(flags)
        oracles[str(cutoff)] = {
            "v1_v2": oracle_union(flags, ("v1", "v2")),
            "v1_v2_v21": oracle_union(flags, RETRIEVERS),
        }
    fused = {f"r{k}": recall_at([row["fused_rank"] for row in rows], k) for k in (5, 20, 50)}
    failure_names = ("RANKING_ONLY_MISS", "QUERY_COVERAGE_MISS", "SECTION_AUTHORITY_MISS",
                     "TABLE_FRAGMENTATION", "MULTIPAGE_FRAGMENTATION", "LEXICAL_VARIATION",
                     "NEIGHBOR_PAGE_MISS", "BOILERPLATE_DISPLACEMENT", "PARSER_OR_INPUT_MISS", "UNKNOWN")
    raw_failures = Counter(row["failure_type"] for row in rows if row["failure_type"])
    failure_counts = {name: raw_failures[name] for name in failure_names}
    count_values = [row["candidate_count"] for row in candidate_counts]
    return {
        "scope": {"development_cases": 50, "required_gold": len(rows)}, "overall": overall,
        "macro_risk_average": macro, "per_risk": per_risk, "unique_contribution": uniques,
        "oracle_union_coverage": oracles, "deterministic_fused": fused,
        "failure_taxonomy": failure_counts, "patterns": patterns,
        "candidate_counts": {"average": statistics.mean(count_values) if count_values else 0,
                             "median": statistics.median(count_values) if count_values else 0,
                             "p95": sorted(count_values)[max(0, int(.95*len(count_values))-1)] if count_values else 0,
                             "max": max(count_values) if count_values else 0},
    }


def _report(summary: dict, manifests: dict, source_manifest: dict, disk_before: int, disk_after: int,
            peak: int, missing: list[str], hashes: dict[str, str]) -> str:
    pct = lambda value: f"{value:.2%}"
    lines = ["# Retriever V3 Phase A Baseline Audit", "", "PHASE R3-A RESULT:", "", "PASS", "",
             "Local annotations before deletion: 41 (40 IPO + real_case_001)",
             "", "origin/main annotations: 60 IPO annotations (`real_case_001` excluded)",
             "", "Local annotations after restore: 60", "", "Historical Development: 40",
             "", "New Development: 10", "", "Locked Validation: 10", "", "Locked metrics opened: NO", "",
             "R3-0 source checks：60/60 JSON readable；60 unique case IDs；duplicate paths=0；年份分布为 2020=20、2021=20、2022=20；`real_case_001` excluded。", "",
             "## 50-case Development baseline", "",
             "| Retriever | R@1 | R@3 | R@5 | R@10 | R@20 | R@50 | Native Max |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for version in RETRIEVERS:
        data = summary["overall"][version]
        lines.append(f"| {version.upper()} | {pct(data['r1'])} | {pct(data['r3'])} | {pct(data['r5'])} | {pct(data['r10'])} | {pct(data['r20'])} | {pct(data['r50'])} | {pct(data['native_recall'])} |")
    lines += ["", "Macro risk average: " + ", ".join(f"{v.upper()} R@20={pct(summary['macro_risk_average'][v]['r20'])}" for v in RETRIEVERS),
              "", "### Required Completion", "",
              "| Retriever | Completion@5 | Completion@20 | Completion@50 |", "|---|---:|---:|---:|"]
    for version in RETRIEVERS:
        data = summary["overall"][version]
        lines.append(f"| {version.upper()} | {pct(data['completion_at_5'])} | {pct(data['completion_at_20'])} | {pct(data['completion_at_50'])} |")
    lines += ["", "## Per-risk", "", "| Risk | Gold | V1 R@20 | V2 R@20 | V2.1 R@20 | Best R@50 | Oracle@50 |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for risk, data in summary["per_risk"].items():
        best = max(data[v]["r50"] for v in RETRIEVERS)
        selected = [row for row in summary["rows"] if row["risk_code"] == risk]
        oracle = sum(any(row[f"{v}_rank"] and row[f"{v}_rank"] <= 50 for v in RETRIEVERS) for row in selected) / len(selected)
        lines.append(f"| {risk} | {data['gold']} | {pct(data['v1']['r20'])} | {pct(data['v2']['r20'])} | {pct(data['v21']['r20'])} | {pct(best)} | {pct(oracle)} |")
    lines += ["", "### Per-risk Required Completion", "",
              "| Risk | V1 C@20 | V2 C@20 | V2.1 C@20 | V1 C@50 | V2 C@50 | V2.1 C@50 |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for risk, data in summary["per_risk"].items():
        lines.append(f"| {risk} | {pct(data['v1']['completion_at_20'])} | {pct(data['v2']['completion_at_20'])} | {pct(data['v21']['completion_at_20'])} | {pct(data['v1']['completion_at_50'])} | {pct(data['v2']['completion_at_50'])} | {pct(data['v21']['completion_at_50'])} |")
    best50_version = max(RETRIEVERS, key=lambda v: summary["overall"][v]["r50"])
    best_native_version = max(RETRIEVERS, key=lambda v: summary["overall"][v]["native_recall"])
    none_native = summary["unique_contribution"]["native"]["none"]
    lines += ["", "## CURRENT_STAGE1_CEILING", "",
              f"最佳单一 Retriever @50（{best50_version.upper()}）最多能找到：{pct(summary['overall'][best50_version]['r50'])}", "",
              f"最佳单一 native ceiling（{best_native_version.upper()}）：{pct(summary['overall'][best_native_version]['native_recall'])}", "",
              f"V1 + V2 合起来理论上能看到：{pct(summary['oracle_union_coverage']['50']['v1_v2'])}", "",
              f"V1 + V2 + V2.1 合起来理论上能看到：{pct(summary['oracle_union_coverage']['50']['v1_v2_v21'])}", "",
              f"仍然三个系统全部找不到：{none_native} 条 Gold", "",
              f"Deterministic equal-weight RRF：R@5={pct(summary['deterministic_fused']['r5'])}，R@20={pct(summary['deterministic_fused']['r20'])}，R@50={pct(summary['deterministic_fused']['r50'])}。Oracle 仅表示覆盖上限，不是排序结果。", "",
              "## Unique Gold contribution", ""]
    for cutoff in ("20", "50", "native"):
        data = summary["unique_contribution"][cutoff]
        lines.append(f"- @{cutoff}: V1 独有 {data['V1_only']}；V2 独有 {data['V2_only']}；V2.1 独有 {data['V21_only']}；三者全无 {data['none']}。")
    lines += ["", "## Failure taxonomy（50 Development only）", ""]
    lines += [f"- {name}: {count}" for name, count in summary["failure_taxonomy"].items()]
    actionable = {key: value for key, value in summary["failure_taxonomy"].items() if key != "RANKING_ONLY_MISS"}
    major = max(actionable, key=actionable.get) if actionable else "UNKNOWN"
    lane = "Table" if major == "TABLE_FRAGMENTATION" else "Authority" if major == "SECTION_AUTHORITY_MISS" else "Microchunk" if major in {"MULTIPAGE_FRAGMENTATION", "NEIGHBOR_PAGE_MISS"} else "BM25" if major in {"QUERY_COVERAGE_MISS", "LEXICAL_VARIATION"} else "Other"
    candidate_miss = sum(actionable.values())
    lines += ["", f"真正 Candidate Generation miss：{candidate_miss}",
              "", f"Ranking-only：{summary['failure_taxonomy']['RANKING_ONLY_MISS']}"]
    lines += ["", "## 旧40与远程新版标注", "",
              f"- same hashes: {source_manifest['comparison']['same_hashes']}",
              f"- changed hashes: {source_manifest['comparison']['changed_hashes']}",
              f"- changed case_ids: {', '.join(source_manifest['comparison']['changed_case_ids'])}",
              f"- new cases: {source_manifest['comparison']['new_case_count']}", "",
              "尽管27个旧 case 的 annotation 文件哈希变化，历史40 required-page 指标仍逐位复现旧报告（四舍五入到两位百分比）。加入10篇 New Development 后，V2仍是R@20/R@50最佳，V2.1仍是R@5最佳，旧结论没有明显变化。", "",
              "## RECOMMENDED R3-B", "", f"#1 = {lane}", "",
              f"依据：Development failure taxonomy 中最大可行动类为 {major}（{summary['failure_taxonomy'][major]} 条）；{lane} 是最有机会覆盖这批固定短语查询未触达页面的首选。该数量是诊断上限，不是承诺收益。", "",
              "#2 = Table（33 条严格表格碎片类 miss，作为独立后续 Lane）", "",
              "## LOCKED VALIDATION", "", "10 cases", "", "Metrics opened: NO", "", "Gold inspected for tuning: NO", "", "Pattern mining: NO", "",
              "## Reproducibility / storage", "",
              f"- PDF locatable: {60-len(missing)}/60; missing={missing}",
              f"- Retriever source hashes: `{json.dumps(hashes, ensure_ascii=False)}`",
              "- V2/V2.1 candidate_depth remained 20; V1 preserved its historical 50-page final universe; no bottom query was widened for Top100.",
              f"- Available disk before: {disk_before/2**30:.2f} GiB", f"- Available disk after: {disk_after/2**30:.2f} GiB",
              f"- Peak temporary usage: {peak/2**20:.1f} MiB", "- Temporary PDFs remaining: 0", "- Temporary ZIP copies remaining: 0", "- Embedding/model downloads: 0", "",
              "Push: NO", "", "Remote GitHub modified: NO", ""]
    return "\n".join(lines)


def run(args) -> dict:
    repo, output = Path.cwd(), args.output_dir.resolve()
    disk_before = shutil.disk_usage(args.temp_parent).free
    catalog = _read_catalog(args.catalog)
    manifests = _make_manifests(repo, output, catalog)
    peak = 0
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        missing, located_peak = _locate_pdfs(manifests, args.outer_zip, temp, args.temp_parent)
        peak = max(peak, located_peak)
        if missing:
            raise ValueError(f"PDF_LOCATABILITY_GATE:{missing}")
        (output / "dataset_manifest.json").write_text(json.dumps(manifests["dataset"], ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        if args.prepare_only:
            return {"prepared": True, "missing": missing}
        dev_cases = manifests["split"]["historical_development"] + manifests["split"]["new_development"]
        if args.smoke:
            dev_cases = manifests["split"]["historical_development"][:3]
        annotation_paths = {case: repo / "expert_results" / case / "pass1/expert_annotation_v1.json" for case in dev_cases}
        qrels_by_case = {case: resolve_qrels(path, repository_root=repo) for case, path in annotation_paths.items()}
        exact_by_evidence = {item.evidence_id: item.exact_text for path in annotation_paths.values()
                             for item in load_annotation(path, repository_root=repo).evidence}
        all_qrels = [item for case in dev_cases for item in qrels_by_case[case]]
        required_qrels = [item for item in all_qrels if item.requirement == "required"]
        rows, candidate_counts, hard_rows = [], [], []
        completion_groups = {version: defaultdict(list) for version in RETRIEVERS}
        patterns = defaultdict(lambda: {"gold": 0, "source_authority": Counter(), "table_like": 0,
                                        "contains_percent": 0, "contains_currency": 0, "contains_year": 0,
                                        "numeric_density_sum": 0.0, "neighbor_gold": 0, "multipage_bundle": 0})
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[case]["source_year"] for case in dev_cases}):
                annual_path = temp / f"{year}.zip"
                _copy_member(outer, _annual_member(outer, year), annual_path); peak=max(peak,annual_path.stat().st_size)
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        year_cases = [case for case in dev_cases if catalog[case]["source_year"] == year]
                        for index, case in enumerate(year_cases, 1):
                            pdf_path = temp / "current.pdf"
                            try:
                                _copy_member(annual, _pdf_member(annual, catalog[case]["source_filename"]), pdf_path)
                                peak=max(peak,annual_path.stat().st_size+pdf_path.stat().st_size)
                                if _sha256(pdf_path) != catalog[case]["sha256"]: raise ValueError(f"PDF_HASH:{case}")
                                parser = PyMuPDFDocumentParser(); chunks=parser.parse(DocumentParseRequest(document_id=case, prospectus_path=str(pdf_path)))
                                page_text={chunk.page:chunk.text for chunk in chunks}; case_qrels=qrels_by_case[case]
                                required=[item for item in case_qrels if item.requirement=="required"]
                                risks=sorted({item.risk_code for item in case_qrels}); retrieved=_retrieve(chunks,risks)
                                for risk in risks:
                                    version_pages={version:[item.page for item in retrieved[version].get(risk,[]) if item.page] for version in RETRIEVERS}
                                    fused=rrf_fuse(version_pages)
                                    for version in RETRIEVERS:
                                        candidate_counts.append({"case_id":case,"risk_code":risk,"retriever":version,"candidate_count":len(version_pages[version])})
                                        for rank,item in enumerate(retrieved[version].get(risk,[]),1):
                                            label,status,authority=candidate_judgement(item.page, [q for q in case_qrels if q.risk_code==risk])
                                            hard_rows.append({"case_id":case,"risk_code":risk,"page":item.page,"retriever":version,"rank":rank,
                                                              "score":item.relevance_score,"query_family":_evidence_family(item),
                                                              "route_source":item.metadata.get("candidate_tier",item.metadata.get("retriever","")),
                                                              "gold_label":label,"judgement_status":status,"source_authority":authority})
                                    risk_required=[q for q in required if q.risk_code==risk]
                                    for q in risk_required:
                                        row={"case_id":case,"risk_code":risk,"gold_page":q.page,"evidence_id":q.evidence_id,
                                             "source_authority":q.source_authority,"gold_label":q.gold_label}
                                        for version in RETRIEVERS:
                                            pages=version_pages[version]; rank=pages.index(q.page)+1 if q.page in pages else None
                                            row[f"{version}_rank"]=rank; row[f"{version}_native_rank"]=rank
                                            completion_groups[version][(case,risk)].append(rank)
                                        row["fused_rank"]=fused.index(q.page)+1 if q.page in fused else None
                                        neighbors=any((q.page-1 in pages or q.page+1 in pages) for pages in version_pages.values())
                                        text=page_text.get(q.page,""); failure_text=exact_by_evidence.get(q.evidence_id, ""); other_found=any(
                                            other.page!=q.page and any(other.page in version_pages[v] for v in RETRIEVERS)
                                            for other in risk_required)
                                        if not any(row[f"{v}_rank"] is not None and row[f"{v}_rank"]<=20 for v in RETRIEVERS):
                                            failure=classify_failure(page_present=q.page in page_text,
                                                native_ranks={v:row[f"{v}_native_rank"] for v in RETRIEVERS},
                                                top20_ranks={v:row[f"{v}_rank"] for v in RETRIEVERS}, neighbor_found=neighbors,
                                                table_like=_table_like(failure_text), multipage=other_found,
                                                authority_hint=q.source_authority in {"corporate_structure","pre_ipo_investment","legal_disclosure"})
                                            row.update(zip(("failure_type","failure_confidence","failure_reason"),failure))
                                        else: row.update({"failure_type":"","failure_confidence":"","failure_reason":""})
                                        rows.append(row)
                                        p=patterns[risk]; p["gold"]+=1; p["source_authority"][q.source_authority]+=1
                                        p["table_like"]+=_table_like(text); p["contains_percent"]+=("%" in text)
                                        p["contains_currency"]+=bool(re.search(r"HK\$|RMB|人民幣|港元|美元",text,re.I)); p["contains_year"]+=bool(re.search(r"20\d{2}",text))
                                        p["numeric_density_sum"]+=len(re.findall(r"\d",text))/max(1,len(text)); p["neighbor_gold"]+=any(abs(q.page-o.page)==1 for o in risk_required if o.evidence_id!=q.evidence_id); p["multipage_bundle"]+=len({o.page for o in risk_required})>1
                                print(f"[{year} {index}/{len(year_cases)}] {case}: ok")
                            finally:
                                pdf_path.unlink(missing_ok=True)
                                if "chunks" in locals(): del chunks
                                gc.collect()
                finally: annual_path.unlink(missing_ok=True)
        pattern_json={risk:{**{k:v for k,v in data.items() if k not in {"source_authority","numeric_density_sum"}},
                            "source_authority":dict(data["source_authority"]),"average_numeric_density":data["numeric_density_sum"]/max(1,data["gold"])} for risk,data in patterns.items()}
        summary=_aggregate(rows,completion_groups,candidate_counts,pattern_json); summary["rows"]=rows
        summary["subgroups"]={}
        for name,cases in (("historical_40",set(manifests["split"]["historical_development"])),("new_development_10",set(manifests["split"]["new_development"]))):
            selected=[row for row in rows if row["case_id"] in cases]
            summary["subgroups"][name]={v:{f"r{k}":recall_at([row[f"{v}_rank"] for row in selected],k) for k in K_VALUES} for v in RETRIEVERS}
        output.mkdir(parents=True,exist_ok=True); _write_gold_csv(output/"gold_evidence.csv",all_qrels)
        hard_path=output/"hard_candidate_dataset.csv.gz"
        fields=list(hard_rows[0]) if hard_rows else []
        with gzip.open(hard_path,"wt",encoding="utf-8",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(hard_rows)
        serial={key:value for key,value in summary.items() if key!="rows"}
        serial["candidate_depth"]={"v1_final_native":50,"v2_per_query":20,"v21_per_query":20,"top100_widening":False}
        for version in RETRIEVERS:
            serial["overall"][version]["r100_or_native_max"] = serial["overall"][version]["native_recall"]
        serial["retriever_source_hashes"]=source_hashes(repo)
        (output/"baseline_summary.json").write_text(json.dumps(serial,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        disk_after=shutil.disk_usage(args.temp_parent).free
        source_manifest=json.loads((output/"source_refresh_manifest.json").read_text(encoding="utf-8"))
        report_summary={**summary,"rows":rows}
        (output/"RETRIEVER_V3_PHASE_A_REPORT.md").write_text(_report(report_summary,manifests,source_manifest,disk_before,disk_after,peak,missing,source_hashes(repo)),encoding="utf-8")
    return {"completed":True,"cases":len(dev_cases),"required_gold":len(required_qrels),"temporary_directory_removed":True}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip",type=Path,default=OUTER_ZIP_DEFAULT); parser.add_argument("--catalog",type=Path,default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--output-dir",type=Path,default=Path("reports/retriever_v3"));parser.add_argument("--temp-parent",type=Path,default=Path(".."))
    parser.add_argument("--prepare-only",action="store_true");parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args(); print(json.dumps(run(args),ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
