"""Pure read-only projections of the E-lane competition runtime.

Every function here reads what the service already produced and reshapes it for
display.  None of them recompute a status, re-derive a risk level, or fill in a
missing value: an absent channel stays absent and an unresolved conflict stays
unresolved, because the UI is not allowed to repair backend facts.

Keeping these pure also keeps them testable without Streamlit.
"""

from __future__ import annotations

from typing import Any

from competition_ui import risk_level_label
from ipo_risk.runtime.review_projection import (
    conflicts,
    review_targets as _review_targets,
)

RESOLUTION_LABELS = {
    "detected": "已检出",
    "rechecking": "复核中",
    "resolved": "已解决",
    "partially_resolved": "部分解决",
    "unresolved": "未解决",
}

EVENT_TYPE_LABELS = {
    "parser": "解析",
    "retriever": "检索",
    "agent": "Agent",
    "skill": "Skill",
    "llm": "LLM",
    "verifier": "Verifier",
    "market": "市场",
    "model": "模型",
    "conflict": "冲突",
    "recheck": "定向复核",
    "supervisor": "Supervisor",
    "human_review": "人工复核",
}


def _diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("component_diagnostics") or {}


def competition_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    return _diagnostics(payload).get("competition_runtime") or {}


def sidecar(payload: dict[str, Any]) -> dict[str, Any]:
    return competition_runtime(payload).get("sidecar") or {}


def traceability(payload: dict[str, Any]) -> dict[str, Any]:
    return competition_runtime(payload).get("traceability") or {}


def supervision_synthesis(payload: dict[str, Any]) -> dict[str, Any]:
    return _diagnostics(payload).get("final_supervision_llm") or {}


def judgement(payload: dict[str, Any]) -> dict[str, Any] | None:
    return supervision_synthesis(payload).get("judgement")


def recheck_outcomes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list((_diagnostics(payload).get("targeted_recheck") or {}).get("outcomes") or [])


def conflict_short_name(conflict: dict[str, Any]) -> str:
    """``conflict:{run_id}:{rule}:{discriminator}`` -> ``rule · discriminator``."""

    parts = str(conflict.get("conflict_id", "")).split(":", 3)
    if len(parts) == 4:
        return f"{parts[2]} · {parts[3]}"
    return str(conflict.get("conflict_id", ""))


def _conflict_summary_zh(conflict: dict[str, Any]) -> str:
    conflict_id = str(conflict.get("conflict_id") or "")
    if "agent_verifier_disagreement" in conflict_id:
        return "智能体提出了风险项，但验证器将其保留为待复核，风险判断与验证状态尚未完全一致。"
    if "unresolved_agent_claim" in conflict_id:
        return "智能体检索到相关原文证据，但尚未映射为可验证的结构化事实，文档通道暂未形成对应风险。"
    if "document_model_divergence" in conflict_id:
        return "冻结模型的主要驱动方向与招股书通道的风险判断不一致；模型分数未经校准，该分歧被保留。"
    return "该跨通道冲突已被系统保留，需结合参与方输出进一步复核。"


def _resolution_note_zh(conflict: dict[str, Any], outcome: dict[str, Any]) -> str:
    conflict_id = str(conflict.get("conflict_id") or "")
    new_count = len(outcome.get("new_evidence_ids") or [])
    if "document_model_divergence" in conflict_id:
        return "该冲突跨越招股书与模型通道，无法仅通过文档重新检索解决，继续保留至 Final Supervisor。"
    if new_count:
        return f"定向重新检索新增 {new_count} 条范围内证据；尚未解决的部分继续进入人工复核。"
    return "本轮未取得可改变结论的新依据，冲突按原状态保留。"


def conflict_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    """One display row per detected conflict, with its re-check result attached."""

    outcomes = {item["conflict_id"]: item for item in recheck_outcomes(payload)}
    rows = []
    for conflict in conflicts(payload):
        outcome = outcomes.get(conflict["conflict_id"], {})
        rows.append(
            {
                "冲突": conflict_short_name(conflict),
                "参与方": " ↔ ".join(conflict.get("involved_agents", [])),
                "状态": RESOLUTION_LABELS.get(conflict.get("status", ""), conflict.get("status", "")),
                "定向复核": "已执行" if outcome else "未执行（受控预算）",
                "新增原文证据": len(outcome.get("new_evidence_ids", [])),
                "说明": _conflict_summary_zh(conflict),
                "复核结论": _resolution_note_zh(conflict, outcome),
            }
        )
    return rows


def conflict_status_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for conflict in conflicts(payload):
        status = conflict.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    return counts


def trace_rows(payload: dict[str, Any]) -> list[dict[str, object]]:
    """One display row per trace event, in the order the sidecar recorded them."""

    rows = []
    for index, event in enumerate(sidecar(payload).get("trace_events") or [], start=1):
        details = event.get("details") or {}
        rows.append(
            {
                "#": index,
                "类型": EVENT_TYPE_LABELS.get(event.get("event_type", ""), event.get("event_type", "")),
                "智能体": event.get("agent_name") or "",
                "动作": event.get("action") or "",
                "工具 / 技能": event.get("tool_or_skill") or "",
                "状态": event.get("status") or "",
                "模型服务方": event.get("provider_name") or "",
                "模型": event.get("model_name") or "",
                "提示词版本": event.get("prompt_version") or "",
                "原文证据": len(event.get("evidence_ids") or []),
                "计算依据": len(event.get("calculation_ids") or []),
                "延迟(ms)": event.get("latency_ms"),
                "无原文证据原因": details.get("no_evidence_reason") or "",
            }
        )
    return rows


def traceability_metrics(payload: dict[str, Any]) -> list[dict[str, object]]:
    report = traceability(payload)
    if not report:
        return []
    return [
        {"指标": "智能体可追溯率", "值": report.get("agent_traceability"),
         "计数": f"{report.get('agent_identified_count')}/{report.get('event_count')}"},
        {"指标": "工具 / 技能可追溯率", "值": report.get("tool_traceability"),
         "计数": f"{report.get('tool_identified_count')}/{report.get('event_count')}"},
        {"指标": "原文证据说明率", "值": report.get("evidence_traceability"),
         "计数": f"{report.get('evidence_accounted_count')}/{report.get('event_count')}"},
        {"指标": "原文证据引用可解析率", "值": (
            1.0 if not report.get("referenced_evidence_count")
            else round(report.get("resolved_evidence_count", 0) / report["referenced_evidence_count"], 6)
        ),
         "计数": f"{report.get('resolved_evidence_count')}/{report.get('referenced_evidence_count')}"},
        {"指标": "综合可追溯率", "值": report.get("overall_traceability"), "计数": ""},
    ]


def evidence_catalog(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Every Evidence item attached to a risk, with its owning risk context.

    Ordering is by page then evidence id, so the viewer walks the document in
    reading order rather than in whatever order the agents happened to run.
    """

    catalog: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        for risk in payload.get(bucket) or []:
            for evidence in risk.get("evidence") or []:
                key = (risk["risk_id"], evidence["evidence_id"])
                if key in seen:
                    continue
                seen.add(key)
                catalog.append(
                    {
                        "evidence_id": evidence["evidence_id"],
                        "page": evidence.get("page"),
                        "bbox": evidence.get("bbox"),
                        "section": evidence.get("section") or "",
                        "text": evidence.get("text") or "",
                        "source_type": evidence.get("source_type") or "",
                        "relevance_score": evidence.get("relevance_score"),
                        # Retrieval metadata travels with the item: the viewer
                        # localises the cited text with the same inputs the
                        # screenshot export uses, so both draw the same box.
                        "evidence_metadata": evidence.get("metadata") or {},
                        "risk_id": risk["risk_id"],
                        "risk_code": risk.get("risk_code", ""),
                        "risk_level": risk.get("level", ""),
                        "risk_category": risk.get("category", ""),
                        "risk_conclusion": risk.get("conclusion", ""),
                        "agent_name": risk.get("agent_name", ""),
                        "verification_status": risk.get("verification_status", ""),
                        "verification_notes": risk.get("verification_notes", ""),
                        "calculation": risk.get("calculation"),
                        "risk_metadata": risk.get("metadata") or {},
                    }
                )
    catalog.sort(key=lambda item: (item["page"] if item["page"] is not None else 10**6, item["evidence_id"]))
    return catalog


def evidence_label(item: dict[str, Any]) -> str:
    page = item.get("page")
    page_text = f"第 {page} 页" if page else "页码不可用"
    return f"{item.get('risk_code', '')} · {page_text} · {item['evidence_id'][:8]}"


# The neutral ``kind`` the domain projection reports, in reviewer-facing Chinese.
TARGET_KIND_LABELS = {
    "verified_risk": "已验证风险",
    "pending_risk": "待复核风险",
    "rejected_risk": "已驳回风险",
}


def review_targets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Everything a reviewer may rule on, labelled for the console.

    Which items are reviewable is decided once, in
    ``ipo_risk.runtime.review_projection``, and shared with the review API.
    This wrapper only adds display strings, so the two surfaces can never
    disagree about what was open for review.
    """

    labelled: list[dict[str, Any]] = []
    for target in _review_targets(payload):
        if target["kind"] == "conflict":
            kind = f"冲突 · {RESOLUTION_LABELS.get(target['machine_status'], target['machine_status'])}"
            title = " ↔ ".join(target["involved_agents"])
        else:
            kind = TARGET_KIND_LABELS[target["kind"]]
            title = f"{target['risk_code']} · {risk_level_label(target['risk_level'])}"
        labelled.append(
            {
                "target_id": target["target_id"],
                "kind": kind,
                "title": title,
                "machine_status": target["machine_status"],
                "detail": target["detail"],
                "evidence_ids": target["evidence_ids"],
            }
        )
    return labelled


def machine_vs_human_rows(
    payload: dict[str, Any], reviews_by_target: dict[str, Any]
) -> list[dict[str, object]]:
    """Side-by-side machine and human verdicts; the two are never merged."""

    rows = []
    for target in review_targets(payload):
        review = reviews_by_target.get(target["target_id"])
        rows.append(
            {
                "对象": target["title"],
                "类别": target["kind"],
                "机器结论": target["machine_status"],
                "人工结论": review.decision.value if review is not None else "未复核",
                "复核后状态": review.post_review_status if review is not None else "",
                "复核人": review.reviewer_id if review is not None else "",
                "备注": review.reviewer_note if review is not None else "",
            }
        )
    return rows
