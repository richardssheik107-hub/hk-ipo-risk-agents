"""Phase-2b compatibility layer for additional legacy calculation-input shapes.

This module only reshapes structured facts already stored in pass1 into the
canonical aliases understood by the Phase-2b v1 normalizers. It never parses
prose, fabricates a numeric fact, or resolves an unfrozen cross-period policy.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .annotation_audit import STATUS_INSUFFICIENT
from .annotation_backfill_normalizers import canonicalize_record as canonicalize_v1


def _mapping(value: Any) -> dict[str, Any] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _augment_revenue(inputs: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(inputs)

    # Scalar legacy aliases.
    scalar_aliases = (
        ("base_revenue", "comparison_revenue"),
        ("prior_comparable_revenue", "current_revenue"),
        ("comparator_revenue", "current_revenue"),
        ("revenue_from", "revenue_to"),
    )
    for prior_key, current_key in scalar_aliases:
        if prior_key in out and current_key in out:
            out.setdefault("previous_revenue", out[prior_key])
            out.setdefault("current_revenue", out[current_key])
            break

    # Nested current/comparison period objects.
    current_period = _mapping(out.get("current_period"))
    comparison_period = _mapping(out.get("comparison_period"))
    if current_period and comparison_period:
        if "revenue" in current_period and "revenue" in comparison_period:
            out.setdefault("previous_revenue", comparison_period["revenue"])
            out.setdefault("current_revenue", current_period["revenue"])
            out.setdefault("prior_period", comparison_period.get("period"))
            out["current_period"] = current_period.get("period")

    # Legacy comparison rows use from_/to_ rather than prior_/current_.
    comparisons = out.get("comparisons")
    if isinstance(comparisons, list):
        normalized = []
        for row in comparisons:
            if not isinstance(row, Mapping):
                continue
            item = dict(row)
            if "from_revenue" in item and "to_revenue" in item:
                item.setdefault("prior_revenue", item["from_revenue"])
                item.setdefault("current_revenue", item["to_revenue"])
                item.setdefault("prior_period", item.get("from_period"))
                item.setdefault("current_period", item.get("to_period"))
            normalized.append(item)
        out["comparisons"] = normalized
    return out


def _flatten_loss_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(inputs)
    flattened: list[dict[str, Any]] = []

    # Nested comparable-period sets (e.g. full_year + seven_months).
    sets = out.get("comparable_period_sets")
    if isinstance(sets, list):
        for group in sets:
            if not isinstance(group, Mapping):
                continue
            periods = group.get("periods")
            if isinstance(periods, list):
                for row in periods:
                    if isinstance(row, Mapping) and "loss" in row:
                        flattened.append({"period": row.get("period"), "loss": row.get("loss")})

    # Direct legacy named comparable lists.
    for key in (
        "comparable_annual_periods",
        "comparable_interim_periods",
        "interim_periods",
        "interim_comparable_periods",
    ):
        periods = out.get(key)
        if not isinstance(periods, list):
            continue
        for row in periods:
            if not isinstance(row, Mapping):
                continue
            value = None
            for value_key in (
                "loss", "net_loss", "loss_for_period", "profit_or_loss",
                "profit_loss", "net_profit",
            ):
                if value_key in row:
                    value = row[value_key]
                    break
            if value is not None:
                flattened.append({"period": row.get("period"), "loss": value})

    # Preserve any direct loss_periods already present.
    direct = out.get("loss_periods")
    if isinstance(direct, list):
        for row in direct:
            if isinstance(row, Mapping) and "loss" in row:
                flattened.append({"period": row.get("period"), "loss": row.get("loss")})

    if flattened:
        deduped = []
        seen = set()
        for row in flattened:
            token = (str(row.get("period")), str(row.get("loss")))
            if token not in seen:
                seen.add(token)
                deduped.append(row)
        out["loss_periods"] = deduped
    return out


def _augment_concentration(inputs: dict[str, Any], kind: str) -> dict[str, Any]:
    out = deepcopy(inputs)

    # Customer zero-denominator aliases used by pre-revenue issuers.
    if kind == "customer":
        if "customer_revenue_denominator" in out:
            out.setdefault("total_revenue", out["customer_revenue_denominator"])
        elif "product_sales_revenue" in out:
            out.setdefault("total_revenue", out["product_sales_revenue"])

    # Scalar supplier denominator/numerator aliases.
    if kind == "supplier":
        denominator_aliases = (
            "total_material_procurement_cost",
            "normalized_total_sales_cost_rmb_million",
            "total_service_cost",
            "denominator_rnd_and_administrative_expenses",
        )
        for key in denominator_aliases:
            if key in out:
                out.setdefault("total_supplier_purchases", out[key])
                break
        for key in (
            "largest_supplier_cost",
            "largest_supplier_service_cost",
        ):
            if key in out:
                out.setdefault("largest_supplier_purchases", out[key])
                break
        for key in (
            "top_five_supplier_cost",
            "top_five_supplier_service_cost",
        ):
            if key in out:
                out.setdefault("top_five_supplier_purchase_sum", out[key])
                break

    # Parallel arrays -> period objects. This is a pure zip of already structured
    # facts and does not infer a period-selection policy.
    periods = out.get("periods")
    if isinstance(periods, list) and periods and all(not isinstance(p, Mapping) for p in periods):
        largest_key_candidates = (
            f"largest_{kind}_pct",
            f"largest_{kind}s_pct",
        )
        top_key_candidates = (
            f"top_five_{kind}_pct",
            f"top_five_{kind}s_pct",
        )
        largest_values = None
        top_values = None
        for key in largest_key_candidates:
            if isinstance(out.get(key), list) and len(out[key]) == len(periods):
                largest_values = out[key]
                break
        for key in top_key_candidates:
            if isinstance(out.get(key), list) and len(out[key]) == len(periods):
                top_values = out[key]
                break
        if largest_values is not None or top_values is not None:
            rows = []
            for idx, period in enumerate(periods):
                row: dict[str, Any] = {"period": period}
                if largest_values is not None:
                    row[f"largest_{kind}_pct"] = largest_values[idx]
                if top_values is not None:
                    row[f"top_five_{kind}_pct"] = top_values[idx]
                rows.append(row)
            out["periods"] = rows

    return out


def _retry(record: Mapping[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    overlay = dict(record)
    overlay["calculation_inputs"] = inputs
    result = canonicalize_v1(overlay)
    result["compatibility_layer"] = "legacy_structured_alias_v2"
    return result


def canonicalize_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Run v1 first, then retry unresolved rows with additional safe aliases."""
    first = canonicalize_v1(record)
    if first.get("re_audit_status") != STATUS_INSUFFICIENT:
        return first

    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return first
    risk = str(record.get("risk_code") or "")

    if risk == "revenue_growth":
        return _retry(record, _augment_revenue(dict(inputs)))
    if risk == "continuous_loss":
        return _retry(record, _flatten_loss_inputs(dict(inputs)))
    if risk == "customer_concentration":
        return _retry(record, _augment_concentration(dict(inputs), "customer"))
    if risk == "supplier_concentration":
        return _retry(record, _augment_concentration(dict(inputs), "supplier"))
    return first
