"""Deterministic Phase-1 audit for GPT expert IPO annotations.

This module is intentionally read-only with respect to pass1 artifacts.  It
recomputes only policy rules that are frozen by the annotation protocol and
routes policy/semantic uncertainty to explicit review queues.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
import csv
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

EXPECTED_RISK_CODES = (
    "cash_runway",
    "continuous_loss",
    "revenue_growth",
    "customer_concentration",
    "supplier_concentration",
    "redemption_rights",
    "material_litigation_compliance",
    "precommercial_product",
)

SEMANTIC_RISKS = frozenset(
    {
        "redemption_rights",
        "material_litigation_compliance",
        "precommercial_product",
    }
)
CALCULATION_REQUIRED_RISKS = frozenset(
    {
        "cash_runway",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    }
)

STATUS_PASS = "PASS"
STATUS_HARD = "HARD_DETERMINISTIC_CONFLICT"
STATUS_INSUFFICIENT = "INSUFFICIENT_INPUT"
STATUS_EVIDENCE = "EVIDENCE_INPUT_CONFLICT"
STATUS_POLICY = "POLICY_AMBIGUITY"
STATUS_SECOND_PASS = "SECOND_PASS_REQUIRED"

STATUS_PRIORITY = {
    STATUS_PASS: 0,
    STATUS_SECOND_PASS: 1,
    STATUS_POLICY: 2,
    STATUS_INSUFFICIENT: 3,
    STATUS_EVIDENCE: 4,
    STATUS_HARD: 5,
}

ALLOWED_EVIDENCE_ROLES = {"primary", "supporting", "context", "cross_check"}
ALLOWED_REQUIREMENTS = {"required", "alternative", "supporting_only"}
ALLOWED_SOURCE_AUTHORITIES = {
    "audited_financial_statement",
    "accountants_report",
    "financial_information",
    "business_section",
    "legal_disclosure",
    "corporate_structure",
    "pre_ipo_investment",
    "summary",
    "risk_factors",
    "other",
}

STATE_TABLE = {
    (False, "rejected"): {"not_applicable"},
    (True, "verified"): {"low", "medium", "high", "critical"},
    (True, "needs_review"): {None, "low", "medium", "high", "critical"},
}


@dataclass(frozen=True)
class Finding:
    case_id: str
    risk_code: str
    audit_status: str
    finding_code: str
    message: str
    current_applicable: Any = None
    current_status: Any = None
    current_level: Any = None
    recomputed_applicable: Any = None
    recomputed_status: Any = None
    recomputed_level: Any = None
    details: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["details"] = dict(self.details or {})
        return data


def sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_annotation_files(root: Path) -> list[Path]:
    return sorted(root.glob("expert_results/ipo_*/pass1/expert_annotation_v1.json"))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _first_number(data: Mapping[str, Any], names: Sequence[str]) -> float | None:
    for name in names:
        if name in data:
            value = _number(data.get(name))
            if value is not None:
                return value
    return None


def _state_is_valid(record: Mapping[str, Any]) -> bool:
    key = (record.get("applicable"), record.get("expected_status"))
    return record.get("expected_level") in STATE_TABLE.get(key, set())


def _expected_tuple(level: str) -> tuple[bool, str, str]:
    if level == "not_applicable":
        return False, "rejected", "not_applicable"
    return True, "verified", level


def _matches_expected(record: Mapping[str, Any], level: str) -> bool:
    applicable, status, expected_level = _expected_tuple(level)
    return (
        record.get("applicable") is applicable
        and record.get("expected_status") == status
        and record.get("expected_level") == expected_level
    )


def _hard_conflict(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    level: str,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> Finding:
    applicable, status, expected_level = _expected_tuple(level)
    return Finding(
        case_id=case_id,
        risk_code=risk_code,
        audit_status=STATUS_HARD,
        finding_code=code,
        message=message,
        current_applicable=record.get("applicable"),
        current_status=record.get("expected_status"),
        current_level=record.get("expected_level"),
        recomputed_applicable=applicable,
        recomputed_status=status,
        recomputed_level=expected_level,
        details=details,
    )


def _pass(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    level: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> Finding:
    if level is None:
        return Finding(
            case_id=case_id,
            risk_code=risk_code,
            audit_status=STATUS_PASS,
            finding_code="PASS",
            message="Record passes Phase-1 checks.",
            current_applicable=record.get("applicable"),
            current_status=record.get("expected_status"),
            current_level=record.get("expected_level"),
            details=details,
        )
    applicable, status, expected_level = _expected_tuple(level)
    return Finding(
        case_id=case_id,
        risk_code=risk_code,
        audit_status=STATUS_PASS,
        finding_code="PASS",
        message="Stored label agrees with frozen deterministic rule.",
        current_applicable=record.get("applicable"),
        current_status=record.get("expected_status"),
        current_level=record.get("expected_level"),
        recomputed_applicable=applicable,
        recomputed_status=status,
        recomputed_level=expected_level,
        details=details,
    )


def _insufficient(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> Finding:
    return Finding(
        case_id=case_id,
        risk_code=risk_code,
        audit_status=STATUS_INSUFFICIENT,
        finding_code=code,
        message=message,
        current_applicable=record.get("applicable"),
        current_status=record.get("expected_status"),
        current_level=record.get("expected_level"),
        details=details,
    )


def _policy(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> Finding:
    return Finding(
        case_id=case_id,
        risk_code=risk_code,
        audit_status=STATUS_POLICY,
        finding_code=code,
        message=message,
        current_applicable=record.get("applicable"),
        current_status=record.get("expected_status"),
        current_level=record.get("expected_level"),
        details=details,
    )


def _evidence_conflict(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> Finding:
    return Finding(
        case_id=case_id,
        risk_code=risk_code,
        audit_status=STATUS_EVIDENCE,
        finding_code=code,
        message=message,
        current_applicable=record.get("applicable"),
        current_status=record.get("expected_status"),
        current_level=record.get("expected_level"),
        details=details,
    )


def _cash_runway_level(months: float) -> str:
    if months < 3:
        return "critical"
    if months < 6:
        return "high"
    if months < 12:
        return "medium"
    return "not_applicable"


def audit_cash_runway(case_id: str, record: Mapping[str, Any]) -> Finding:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _insufficient(
            case_id, "cash_runway", record, "CASH_INPUTS_MISSING",
            "cash_runway requires structured calculation_inputs.",
        )

    cash = _first_number(inputs, ("cash", "cash_and_cash_equivalents", "cash_equivalents"))
    op_cash_flow = _first_number(
        inputs,
        (
            "net_cash_used_in_operating_activities",
            "net_cash_from_operating_activities",
            "operating_cash_flow",
        ),
    )
    period_months = _first_number(inputs, ("period_months", "months_in_period"))

    if op_cash_flow is not None and op_cash_flow >= 0:
        level = "not_applicable"
        details = {"operating_cash_flow": op_cash_flow, "rule": "nonnegative_operating_cash_flow"}
        if _matches_expected(record, level):
            return _pass(case_id, "cash_runway", record, level, details)
        return _hard_conflict(
            case_id, "cash_runway", record, level,
            "CASH_POSITIVE_OPERATING_FLOW_LABEL_CONFLICT",
            "Non-negative operating cash flow means no operating cash burn under the frozen protocol.",
            details,
        )

    monthly_burn = _first_number(inputs, ("monthly_cash_burn", "monthly_operating_cash_burn"))
    if monthly_burn is not None:
        monthly_burn = abs(monthly_burn)
    if monthly_burn in (None, 0.0) and op_cash_flow is not None and period_months not in (None, 0.0):
        monthly_burn = abs(op_cash_flow) / period_months

    if cash is None or monthly_burn is None or monthly_burn <= 0:
        return _insufficient(
            case_id,
            "cash_runway",
            record,
            "CASH_RECOMPUTE_INPUTS_INSUFFICIENT",
            "Need cash plus a positive monthly operating cash burn derivable from calculation_inputs.",
            {"cash": cash, "monthly_cash_burn": monthly_burn, "period_months": period_months},
        )

    months = cash / monthly_burn
    level = _cash_runway_level(months)
    details = {"cash": cash, "monthly_cash_burn": monthly_burn, "cash_runway_months": months}
    if _matches_expected(record, level):
        return _pass(case_id, "cash_runway", record, level, details)
    return _hard_conflict(
        case_id,
        "cash_runway",
        record,
        level,
        "CASH_RUNWAY_LABEL_CONFLICT",
        f"Recomputed cash runway is {months:.6g} months; stored label does not match frozen thresholds.",
        details,
    )


def _revenue_growth_level(growth_pct: float) -> str:
    if growth_pct <= -20:
        return "high"
    if growth_pct < 0:
        return "medium"
    return "not_applicable"


def audit_revenue_growth(case_id: str, record: Mapping[str, Any]) -> Finding:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _insufficient(
            case_id, "revenue_growth", record, "REVENUE_INPUTS_MISSING",
            "revenue_growth requires structured calculation_inputs.",
        )
    previous = _first_number(inputs, ("previous_revenue", "prior_revenue", "base_revenue"))
    current = _first_number(inputs, ("current_revenue", "latest_revenue"))
    if previous is None or current is None:
        return _insufficient(
            case_id, "revenue_growth", record, "REVENUE_RECOMPUTE_INPUTS_INSUFFICIENT",
            "Need previous_revenue and current_revenue.",
            {"previous_revenue": previous, "current_revenue": current},
        )
    if previous <= 0:
        return _policy(
            case_id,
            "revenue_growth",
            record,
            "REVENUE_GROWTH_DENOMINATOR_NONPOSITIVE",
            "Comparable growth cannot be deterministically computed from a non-positive denominator.",
            {"previous_revenue": previous, "current_revenue": current},
        )
    growth_pct = (current - previous) / previous * 100.0
    level = _revenue_growth_level(growth_pct)
    details = {"previous_revenue": previous, "current_revenue": current, "growth_pct": growth_pct}
    if _matches_expected(record, level):
        return _pass(case_id, "revenue_growth", record, level, details)
    return _hard_conflict(
        case_id,
        "revenue_growth",
        record,
        level,
        "REVENUE_GROWTH_LABEL_CONFLICT",
        f"Recomputed comparable revenue growth is {growth_pct:.6g}%; stored label conflicts with frozen thresholds.",
        details,
    )


def _concentration_level(largest: float, top_five: float) -> str:
    if largest >= 50 or top_five >= 80:
        return "high"
    if largest >= 30 or top_five >= 60:
        return "medium"
    return "not_applicable"


def _period_candidates(inputs: Mapping[str, Any], prefix: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ("periods", "period_values", f"{prefix}_periods", f"{prefix}_history"):
        value = inputs.get(key)
        if isinstance(value, list):
            for row in value:
                if not isinstance(row, Mapping):
                    continue
                largest = _first_number(row, (f"largest_{prefix}_pct", "largest_pct", "largest_share_pct"))
                top_five = _first_number(row, (f"top_five_{prefix}_pct", "top_five_pct", "top5_pct"))
                if largest is not None and top_five is not None:
                    candidates.append(
                        {
                            "period": row.get("period"),
                            "largest_pct": largest,
                            "top_five_pct": top_five,
                            "level": _concentration_level(largest, top_five),
                        }
                    )
    return candidates


def audit_concentration(case_id: str, record: Mapping[str, Any], kind: str) -> Finding:
    risk_code = f"{kind}_concentration"
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _insufficient(
            case_id, risk_code, record, "CONCENTRATION_INPUTS_MISSING",
            f"{risk_code} requires structured calculation_inputs.",
        )

    prefix = kind
    largest = _first_number(inputs, (f"largest_{prefix}_pct", "largest_pct", "largest_share_pct"))
    top_five = _first_number(inputs, (f"top_five_{prefix}_pct", "top_five_pct", "top5_pct"))

    period_rows = _period_candidates(inputs, prefix)
    if period_rows:
        latest = period_rows[-1]
        levels = {row["level"] for row in period_rows}
        triggered = {level for level in levels if level != "not_applicable"}
        latest_triggered = latest["level"] != "not_applicable"
        any_triggered = bool(triggered)
        if latest_triggered != any_triggered or len(levels) > 1:
            return _policy(
                case_id,
                risk_code,
                record,
                "POLICY_AMBIGUITY_CONCENTRATION_PERIOD",
                "Structured period history yields different concentration states across periods; Phase 1 does not choose latest-period versus any-period policy.",
                {"periods": period_rows, "latest_period_result": latest["level"], "any_period_triggered": any_triggered},
            )
        largest = latest["largest_pct"]
        top_five = latest["top_five_pct"]

    if largest is None or top_five is None:
        if any(
            inputs.get(key) is not None
            for key in (
                "bound_operator",
                f"largest_{prefix}_bound",
                f"top_five_{prefix}_bound",
                "largest_bound",
                "top_five_bound",
            )
        ):
            return _policy(
                case_id,
                risk_code,
                record,
                "CONCENTRATION_BOUND_PROOF_REQUIRES_REVIEW",
                "A formal bound proof is present; Phase 1 does not coerce strict bounds into point estimates.",
                {"calculation_inputs": dict(inputs)},
            )
        return _insufficient(
            case_id,
            risk_code,
            record,
            "CONCENTRATION_RECOMPUTE_INPUTS_INSUFFICIENT",
            "Need exact largest and top-five percentage inputs, or a separately reviewed formal bound proof.",
            {"largest_pct": largest, "top_five_pct": top_five},
        )

    if largest < 0 or top_five < 0:
        return _evidence_conflict(
            case_id,
            risk_code,
            record,
            "CONCENTRATION_NEGATIVE_RATIO",
            "Concentration percentages cannot be negative.",
            {"largest_pct": largest, "top_five_pct": top_five},
        )

    level = _concentration_level(largest, top_five)
    details = {"largest_pct": largest, "top_five_pct": top_five}
    if _matches_expected(record, level):
        return _pass(case_id, risk_code, record, level, details)
    return _hard_conflict(
        case_id,
        risk_code,
        record,
        level,
        "CONCENTRATION_LABEL_CONFLICT",
        f"Recomputed {kind} concentration is largest={largest:.6g}%, top-five={top_five:.6g}%; stored label conflicts with 30/60 medium and 50/80 high thresholds.",
        details,
    )


_MONTH_PATTERNS = (
    (r"\b(?:twelve|12)\s+months?\b|\byear ended\b|\bfinancial year\b", "FY"),
    (r"\b(?:six|6)\s+months?\b|\bhalf[- ]year\b", "H1"),
    (r"\b(?:nine|9)\s+months?\b", "9M"),
    (r"\b(?:three|3)\s+months?\b", "3M"),
    (r"\b(?:eight|8)\s+months?\b", "8M"),
    (r"\b(?:ten|10)\s+months?\b", "10M"),
    (r"\b(?:eleven|11)\s+months?\b", "11M"),
    (r"\b(?:four|4)\s+months?\b", "4M"),
    (r"\b(?:five|5)\s+months?\b", "5M"),
    (r"\b(?:seven|7)\s+months?\b", "7M"),
)


def period_signature(period: Any) -> str:
    text = str(period or "").strip().lower()
    for pattern, label in _MONTH_PATTERNS:
        if re.search(pattern, text):
            return label
    return "UNKNOWN"


def audit_continuous_loss(case_id: str, record: Mapping[str, Any]) -> Finding:
    inputs = record.get("calculation_inputs")
    if not isinstance(inputs, Mapping):
        return _insufficient(
            case_id, "continuous_loss", record, "LOSS_INPUTS_MISSING",
            "continuous_loss requires structured comparable-period facts.",
        )
    periods = inputs.get("loss_periods")
    if not isinstance(periods, list) or not periods:
        return _insufficient(
            case_id, "continuous_loss", record, "LOSS_PERIODS_MISSING",
            "Need a non-empty loss_periods list.",
        )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown: list[dict[str, Any]] = []
    for row in periods:
        if not isinstance(row, Mapping):
            return _evidence_conflict(
                case_id, "continuous_loss", record, "LOSS_PERIOD_ROW_INVALID",
                "Every loss_periods entry must be an object.",
            )
        loss = _number(row.get("loss"))
        if loss is None:
            return _insufficient(
                case_id, "continuous_loss", record, "LOSS_VALUE_MISSING",
                "Every loss_periods entry needs a numeric loss.",
                {"period": row.get("period")},
            )
        if loss >= 0:
            continue
        sig = period_signature(row.get("period"))
        normalized = {"period": row.get("period"), "loss": loss, "signature": sig}
        if sig == "UNKNOWN":
            unknown.append(normalized)
        groups[sig].append(normalized)

    if unknown:
        return _policy(
            case_id,
            "continuous_loss",
            record,
            "COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS",
            "At least one loss period has an unrecognized period type; comparability cannot be frozen deterministically.",
            {"unknown_periods": unknown, "groups": dict(groups)},
        )

    nonempty_groups = {k: v for k, v in groups.items() if v}
    if len(nonempty_groups) > 1:
        stored_result = record.get("calculation_result")
        stored_count = None
        if isinstance(stored_result, Mapping):
            stored_count = _number(stored_result.get("loss_period_count"))
        total_losses = sum(len(v) for v in nonempty_groups.values())
        return _policy(
            case_id,
            "continuous_loss",
            record,
            "COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS",
            "Loss facts mix period types (for example FY and stub periods). Phase 1 does not pool incomparable periods.",
            {
                "comparable_groups": {k: len(v) for k, v in nonempty_groups.items()},
                "total_loss_periods": total_losses,
                "stored_loss_period_count": stored_count,
            },
        )

    comparable_count = max((len(v) for v in nonempty_groups.values()), default=0)
    if comparable_count >= 3:
        level = "high"
    elif comparable_count >= 2:
        level = "medium"
    else:
        level = "not_applicable"

    details = {
        "comparable_period_signature": next(iter(nonempty_groups), None),
        "comparable_loss_period_count": comparable_count,
    }
    if _matches_expected(record, level):
        return _pass(case_id, "continuous_loss", record, level, details)
    return _hard_conflict(
        case_id,
        "continuous_loss",
        record,
        level,
        "CONTINUOUS_LOSS_LABEL_CONFLICT",
        f"{comparable_count} comparable loss periods imply {level} under the frozen protocol.",
        details,
    )


def _validate_evidence(
    case_id: str,
    risk_code: str,
    record: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
) -> Finding | None:
    rows = [row for row in evidence_rows if row.get("risk_code") == risk_code]
    if not rows:
        return _evidence_conflict(
            case_id,
            risk_code,
            record,
            "EVIDENCE_MISSING",
            "No evidence record is linked to this risk.",
        )

    errors: list[str] = []
    for idx, row in enumerate(rows):
        page = row.get("page")
        if page is None or page == "":
            errors.append(f"evidence[{idx}].page missing")
        exact_text = row.get("exact_text")
        if not isinstance(exact_text, str) or not exact_text.strip():
            errors.append(f"evidence[{idx}].exact_text missing")
        if row.get("evidence_role") not in ALLOWED_EVIDENCE_ROLES:
            errors.append(f"evidence[{idx}].evidence_role invalid")
        if row.get("requirement") not in ALLOWED_REQUIREMENTS:
            errors.append(f"evidence[{idx}].requirement invalid")
        if row.get("source_authority") not in ALLOWED_SOURCE_AUTHORITIES:
            errors.append(f"evidence[{idx}].source_authority invalid")
        confidence = _number(row.get("confidence"))
        if confidence is None or not (0 <= confidence <= 1):
            errors.append(f"evidence[{idx}].confidence invalid")
        if row.get("case_id") not in (None, case_id):
            errors.append(f"evidence[{idx}].case_id mismatch")
    if errors:
        return _evidence_conflict(
            case_id,
            risk_code,
            record,
            "EVIDENCE_STRUCTURE_INVALID",
            "; ".join(errors),
            {"errors": errors},
        )
    return None


def _audit_record(
    case_id: str,
    record: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
) -> Finding:
    risk_code = str(record.get("risk_code") or "")

    if not _state_is_valid(record):
        return _evidence_conflict(
            case_id,
            risk_code,
            record,
            "STATE_CONSISTENCY_INVALID",
            "applicable / expected_status / expected_level combination violates the frozen state table.",
        )

    if risk_code in CALCULATION_REQUIRED_RISKS and record.get("calculation_required") is not True:
        return _evidence_conflict(
            case_id,
            risk_code,
            record,
            "CALCULATION_REQUIRED_FLAG_INVALID",
            f"{risk_code} must set calculation_required=true under the protocol.",
        )

    evidence_finding = _validate_evidence(case_id, risk_code, record, evidence_rows)
    if evidence_finding is not None:
        return evidence_finding

    if risk_code == "cash_runway":
        return audit_cash_runway(case_id, record)
    if risk_code == "continuous_loss":
        return audit_continuous_loss(case_id, record)
    if risk_code == "revenue_growth":
        return audit_revenue_growth(case_id, record)
    if risk_code == "customer_concentration":
        return audit_concentration(case_id, record, "customer")
    if risk_code == "supplier_concentration":
        return audit_concentration(case_id, record, "supplier")
    if risk_code in SEMANTIC_RISKS:
        return Finding(
            case_id=case_id,
            risk_code=risk_code,
            audit_status=STATUS_SECOND_PASS,
            finding_code="SEMANTIC_RISK_SECOND_PASS_REQUIRED",
            message="Semantic risk is structurally complete but requires independent second-pass review.",
            current_applicable=record.get("applicable"),
            current_status=record.get("expected_status"),
            current_level=record.get("expected_level"),
        )
    return _evidence_conflict(
        case_id,
        risk_code,
        record,
        "UNKNOWN_RISK_CODE",
        "Risk code is not part of the eight-code protocol.",
    )


def audit_case(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        case_id = path.parents[1].name
        finding = Finding(
            case_id=case_id,
            risk_code="__bundle__",
            audit_status=STATUS_EVIDENCE,
            finding_code="INVALID_JSON",
            message=str(exc),
        )
        return {
            "case_id": case_id,
            "path": path.as_posix(),
            "sha256": sha256_file(path),
            "findings": [finding.to_dict()],
            "risk_record_count": 0,
        }

    case_id = str(bundle.get("case_id") or path.parents[1].name)
    findings: list[Finding] = []
    risks = bundle.get("risks")
    evidence = bundle.get("evidence")

    if not isinstance(risks, list):
        findings.append(Finding(case_id, "__bundle__", STATUS_EVIDENCE, "RISKS_ARRAY_MISSING", "Top-level risks must be an array."))
        risks = []
    if not isinstance(evidence, list):
        findings.append(Finding(case_id, "__bundle__", STATUS_EVIDENCE, "EVIDENCE_ARRAY_MISSING", "Top-level evidence must be an array."))
        evidence = []

    if bundle.get("document_id") != case_id:
        findings.append(
            Finding(
                case_id,
                "__bundle__",
                STATUS_EVIDENCE,
                "DOCUMENT_ID_MISMATCH",
                f"document_id={bundle.get('document_id')!r} does not match case_id={case_id!r}.",
            )
        )

    codes = [r.get("risk_code") for r in risks if isinstance(r, Mapping)]
    counts = Counter(codes)
    missing = sorted(set(EXPECTED_RISK_CODES) - set(codes))
    duplicates = sorted(code for code, count in counts.items() if code and count > 1)
    unexpected = sorted(code for code in set(codes) - set(EXPECTED_RISK_CODES) if code)
    if missing or duplicates or unexpected:
        findings.append(
            Finding(
                case_id,
                "__bundle__",
                STATUS_EVIDENCE,
                "RISK_SET_INVALID",
                "Bundle must contain exactly one record for each of the eight expected risk codes.",
                details={"missing": missing, "duplicates": duplicates, "unexpected": unexpected},
            )
        )

    evidence_rows = [row for row in evidence if isinstance(row, Mapping)]
    for record in risks:
        if not isinstance(record, Mapping):
            findings.append(Finding(case_id, "__bundle__", STATUS_EVIDENCE, "RISK_RECORD_INVALID", "Every risks entry must be an object."))
            continue
        record_case_id = record.get("case_id")
        record_document_id = record.get("document_id")
        if record_case_id not in (None, case_id) or record_document_id not in (None, case_id):
            findings.append(
                Finding(
                    case_id,
                    str(record.get("risk_code") or "__unknown__"),
                    STATUS_EVIDENCE,
                    "RECORD_ID_MISMATCH",
                    "Risk-level case_id/document_id does not match bundle case_id.",
                    current_applicable=record.get("applicable"),
                    current_status=record.get("expected_status"),
                    current_level=record.get("expected_level"),
                )
            )
            continue
        findings.append(_audit_record(case_id, record, evidence_rows))

    return {
        "case_id": case_id,
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "risk_record_count": len(risks),
        "findings": [finding.to_dict() for finding in findings],
    }


def _flatten_findings(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        for finding in case.get("findings", []):
            row = dict(finding)
            row["source_path"] = case.get("path")
            row["pass1_sha256"] = case.get("sha256")
            details = row.get("details") or {}
            row["details_json"] = json.dumps(details, ensure_ascii=False, sort_keys=True)
            row.pop("details", None)
            rows.append(row)
    return rows


def _summary(cases: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["audit_status"] for row in rows)
    by_risk: dict[str, dict[str, int]] = {}
    for risk in [*EXPECTED_RISK_CODES, "__bundle__"]:
        risk_rows = [row for row in rows if row["risk_code"] == risk]
        if risk_rows:
            by_risk[risk] = dict(sorted(Counter(row["audit_status"] for row in risk_rows).items()))

    return {
        "cases_scanned": len(cases),
        "risk_records_scanned": sum(int(case.get("risk_record_count", 0)) for case in cases),
        "finding_counts": {status: status_counts.get(status, 0) for status in STATUS_PRIORITY},
        "by_risk_code": by_risk,
        "pass1_unchanged": True,
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id",
        "risk_code",
        "audit_status",
        "finding_code",
        "message",
        "current_applicable",
        "current_status",
        "current_level",
        "recomputed_applicable",
        "recomputed_status",
        "recomputed_level",
        "source_path",
        "pass1_sha256",
        "details_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_reports(cases: Sequence[Mapping[str, Any]], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    per_case_dir = output_dir / "per_case"
    per_case_dir.mkdir(parents=True, exist_ok=True)

    rows = _flatten_findings(cases)
    summary = _summary(cases, rows)

    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "risk_conflicts.csv",
        [row for row in rows if row["audit_status"] in {STATUS_HARD, STATUS_INSUFFICIENT, STATUS_EVIDENCE}],
    )
    _write_csv(
        output_dir / "policy_ambiguities.csv",
        [row for row in rows if row["audit_status"] == STATUS_POLICY],
    )
    _write_csv(
        output_dir / "semantic_review_queue.csv",
        [row for row in rows if row["audit_status"] == STATUS_SECOND_PASS],
    )

    for case in cases:
        case_id = str(case["case_id"])
        (per_case_dir / f"{case_id}.json").write_text(
            json.dumps(case, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return summary


def run_audit(root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    files = discover_annotation_files(root)
    before = {path: sha256_file(path) for path in files}
    cases = [audit_case(path) for path in files]
    if output_dir is not None:
        summary = write_reports(cases, output_dir)
    else:
        summary = _summary(cases, _flatten_findings(cases))
    after = {path: sha256_file(path) for path in files}
    changed = [path.as_posix() for path in files if before[path] != after[path]]
    if changed:
        raise RuntimeError(f"Phase-1 audit modified pass1 artifacts: {changed}")
    summary["pass1_unchanged"] = True
    summary["pass1_file_count"] = len(files)
    return summary
