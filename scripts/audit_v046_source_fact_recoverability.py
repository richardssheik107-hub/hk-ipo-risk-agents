"""Separate M1 fact recoverability from M2 exact-anchor edition mismatch.

This script is evaluator-only. It consumes Existing Gold after source
discovery, downloads official Chinese editions from an already-built shadow
catalog, and emits booleans/classifications only. Gold quote text and numeric
signatures are never written to the output.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import fitz

from ipo_risk.evaluation.source_edition_audit import document_supports_risk_fact
from ipo_risk.sources.hkex_editions import download_official_pdf


AUDIT_VERSION = "v046_source_edition_fact_recoverability_v1"


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _pdf_pages(payload: bytes) -> tuple[str, ...]:
    with fitz.open(stream=payload, filetype="pdf") as document:
        return tuple(page.get_text("text") for page in document)


def build(
    *,
    shadow_catalog: Path,
    gold_manifest: Path,
    risk_benchmark: Path,
) -> dict[str, object]:
    shadow = _read_json(shadow_catalog)
    gold = _read_json(gold_manifest)
    benchmark_rows = _read_csv(risk_benchmark)
    benchmark = {row["risk_unit_id"]: row for row in benchmark_rows}
    target_cases = {str(row["case_id"]) for row in shadow["records"]}

    evidence_by_risk: dict[tuple[str, str], list[str]] = defaultdict(list)
    evidence_count_by_case: Counter[str] = Counter()
    for evidence in gold["evidence_units"]:
        if (
            evidence["case_id"] in target_cases
            and evidence["primary_scope"] is True
        ):
            key = (evidence["case_id"], evidence["source_risk_code"])
            evidence_by_risk[key].append(evidence["exact_text"])
            evidence_count_by_case[evidence["case_id"]] += 1

    pages_by_case: dict[str, tuple[str, ...]] = {}
    source_record_by_case = {str(row["case_id"]): row for row in shadow["records"]}
    records: list[dict[str, object]] = []
    for risk in gold["risk_units"]:
        case_id = str(risk["case_id"])
        if (
            case_id not in target_cases
            or risk["primary_scope"] is not True
            or risk["evaluable_positive"] is not True
        ):
            continue
        benchmark_row = benchmark.get(str(risk["risk_unit_id"]), {})
        pipeline_available = (
            benchmark_row.get("predicted_present") == "True"
            and benchmark_row.get("predicted_positive") == "True"
        )
        if case_id not in pages_by_case:
            chinese_documents = [
                item
                for item in source_record_by_case[case_id]["documents"]
                if item["language"] == "zh-Hant"
            ]
            if not chinese_documents:
                pages_by_case[case_id] = ()
            else:
                payload = download_official_pdf(chinese_documents[0]["source_url"])
                pages_by_case[case_id] = _pdf_pages(payload)
        risk_family = str(risk["competition_risk_family"])
        anchors = evidence_by_risk[(case_id, str(risk["source_risk_code"]))]
        deterministic_document_proof = document_supports_risk_fact(
            pages_by_case[case_id],
            risk_family=risk_family,
            gold_anchor_texts=anchors,
        )
        fact_available = pipeline_available or deterministic_document_proof
        if pipeline_available:
            classification = "M1_FACT_RECOVERABLE_FROM_CURRENT_CHINESE_PIPELINE"
        elif deterministic_document_proof:
            classification = "M1_FACT_AVAILABLE_IN_OFFICIAL_CHINESE_DOCUMENT"
        else:
            classification = "M1_FACT_RECOVERABILITY_NOT_PROVEN"
        records.append(
            {
                "case_id": case_id,
                "risk_unit_id": risk["risk_unit_id"],
                "risk_family": risk_family,
                "pipeline_fact_available_from_current_catalog": pipeline_available,
                "deterministic_official_chinese_document_proof": deterministic_document_proof,
                "m1_fact_available_in_chinese": fact_available,
                "m2_exact_anchor_assessment": (
                    "OUT_OF_SCOPE_REQUIRES_SEPARATE_EVALUATOR_AUDIT"
                ),
                "classification": classification,
            }
        )

    records.sort(key=lambda item: (str(item["case_id"]), str(item["risk_unit_id"])))
    by_case: list[dict[str, object]] = []
    for case_id in sorted(target_cases):
        units = [row for row in records if row["case_id"] == case_id]
        source = source_record_by_case[case_id]
        documents = {item["language"]: item for item in source["documents"]}
        by_case.append(
            {
                "case_id": case_id,
                "stock_code": source["stock_code"],
                "current_catalog_document_hash": source["current_catalog_sha256"],
                "current_document_language": source["current_catalog_language"],
                "official_english_counterpart_found": source["official_english_found"],
                "official_chinese_counterpart_found": source["official_chinese_found"],
                "hkex_filing_identity": source["filing_identity"],
                "edition_relationship_confidence": source[
                    "edition_relationship_confidence"
                ],
                "english_file_sha256": documents.get("en", {}).get("sha256"),
                "chinese_file_sha256": documents.get("zh-Hant", {}).get("sha256"),
                "m2_exact_anchor_assessment": (
                    "OUT_OF_SCOPE_REQUIRES_SEPARATE_EVALUATOR_AUDIT"
                ),
                "affected_M1_count": len(units),
                "affected_M2_count": evidence_count_by_case[case_id],
                "m1_fact_available_in_chinese_count": sum(
                    bool(unit["m1_fact_available_in_chinese"]) for unit in units
                ),
                "classification": (
                    "M1_FACT_RECOVERABLE_FROM_CHINESE"
                    if all(unit["m1_fact_available_in_chinese"] for unit in units)
                    else "PARTIAL_M1_FACT_RECOVERABILITY_FROM_CHINESE"
                ),
            }
        )
    available_count = sum(bool(row["m1_fact_available_in_chinese"]) for row in records)
    return {
        "audit_version": AUDIT_VERSION,
        "runtime_received_gold": False,
        "gold_used_after_source_discovery_evaluator_side_only": True,
        "gold_text_persisted": False,
        "official_pdf_text_persisted": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "case_count": len(by_case),
        "affected_M1_count": len(records),
        "affected_M2_count": sum(evidence_count_by_case.values()),
        "m1_fact_available_in_chinese_count": available_count,
        "m1_fact_recoverability_not_proven_count": len(records) - available_count,
        "case_records": by_case,
        "risk_unit_records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shadow-catalog", type=Path, required=True)
    parser.add_argument("--gold-manifest", type=Path, required=True)
    parser.add_argument("--risk-benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        shadow_catalog=args.shadow_catalog,
        gold_manifest=args.gold_manifest,
        risk_benchmark=args.risk_benchmark,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"case_count={payload['case_count']} "
        f"affected_M1={payload['affected_M1_count']} "
        f"m1_fact_available_in_chinese={payload['m1_fact_available_in_chinese_count']} "
        f"affected_M2={payload['affected_M2_count']} gold_text_persisted=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
