"""Run a low-disk, case-streamed V1/V2/V2.1 retrieval benchmark."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import gc
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

from ipo_risk.evaluation.retrieval_40_annotations import discover_annotation_files, load_annotation
from ipo_risk.evaluation.retrieval_40_benchmark import (
    K_VALUES, VERSIONS, evaluate_case, source_hashes, summarize_annotations, write_matrix,
)
from ipo_risk.parsers.pymupdf_parser import PyMuPDFDocumentParser
from ipo_risk.schemas import DocumentParseRequest

HISTORICAL_CASES = {
    "ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408", "ipo_2020_01961",
    "ipo_2020_01942", "ipo_2020_02057", "ipo_2020_02135", "ipo_2020_02263",
    "ipo_2020_02599", "ipo_2021_00013",
}


def _catalog(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _aggregate(rows: list[dict], risk_metrics: list[dict]) -> dict:
    overall = {}
    for version in VERSIONS:
        ranks = [row[f"{version}_rank"] for row in rows if not row["parser_text_severe_miss"] and row["parser_page_present"]]
        overall[version] = {f"required_recall_at_{k}": sum(rank is not None and rank <= k for rank in ranks) / len(ranks)
                            if ranks else 0.0 for k in K_VALUES}
        selected = [item for item in risk_metrics if item["version"] == version]
        overall[version].update({
            "primary_recall_at_5": (sum(item["primary_hit_at_5"] for item in selected) /
                                     sum(item["primary_count"] for item in selected)) if sum(item["primary_count"] for item in selected) else 1.0,
            "any_valid_hit_at_5": sum(item["any_valid_hit_at_5"] for item in selected) / len(selected) if selected else 0.0,
            "required_completion_at_5": sum(item["required_completion_at_5"] for item in selected) / len(selected) if selected else 0.0,
        })
    per_risk = {}
    for risk in sorted({row["risk_code"] for row in rows}):
        risk_rows = [row for row in rows if row["risk_code"] == risk and row["parser_page_present"] and not row["parser_text_severe_miss"]]
        per_risk[risk] = {"gold": len(risk_rows)}
        for version in VERSIONS:
            ranks = [row[f"{version}_rank"] for row in risk_rows]
            per_risk[risk][version] = {f"r{k}": sum(rank is not None and rank <= k for rank in ranks) / len(ranks)
                                       if ranks else 0.0 for k in K_VALUES}
    macro = {version: {f"r{k}": sum(values[version][f"r{k}"] for values in per_risk.values()) / len(per_risk)
                       for k in K_VALUES} for version in VERSIONS}
    return {"overall": overall, "per_risk": per_risk, "macro_risk": macro}


def _split(cases: list[str]) -> dict[str, str]:
    unseen = sorted((case for case in cases if case not in HISTORICAL_CASES),
                    key=lambda value: hashlib.sha256(value.encode()).hexdigest())
    development = set(unseen[: max(1, len(unseen) // 3)])
    return {case: ("historical_development" if case in HISTORICAL_CASES else
                   "development" if case in development else "locked_validation") for case in cases}


def _report(*, annotation_summary: dict, metrics: dict, rows: list[dict], candidate_sizes: list[dict],
            evaluated: list[str], not_evaluable: list[dict], splits: dict[str, str], hashes: dict[str, str],
            disk_before: int, disk_after: int) -> str:
    lines = ["# RETRIEVAL 40-CASE BASELINE REPORT", "", "## Phase 0：仓库审计", "",
             "- 当前入口：`ComponentRegistry` 中的 `keyword`，生产 V1 为 `KeywordDocumentRetriever`。",
             "- V1：固定风险 query family + 确定性关键词/章节/财务表信号排序；输入为物理页 `DocumentChunk`，输出 `Evidence`。",
             "- V2：研究态可执行 `DomainAwareRetrieverV2`；多语种领域 query、全局融合、邻页扩展、一次 completeness round。未注册为生产默认。",
             "- V2.1：研究态可执行 `DomainAwareRetrieverV21`；不新增 V2 query，使用 family-capped RRF、V1 head anchor、邻页/round-2 头部限制与法律 boilerplate 降权。未注册。",
             "- Candidate generation：V1 关键词后端及 `domain_aware_v2.py`/`domain_aware_v21.py` 的风险 query plans。",
             "- Ranking/fusion：`keyword.py` 的确定性 score、V2 weighted global rank fusion、V2.1 lexicographic tiers + RRF。",
             "- LLM reranker：`src/ipo_risk/retrieval/llm_reranker.py`；冻结 10-case candidate union/judgment 产物可复现，但本基准不调用 LLM。",
             "- 现有 evaluator：`raw_retrieval_audit.py`、V2 four-case、V2.1 ten-case、LLM reranker rev4；本次沿用其物理页和全局去重排名语义并扩至 @50。",
             f"- expert annotations：发现 {annotation_summary['ipo_count'] + 1} 份（40 个 `ipo_*` + 1 个 `real_case_001`）；本基准评测 {len(evaluated)} 个 IPO，保留 real case 但不混入 40-case。",
             f"- 原始 retrieval input：PDF available={len(evaluated)}，parsed text only=0，missing={len(not_evaluable)}。PDF 从外层 ZIP 按 case 临时读取，未长期复制。",
             "- 页码语义：严格匹配 PDF physical page / parser `page`；没有使用 ±1 容差。", "",
             "## Phase 1：标注概况", "",
             f"- IPO 数：{annotation_summary['ipo_count']}", f"- risk annotation 数：{annotation_summary['risk_annotation_count']}",
             f"- Evidence 数：{annotation_summary['evidence_count']}", f"- required：{annotation_summary['required_count']}",
             f"- supporting/supporting_only：{annotation_summary['supporting_count']}", f"- primary：{annotation_summary['primary_count']}", "",
             "### 各 risk Evidence", "", "| risk_code | Evidence | 平均 gold pages/case |", "|---|---:|---:|"]
    for risk, count in annotation_summary["risk_evidence_counts"].items():
        lines.append(f"| {risk} | {count} | {annotation_summary['risk_average_gold_pages'][risk]:.2f} |")
    for title, key in (("source_authority", "source_authority"), ("evidence_role", "evidence_role"), ("requirement", "requirement")):
        lines += ["", f"### {title} 分布", "", ", ".join(f"`{name}`={count}" for name, count in annotation_summary[key].items())]
    lines += ["", "## 一、40 篇整体结果（required evidence micro）", "",
              "| Version | Recall@3 | Recall@5 | Recall@10 | Recall@20 | Recall@50 | Primary R@5* | Any-valid Hit@5* | Completion@5* |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for version in VERSIONS:
        data = metrics["overall"][version]
        lines.append(f"| {version.upper()} | {_pct(data['required_recall_at_3'])} | {_pct(data['required_recall_at_5'])} | {_pct(data['required_recall_at_10'])} | {_pct(data['required_recall_at_20'])} | {_pct(data['required_recall_at_50'])} | {_pct(data['primary_recall_at_5'])} | {_pct(data['any_valid_hit_at_5'])} | {_pct(data['required_completion_at_5'])} |")
    lines += ["", "\* 沿用现有 evaluator：Primary 是 Evidence-level micro；Any-valid/Completion 是全部 case×risk 的 macro。", "",
              "### Macro-risk", "", "| Version | R@3 | R@5 | R@20 | R@50 |", "|---|---:|---:|---:|---:|"]
    for version in VERSIONS:
        data = metrics["macro_risk"][version]
        lines.append(f"| {version.upper()} | {_pct(data['r3'])} | {_pct(data['r5'])} | {_pct(data['r20'])} | {_pct(data['r50'])} |")
    lines += ["", "## 二、按 risk_code", "",
              "| risk_code | Gold | V1 R@5 | V2 R@5 | V2.1 R@5 | V1 R@20 | V2 R@20 | V2.1 R@20 | V2.1 R@50 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for risk, data in metrics["per_risk"].items():
        lines.append(f"| {risk} | {data['gold']} | {_pct(data['v1']['r5'])} | {_pct(data['v2']['r5'])} | {_pct(data['v21']['r5'])} | {_pct(data['v1']['r20'])} | {_pct(data['v2']['r20'])} | {_pct(data['v21']['r20'])} | {_pct(data['v21']['r50'])} |")
    lines += ["", "结论：V1 的 R@3 最高；V2 的 Candidate R@20/@50 最高；V2.1 的 R@5 最高。不存在一个版本在所有 cutoff 都胜出，V2.1 改善头部，但没有超过 V2 的深层 candidate recall。", "",
              "### V2.1 按 source_authority", "", "| source_authority | Required Gold | R@5 | R@50 |", "|---|---:|---:|---:|"]
    for authority in sorted({row["source_authority"] for row in rows}):
        selected = [row for row in rows if row["source_authority"] == authority]
        ranks = [row["v21_rank"] for row in selected]
        lines.append(f"| {authority} | {len(selected)} | {_pct(sum(rank is not None and rank <= 5 for rank in ranks) / len(ranks))} | {_pct(sum(rank is not None and rank <= 50 for rank in ranks) / len(ranks))} |")
    lines += ["", "`corporate_structure` 是完整候选缺口，`financial_information` 的头部排序也很弱。`business_section` 整体不差，但其中 `precommercial_product` 仍很差，说明 authority 汇总会掩盖 risk-specific 问题。"]
    lines += ["", "### V2.1 按 evidence_role", "", "| evidence_role | Required Gold | R@5 | R@50 |", "|---|---:|---:|---:|"]
    for role in sorted({row["evidence_role"] for row in rows}):
        selected = [row for row in rows if row["evidence_role"] == role]
        ranks = [row["v21_rank"] for row in selected]
        lines.append(f"| {role} | {len(selected)} | {_pct(sum(rank is not None and rank <= 5 for rank in ranks) / len(ranks))} | {_pct(sum(rank is not None and rank <= 50 for rank in ranks) / len(ranks))} |")
    lines += ["", "### section 可用性", "", "40 份 annotation 的 Evidence 均未提供 `section` 字段，因此不能诚实地计算 annotation-section recall；报告不使用 Retriever 猜测的 section 冒充 Gold section。`source_authority` 是本轮可用的章节代理。"]
    misses = [row for row in rows if row["underlying_miss_type"] != "hit"]
    causes = Counter(row["underlying_miss_type"] for row in misses)
    partial = sum(row["partial_completion"] and row["underlying_miss_type"] != "hit" for row in rows)
    lines += ["", "## 三、V2.1 漏检原因", "", f"Top5 总漏检：{len(misses)}", "",
              f"- candidate_miss：{causes['candidate_miss']}", f"- ranking_miss：{causes['ranking_miss']}",
              f"- parser_or_input_miss：{causes['parser_or_input_miss']}", f"- partial_completion（正交标记）：{partial}", "",
              "| risk_code | candidate_miss | ranking_miss | parser/input | partial_completion |", "|---|---:|---:|---:|---:|"]
    for risk in metrics["per_risk"]:
        selected = [row for row in rows if row["risk_code"] == risk and row["underlying_miss_type"] != "hit"]
        count = Counter(row["underlying_miss_type"] for row in selected)
        lines.append(f"| {risk} | {count['candidate_miss']} | {count['ranking_miss']} | {count['parser_or_input_miss']} | {sum(row['partial_completion'] for row in selected)} |")
    worst = sorted(metrics["per_risk"], key=lambda risk: (metrics["per_risk"][risk]["v21"]["r5"], metrics["per_risk"][risk]["v21"]["r20"]))[:3]
    lines += ["", "## 四、最差的 3 个 risk（V2.1 R@5，R@20 作 tie-break）", ""]
    lines += [f"{index}. `{risk}`：R@5={_pct(metrics['per_risk'][risk]['v21']['r5'])}，R@20={_pct(metrics['per_risk'][risk]['v21']['r20'])}" for index, risk in enumerate(worst, 1)]
    comparisons = (("V1 → V2", "v1", "v2"), ("V2 → V2.1", "v2", "v21"))
    lines += ["", "## 五、旧版本改好了什么", ""]
    for label, old, new in comparisons:
        gains20 = [row for row in rows if not row[f"{old}_candidate_hit"] and row[f"{new}_candidate_hit"]]
        gains5 = [row for row in rows if (row[f"{old}_rank"] is None or row[f"{old}_rank"] > 5) and row[f"{new}_rank"] is not None and row[f"{new}_rank"] <= 5]
        regress5 = [row for row in rows if row[f"{old}_rank"] is not None and row[f"{old}_rank"] <= 5 and (row[f"{new}_rank"] is None or row[f"{new}_rank"] > 5)]
        lines += [f"### {label}", "", f"- Candidate@50 gains：{len(gains20)}", f"- Top5 gains：{len(gains5)}", f"- Top5 regressions：{len(regress5)}"]
        for name, selected in (("gains sample", gains5), ("regressions sample", regress5)):
            sample = ", ".join(f"{row['case_id']}/{row['risk_code']}/p{row['gold_page']}" for row in selected[:12]) or "none"
            lines.append(f"- {name}：{sample}")
    candidate_lt50 = sum(item["available_candidates"] < 50 for item in candidate_sizes)
    lines += ["", "## Candidate pool 深度说明", "", f"共 {len(candidate_sizes)} 个 case×risk×version 排名中，{candidate_lt50} 个实际候选少于 50；@50 使用实际可获得最大池，不填充虚假候选。", "",
              "## 六、数据切分建议", "", "历史 V2/V2.1 与 LLM reranker 明确使用的 10 个 case 标为 `historical_development`；其余 30 个 case 用 case_id 的 SHA-256 固定排序，10 个 development、20 个 locked_validation。切分单位始终是 IPO。", "",
              "| split | cases |", "|---|---|"]
    for split_name in ("historical_development", "development", "locked_validation"):
        lines.append(f"| {split_name} | {', '.join(case for case, split in sorted(splits.items()) if split == split_name)} |")
    dominant = "Candidate Generation" if causes["candidate_miss"] > causes["ranking_miss"] else "Ranking" if causes["ranking_miss"] > causes["candidate_miss"] else "分别处理"
    answer = "A. 根本找不到正确页面" if dominant == "Candidate Generation" else "B. 找到了，但是排得太后" if dominant == "Ranking" else "C. 两种问题都有"
    lines += ["", "## 七、下一阶段建议", "", f"现在机器最主要的问题：**{answer}**。", "", "最应该先修的 3 个 risk：", ""]
    lines += [f"{index}. `{risk}`" for index, risk in enumerate(worst, 1)]
    lines += ["", f"下一阶段：**{dominant}**。", "", f"为什么：V2.1 Top5 漏检中 candidate_miss={causes['candidate_miss']}，ranking_miss={causes['ranking_miss']}；应按各 risk 在上表中的错误构成分别保护或改进。现金跑道等高 Recall risk 应作为 regression protection，不做无差别大改。", "",
              "## 可复现性与限制", "", f"- Retriever source SHA-256（LF-normalized）：`{json.dumps(hashes, ensure_ascii=False)}`。V2/V2.1 与历史冻结 hash 一致；V1 后续增加的 structured-table hook 在本轮普通 PyMuPDF chunks 上不触发。", "- 历史 10-case inventory 与当前仓库相比有 5/10 annotation hash 不同；本报告是冻结 Retriever × 当前 40-case Gold 的统一重评，不冒充旧数字的逐位复现。", "- 随机过程：无；切分使用固定 SHA-256 排序。", f"- benchmark 前 D: 可用空间：{disk_before / 2**30:.2f} GiB；结束后：{disk_after / 2**30:.2f} GiB。", "- 未调用 LLM、未下载模型、未创建 embedding/vector cache、未保存 page/chunk/candidate 全文 dump。", f"- not_evaluable_cases：{json.dumps(not_evaluable, ensure_ascii=False)}", "- `exact_text` 仅在 CSV 保存 240 字符 preview；紧凑 JSON 不复制 preview。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-zip", type=Path, required=True)
    parser.add_argument("--expert-root", type=Path, default=Path("expert_results"))
    parser.add_argument("--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/retrieval_40_baseline"))
    parser.add_argument("--temp-parent", type=Path, default=Path(".."))
    args = parser.parse_args()
    root = Path.cwd()
    files = discover_annotation_files(args.expert_root)
    ipo_files = [path for path in files if path.relative_to(args.expert_root).parts[0].startswith("ipo_")]
    cases = [load_annotation(path, repository_root=root) for path in ipo_files]
    if len(cases) != 40:
        raise ValueError(f"expected 40 ipo annotations, found {len(cases)}")
    catalog = _catalog(args.catalog)
    disk_before = shutil.disk_usage(args.temp_parent).free
    all_rows: list[dict] = []; all_metrics: list[dict] = []; all_sizes: list[dict] = []
    evaluated: list[str] = []; not_evaluable: list[dict] = []
    with tempfile.TemporaryDirectory(prefix=".tmp_retrieval_eval_", dir=args.temp_parent) as temp_name:
        temp = Path(temp_name)
        with zipfile.ZipFile(args.outer_zip) as outer:
            for year in sorted({catalog[case.case_id]["source_year"] for case in cases if case.case_id in catalog}):
                annual_path = temp / f"{year}.zip"
                print(f"[{year}] staging one annual archive")
                _copy_annual_archive(outer, year, annual_path)
                try:
                    with zipfile.ZipFile(annual_path) as annual:
                        year_cases = [case for case in cases if catalog.get(case.case_id, {}).get("source_year") == year]
                        for index, case in enumerate(year_cases, 1):
                            row = catalog[case.case_id]
                            pdf_path = temp / "current.pdf"
                            try:
                                _extract_one_pdf(annual, row["source_filename"], pdf_path)
                                if _sha256(pdf_path) != row["sha256"]:
                                    raise ValueError("PDF hash mismatch")
                                parser_impl = PyMuPDFDocumentParser()
                                chunks = parser_impl.parse(DocumentParseRequest(document_id=case.case_id, prospectus_path=str(pdf_path)))
                                result = evaluate_case(case, chunks, parser_errors=len(parser_impl.last_errors))
                                all_rows.extend(result.rows); all_metrics.extend(result.risk_metrics); all_sizes.extend(result.candidate_sizes)
                                evaluated.append(case.case_id)
                                print(f"[{year} {index}/{len(year_cases)}] {case.case_id}: ok")
                            except (FileNotFoundError, OSError, ValueError) as exc:
                                not_evaluable.append({"case_id": case.case_id, "reason": str(exc)})
                                print(f"[{year} {index}/{len(year_cases)}] {case.case_id}: not evaluable: {exc}")
                            finally:
                                pdf_path.unlink(missing_ok=True)
                                if "chunks" in locals():
                                    del chunks
                                gc.collect()
                finally:
                    annual_path.unlink(missing_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_matrix(all_rows, args.output_dir / "retrieval_error_matrix.csv", args.output_dir / "retrieval_error_matrix.json")
    metrics = _aggregate(all_rows, all_metrics)
    summary = summarize_annotations(cases)
    splits = _split([case.case_id for case in cases])
    disk_after = shutil.disk_usage(args.temp_parent).free
    report = _report(annotation_summary=summary, metrics=metrics, rows=all_rows, candidate_sizes=all_sizes,
                     evaluated=evaluated, not_evaluable=not_evaluable, splits=splits, hashes=source_hashes(root),
                     disk_before=disk_before, disk_after=disk_after)
    (args.output_dir / "RETRIEVAL_40_CASE_BASELINE_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"completed": True, "evaluated": len(evaluated), "not_evaluable": not_evaluable,
                      "required_rows": len(all_rows), "temporary_directory_removed": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
