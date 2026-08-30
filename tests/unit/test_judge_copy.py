from judge_copy import (
    highest_risk_level,
    judge_status_label,
    risk_reasoning,
    risk_reasoning_annotation,
    risk_review_focus,
    supervisor_narrative_zh,
    summarize_risks,
    to_simplified_ui,
)


def test_known_risk_copy_is_business_facing() -> None:
    assert "客户" in risk_reasoning("customer_concentration")
    assert "合同" in risk_review_focus("customer_concentration")


def test_unknown_risk_copy_fails_safe_to_generic_explanation() -> None:
    assert "受治理" in risk_reasoning("future_unknown_risk")
    assert "复核" in risk_review_focus("future_unknown_risk")


def test_summary_is_presentation_only_counting() -> None:
    risks = [
        {"level": "high", "verification_status": "verified", "evidence": [{}, {}]},
        {"level": "medium", "verification_status": "needs_review", "evidence": [{}]},
    ]
    assert summarize_risks(risks) == {
        "total": 2,
        "high_or_critical": 1,
        "medium": 1,
        "verified": 1,
        "needs_review": 1,
        "evidence_count": 3,
        "highest_level": "high",
    }
    assert highest_risk_level(risks) == "high"


def test_non_evidence_ui_copy_is_simplified() -> None:
    assert to_simplified_ui("風險審閱與證據鏈") == "风险审阅与证据链"
    assert judge_status_label("needs_review") == "待复核"


def test_evidence_text_is_not_implicitly_converted() -> None:
    evidence = "本公司於香港聯交所上市。"
    # 原文只能由证据视图直接展示；转换函数不会自动遍历或修改载荷。
    payload = {"text": evidence}
    assert payload["text"] == evidence


def test_risk_reasoning_annotation_explains_basis_impact_and_review_boundary() -> None:
    annotation = risk_reasoning_annotation(
        {
            "risk_code": "customer_concentration",
            "verification_status": "needs_review",
            "verification_notes": "Calculation is missing.",
            "evidence": [{"page": 10}, {"page": 12}],
        }
    )

    assert "2 条" in annotation["basis"]
    assert "待复核" in annotation["basis"]
    assert "客户" in annotation["impact"]
    assert "缺少可复算的确定性计算" in annotation["boundary"]
    assert "合同稳定性" in annotation["review_focus"]


def test_supervisor_narrative_is_long_form_but_keeps_model_boundary() -> None:
    payload = {
        "domains": {
            "financial": {
                "risks": [
                    {
                        "risk_code": "customer_concentration",
                        "level": "medium",
                        "verification_status": "needs_review",
                        "evidence": [{"page": 10}],
                    }
                ]
            }
        },
        "market_context": {
            "observations": [
                {"availability": "available"},
                {"availability": "unavailable"},
            ]
        },
        "final_supervision": {
            "channel_states": [{"channel": "model", "status": "available"}]
        },
        "component_diagnostics": {
            "final_supervision_llm": {
                "status": "available",
                "outcome": "accepted",
                "fail_closed": False,
                "scope_check": {"status": "passed"},
                "judgement": {"overall_risk": "medium"},
            },
            "conflict_detection": {
                "conflicts": [{"status": "unresolved"}]
            }
        },
    }

    narrative = supervisor_narrative_zh(payload)

    assert "综合审阅结论为中风险" in narrative
    assert "规则筛选参考为暂不可用风险" in narrative
    assert "招股书风险的具体依据如下" in narrative
    assert "待复核状态" in narrative
    assert "1/2 项 Market-X 核心观测" in narrative
    assert "未经概率校准" in narrative
    assert "未解决的分歧" in narrative
    assert "建议后续复核" in narrative
    assert "。；" not in narrative


def test_verified_risk_annotation_does_not_claim_verification_is_incomplete() -> None:
    annotation = risk_reasoning_annotation(
        {
            "risk_code": "cash_runway",
            "verification_status": "verified",
            "verification_notes": "legacy verifier note",
            "evidence": [{"page": 20}],
        }
    )

    assert "已通过当前验证规则" in annotation["basis"]
    assert "已验证仅表示" in annotation["boundary"]
    assert "尚未完成最终验证" not in annotation["boundary"]


def test_pending_risk_annotation_never_says_there_is_no_boundary() -> None:
    annotation = risk_reasoning_annotation(
        {
            "risk_code": "customer_concentration",
            "verification_status": "needs_review",
            "verification_notes": "",
            "evidence": [{"page": 7}],
        }
    )

    assert "仍未完全闭合" in annotation["boundary"]


def test_supervisor_narrative_excludes_rejected_candidates_from_formal_risks() -> None:
    payload = {
        "domains": {
            "financial": {
                "risks": [
                    {
                        "risk_code": "cash_runway",
                        "level": "critical",
                        "verification_status": "rejected",
                        "evidence": [{"page": 2}],
                    }
                ]
            }
        },
        "prediction": {"risk_level": "low"},
    }

    narrative = supervisor_narrative_zh(payload)

    assert "没有风险事项进入审阅范围" in narrative
    assert "其中 1 项为高或极高风险" not in narrative
    assert "不等同于发行人不存在风险" in narrative
