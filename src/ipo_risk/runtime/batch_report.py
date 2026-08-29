"""The batch report: several analysed companies on one page, without a verdict.

The case report answers "what did this run find in this prospectus".  A reviewer
looking at a portfolio needs the other question -- which of these companies to
open first, and what each one's evidence is actually worth -- and that is the
one place where a summary is most tempted to say more than the runs did.

So this report carries two things and nothing in between: the recorded state of
each case (risk counts by severity, conflicts, Final Supervisor outcome,
traceability, Evidence and screenshot coverage, which channels were available)
and a triage ordering whose rule is printed next to it.  The ordering sorts the
severities the document channel actually recorded.  It is not a score, not a
probability and not a cross-company prediction: no frozen model ran in these
cases unless the model channel says so, and the report states which it was.

Absences stay absences.  A case whose market channel was unavailable contributes
no market fact; a case nobody reviewed is reported unreviewed rather than
uncontested; a case whose Final Supervisor fell back to the deterministic
composition is not counted as a real-provider arbitration.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

BATCH_REPORT_SCHEMA_VERSION = "v045_role_e_batch_report_v1"

RISK_LEVELS = ("critical", "high", "medium", "low")
RISK_GROUPS = ("verified_risks", "pending_risks", "rejected_risks")

# The triage rule, printed in the report itself so the ordering can never be
# read as a model output.  Severity counts come from the document channel's
# verified risks; ties fall back to pending risks and then to the case id, so
# the order is total and reproducible.
TRIAGE_RULE = (
    "ordered by the number of verified risks at each severity, critical first, then high, "
    "medium, low; ties broken by pending-risk count and then by case_id. This orders recorded "
    "risk counts. It is not a score, not a probability and not a prediction of post-listing "
    "performance."
)


def _risks(result: Mapping[str, Any], group: str) -> list[dict[str, Any]]:
    return [item for item in (result.get(group) or []) if isinstance(item, dict)]


def _level_counts(risks: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {level: 0 for level in RISK_LEVELS}
    for risk in risks:
        level = str(risk.get("level") or "")
        if level in counts:
            counts[level] += 1
    return counts


def _case_row(
    case: Mapping[str, Any],
    result: Mapping[str, Any],
    screenshots: Mapping[str, Any] | None,
    human_review: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """One company's recorded state, read back out of its own artifacts."""

    verified = _risks(result, "verified_risks")
    pending = _risks(result, "pending_risks")
    rejected = _risks(result, "rejected_risks")
    gate = case.get("gate_e1") or {}
    traceability = case.get("traceability") or {}
    channels = dict(case.get("channel_states") or {})
    return {
        "case_id": case.get("case_id"),
        "company_name": result.get("company_name") or case.get("company_name"),
        "stock_code": case.get("stock_code"),
        "listing_date": case.get("listing_date"),
        "status": case.get("status"),
        "analysis_id": case.get("analysis_id"),
        "verified_risk_count": len(verified),
        "pending_risk_count": len(pending),
        "rejected_risk_count": len(rejected),
        "verified_level_counts": _level_counts(verified),
        "pending_level_counts": _level_counts(pending),
        "verified_risk_codes": [
            {
                "risk_code": risk.get("risk_code"),
                "level": risk.get("level"),
                "agent_name": risk.get("agent_name"),
                "evidence_count": len(risk.get("evidence") or []),
                "has_calculation": bool(risk.get("calculation")),
            }
            for risk in verified
        ],
        "pending_risk_codes": [
            {"risk_code": risk.get("risk_code"), "level": risk.get("level")} for risk in pending
        ],
        "channel_states": channels,
        "unavailable_channels": sorted(
            channel for channel, state in channels.items() if state != "available"
        ),
        "conflict_count": case.get("conflict_count"),
        "conflict_statuses": dict(case.get("conflict_statuses") or {}),
        "recheck_attempted": case.get("recheck_attempted"),
        "final_supervision": {
            "status": case.get("llm_synthesis_status"),
            "outcome": case.get("llm_synthesis_outcome"),
            "reason": case.get("llm_synthesis_reason"),
            "deterministic_severity_floor": case.get("deterministic_severity_floor"),
            "real_provider_arbitration": gate.get("successful_llm_arbitration") is True
            and gate.get("provider_is_real_remote") is True
            and gate.get("deterministic_fallback_used") is False,
            "deterministic_fallback_used": gate.get("deterministic_fallback_used"),
            "provider_name": gate.get("provider_name"),
            "gate_e1_satisfied": gate.get("satisfied") is True,
            "scope_corrected": gate.get("scope_corrected"),
        },
        "traceability": traceability.get("overall_traceability"),
        "evidence_row_count": case.get("evidence_export_row_count"),
        "screenshots": _screenshot_row(screenshots),
        "human_review": {
            "review_count": (human_review or {}).get("review_count", 0),
            "reviewed": bool((human_review or {}).get("reviewed")),
        },
        "probability_claimed": case.get("probability_claimed"),
        "creates_no_new_risk": case.get("creates_no_new_risk"),
        "prospectus_sha256": (case.get("prospectus_verification") or {}).get("sha256"),
    }


def _screenshot_row(screenshots: Mapping[str, Any] | None) -> dict[str, Any]:
    """Screenshot coverage, or an explicit absence of it."""

    if not screenshots:
        return {
            "available": False,
            "status": "not_exported",
            "screenshot_count": None,
            "precise_localisation_count": None,
        }
    return {
        "available": True,
        "status": screenshots.get("status"),
        "cited_evidence_count": screenshots.get("cited_evidence_count"),
        "screenshot_count": screenshots.get("screenshot_count"),
        "precise_localisation_count": screenshots.get("precise_localisation_count"),
        "page_level_fallback_count": screenshots.get("page_level_fallback_count"),
        "no_geometry_count": screenshots.get("no_geometry_count"),
    }


def _triage_key(row: Mapping[str, Any]) -> tuple:
    counts = row["verified_level_counts"]
    return (
        -counts["critical"],
        -counts["high"],
        -counts["medium"],
        -counts["low"],
        -(row["pending_risk_count"] or 0),
        str(row["case_id"]),
    )


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    code_frequency: dict[str, int] = {}
    for row in rows:
        for item in row["verified_risk_codes"]:
            code = str(item["risk_code"])
            code_frequency[code] = code_frequency.get(code, 0) + 1
    channel_unavailability: dict[str, int] = {}
    for row in rows:
        for channel, state in row["channel_states"].items():
            if state != "available":
                channel_unavailability[f"{channel}:{state}"] = (
                    channel_unavailability.get(f"{channel}:{state}", 0) + 1
                )
    severity_totals = {level: 0 for level in RISK_LEVELS}
    for row in rows:
        for level, count in row["verified_level_counts"].items():
            severity_totals[level] += count
    traceabilities = [row["traceability"] for row in rows if isinstance(row["traceability"], (int, float))]
    screenshot_rows = [row["screenshots"] for row in rows if row["screenshots"]["available"]]
    return {
        "case_count": len(rows),
        "verified_risk_total": sum(row["verified_risk_count"] for row in rows),
        "pending_risk_total": sum(row["pending_risk_count"] for row in rows),
        "rejected_risk_total": sum(row["rejected_risk_count"] for row in rows),
        "verified_severity_totals": severity_totals,
        "risk_code_frequency": dict(sorted(code_frequency.items(), key=lambda item: (-item[1], item[0]))),
        "cases_with_real_provider_arbitration": sum(
            1 for row in rows if row["final_supervision"]["real_provider_arbitration"]
        ),
        "cases_with_deterministic_fallback": sum(
            1 for row in rows if row["final_supervision"]["deterministic_fallback_used"] is True
        ),
        "cases_with_gate_e1_satisfied": sum(
            1 for row in rows if row["final_supervision"]["gate_e1_satisfied"]
        ),
        "channel_unavailability": dict(sorted(channel_unavailability.items())),
        "minimum_traceability": min(traceabilities) if traceabilities else None,
        "cases_at_full_traceability": sum(1 for value in traceabilities if value == 1.0),
        "evidence_row_total": sum(int(row["evidence_row_count"] or 0) for row in rows),
        "screenshot_total": sum(int(item["screenshot_count"] or 0) for item in screenshot_rows),
        "precise_localisation_total": sum(
            int(item["precise_localisation_count"] or 0) for item in screenshot_rows
        ),
        "cases_without_screenshot_export": sum(
            1 for row in rows if not row["screenshots"]["available"]
        ),
        "human_review_total": sum(int(row["human_review"]["review_count"] or 0) for row in rows),
        "cases_reviewed_by_a_human": sum(1 for row in rows if row["human_review"]["reviewed"]),
        "cases_claiming_probability": sum(1 for row in rows if row["probability_claimed"] is True),
    }


def _limitations(rows: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any]) -> list[str]:
    """What this batch cannot support, stated from the data rather than assumed."""

    notes: list[str] = []
    if aggregate["channel_unavailability"]:
        notes.append(
            "Optional channels were not available in every case "
            f"({', '.join(f'{key} ×{value}' for key, value in aggregate['channel_unavailability'].items())}); "
            "no market fact or model score is contributed by a channel that did not run."
        )
    if aggregate["cases_with_deterministic_fallback"]:
        notes.append(
            f"{aggregate['cases_with_deterministic_fallback']} case(s) completed on the deterministic "
            "composition after the Final Supervisor could not arbitrate. Those pages are complete, and "
            "they do not count as real-provider acceptance."
        )
    if aggregate["cases_with_gate_e1_satisfied"] < aggregate["case_count"]:
        notes.append(
            f"Gate E1 is satisfied in {aggregate['cases_with_gate_e1_satisfied']}/{aggregate['case_count']} "
            "case(s); the rest are recorded with their unmet conditions in each case's Gate E1 evidence."
        )
    if aggregate["cases_reviewed_by_a_human"] < aggregate["case_count"]:
        notes.append(
            f"{aggregate['case_count'] - aggregate['cases_reviewed_by_a_human']} case(s) carry no human "
            "review. That is an absence of review, not an approval."
        )
    if aggregate["cases_without_screenshot_export"]:
        notes.append(
            f"{aggregate['cases_without_screenshot_export']} case(s) have no screenshot manifest; run the "
            "Evidence screenshot export against this directory to produce one."
        )
    notes.append(
        "The ordering below ranks recorded risk counts. No post-listing outcome was read for any case "
        "in this batch, so nothing here is a claim about how these companies will perform."
    )
    return notes


def build_batch_report(
    *,
    summary: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    screenshots: Mapping[str, Mapping[str, Any]] | None = None,
    human_reviews: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """One report over every executed case in a matrix run.

    A declared case that did not execute is listed with the reason the matrix
    recorded, so the batch cannot silently shrink to the cases that worked.
    """

    screenshots = screenshots or {}
    human_reviews = human_reviews or {}
    executed: list[dict[str, Any]] = []
    unexecuted: list[dict[str, Any]] = []
    for case in summary.get("cases", []) or []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "")
        result = results.get(case_id)
        if result is None or case.get("traceability") is None:
            unexecuted.append(
                {
                    "case_id": case_id,
                    "stock_code": case.get("stock_code"),
                    "status": case.get("status"),
                    "reason": case.get("reason") or "the matrix recorded no executed run for this case",
                }
            )
            continue
        executed.append(
            _case_row(case, result, screenshots.get(case_id), human_reviews.get(case_id))
        )
    executed.sort(key=_triage_key)
    aggregate = _aggregate(executed)
    return {
        "schema_version": BATCH_REPORT_SCHEMA_VERSION,
        "matrix": {
            "demo_version": summary.get("demo_version"),
            "config": summary.get("config"),
            "cases_manifest_version": summary.get("cases_manifest_version"),
            "code_base_sha": summary.get("code_base_sha"),
            "code_base_dirty": summary.get("code_base_dirty"),
            "cases_manifest_sha256": summary.get("cases_manifest_sha256"),
            "config_sha256": summary.get("config_sha256"),
            "declared_case_count": summary.get("declared_case_count"),
            "executed_case_count": summary.get("executed_case_count"),
            "all_prospectus_sha256_verified": summary.get("all_prospectus_sha256_verified"),
            "outcome_labels_accessed": summary.get("outcome_labels_accessed"),
            "blind_2025_y_accessed": summary.get("blind_2025_y_accessed"),
        },
        "triage_rule": TRIAGE_RULE,
        "cases": executed,
        "unexecuted_cases": unexecuted,
        "aggregate": aggregate,
        "limitations": _limitations(executed, aggregate),
    }


def _row(cells: Iterable[Any]) -> str:
    return "| " + " | ".join("—" if cell in (None, "") else str(cell) for cell in cells) + " |"


def render_batch_report(report: Mapping[str, Any]) -> str:
    """The same report as the reviewer-facing Markdown page."""

    matrix = report["matrix"]
    aggregate = report["aggregate"]
    lines = [
        "# 批量风险报告 — Batch risk report",
        "",
        f"- 运行配置 config: `{matrix.get('config')}`",
        f"- 代码版本 code_base_sha: `{matrix.get('code_base_sha') or '—'}`"
        + (" · **工作树有未提交改动**" if matrix.get("code_base_dirty") else ""),
        f"- 案例清单 cases_manifest_sha256: `{matrix.get('cases_manifest_sha256') or '—'}`"
        f" · config_sha256: `{matrix.get('config_sha256') or '—'}`",
        f"- 案例数: 声明 {matrix.get('declared_case_count')} · 实际执行 "
        f"{matrix.get('executed_case_count')}",
        f"- 招股书 SHA-256 全部符合冻结目录: "
        f"`{matrix.get('all_prospectus_sha256_verified')}`"
        f" · 读取上市后 outcome: `{matrix.get('outcome_labels_accessed')}`"
        f" · 触碰 2025 Blind: `{matrix.get('blind_2025_y_accessed')}`",
        "",
        "## 排查顺序 Triage order",
        "",
        f"> {report['triage_rule']}",
        "",
        _row(("#", "案例", "股票", "已验证风险", "critical/high/medium/low", "待复核", "冲突", "Final Supervisor", "可追溯", "Evidence", "截图")),
        _row(("---",) * 11),
    ]
    for index, case in enumerate(report["cases"], start=1):
        counts = case["verified_level_counts"]
        supervision = case["final_supervision"]
        verdict = (
            f"{supervision['outcome'] or '—'}"
            + (" · real provider" if supervision["real_provider_arbitration"] else "")
            + (" · deterministic fallback" if supervision["deterministic_fallback_used"] else "")
        )
        shots = case["screenshots"]
        shot_cell = (
            f"{shots['screenshot_count']}（精确 {shots['precise_localisation_count']}）"
            if shots["available"]
            else "未导出"
        )
        lines.append(
            _row(
                (
                    index,
                    f"{case['company_name'] or case['case_id']}<br>`{case['case_id']}`",
                    case["stock_code"],
                    case["verified_risk_count"],
                    f"{counts['critical']}/{counts['high']}/{counts['medium']}/{counts['low']}",
                    case["pending_risk_count"],
                    case["conflict_count"],
                    verdict,
                    case["traceability"],
                    case["evidence_row_count"],
                    shot_cell,
                )
            )
        )

    lines += ["", "## 逐案摘要 Per-case detail", ""]
    for case in report["cases"]:
        supervision = case["final_supervision"]
        lines += [
            f"### {case['company_name'] or case['case_id']} · {case['stock_code']}",
            "",
            f"- case_id `{case['case_id']}` · 上市日 `{case['listing_date']}` · 运行状态 "
            f"`{case['status']}`",
            f"- 招股书 SHA-256 `{case['prospectus_sha256'] or '—'}`",
        ]
        risk_lines = [
            f"- **{item['risk_code']}** · {item['level']} · agent `{item['agent_name']}` · "
            f"{item['evidence_count']} 条 Evidence"
            + ("（含确定性 Calculation）" if item["has_calculation"] else "")
            for item in case["verified_risk_codes"]
        ]
        lines += ["- 已验证风险："] + (
            [f"  {line}" for line in risk_lines]
            if risk_lines
            else ["  - 本次运行文档通道未提出正式风险；此处不代填。"]
        )
        if case["pending_risk_codes"]:
            lines.append(
                "- 待复核："
                + "、".join(
                    f"{item['risk_code']}（{item['level']}）" for item in case["pending_risk_codes"]
                )
            )
        lines += [
            f"- 通道状态：" + "、".join(
                f"`{channel}`={state}" for channel, state in sorted(case["channel_states"].items())
            ),
            f"- Final Supervisor：`{supervision['status']}` / `{supervision['outcome']}`"
            + (f" — {supervision['reason']}" if supervision["reason"] else "")
            + f"；确定性下限 `{supervision['deterministic_severity_floor']}`"
            + ("；Gate E1 satisfied" if supervision["gate_e1_satisfied"] else "；Gate E1 未满足")
            + ("；本次经过一次有界 scope 纠正" if supervision["scope_corrected"] else ""),
            f"- 冲突 {case['conflict_count']}（"
            + (
                "、".join(
                    f"{status} {count}" for status, count in sorted(case["conflict_statuses"].items())
                )
                or "无"
            )
            + f"）· 定向复核 {case['recheck_attempted']} 次 · 可追溯 {case['traceability']}",
            f"- 人工复核：{case['human_review']['review_count']} 条"
            + ("" if case["human_review"]["reviewed"] else "（未复核 ≠ 已认可）"),
            "",
        ]

    if report["unexecuted_cases"]:
        lines += ["## 未执行的案例", ""]
        for case in report["unexecuted_cases"]:
            lines.append(f"- `{case['case_id']}` · {case['status']} — {case['reason']}")
        lines.append("")

    lines += [
        "## 汇总 Aggregate",
        "",
        f"- 已验证风险合计 {aggregate['verified_risk_total']} 条（critical "
        f"{aggregate['verified_severity_totals']['critical']} · high "
        f"{aggregate['verified_severity_totals']['high']} · medium "
        f"{aggregate['verified_severity_totals']['medium']} · low "
        f"{aggregate['verified_severity_totals']['low']}）；待复核 "
        f"{aggregate['pending_risk_total']} 条",
        "- 跨案例风险码频次："
        + (
            "、".join(f"{code} ×{count}" for code, count in aggregate["risk_code_frequency"].items())
            or "无"
        ),
        f"- real-provider 仲裁 {aggregate['cases_with_real_provider_arbitration']}/"
        f"{aggregate['case_count']} · 确定性降级 {aggregate['cases_with_deterministic_fallback']} · "
        f"Gate E1 满足 {aggregate['cases_with_gate_e1_satisfied']}",
        f"- 可追溯率最低 {aggregate['minimum_traceability']} · 达到 1.0 的案例 "
        f"{aggregate['cases_at_full_traceability']}/{aggregate['case_count']}",
        f"- Evidence 行合计 {aggregate['evidence_row_total']} · 截图 "
        f"{aggregate['screenshot_total']}（精确定位 {aggregate['precise_localisation_total']}）",
        f"- 人工复核合计 {aggregate['human_review_total']} 条，覆盖 "
        f"{aggregate['cases_reviewed_by_a_human']}/{aggregate['case_count']} 个案例",
        "",
        "## 这份报告不支持什么 Limitations",
        "",
    ]
    lines.extend(f"- {note}" for note in report["limitations"])
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "BATCH_REPORT_SCHEMA_VERSION",
    "RISK_LEVELS",
    "TRIAGE_RULE",
    "build_batch_report",
    "render_batch_report",
]
