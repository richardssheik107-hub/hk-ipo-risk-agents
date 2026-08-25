from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from competition_ui import (  # noqa: E402
    available_market_observation_count,
    channel_state_map,
    domain_summary_rows,
    evidence_reference_count,
    executive_supervisor_view,
    localize_market_observation_rows,
    report_section_title,
    risk_display_name,
    risk_inventory_rows,
    roadmap_rows,
    stage_notice_zh,
    stage_summary_zh,
    stage_title_zh,
    status_label,
)


def _payload() -> dict[str, object]:
    return {
        "verified_risks": [
            {"evidence": [{"evidence_id": "e1"}, {"evidence_id": "e2"}]},
            {"evidence": []},
        ],
        "market_context": {
            "observations": [
                {"feature": "prior_ipo_count_30d", "value": 3, "availability": "available"},
                {"feature": "hsi_return_5d", "value": None, "availability": "missing", "missing_reason": "not_ready"},
                {"feature": "prior_ipo_return_5d", "value": 0.1, "availability": "available"},
            ]
        },
        "final_supervision": {
            "summary": "Document summary says 0 unresolved conflict(s).",
            "channel_states": [
                {"channel": "document", "status": "available"},
                {"channel": "market", "status": "available"},
                {"channel": "model", "status": "disabled"},
                {"channel": "rule", "status": "available"},
            ],
        },
        "domains": {
            "financial": {
                "risk_count": 1,
                "status": "completed",
                "status_counts": {"verified": 1},
                "risks": [
                    {
                        "risk_code": "cash_runway",
                        "level": "critical",
                        "score": 90,
                        "verification_status": "verified",
                        "evidence": [{"evidence_id": "e1"}, {"evidence_id": "e2"}],
                    }
                ],
            },
            "legal": {
                "risk_count": 0,
                "status": "no_risk_emitted",
                "status_counts": {},
                "risks": [],
            },
            "business": {
                "risk_count": 0,
                "status": "no_risk_emitted",
                "status_counts": {},
                "risks": [],
            },
        },
    }


def test_executive_helpers_only_derive_existing_payload_values() -> None:
    payload = _payload()

    assert evidence_reference_count(payload) == 2
    assert available_market_observation_count(payload) == (2, 3)
    assert channel_state_map(payload) == {
        "document": "available",
        "market": "available",
        "model": "disabled",
        "rule": "available",
    }


def test_executive_supervisor_view_keeps_document_summary_separate_from_competition_conflicts() -> None:
    payload = _payload()
    payload["component_diagnostics"] = {
        "final_supervision_llm": {
            "status": "unavailable",
            "reason": "LLM final supervision unavailable: LLMProviderError: LLM transport request failed",
            "judgement": None,
        },
        "conflict_detection": {
            "conflicts": [
                {"status": "partially_resolved"},
                {"status": "partially_resolved"},
                {"status": "unresolved"},
                {"status": "unresolved"},
                {"status": "unresolved"},
            ]
        },
    }

    view = executive_supervisor_view(payload)
    assert view["mode"] == "deterministic_fallback"
    assert view["title"] == "确定性 Document Supervisor 汇总"
    assert "0 unresolved" in view["body"]
    assert view["conflict_counts"] == {"partially_resolved": 2, "unresolved": 3}
    assert "transport request failed" in view["llm_reason"]


def test_executive_supervisor_view_prefers_available_llm_judgement() -> None:
    payload = _payload()
    payload["component_diagnostics"] = {
        "final_supervision_llm": {
            "status": "available",
            "reason": "grounded supervisory synthesis available",
            "judgement": {
                "final_explanation": "Grounded competition-wide explanation.",
                "overall_risk_rationale": "Fallback rationale.",
            },
        },
        "conflict_detection": {"conflicts": [{"status": "resolved"}]},
    }

    view = executive_supervisor_view(payload)
    assert view["mode"] == "llm"
    assert view["title"] == "LLM Final Supervisor 综合判断"
    assert view["body"] == "Grounded competition-wide explanation."
    assert view["conflict_counts"] == {"resolved": 1}


def test_workspace_inventory_localizes_display_without_changing_source_values() -> None:
    rows = risk_inventory_rows(_payload())
    assert rows == [
        {
            "领域": "财务风险",
            "风险项": "现金可支撑期",
            "风险代码": "cash_runway",
            "等级": "极高",
            "规则评分": 90,
            "验证状态": "已验证",
            "Evidence": 2,
        }
    ]
    assert risk_display_name("cash_runway") == "现金可支撑期"


def test_domain_summary_uses_natural_chinese_labels() -> None:
    rows = domain_summary_rows(_payload())
    assert [row["领域"] for row in rows] == ["财务风险", "法律与合规", "业务风险"]
    assert rows[0]["风险项"] == 1
    assert rows[0]["已验证"] == 1
    assert rows[1]["状态"] == "未识别到风险"
    assert rows[2]["风险项"] == 0


def test_market_rows_localize_common_headers_but_keep_feature_ids() -> None:
    rows = localize_market_observation_rows((_payload()["market_context"] or {})["observations"])
    assert rows[0]["指标"] == "prior_ipo_count_30d"
    assert rows[0]["可用状态"] == "可用"
    assert rows[1]["缺失原因"] == "not_ready"


def test_stage_and_report_copy_preserve_project_terms() -> None:
    stage = SimpleNamespace(
        stage_id="prediction",
        title="Prediction",
        status=SimpleNamespace(value="partial"),
        summary="raw summary",
        blocking_gate=None,
    )
    assert stage_title_zh(stage) == "风险预测"
    assert "PR-F" in stage_summary_zh(stage)
    assert "PR-F" in (stage_notice_zh(stage) or "")
    assert report_section_title(9, "fallback") == "Final Supervisor 综合结论"
    assert status_label("disabled") == "未启用"


def test_future_modules_are_explicitly_planned_and_have_no_fake_metrics() -> None:
    rows = roadmap_rows()
    assert [row["阶段"] for row in rows] == ["CH-1", "CH-2", "CH-3", "CH-4", "CH-5", "CH-6"]
    assert all(row["状态"] == "v0.4.3 后启动" for row in rows)
    assert all(set(row) == {"阶段", "模块", "状态", "目标"} for row in rows)
