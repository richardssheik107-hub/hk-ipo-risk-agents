"""Canonicalize legacy structured financial facts for Expert Annotation Phase 2b.

These helpers normalize only facts already present in pass1 calculation fields.
They do not edit pass1 and do not infer missing prospectus facts from prose.
Cross-period and zero-denominator uncertainty remains explicit policy review.
"""
from __future__ import annotations

from collections import defaultdict
import json
from typing import Any, Mapping, Sequence

from .annotation_audit import (
    STATUS_HARD,
    STATUS_INSUFFICIENT,
    STATUS_PASS,
    STATUS_POLICY,
    audit_cash_runway,
    audit_concentration,
    audit_revenue_growth,
    period_signature,
)

PHASE2B_VERSION = "expert_annotation_phase2b_backfill_v1"
BACKFILL_VERSION = "expert_annotation_structured_input_backfill_v1"
BACKFILL_FILENAME = "structured_input_backfill_v1.json"
P0 = "P0_POSITIVE_OR_NEEDS_REVIEW"


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _first_num(data: Mapping[str, Any], names: Sequence[str]) -> tuple[float | None, str | None]:
    for name in names:
        value = _num(data.get(name))
        if value is not None:
            return value, name
    return None, None


def _expected(level: str) -> tuple[bool, str, str]:
    if level == "not_applicable":
        return False, "rejected", "not_applicable"
    return True, "verified", level


def _matches(record: Mapping[str, Any], level: str) -> bool:
    a, s, l = _expected(level)
    return (
        record.get("applicable") is a
        and record.get("expected_status") == s
        and record.get("expected_level") == l
    )


def _result(
    *,
    status: str,
    code: str,
    level: str | None = None,
    canonical_inputs: Mapping[str, Any] | None = None,
    normalized_facts: Any = None,
    source_fields: Sequence[str] = (),
    message: str = "",
) -> dict[str, Any]:
    return {
        "re_audit_status": status,
        "finding_code": code,
        "recomputed_level": level,
        "canonical_calculation_inputs": dict(canonical_inputs or {}),
        "normalized_facts": normalized_facts,
        "source_fields": list(source_fields),
        "message": message,
    }


def _custom_label_result(
    record: Mapping[str, Any],
    level: str,
    *,
    code: str,
    canonical_inputs: Mapping[str, Any],
    normalized_facts: Any,
    source_fields: Sequence[str],
    message: str,
) -> dict[str, Any]:
    status = STATUS_PASS if _matches(record, level) else STATUS_HARD
    result = _result(
        status=status,
        code="PASS" if status == STATUS_PASS else code,
        level=level,
        canonical_inputs=canonical_inputs,
        normalized_facts=normalized_facts,
        source_fields=source_fields,
        message=message,
    )
    if status == STATUS_HARD:
        a, s, l = _expected(level)
        result["proposed_replacement"] = {
            "applicable": a,
            "expected_status": s,
            "expected_level": l,
        }
    return result


def _cash_level(cash: float, flow: float, months: float | None, monthly_burn: float | None) -> tuple[str, float | None]:
    if flow >= 0:
        return "not_applicable", None
    burn = abs(monthly_burn) if monthly_burn not in (None, 0.0) else None
    if burn is None and months not in (None, 0.0):
        burn = abs(flow) / float(months)
    if burn is None or burn <= 0:
        raise ValueError("monthly burn is not derivable")
    runway = cash / burn
    if runway < 3:
        return "critical", runway
    if runway < 6:
        return "high", runway
    if runway < 12:
        return "medium", runway
    return "not_applicable", runway


def _cash_point(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    cash, cash_key = _first_num(
        row,
        (
            "cash",
            "cash_and_cash_equivalents",
            "cash_and_cash_equivalents_cfs",
            "cash_flow_statement_cash_and_cash_equivalents",
        ),
    )
    flow, flow_key = _first_num(
        row,
        (
            "net_cash_used_in_operating_activities",
            "net_cash_from_operating_activities",
            "operating_cash_flow",
        ),
    )
    months, month_key = _first_num(row, ("period_months", "months_in_period"))
    burn, burn_key = _first_num(
        row,
        ("monthly_cash_burn", "monthly_operating_cash_burn", "monthly_operating_cash_burn_hk_000"),
    )
    if cash is None or flow is None or (flow < 0 and months in (None, 0.0) and burn in (None, 0.0)):
        return None, [key for key in (cash_key, flow_key, month_key, burn_key) if key]
    point = {
        "period": row.get("period"),
        "cash": cash,
        "net_cash_used_in_operating_activities": flow,
    }
    if months not in (None, 0.0):
        point["period_months"] = months
    if burn not in (None, 0.0):
        point["monthly_cash_burn"] = abs(burn)
    return point, [key for key in (cash_key, flow_key, month_key, burn_key) if key]


def canonicalize_cash(record: Mapping[str, Any]) -> dict[str, Any]:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_CASH_INPUTS_MISSING")
    rows = inputs.get("periods")
    points: list[dict[str, Any]] = []
    source_fields: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping):
                point, fields = _cash_point(row)
                source_fields.extend(fields)
                if point is not None:
                    points.append(point)
    else:
        point, fields = _cash_point(inputs)
        source_fields.extend(fields)
        if point is not None:
            points.append(point)
    if not points:
        return _result(
            status=STATUS_INSUFFICIENT,
            code="PHASE2B_CASH_CANONICAL_FACTS_INSUFFICIENT",
            source_fields=source_fields,
        )
    assessments = []
    try:
        for point in points:
            level, runway = _cash_level(
                point["cash"],
                point["net_cash_used_in_operating_activities"],
                _num(point.get("period_months")),
                _num(point.get("monthly_cash_burn")),
            )
            assessments.append({**point, "level": level, "cash_runway_months": runway})
    except ValueError:
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_CASH_BURN_NOT_DERIVABLE")
    levels = {row["level"] for row in assessments}
    if len(levels) > 1:
        return _result(
            status=STATUS_POLICY,
            code="POLICY_AMBIGUITY_CASH_PERIOD_SELECTION",
            normalized_facts=assessments,
            source_fields=source_fields,
            message="Multiple disclosed cash-runway periods imply different frozen levels; period selection is not frozen.",
        )
    chosen = points[-1]
    overlay = dict(record)
    overlay["calculation_inputs"] = chosen
    finding = audit_cash_runway("phase2b", overlay)
    out = _result(
        status=finding.audit_status,
        code=finding.finding_code,
        level=finding.recomputed_level,
        canonical_inputs=chosen,
        normalized_facts=assessments,
        source_fields=source_fields,
        message=finding.message,
    )
    if finding.audit_status == STATUS_HARD:
        out["proposed_replacement"] = {
            "applicable": finding.recomputed_applicable,
            "expected_status": finding.recomputed_status,
            "expected_level": finding.recomputed_level,
        }
    return out


def _period_value(row: Mapping[str, Any]) -> tuple[float | None, str | None]:
    return _first_num(
        row,
        (
            "loss",
            "net_loss",
            "loss_for_period",
            "loss_for_year",
            "profit_or_loss",
            "profit_loss",
            "profit_for_period",
            "profit_and_total_comprehensive_income",
            "profit_and_total_comprehensive_income_attributable_to_owners",
        ),
    )


def _loss_rows(inputs: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    result: list[dict[str, Any]] = []
    sources: list[str] = []
    list_keys = (
        "loss_periods",
        "comparable_full_year_periods",
        "comparable_periods",
        "annual_periods",
        "three_month_periods",
        "six_month_periods",
        "nine_month_periods",
        "periods",
    )
    seen: set[tuple[str, float]] = set()
    for key in list_keys:
        rows = inputs.get(key)
        if not isinstance(rows, list) or not rows:
            continue
        if all(isinstance(row, Mapping) for row in rows):
            for row in rows:
                value, value_key = _period_value(row)
                if value is None:
                    continue
                item = {"period": row.get("period"), "loss": value}
                token = (str(item["period"]), float(value))
                if token in seen:
                    continue
                seen.add(token)
                result.append(item)
                sources.extend([key, value_key or ""])
    periods = inputs.get("periods")
    if isinstance(periods, list) and periods and all(not isinstance(x, Mapping) for x in periods):
        for values_key in (
            "losses",
            "net_losses",
            "profit_or_loss",
            "profit_and_total_comprehensive_income",
            "profit_and_total_comprehensive_income_attributable_to_owners",
        ):
            values = inputs.get(values_key)
            if isinstance(values, list) and len(values) == len(periods):
                for period, raw in zip(periods, values):
                    value = _num(raw)
                    if value is None:
                        continue
                    item = {"period": period, "loss": value}
                    token = (str(period), float(value))
                    if token not in seen:
                        seen.add(token)
                        result.append(item)
                sources.extend(["periods", values_key])
                break
    return result, [s for s in sources if s]


def _loss_level(count: int) -> str:
    if count >= 3:
        return "high"
    if count >= 2:
        return "medium"
    return "not_applicable"


def canonicalize_continuous_loss(record: Mapping[str, Any]) -> dict[str, Any]:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_LOSS_INPUTS_MISSING")
    rows, fields = _loss_rows(inputs)
    if not rows:
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_LOSS_FACTS_INSUFFICIENT")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown = []
    for row in rows:
        sig = period_signature(row["period"])
        enriched = {**row, "signature": sig}
        if sig == "UNKNOWN":
            unknown.append(enriched)
        groups[sig].append(enriched)
    if unknown:
        return _result(
            status=STATUS_POLICY,
            code="COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS",
            normalized_facts={"groups": dict(groups), "unknown": unknown},
            source_fields=fields,
        )
    group_assessments = {}
    for sig, group in groups.items():
        loss_count = sum(1 for row in group if row["loss"] < 0)
        group_assessments[sig] = {"loss_count": loss_count, "level": _loss_level(loss_count), "periods": group}
    levels = {row["level"] for row in group_assessments.values()}
    if len(levels) > 1:
        return _result(
            status=STATUS_POLICY,
            code="COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS",
            normalized_facts=group_assessments,
            source_fields=fields,
            message="Comparable duration groups imply different levels; Phase 2b does not pool them.",
        )
    level = next(iter(levels))
    canonical = {"loss_periods": [{"period": r["period"], "loss": r["loss"]} for r in rows]}
    return _custom_label_result(
        record,
        level,
        code="CONTINUOUS_LOSS_LABEL_CONFLICT_AFTER_BACKFILL",
        canonical_inputs=canonical,
        normalized_facts=group_assessments,
        source_fields=fields,
        message="All comparable duration groups imply the same continuous-loss level.",
    )


def _revenue_pairs(inputs: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    pairs: list[dict[str, Any]] = []
    fields: list[str] = []
    previous, prev_key = _first_num(inputs, ("previous_revenue", "prior_revenue", "base_revenue", "prior_period_revenue"))
    current, cur_key = _first_num(inputs, ("current_revenue", "latest_revenue", "current_period_revenue"))
    if previous is not None and current is not None:
        pairs.append({
            "prior_period": inputs.get("prior_period") or inputs.get("previous_period"),
            "current_period": inputs.get("current_period"),
            "previous_revenue": previous,
            "current_revenue": current,
        })
        fields.extend([prev_key or "", cur_key or ""])
    comparisons = inputs.get("comparisons")
    if isinstance(comparisons, list):
        for row in comparisons:
            if not isinstance(row, Mapping):
                continue
            p, pk = _first_num(row, ("previous_revenue", "prior_revenue", "prior_period_revenue"))
            c, ck = _first_num(row, ("current_revenue", "latest_revenue", "current_period_revenue"))
            if p is not None and c is not None:
                pairs.append({
                    "prior_period": row.get("prior_period") or row.get("previous_period"),
                    "current_period": row.get("current_period"),
                    "previous_revenue": p,
                    "current_revenue": c,
                })
                fields.extend(["comparisons", pk or "", ck or ""])
    periods = inputs.get("periods")
    if isinstance(periods, list) and periods:
        if all(isinstance(row, Mapping) for row in periods):
            sequence = []
            for row in periods:
                rev, rk = _first_num(row, ("revenue", "total_revenue", "product_sales_revenue"))
                if rev is not None:
                    sequence.append((row.get("period"), rev, rk))
            for left, right in zip(sequence, sequence[1:]):
                if period_signature(left[0]) == period_signature(right[0]) != "UNKNOWN":
                    pairs.append({
                        "prior_period": left[0],
                        "current_period": right[0],
                        "previous_revenue": left[1],
                        "current_revenue": right[1],
                    })
                    fields.extend(["periods", left[2] or "", right[2] or ""])
        elif all(not isinstance(row, Mapping) for row in periods):
            revenues = inputs.get("revenue")
            if isinstance(revenues, list) and len(revenues) == len(periods):
                sequence = [(period, _num(value)) for period, value in zip(periods, revenues)]
                for left, right in zip(sequence, sequence[1:]):
                    if left[1] is not None and right[1] is not None and period_signature(left[0]) == period_signature(right[0]) != "UNKNOWN":
                        pairs.append({
                            "prior_period": left[0],
                            "current_period": right[0],
                            "previous_revenue": left[1],
                            "current_revenue": right[1],
                        })
                        fields.extend(["periods", "revenue"])
    unique = []
    seen = set()
    for row in pairs:
        token = (str(row.get("prior_period")), str(row.get("current_period")), row["previous_revenue"], row["current_revenue"])
        if token not in seen:
            seen.add(token)
            unique.append(row)
    return unique, [f for f in fields if f]


def _growth_level(pct: float) -> str:
    if pct <= -20:
        return "high"
    if pct < 0:
        return "medium"
    return "not_applicable"


def canonicalize_revenue(record: Mapping[str, Any]) -> dict[str, Any]:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_REVENUE_INPUTS_MISSING")
    pairs, fields = _revenue_pairs(inputs)
    if not pairs:
        zero_fields = []
        for key, value in inputs.items():
            if "revenue" in str(key).lower() and _num(value) == 0:
                zero_fields.append(str(key))
        result_obj = record.get("calculation_result")
        ambiguity_text = json.dumps(result_obj, ensure_ascii=False).lower() if result_obj is not None else ""
        reasoning = str(record.get("reasoning") or "").lower()
        if zero_fields and ("open-01" in ambiguity_text or "zero" in ambiguity_text or "open-01" in reasoning or "no revenue" in reasoning):
            return _result(
                status=STATUS_POLICY,
                code="OPEN_01_ZERO_REVENUE_GROWTH",
                canonical_inputs={"zero_revenue_fields": {k: inputs[k] for k in zero_fields}},
                normalized_facts={"zero_revenue_fields": zero_fields},
                source_fields=zero_fields,
                message="Zero-revenue growth denominator remains an open policy item.",
            )
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_REVENUE_COMPARABLE_PAIR_INSUFFICIENT")
    assessments = []
    for pair in pairs:
        previous = pair["previous_revenue"]
        current = pair["current_revenue"]
        if previous <= 0:
            return _result(
                status=STATUS_POLICY,
                code="REVENUE_GROWTH_DENOMINATOR_NONPOSITIVE",
                normalized_facts=pairs,
                source_fields=fields,
            )
        pct = (current - previous) / previous * 100.0
        assessments.append({**pair, "growth_pct": pct, "level": _growth_level(pct)})
    levels = {row["level"] for row in assessments}
    if len(levels) > 1:
        return _result(
            status=STATUS_POLICY,
            code="POLICY_AMBIGUITY_REVENUE_PERIOD_AGGREGATION",
            normalized_facts=assessments,
            source_fields=fields,
            message="Multiple comparable growth pairs imply different levels; aggregation/selection is not frozen.",
        )
    pair = pairs[-1]
    canonical = {"previous_revenue": pair["previous_revenue"], "current_revenue": pair["current_revenue"]}
    overlay = dict(record)
    overlay["calculation_inputs"] = canonical
    finding = audit_revenue_growth("phase2b", overlay)
    out = _result(
        status=finding.audit_status,
        code=finding.finding_code,
        level=finding.recomputed_level,
        canonical_inputs=canonical,
        normalized_facts=assessments,
        source_fields=fields,
        message=finding.message,
    )
    if finding.audit_status == STATUS_HARD:
        out["proposed_replacement"] = {
            "applicable": finding.recomputed_applicable,
            "expected_status": finding.recomputed_status,
            "expected_level": finding.recomputed_level,
        }
    return out


def _sum_or_num(value: Any) -> float | None:
    direct = _num(value)
    if direct is not None:
        return direct
    if isinstance(value, list):
        nums = [_num(v) for v in value]
        if nums and all(v is not None for v in nums):
            return float(sum(v for v in nums if v is not None))
    return None


def _pct_point(row: Mapping[str, Any], kind: str) -> tuple[dict[str, Any], list[str], bool]:
    fields: list[str] = []
    largest_names = (
        f"largest_{kind}_pct",
        f"largest_{kind}s_pct",
        f"largest_{kind}_percentage",
        f"largest_{kind}_disclosed_pct",
        f"disclosed_largest_{kind}_pct",
    )
    top_names = (
        f"top_five_{kind}_pct",
        f"top_five_{kind}s_pct",
        f"top_five_{kind}_percentage",
        f"top_five_{kind}s_percentage",
        f"disclosed_top_five_{kind}_pct",
        f"disclosed_top_five_{kind}s_pct",
    )
    largest, lk = _first_num(row, largest_names)
    top5, tk = _first_num(row, top_names)
    if lk:
        fields.append(lk)
    if tk:
        fields.append(tk)

    if kind == "customer":
        denom, dk = _first_num(row, ("total_revenue", "revenue"))
        largest_amount, lak = _first_num(row, ("largest_customer_revenue", "largest_customer_sales"))
        top_amount = None
        tak = None
        for key in ("top_five_customer_revenue", "top_five_customer_revenue_sum", "top_five_customer_sales", "top_five_customer_revenues"):
            if key in row:
                top_amount = _sum_or_num(row.get(key))
                if top_amount is not None:
                    tak = key
                    break
    else:
        denom, dk = _first_num(row, ("total_supplier_purchases", "total_purchases", "purchase_total"))
        largest_amount, lak = _first_num(row, ("largest_supplier_purchases", "largest_supplier_purchase"))
        top_amount = None
        tak = None
        for key in ("top_five_supplier_purchase_sum", "top_five_supplier_purchases", "top_five_suppliers_purchases"):
            if key in row:
                top_amount = _sum_or_num(row.get(key))
                if top_amount is not None:
                    tak = key
                    break
    zero_denom = denom == 0
    if denom not in (None, 0.0):
        if largest is None and largest_amount is not None:
            largest = largest_amount / denom * 100.0
            fields.extend([dk or "", lak or ""])
        if top5 is None and top_amount is not None:
            top5 = top_amount / denom * 100.0
            fields.extend([dk or "", tak or ""])
    return {
        "period": row.get("period"),
        "largest_pct": largest,
        "top_five_pct": top5,
    }, [f for f in fields if f], zero_denom


def _pct_level(largest: float | None, top5: float | None) -> str | None:
    if (largest is not None and largest >= 50) or (top5 is not None and top5 >= 80):
        return "high"
    if (largest is not None and largest >= 30) or (top5 is not None and top5 >= 60):
        return "medium"
    if largest is not None and top5 is not None:
        return "not_applicable"
    return None


def canonicalize_concentration(record: Mapping[str, Any], kind: str) -> dict[str, Any]:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_CONCENTRATION_INPUTS_MISSING")
    raw_rows = inputs.get("periods")
    rows: list[Mapping[str, Any]]
    if isinstance(raw_rows, list) and raw_rows and all(isinstance(row, Mapping) for row in raw_rows):
        rows = list(raw_rows)
    else:
        rows = [inputs]
    facts = []
    fields: list[str] = []
    zero_denominator = False
    for row in rows:
        fact, f, zero = _pct_point(row, kind)
        facts.append(fact)
        fields.extend(f)
        zero_denominator = zero_denominator or zero
    if kind == "customer" and zero_denominator:
        return _result(
            status=STATUS_POLICY,
            code="OPEN_01_ZERO_REVENUE_CONCENTRATION",
            normalized_facts=facts,
            source_fields=fields,
            message="Customer concentration denominator is zero; OPEN-01 remains unresolved.",
        )
    assessments = []
    incomplete = []
    for fact in facts:
        level = _pct_level(_num(fact.get("largest_pct")), _num(fact.get("top_five_pct")))
        row = {**fact, "level": level}
        if level is None:
            incomplete.append(row)
        else:
            assessments.append(row)
    if incomplete:
        return _result(
            status=STATUS_INSUFFICIENT,
            code="PHASE2B_CONCENTRATION_FACTS_STILL_INSUFFICIENT",
            normalized_facts={"assessed": assessments, "incomplete": incomplete},
            source_fields=fields,
        )
    levels = {row["level"] for row in assessments}
    if len(levels) > 1:
        return _result(
            status=STATUS_POLICY,
            code="POLICY_AMBIGUITY_CONCENTRATION_PERIOD",
            normalized_facts=assessments,
            source_fields=fields,
            message="Canonicalized periods imply different concentration states; latest-vs-any-period policy is not frozen.",
        )
    level = next(iter(levels))
    chosen = assessments[-1]
    canonical = {}
    if chosen["largest_pct"] is not None:
        canonical[f"largest_{kind}_pct"] = chosen["largest_pct"]
    if chosen["top_five_pct"] is not None:
        canonical[f"top_five_{kind}_pct"] = chosen["top_five_pct"]
    if len(canonical) == 2:
        overlay = dict(record)
        overlay["calculation_inputs"] = canonical
        finding = audit_concentration("phase2b", overlay, kind)
        out = _result(
            status=finding.audit_status,
            code=finding.finding_code,
            level=finding.recomputed_level,
            canonical_inputs=canonical,
            normalized_facts=assessments,
            source_fields=fields,
            message=finding.message,
        )
        if finding.audit_status == STATUS_HARD:
            out["proposed_replacement"] = {
                "applicable": finding.recomputed_applicable,
                "expected_status": finding.recomputed_status,
                "expected_level": finding.recomputed_level,
            }
        return out
    return _custom_label_result(
        record,
        level,
        code="CONCENTRATION_LABEL_CONFLICT_AFTER_BACKFILL",
        canonical_inputs=canonical,
        normalized_facts=assessments,
        source_fields=fields,
        message="Available exact percentage is sufficient to establish the triggered level.",
    )


def canonicalize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    risk = str(record.get("risk_code") or "")
    if risk == "cash_runway":
        return canonicalize_cash(record)
    if risk == "continuous_loss":
        return canonicalize_continuous_loss(record)
    if risk == "revenue_growth":
        return canonicalize_revenue(record)
    if risk == "customer_concentration":
        return canonicalize_concentration(record, "customer")
    if risk == "supplier_concentration":
        return canonicalize_concentration(record, "supplier")
    return _result(status=STATUS_INSUFFICIENT, code="PHASE2B_UNSUPPORTED_RISK")
