"""Human Review console: reviewer verdicts kept beside, never inside, the machine's.

A decision recorded here is written to its own reviewer sidecar keyed by
``analysis_id``.  The machine result file is not touched, and the console shows
both verdicts side by side so an auditor can always see what the system said and
what a person decided about it.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from competition_runtime_view import machine_vs_human_rows, review_targets
from ipo_risk.services.human_review_service import HumanReviewService, HumanReviewStoreError
from ipo_risk.schemas.competition_runtime import HumanReviewDecision

DECISION_LABELS = {
    HumanReviewDecision.ACCEPT: "接受（Accept）",
    HumanReviewDecision.REJECT: "驳回（Reject）",
    HumanReviewDecision.NEEDS_FOLLOW_UP: "需继续跟进（Needs Follow-up）",
}

def render_human_review(
    payload: dict[str, Any],
    *,
    analysis_id: str,
    case_id: str,
    run_id: str,
    service: HumanReviewService,
) -> None:
    st.markdown("### 人机复核")
    st.caption(
        "人工结论与机器结论分开存储：本页写入的是独立的 reviewer sidecar，"
        "不会修改任何 RiskItem、Evidence 或分析结果文件。"
    )

    targets = review_targets(payload)
    if not targets:
        st.info("本次运行没有可供复核的风险项或未解决冲突。")
        return

    try:
        latest = service.latest_by_target(analysis_id)
        history = service.history(analysis_id)
    except HumanReviewStoreError as exc:
        st.error(f"读取复核记录失败：{exc}")
        latest, history = {}, []

    labels = {
        target["target_id"]: f"[{target['kind']}] {target['title']} · 机器结论 {target['machine_status']}"
        for target in targets
    }
    with st.form("human_review"):
        target_id = st.selectbox(
            "复核对象", [target["target_id"] for target in targets], format_func=lambda key: labels[key]
        )
        target = next(item for item in targets if item["target_id"] == target_id)
        st.caption(target["detail"] or "该对象没有额外说明。")
        decision = st.radio(
            "复核结论",
            list(HumanReviewDecision),
            format_func=lambda value: DECISION_LABELS[value],
            horizontal=True,
        )
        reviewer_id = st.text_input("复核人标识", value=st.session_state.get("reviewer_id", ""))
        note = st.text_area("复核备注", placeholder="写明依据；备注只进入人工记录，不改写机器结论。")
        evidence_ids = target.get("evidence_ids") or []
        evidence_id = None
        if evidence_ids:
            evidence_id = st.selectbox(
                "关联 Evidence（可选）", ["（不指定）", *evidence_ids]
            )
            evidence_id = None if evidence_id == "（不指定）" else evidence_id
        submitted = st.form_submit_button("提交复核结论", type="primary", use_container_width=True)

    if submitted:
        if not reviewer_id.strip():
            st.error("请填写复核人标识；无署名的复核结论不予记录。")
        else:
            st.session_state["reviewer_id"] = reviewer_id.strip()
            try:
                service.record(
                    analysis_id=analysis_id,
                    case_id=case_id,
                    run_id=run_id,
                    target_id=target_id,
                    original_machine_status=target["machine_status"],
                    decision=decision,
                    reviewer_id=reviewer_id,
                    reviewer_note=note,
                    evidence_id=evidence_id,
                )
            except HumanReviewStoreError as exc:
                st.error(f"复核结论写入失败：{exc}")
            else:
                st.success("复核结论已写入独立的人工复核记录。")
                st.rerun()

    st.markdown("#### 机器结论 vs 人工结论")
    st.dataframe(machine_vs_human_rows(payload, latest), hide_index=True, use_container_width=True)

    with st.expander(f"人工复核历史 · {len(history)} 条", expanded=False):
        if history:
            st.json([review.model_dump(mode="json") for review in history])
        else:
            st.write("本次分析尚无人工复核记录。")
