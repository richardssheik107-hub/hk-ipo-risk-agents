"""Audit fixed-10 Financial period selection without network or runtime Gold input."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Mapping

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
for item in (_ROOT, _SRC):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from ipo_risk.evaluation.role_b_period_selection import (  # noqa: E402
    PeriodSelectionEvidence,
    classify_period_selection,
    extract_component_metadata,
    period_candidates,
    summarize_candidates,
)
from ipo_risk.extraction.financial import FinancialEvidenceExtractor  # noqa: E402


TARGET_RISKS = ("cash_runway", "customer_concentration", "supplier_concentration")
_NUMBER_TOLERANCE = Decimal("0.15")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    # Match Oracle provenance: universal-newline translation makes the hash
    # invariant to Git's LF/CRLF checkout policy.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _walk(value: object) -> Iterable[tuple[str, object]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _expected_profile(inputs: Mapping[str, Any], results: Mapping[str, Any]) -> dict[str, Any]:
    periods: set[str] = set()
    period_months: set[int] = set()
    values: dict[str, list[Decimal]] = {"cash": [], "operating_cash_flow": [], "largest": [], "top_five": []}
    for key, value in _walk({"inputs": inputs, "results": results}):
        key_lower = key.lower()
        if isinstance(value, str):
            for observed in FinancialEvidenceExtractor._explicit_dates(value):
                periods.add(observed.isoformat())
            months = FinancialEvidenceExtractor._period_months(value)
            if months is not None:
                period_months.add(months)
        number = _decimal(value)
        if number is None:
            continue
        if "period_month" in key_lower or "months_in_period" in key_lower:
            if number == number.to_integral_value():
                period_months.add(int(number))
            continue
        if "cash_runway" in key_lower or "monthly" in key_lower or "threshold" in key_lower:
            continue
        if "operating" in key_lower and ("cash" in key_lower or "burn" in key_lower):
            values["operating_cash_flow"].append(number)
        elif "cash" in key_lower and not any(token in key_lower for token in ("flow", "burn")):
            values["cash"].append(number)
        elif "largest" in key_lower and ("pct" in key_lower or "share" in key_lower):
            values["largest"].append(number * 100 if abs(number) <= 1 else number)
        elif "top_five" in key_lower and ("pct" in key_lower or "share" in key_lower):
            values["top_five"].append(number * 100 if abs(number) <= 1 else number)
    # Some audited cash rows persist monthly burn rather than interval OCF.
    monthly = next(
        (
            number
            for key, value in _walk(inputs)
            if "monthly" in key.lower() and "burn" in key.lower() and (number := _decimal(value)) is not None
        ),
        None,
    )
    if not values["operating_cash_flow"] and monthly is not None and len(period_months) == 1:
        values["operating_cash_flow"].append(-abs(monthly * next(iter(period_months))))
    return {
        "periods": sorted(periods),
        "period_months": sorted(period_months),
        "values": values,
        "fact_available": any(values.values()),
    }


def _gold_profile(root: Path, row: Mapping[str, str]) -> dict[str, Any]:
    case_id = row["case_id"]
    risk_code = row["source_risk_code"]
    source = root / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json"
    if not source.is_file() or _sha256(source) != row["source_annotation_hash"]:
        return {"fact_available": False, "reason": "source_annotation_unavailable_or_hash_mismatch"}
    annotation = json.loads(source.read_text(encoding="utf-8-sig"))
    risk = next((item for item in annotation.get("risks", []) if item.get("risk_code") == risk_code), None)
    if not isinstance(risk, Mapping):
        return {"fact_available": False, "reason": "source_risk_missing"}
    inputs = dict(risk.get("calculation_inputs") or {})
    results = dict(risk.get("calculation_result") or {})

    overlay = root / "expert_results" / case_id / "audit" / "financial_resolution_v1.json"
    if overlay.is_file():
        payload = json.loads(overlay.read_text(encoding="utf-8-sig"))
        entry = next((item for item in payload.get("entries", []) if item.get("risk_code") == risk_code), None)
        if isinstance(entry, Mapping):
            outcome = entry.get("source_outcome") or {}
            canonical = outcome.get("canonical_calculation_inputs") if isinstance(outcome, Mapping) else None
            if isinstance(canonical, Mapping):
                # An empty audited canonical input is an explicit statement that
                # exact facts are unavailable.  Do not revive stale pass-1 values.
                inputs = dict(canonical)
                results = {}
    profile = _expected_profile(inputs, results)
    profile["reason"] = "available" if profile["fact_available"] else "audited_fact_unavailable"
    return profile


def _matches(observed: object, expected: Iterable[Decimal]) -> bool:
    value = _decimal(observed)
    if value is None:
        return False
    return any(abs(value - target) <= _NUMBER_TOLERANCE for target in expected)


def _audit_row(
    *,
    root: Path,
    gold: Mapping[str, str],
    metadata: Mapping[str, Any] | None,
    final_correct: bool,
) -> dict[str, Any]:
    case_id = gold["case_id"]
    risk_code = gold["source_risk_code"]
    profile = _gold_profile(root, gold)
    metadata = dict(metadata or {})
    candidates = period_candidates(metadata, risk_code)
    summary = summarize_candidates(candidates)
    issues = list(metadata.get("issues") or [])
    conflict = "conflicting_values_for_same_period" in issues
    retrieved = bool(candidates) or int(metadata.get("retrieved_evidence_count") or 0) > 0
    parser_text = summary["parsed_value_candidate_count"] > 0

    expected_periods = set(profile.get("periods") or [])
    expected_months = set(profile.get("period_months") or [])
    observed_periods = {
        str(item.get("period_end")) for item in candidates if item.get("period_end")
    }
    observed_months = {
        int(item["period_months"])
        for item in candidates
        if item.get("period_months") is not None
    }
    period_present = bool(
        (expected_periods and expected_periods & observed_periods)
        or (not expected_periods and expected_months and expected_months & observed_months)
    )

    expected_values = profile.get("values") or {}
    if risk_code == "cash_runway":
        conversion = metadata.get("financial_conversion") or {}
        cash = conversion.get("cash") or {}
        flow = conversion.get("operating_cash_flow") or {}
        cash_match = _matches(cash.get("value"), expected_values.get("cash", []))
        flow_match = _matches(flow.get("value"), expected_values.get("operating_cash_flow", []))
        value_present = cash_match and flow_match
        compatible = bool(
            cash.get("period_end")
            and cash.get("period_end") == flow.get("period_end")
            and cash.get("currency") == flow.get("currency")
            and cash.get("unit") == flow.get("unit")
            and flow.get("period_months") in {3, 6, 9, 12}
        )
        currency_unit = bool(
            cash.get("currency")
            and cash.get("unit")
            and cash.get("currency") == flow.get("currency")
            and cash.get("unit") == flow.get("unit")
        )
        selected_period = cash.get("period_end") if cash.get("period_end") == flow.get("period_end") else None
    else:
        diagnostics = [item for item in metadata.get("candidate_diagnostics", []) if isinstance(item, Mapping)]
        largest_expected = expected_values.get("largest", [])
        top_expected = expected_values.get("top_five", [])
        value_present = any(
            _matches(item.get("largest_counterparty_pct"), largest_expected)
            and _matches(item.get("top_five_pct"), top_expected)
            for item in diagnostics
        )
        compatible = value_present and period_present
        currency_unit = True
        selected_period = metadata.get("period_end")

    selected_match: bool | None
    if expected_periods:
        selected_match = str(selected_period) in expected_periods
    elif expected_months:
        selected_match = metadata.get("period_months") in expected_months or any(
            item.get("period_months") in expected_months and item.get("selected") is True
            for item in candidates
        )
    else:
        selected_match = None

    if final_correct:
        retrieved = True
        parser_text = True
        period_present = True
        value_present = True
        currency_unit = True
        compatible = True
        conflict = False
        selected_match = True

    evidence = PeriodSelectionEvidence(
        retrieved_candidate_present=retrieved,
        parser_text_present=parser_text,
        correct_period_candidate_present=period_present,
        correct_value_candidate_present=value_present,
        currency_unit_compatible=currency_unit,
        compatible_pair_exists=compatible,
        same_period_conflict_detected=conflict,
        selected_period_matches=selected_match,
    )
    classification = classify_period_selection(evidence)
    if profile.get("fact_available") is not True:
        classification = "deterministic_fact_missing"
    if final_correct:
        # A formally correct final risk is a stronger observation than the
        # compact success diagnostic, which intentionally omits extraction
        # internals.  Do not mislabel omitted success metadata as parser loss.
        classification = "correct"
    return {
        "case_id": case_id,
        "risk_family": risk_code,
        "retrieved_candidate_present": retrieved,
        "parser_text_present": parser_text,
        **summary,
        "diagnostic_candidate_details_available": bool(candidates),
        "expected_metric_or_fact_type": risk_code,
        "expected_profile_status": profile.get("reason"),
        "selected_period": selected_period,
        "correct_period_candidate_present": period_present,
        "correct_value_candidate_present": value_present,
        "currency_unit_compatible": currency_unit,
        "compatible_pair_exists": compatible,
        "compatible_pair_count": int(compatible),
        "same_period_conflict_detected": conflict,
        "conflict_fields": ["financial_value"] if conflict else [],
        "selection_stage": "deterministic_financial_extractor",
        "selection_reason": metadata.get("merge_value_basis") or (
            (metadata.get("financial_conversion") or {}).get("cash", {}).get("pair_selection")
            if isinstance(metadata.get("financial_conversion"), Mapping)
            else None
        ),
        "earliest_failure_stage": classification,
        "classification": classification,
        "period_selection_bug": classification == "period_selection_bug",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--gold-manifest", type=Path, default=Path("reports/v045_role_b/existing_gold_evaluable_manifest.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    risk_rows = _read_csv(root / "reports/v045_role_b/existing_gold_risk_units.csv")
    benchmark_rows = _read_csv(args.run_dir / "evaluation" / "risk_benchmark.csv")
    final_correct = {
        (row.get("case_id", ""), row.get("source_risk_code", "")): row.get("correct", "").lower()
        == "true"
        for row in benchmark_rows
    }
    selected = [
        row
        for row in risk_rows
        if row.get("split") == "development"
        and row.get("primary_scope", "").lower() == "true"
        and row.get("evaluable_positive", "").lower() == "true"
        and row.get("source_risk_code") in TARGET_RISKS
        and (args.run_dir / "run" / row["case_id"] / "analysis_result.json").is_file()
    ]
    rows: list[dict[str, Any]] = []
    for gold in selected:
        result = json.loads(
            (args.run_dir / "run" / gold["case_id"] / "analysis_result.json").read_text(encoding="utf-8")
        )
        serialized = (
            result.get("metadata", {})
            .get("component_diagnostics", {})
            .get("financial", {})
            .get("value", "")
        )
        rows.append(
            _audit_row(
                root=root,
                gold=gold,
                metadata=extract_component_metadata(serialized, gold["source_risk_code"]),
                final_correct=final_correct.get(
                    (gold["case_id"], gold["source_risk_code"]), False
                ),
            )
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "period_selection_audit.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["case_id", "risk_family"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )
    counts = Counter(row["classification"] for row in rows)
    manifest = json.loads((root / args.gold_manifest).read_text(encoding="utf-8"))
    summary = {
        "audit_version": "v046_role_b_period_selection_audit_v1",
        "unit_count": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "proven_selector_bug_count": counts.get("period_selection_bug", 0),
        "gold_manifest_hash": manifest.get("manifest_hash"),
        "gold_used_at_runtime": False,
        "network_calls": 0,
        "validation_opened": False,
        "blind_2025_accessed": False,
        "raw_prospectus_text_persisted": False,
        "raw_gold_text_persisted": False,
    }
    (args.output_dir / "period_selection_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
