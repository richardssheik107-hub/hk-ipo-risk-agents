"""Run the one-shot post-freeze Phase 0.6C Revision-4 Gold evaluation."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable

from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle
from ipo_risk.evaluation.llm_reranker_rev4 import (
    VARIANT_NAMES,
    breakdown,
    evaluate_ranks,
    facet_coverage,
    gold_records,
    promotion_matrix,
    ranks_from_audits,
    reliability_analysis,
    runtime_case_aliases,
    semantic_error_taxonomy,
    stage1_and_llm_ranks,
)
from ipo_risk.evaluation.raw_retrieval_audit import RawRetrievalAudit
from ipo_risk.retrieval.domain_aware_v2 import RISK_DOMAINS


OUT_NAMES = (
    "01_gold_inventory.json",
    "02_baseline_reproduction.json",
    "03_variant_metrics.json",
    "04_variant_metrics.csv",
    "05_case_breakdown.csv",
    "06_domain_breakdown.csv",
    "07_risk_breakdown.csv",
    "08_promotion_regression_matrix.csv",
    "09_candidate_coverage_misses.csv",
    "10_fallback_reliability_analysis.json",
    "11_completed_only_diagnostic.json",
    "12_facet_coverage.json",
    "13_semantic_error_taxonomy.json",
    "14_promotion_decision.json",
    "15_phase_06c_final_report.md",
    "16_post_gold_evaluation_freeze_manifest.json",
)

HISTORICAL = {
    "v1": {
        "required_recall_at": {1: 0.1466, 3: 0.3448, 5: 0.4138, 10: 0.5, 20: 0.569},
        "required_completion_at": {1: 0.1, 3: 0.275, 5: 0.3625, 10: 0.475, 20: 0.55},
        "mrr": 0.2669,
    },
    "v2": {
        "required_recall_at": {1: 0.1466, 3: 0.3103, 5: 0.3793, 10: 0.5086, 20: 0.5948},
        "required_completion_at": {1: 0.1, 3: 0.25, 5: 0.325, 10: 0.4625, 20: 0.55},
        "mrr": 0.2616,
    },
    "v21": {
        "required_recall_at": {1: 0.1207, 3: 0.319, 5: 0.4569, 10: 0.5086, 20: 0.5862},
        "required_completion_at": {1: 0.125, 3: 0.275, 5: 0.45, 10: 0.5, 20: 0.55},
        "mrr": 0.2495,
    },
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git(*args: str, binary: bool = False) -> str | bytes:
    return subprocess.check_output(["git", *args], text=not binary)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _load_gold(ref: str, canonical_cases: list[str]) -> tuple[list[ExpertAnnotationBundle], dict[str, str]]:
    bundles, hashes = [], {}
    for case_id in canonical_cases:
        rel = f"expert_results/{case_id}/pass1/expert_annotation_v1.json"
        raw = _git("show", f"{ref}:{rel}", binary=True)
        assert isinstance(raw, bytes)
        bundle = ExpertAnnotationBundle.model_validate_json(raw)
        if bundle.case_id != case_id:
            raise ValueError(f"GOLD_CASE_ID_MISMATCH:{case_id}")
        bundles.append(bundle)
        hashes[rel] = sha256(raw).hexdigest()
    return bundles, hashes


def _load_audits(root: Path, variant: str, cases: list[str]) -> list[RawRetrievalAudit]:
    return [
        RawRetrievalAudit.model_validate_json(
            (root / variant / case_id / "raw_retrieval_audit.json").read_text(encoding="utf-8")
        )
        for case_id in cases
    ]


def _flatten_metrics(metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in VARIANT_NAMES:
        item = metrics[variant]
        rows.append(
            {
                "variant": variant,
                **{f"required_at_{k}": item["required_recall_at"][k] for k in (1, 3, 5, 10, 20)},
                **{f"completion_at_{k}": item["required_completion_at"][k] for k in (3, 5, 10)},
                "mrr": item["mrr"],
            }
        )
    return rows


def _markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], percent: set[str]) -> str:
    header = "| " + " | ".join(label for _, label in columns) + " |"
    divider = "| " + " | ".join("---" if index == 0 else "---:" for index in range(len(columns))) + " |"
    lines = [header, divider]
    for row in rows:
        values = []
        for key, _ in columns:
            value = row[key]
            values.append(f"{value:.2%}" if key in percent else f"{value:.4f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--gold-ref", default="4ba86a4ebbb3033b6c9966d07f5351afa18dc206")
    parser.add_argument("--pilot-root", type=Path, default=Path("reports/llm_reranker_pilot"))
    parser.add_argument("--output-root", type=Path, default=Path("reports/llm_reranker_pilot/formal_evaluation_rev4"))
    args = parser.parse_args()
    if args.output_root.exists():
        raise SystemExit("OFFICIAL_EVALUATION_OUTPUT_ALREADY_EXISTS")

    pre_path = args.pilot_root / "llm_reranker_pre_gold_freeze_rev4.json"
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    expected_pre_hash = "01983ae29c982d8cdca3a17ed16b422ea9269cb5b4c7f0cc4add11be4711079b"
    if _sha(pre_path) != expected_pre_hash:
        raise SystemExit("PRE_GOLD_MANIFEST_HASH_MISMATCH")
    required_pre = {
        "freeze_revision": 4,
        "decision": "CONTINUE_REVISION_4",
        "pre_gold_freeze_complete": True,
        "gold_loaded": False,
        "blind_2025_accessed": False,
        "official_task_count_actual": 80,
        "official_unique_task_keys": 80,
        "official_completed": 65,
        "official_failed": 15,
        "candidate_pool_sha256": "51037b682dad4d133db14417915fd9eaf749b8109ea8e1641ff1685ebeb17bfe",
        "official_judgment_aggregate_sha256": "aa1b62e87158ccc8e46cb3fe296bfc624fee9b6b8994a4d71355e730c60b3912",
    }
    if any(pre.get(key) != value for key, value in required_pre.items()):
        raise SystemExit("PRE_GOLD_INTEGRITY_FAILURE")
    if pre["source_hash_mismatches"] or not pre["no_official_failure_overwrite"]:
        raise SystemExit("PRE_GOLD_INTEGRITY_FAILURE")

    candidate_path = args.pilot_root / "candidate_pools.json"
    candidate_rows = json.loads(candidate_path.read_text(encoding="utf-8"))
    runtime_cases = list(dict.fromkeys(row["case_id"] for row in candidate_rows))
    baseline_manifest_path = args.baseline_root / "v21_freeze_manifest.json"
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    canonical_cases = [
        *baseline_manifest["development_cases"],
        *baseline_manifest["historical_regression_cases"],
        *baseline_manifest["locked_validation_cases"],
    ]
    aliases = runtime_case_aliases(canonical_cases, runtime_cases)
    bundles, gold_hashes = _load_gold(args.gold_ref, canonical_cases)
    records = gold_records(bundles, aliases)

    judgments = {}
    task_status = {}
    judgment_hashes = {}
    for row in candidate_rows:
        path = args.pilot_root / "judgments" / f"{row['case_id']}__{row['risk_code']}.json"
        frozen = json.loads(path.read_text(encoding="utf-8"))
        judgments[(row["case_id"], row["risk_code"])] = frozen
        canonical_task = (aliases[row["case_id"]], row["risk_code"])
        task_status[canonical_task] = frozen["status"]
        judgment_hashes[path.name] = _sha(path)
    if len(judgments) != 80 or Counter(task_status.values()) != Counter({"completed": 65, "failed": 15}):
        raise SystemExit("OFFICIAL_CACHE_INTEGRITY_FAILURE")

    baseline_audits = {
        variant: _load_audits(args.baseline_root, variant, canonical_cases)
        for variant in ("v1", "v2", "v21")
    }
    for audits in baseline_audits.values():
        for audit in audits:
            rel = f"expert_results/{audit.case_id}/pass1/expert_annotation_v1.json"
            if audit.annotation_sha256 != gold_hashes[rel]:
                raise SystemExit(f"BASELINE_GOLD_HASH_MISMATCH:{audit.case_id}")
    variants = {variant: ranks_from_audits(audits) for variant, audits in baseline_audits.items()}
    d_ranks, e_ranks, llm_order, judgment_bundles = stage1_and_llm_ranks(
        records, candidate_rows, judgments, aliases
    )
    variants["stage1_union"] = d_ranks
    variants["llm_rev4"] = e_ranks
    metrics = {name: evaluate_ranks(records, ranks) for name, ranks in variants.items()}

    args.output_root.mkdir(parents=True)
    by_domain = breakdown(records, variants, group_by="domain")
    by_risk = breakdown(records, variants, group_by="risk")
    by_case = breakdown(records, variants, group_by="case")
    matrix = promotion_matrix(records, variants, task_status)
    reliability = reliability_analysis(task_status)
    reliability.update(
        {
            "diagnostic_replays": 3,
            "diagnostic_replays_included_in_metrics": 0,
            "diagnostic_interpretation": "diagnostic non-reproduction",
            "real_llm_calls_during_evaluation": 0,
            "gold_leakage": False,
            "blind_2025_accessed": False,
        }
    )
    completed_tasks = {task for task, status in task_status.items() if status == "completed"}
    fallback_tasks = set(task_status) - completed_tasks
    completed_diag = {
        "label": "DIAGNOSTIC UPPER-BOUND ONLY",
        "official_all_task_llm": metrics["llm_rev4"],
        "completed_subset": {
            "stage1_union": evaluate_ranks(records, d_ranks, task_filter=completed_tasks),
            "llm_rev4": evaluate_ranks(records, e_ranks, task_filter=completed_tasks),
        },
        "fallback_subset": {
            "stage1_union": evaluate_ranks(records, d_ranks, task_filter=fallback_tasks),
            "llm_rev4": evaluate_ranks(records, e_ranks, task_filter=fallback_tasks),
        },
    }
    facets = facet_coverage(llm_order, judgment_bundles)
    taxonomy = semantic_error_taxonomy(
        records, d_ranks, e_ranks, task_status, llm_order, judgment_bundles
    )

    drift_rows = []
    for variant in ("v1", "v2", "v21"):
        for family in ("required_recall_at", "required_completion_at"):
            for k, historical in HISTORICAL[variant][family].items():
                reproduced = metrics[variant][family][k]
                drift_rows.append(
                    {
                        "variant": variant,
                        "metric": f"{family}_{k}",
                        "historical": historical,
                        "reproduced": reproduced,
                        "absolute_difference": abs(reproduced - historical),
                    }
                )
        drift_rows.append(
            {
                "variant": variant,
                "metric": "mrr",
                "historical": HISTORICAL[variant]["mrr"],
                "reproduced": metrics[variant]["mrr"],
                "absolute_difference": abs(metrics[variant]["mrr"] - HISTORICAL[variant]["mrr"]),
            }
        )
    baseline_drift = any(row["absolute_difference"] > 0.00005 for row in drift_rows)
    baseline_reproduction = {
        "baseline_reproduced": not baseline_drift,
        "display_tolerance": 0.00005,
        "drift_rows": drift_rows,
        "source_ref": "origin/eval/retriever-v21-ten-case-ranking@a99cdf8",
        "source_manifest_sha256": _sha(baseline_manifest_path),
    }

    inventory = {
        "benchmark_label": "POST-FREEZE RETROSPECTIVE BENCHMARK",
        "case_count": len(bundles),
        "risk_task_count": len({record.task for record in records}),
        "evidence_count": len(records),
        "required_evidence_count": sum(record.requirement == "required" for record in records),
        "primary_evidence_count": sum(record.evidence_role == "primary" for record in records),
        "unique_gold_page_count": len({(record.case_id, record.page) for record in records}),
        "canonical_cases": canonical_cases,
        "runtime_case_aliases": aliases,
        "requested_case_id_difference": {
            "runtime": "ipo_2020_00013",
            "canonical_gold": "ipo_2021_00013",
            "sample_changed": False,
        },
        "gold_ref": args.gold_ref,
        "gold_source_hashes": gold_hashes,
        "gold_set_drift": False,
        "previously_exposed_at_project_level": True,
        "reranker_contract_frozen_before_gold": True,
    }

    best = {
        metric: max(
            (
                metrics[v]["required_recall_at"][int(metric.rsplit("_", 1)[-1])]
                if metric.startswith("required")
                else metrics[v]["required_completion_at"][5]
                if metric == "completion_at_5"
                else metrics[v]["mrr"]
            )
            for v in ("v1", "v2", "v21")
        )
        for metric in ("required_at_3", "required_at_5", "completion_at_5", "mrr")
    }
    domain_rows = {(row["domain"], row["variant"]): row for row in by_domain}
    domain_regressions = []
    for domain in sorted(set(RISK_DOMAINS.values())):
        deterministic_best = max(domain_rows[(domain, v)]["required_at_5"] for v in ("v1", "v2", "v21"))
        actual = domain_rows[(domain, "llm_rev4")]["required_at_5"]
        if actual + 1e-12 < deterministic_best:
            domain_regressions.append(
                {"domain": domain, "best_deterministic_required_at_5": deterministic_best, "llm_required_at_5": actual}
            )
    criteria = {
        "required_at_3_beats_best_deterministic": metrics["llm_rev4"]["required_recall_at"][3] > best["required_at_3"],
        "required_at_5_beats_best_deterministic": metrics["llm_rev4"]["required_recall_at"][5] > best["required_at_5"],
        "completion_at_5_at_least_best_deterministic": metrics["llm_rev4"]["required_completion_at"][5] >= best["completion_at_5"],
        "mrr_at_least_v1": metrics["llm_rev4"]["mrr"] >= metrics["v1"]["mrr"],
        "no_domain_required_at_5_regression": not domain_regressions,
        "stage1_at_20_preserved": abs(metrics["llm_rev4"]["required_recall_at"][20] - metrics["stage1_union"]["required_recall_at"][20]) < 1e-12,
        "no_gold_leakage": True,
        "contract_frozen_before_gold": True,
        "blind_2025_untouched": True,
    }
    deltas = {
        f"required_at_{k}": metrics["llm_rev4"]["required_recall_at"][k] - metrics["stage1_union"]["required_recall_at"][k]
        for k in (1, 3, 5, 10, 20)
    }
    deltas.update(
        {
            f"completion_at_{k}": metrics["llm_rev4"]["required_completion_at"][k] - metrics["stage1_union"]["required_completion_at"][k]
            for k in (3, 5, 10)
        }
    )
    deltas["mrr"] = metrics["llm_rev4"]["mrr"] - metrics["stage1_union"]["mrr"]
    main_delta_values = [deltas["required_at_3"], deltas["required_at_5"], deltas["completion_at_5"], deltas["mrr"]]
    semantic_result = "POSITIVE" if all(value > 0 for value in main_delta_values) else "NEGATIVE" if all(value <= 0 for value in main_delta_values) else "MIXED"
    promising = all(criteria.values()) and not baseline_drift
    stage1_at20 = metrics["stage1_union"]["required_recall_at"][20]
    if semantic_result in {"POSITIVE", "MIXED"} and reliability["overall"]["fallback_rate"] > 0.1:
        next_phase = "PHASE_0_6D_RERANKER_V1_1"
    elif stage1_at20 < 0.65:
        next_phase = "CONTINUE_STAGE1_CANDIDATE_RETRIEVAL"
    elif semantic_result == "POSITIVE":
        next_phase = "PHASE_0_7_AGENTIC_SECOND_PASS_RETRIEVAL"
    else:
        next_phase = "STOP_LLM_RERANKER_DIRECTION"
    promotion = {
        "baseline_reproduced": not baseline_drift,
        "gold_set_drift": False,
        "gold_leakage": False,
        "blind_2025_accessed": False,
        "real_llm_calls_during_evaluation": 0,
        "stage1_required_recall_at20": stage1_at20,
        "llm_required_recall_at3": metrics["llm_rev4"]["required_recall_at"][3],
        "llm_required_recall_at5": metrics["llm_rev4"]["required_recall_at"][5],
        "llm_completion_at5": metrics["llm_rev4"]["required_completion_at"][5],
        "llm_mrr": metrics["llm_rev4"]["mrr"],
        "llm_delta_vs_stage1": deltas,
        "official_fallback_rate": reliability["overall"]["fallback_rate"],
        "semantic_ranking_result": semantic_result,
        "structured_output_reliability": "POOR",
        "llm_reranker_pilot_promising": promising,
        "promotion_criteria": criteria,
        "domain_regressions": domain_regressions,
        "next_recommended_phase": next_phase,
        "production_ready": False,
    }

    coverage_misses = [row for row in matrix if row["classification"] == "NOT_IN_STAGE1"]
    _write_json(args.output_root / OUT_NAMES[0], inventory)
    _write_json(args.output_root / OUT_NAMES[1], baseline_reproduction)
    _write_json(args.output_root / OUT_NAMES[2], {"variants": metrics, "llm_vs_stage1_delta": deltas})
    metric_rows = _flatten_metrics(metrics)
    _write_csv(args.output_root / OUT_NAMES[3], metric_rows, list(metric_rows[0]))
    _write_csv(args.output_root / OUT_NAMES[4], by_case, list(by_case[0]))
    _write_csv(args.output_root / OUT_NAMES[5], by_domain, list(by_domain[0]))
    _write_csv(args.output_root / OUT_NAMES[6], by_risk, list(by_risk[0]))
    _write_csv(args.output_root / OUT_NAMES[7], matrix, list(matrix[0]))
    _write_csv(args.output_root / OUT_NAMES[8], coverage_misses, list(matrix[0]))
    _write_json(args.output_root / OUT_NAMES[9], reliability)
    _write_json(args.output_root / OUT_NAMES[10], completed_diag)
    _write_json(args.output_root / OUT_NAMES[11], facets)
    _write_json(args.output_root / OUT_NAMES[12], taxonomy)
    _write_json(args.output_root / OUT_NAMES[13], promotion)

    main_columns = [
        ("variant", "Variant"), ("required_at_1", "Required@1"),
        ("required_at_3", "Required@3"), ("required_at_5", "Required@5"),
        ("required_at_10", "Required@10"), ("required_at_20", "Required@20"),
        ("completion_at_3", "Completion@3"), ("completion_at_5", "Completion@5"),
        ("completion_at_10", "Completion@10"), ("mrr", "MRR"),
    ]
    percent_columns = {key for key, _ in main_columns if key != "variant" and key != "mrr"}
    delta_rows = []
    for key in ("required_at_1", "required_at_3", "required_at_5", "required_at_10", "required_at_20", "completion_at_3", "completion_at_5", "completion_at_10", "mrr"):
        stage = metrics["stage1_union"]["mrr"] if key == "mrr" else metrics["stage1_union"]["required_recall_at"][int(key.rsplit("_",1)[-1])] if key.startswith("required") else metrics["stage1_union"]["required_completion_at"][int(key.rsplit("_",1)[-1])]
        llm = metrics["llm_rev4"]["mrr"] if key == "mrr" else metrics["llm_rev4"]["required_recall_at"][int(key.rsplit("_",1)[-1])] if key.startswith("required") else metrics["llm_rev4"]["required_completion_at"][int(key.rsplit("_",1)[-1])]
        delta_rows.append({"metric": key, "stage1": stage, "llm": llm, "delta": llm-stage})
    domain_table = _markdown_table(
        by_domain,
        [("domain", "Domain"), ("variant", "Variant"), ("required_at_3", "Required@3"), ("required_at_5", "Required@5"), ("required_at_20", "Required@20"), ("completion_at_5", "Completion@5"), ("mrr", "MRR")],
        {"required_at_3", "required_at_5", "required_at_20", "completion_at_5"},
    )
    risk_e = [row for row in by_risk if row["variant"] == "llm_rev4"]
    risk_table = _markdown_table(
        risk_e,
        [("risk", "Risk"), ("required_count", "Required"), ("required_at_3", "Required@3"), ("required_at_5", "Required@5"), ("required_at_20", "Required@20"), ("completion_at_5", "Completion@5"), ("mrr", "MRR")],
        {"required_at_3", "required_at_5", "required_at_20", "completion_at_5"},
    )
    recoveries = [row for row in matrix if row["classification"] in {"RECOVERED_TO_TOP3", "RECOVERED_TO_TOP5", "DEEP_GAIN"}]
    regressions = [row for row in matrix if row["classification"] in {"DEMOTED_FROM_TOP3", "DEMOTED_FROM_TOP5"}]
    report = f"""# Phase 0.6C Final Report — Revision 4

## One-line answer

**LLM reranker effective: {str(semantic_result == 'POSITIVE').lower()} for semantic ordering; runtime reliability remains poor at 18.75% fallback, and this pilot is not production-ready.**

## 1. Research Question

Given a high-recall deterministic candidate set, does an LLM provide incremental semantic ranking value beyond keyword/rule-based retrieval?

## 2. Experimental Integrity

- Pre-Gold Revision 4 verified before unlock: `true`.
- Official tasks: `80/80`; completed `65`; fallback `15`.
- Candidate SHA-256: `{_sha(candidate_path)}`.
- Official judgment aggregate SHA-256: `{pre['official_judgment_aggregate_sha256']}`.
- Gold was used only by this evaluator after output freeze.
- Real LLM calls during evaluation: `0`.
- 2025 blind accessed: `false`.
- No post-Gold tuning or output replacement was performed.
- Diagnostic replay interpretation: **diagnostic non-reproduction**. The original structured-output failures were not reproducible under identical diagnostic replay, but their original official fallbacks were retained as Revision-4 reliability costs.

## 3. Dataset

This is a **post-freeze retrospective development benchmark**, not blind or unseen validation. The 10 cases were previously exposed at project level, while the LLM semantic contract was frozen before Gold evaluation.

- Cases: `{inventory['case_count']}`
- Risk tasks: `{inventory['risk_task_count']}`
- Evidence / required / primary: `{inventory['evidence_count']} / {inventory['required_evidence_count']} / {inventory['primary_evidence_count']}`
- Unique Gold pages: `{inventory['unique_gold_page_count']}`
- Canonical manifest uses `ipo_2021_00013`; the frozen runtime cache uses `ipo_2020_00013`. The evaluator records a unique suffix-based identity alias and does not change the sample.

## 4. Variants

- A: V1 KeywordDocumentRetriever
- B: V2 DomainAwareRetrieverV2
- C: V2.1 frozen PR-46 research ranking
- D: Stage1 Union baseline, no semantic reranking
- E: Revision-4 LLM reranker; official failures use Stage1 order

## 5. Main Results

{_markdown_table(metric_rows, main_columns, percent_columns)}

The four primary decision metrics are Required@3, Required@5, Completion@5 and MRR. Baseline reproduced: `{str(not baseline_drift).lower()}`.

## 6. Incremental LLM Value — E vs D

{_markdown_table(delta_rows, [("metric","Metric"),("stage1","Stage1 Union"),("llm","LLM Rev4"),("delta","Delta")], set())}

## 7. Reliability

| Metric | Value |
| --- | ---: |
| Official Tasks | 80 |
| LLM Completed | 65 |
| Fallback | 15 |
| Fallback Rate | 18.75% |
| Diagnostic Replays | 3 |
| Replays Included in Metrics | 0 |
| Gold Leakage | false |
| 2025 Accessed | false |

Structured-output reliability: **POOR**. Semantic and engineering conclusions are intentionally separate.

## 8. Completed-only Diagnostic

Completed-only results are a **diagnostic upper bound only** and never replace the all-task official result. See `11_completed_only_diagnostic.json`.

## 9. Domain Results

{domain_table}

## 10. Risk Results — Official LLM Rev4

{risk_table}

## 11. Candidate Coverage vs Ranking Errors

- Stage1 Required Recall@20: `{stage1_at20:.2%}`.
- Candidate-coverage misses among required rows: `{len(coverage_misses)}`.
- Stage1 interpretation: `{'severe bottleneck' if stage1_at20 < .65 else 'improved but insufficient' if stage1_at20 < .75 else 'reasonable for second-pass work' if stage1_at20 <= .8 else 'strong foundation'}`.

## 12. Head Recoveries

- Recoveries to Top 3/5 or deep gains: `{len(recoveries)}`.
- Full rows: `08_promotion_regression_matrix.csv`.

## 13. Head Regressions

- Demotions from Top 3/5: `{len(regressions)}`.
- No ranking policy was changed after inspection.

## 14. Facet Coverage

Facet coverage is diagnostic and is not a substitute for Gold Evidence Recall. Full @3/@5/@10 results are in `12_facet_coverage.json`.

## 15. Semantic Error Taxonomy

Top-5 required misses: `{taxonomy['top5_required_miss_count']}`. Counts: `{json.dumps(taxonomy['counts'], ensure_ascii=False)}`.

## 16. Promotion Decision

- `SEMANTIC_RANKING_RESULT = {semantic_result}`
- `STRUCTURED_OUTPUT_RELIABILITY = POOR`
- `LLM_RERANKER_PILOT_PROMISING = {str(promising).lower()}`
- `PRODUCTION_READY = false`

## 17. Limitations

- Retrospective benchmark; all 10 cases were previously exposed at project level.
- 18.75% structured-output fallback is a material reliability cost.
- Single-pass Stage1 candidate ceiling constrains reranking.
- No 2025 validation was accessed.
- No end-to-end Agent/Verifier evaluation is part of this phase.
- The completed-only slice is diagnostic, not an official result.

## 18. Next Phase Recommendation

`NEXT_RECOMMENDED_PHASE = {next_phase}`

No Phase 0.7/0.6D implementation is performed here. Any Reranker V1.1 work must use a fresh benchmark and cannot claim validation on these 10 cases.

## Frozen Decision Fields

```text
BASELINE_REPRODUCED = {str(not baseline_drift).lower()}
GOLD_SET_DRIFT = false
GOLD_LEAKAGE = false
2025_BLIND_ACCESSED = false
REAL_LLM_CALLS_DURING_EVALUATION = 0
STAGE1_REQUIRED_RECALL_AT20 = {stage1_at20:.12f}
LLM_REQUIRED_RECALL_AT3 = {metrics['llm_rev4']['required_recall_at'][3]:.12f}
LLM_REQUIRED_RECALL_AT5 = {metrics['llm_rev4']['required_recall_at'][5]:.12f}
LLM_COMPLETION_AT5 = {metrics['llm_rev4']['required_completion_at'][5]:.12f}
LLM_MRR = {metrics['llm_rev4']['mrr']:.12f}
LLM_DELTA_VS_STAGE1_AT3 = {deltas['required_at_3']:.12f}
LLM_DELTA_VS_STAGE1_AT5 = {deltas['required_at_5']:.12f}
OFFICIAL_FALLBACK_RATE = 0.187500000000
SEMANTIC_RANKING_RESULT = {semantic_result}
STRUCTURED_OUTPUT_RELIABILITY = POOR
LLM_RERANKER_PILOT_PROMISING = {str(promising).lower()}
NEXT_RECOMMENDED_PHASE = {next_phase}
```
"""
    (args.output_root / OUT_NAMES[14]).write_text(report, encoding="utf-8")

    output_hashes = {name: _sha(args.output_root / name) for name in OUT_NAMES[:15]}
    evaluation_sources = [
        Path("src/ipo_risk/evaluation/llm_reranker_rev4.py"),
        Path("scripts/evaluate_llm_reranker_rev4.py"),
    ]
    post = {
        "artifact": "post_gold_evaluation_freeze_manifest",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "branch": _git("branch", "--show-current").strip(),
        "head_sha": _git("rev-parse", "HEAD").strip(),
        "freeze_revision": 4,
        "pre_gold_manifest_sha256": _sha(pre_path),
        "official_judgment_aggregate_sha256": pre["official_judgment_aggregate_sha256"],
        "candidate_pool_sha256": _sha(candidate_path),
        "gold_ref": args.gold_ref,
        "gold_source_hashes": gold_hashes,
        "baseline_source_ref": "origin/eval/retriever-v21-ten-case-ranking@a99cdf8",
        "baseline_source_manifest_sha256": _sha(baseline_manifest_path),
        "evaluation_code_hashes": {str(path).replace("\\", "/"): _sha(path) for path in evaluation_sources},
        "output_hashes": output_hashes,
        "baseline_drift": baseline_drift,
        "gold_set_drift": False,
        "gold_loaded_after_freeze": True,
        "gold_used_by_evaluator_only": True,
        "blind_2025_accessed": False,
        "real_llm_calls_during_evaluation": 0,
        "official_completed": 65,
        "official_failed": 15,
        "official_fallback_rate": 0.1875,
        "diagnostic_replays_included_in_metrics": 0,
        "post_gold_tuning": False,
        "production_code_changed_by_evaluation": False,
    }
    _write_json(args.output_root / OUT_NAMES[15], post)
    print(json.dumps({"completed": True, "output_root": str(args.output_root), **promotion}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
