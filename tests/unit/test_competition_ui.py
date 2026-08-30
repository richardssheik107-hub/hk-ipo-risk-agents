from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import competition_ui as competition_ui_module  # noqa: E402
from competition_ui import (  # noqa: E402
    available_market_observation_count,
    channel_state_map,
    domain_summary_rows,
    evidence_reference_count,
    executive_supervisor_view,
    localize_market_observation_rows,
    market_degradation_summary,
    market_missing_reason_label,
    market_runtime_summary,
    reader_markdown_report,
    report_section_title,
    risk_display_name,
    risk_inventory_rows,
    roadmap_rows,
    stage_notice_zh,
    stage_status_label,
    stage_summary_zh,
    stage_title_zh,
    status_label,
)


def test_theme_localizes_visible_file_uploader_copy(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _capture(body: str, *, unsafe_allow_html: bool = False) -> None:
        captured["body"] = body
        captured["unsafe_allow_html"] = unsafe_allow_html

    monkeypatch.setattr(competition_ui_module.st, "markdown", _capture)
    competition_ui_module.apply_competition_theme()

    css = str(captured["body"])
    assert 'content:"选择文件"' in css
    assert 'content:"单个文件不超过 200 MB · PDF"' in css
    assert 'content:"已就绪"' in css
    assert 'content:"Ready"' not in css
    assert captured["unsafe_allow_html"] is True


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
    assert "本次共识别 1 项正式风险" in view["body"]
    assert "unresolved" not in view["body"]
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
    assert "本次共识别 1 项正式风险" in view["body"]
    assert "Grounded competition-wide explanation." not in view["body"]
    assert view["conflict_counts"] == {"resolved": 1}


def test_reader_report_is_chinese_and_excludes_backend_metadata() -> None:
    payload = _payload()
    payload["profile"] = {
        "company_name": "示例公司",
        "stock_code": "0001.HK",
        "listing_date": "2024-01-01",
        "industry": "消费",
    }
    payload["prediction"] = {"risk_score": 42, "risk_level": "medium"}
    risk = payload["domains"]["financial"]["risks"][0]
    risk["evidence"] = [{"evidence_id": "internal-e1", "page": 7, "text": "引用原文"}]
    risk["metadata"] = {"prospectus_sha256": "secret-technical-hash"}

    report = reader_markdown_report(payload)

    assert report.startswith("# 示例公司港股 IPO 风险分析报告")
    assert "引用原文" in report
    assert "结构化字段" not in report
    assert "Structured section metadata" not in report
    assert "component_diagnostics" not in report
    assert "prospectus_sha256" not in report
    assert "secret-technical-hash" not in report
    assert "internal-e1" not in report


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
    assert status_label("completed_with_real_llm") == "真实 LLM 完成"
    assert status_label("completed_with_partial_llm") == "部分 LLM 完成"
    assert status_label("completed_with_deterministic_fallback") == "确定性降级完成"


def test_future_modules_are_explicitly_planned_and_have_no_fake_metrics() -> None:
    rows = roadmap_rows()
    assert [row["阶段"] for row in rows] == ["CH-1", "CH-2", "CH-3", "CH-4", "CH-5", "CH-6"]
    assert all(row["状态"] == "v0.4.3 后启动" for row in rows)
    assert all(set(row) == {"阶段", "模块", "状态", "目标"} for row in rows)


def _market_payload(provenance: dict[str, object]) -> dict[str, object]:
    return {"market_context": {"status": "available", "provenance": provenance}}


def test_market_runtime_summary_names_the_dynamic_recomputation() -> None:
    """"Available 15/15" reads identically for a frozen read and a rebuild."""

    rows = market_runtime_summary(_market_payload({
        "runtime_path": "dynamic_pit",
        "pit_cutoff_date": "2025-02-12",
        "dataset_split": "blind",
        "identity_source": "official_bridge_case_id",
        "prior_ipo_universe_size": 446,
        "outcome_history_available": True,
        "extended_status": "not_configured",
    }))
    by_label = {row["项目"]: row["取值"] for row in rows}
    assert by_label["运行路径"] == "动态 PIT 重算"
    assert by_label["PIT 截止时点"] == "2025-02-12"
    assert by_label["数据集划分"] == "盲测集"
    assert by_label["前序 IPO 样本量"] == 446
    assert by_label["Extended 市场环境"] == "未配置"


def test_market_runtime_summary_keeps_the_frozen_path_free_of_dynamic_fields() -> None:
    rows = market_runtime_summary(_market_payload({
        "runtime_path": "frozen",
        "listing_date": "2024-08-20",
        "dataset_split": "validation",
    }))
    by_label = {row["项目"]: row["取值"] for row in rows}
    assert by_label["运行路径"] == "冻结 PR-B 产物"
    assert by_label["PIT 截止时点"] == "2024-08-20"
    for dynamic_only in ("身份解析", "前序 IPO 样本量", "前序结果数据层"):
        assert dynamic_only not in by_label


def test_market_runtime_summary_states_an_unconfigured_outcome_tier() -> None:
    """Missing because the source is absent is not missing because zero."""

    rows = market_runtime_summary(_market_payload({
        "runtime_path": "dynamic_pit",
        "outcome_history_available": False,
    }))
    by_label = {row["项目"]: row["取值"] for row in rows}
    assert "不补零" in str(by_label["前序结果数据层"])


def test_market_runtime_summary_invents_nothing_without_provenance() -> None:
    assert market_runtime_summary({}) == []
    assert market_runtime_summary({"market_context": {"status": "available"}}) == []
    # A provenance that claims only a runtime path yields only that row.
    rows = market_runtime_summary(_market_payload({"runtime_path": "dynamic_pit"}))
    assert [row["项目"] for row in rows] == ["运行路径"]


def test_market_degradation_summary_explains_a_governed_boundary_in_words() -> None:
    """"Unavailable" alone reads as a broken pipeline; a boundary is not that."""

    payload = {"market_context": {"observations": [
        {"availability": "unavailable",
         "missing_reason": "prior_ipo_universe_right_boundary_incomplete"}
    ] * 15}}
    text = market_degradation_summary(payload)
    assert "语料覆盖终点" in text
    assert "15/15 项" in text
    # The machine-readable code survives alongside the explanation.
    assert "prior_ipo_universe_right_boundary_incomplete" in text


def test_market_degradation_summary_is_silent_when_everything_is_available() -> None:
    payload = {"market_context": {"observations": [
        {"availability": "available", "value": 1.0}
    ]}}
    assert market_degradation_summary(payload) == ""
    assert market_degradation_summary({}) == ""


def test_market_degradation_summary_ranks_reasons_by_how_many_they_explain() -> None:
    payload = {"market_context": {"observations": [
        {"availability": "unavailable", "missing_reason": "missing_industry_classification"},
        {"availability": "unavailable", "missing_reason": "prior_ipo_outcome_source_not_configured"},
        {"availability": "unavailable", "missing_reason": "prior_ipo_outcome_source_not_configured"},
        {"availability": "available", "value": 2.0},
    ]}}
    text = market_degradation_summary(payload)
    assert text.index("未配置前序 IPO 结果数据层") < text.index("缺少行业分类")
    assert "2/4 项" in text and "1/4 项" in text


def test_an_unmapped_reason_code_is_shown_verbatim_not_smoothed_away() -> None:
    """An unrecognised reason is itself information and must not be hidden."""

    assert market_missing_reason_label("a_brand_new_code") == "a_brand_new_code"
    assert market_missing_reason_label("") == ""


def test_observation_rows_localize_the_reason_while_keeping_the_code() -> None:
    rows = localize_market_observation_rows([
        {"name": "same_industry_ipo_count_180d", "availability": "unavailable",
         "missing_reason": "missing_industry_classification"}
    ])
    assert rows[0]["指标"] == "same_industry_ipo_count_180d"
    assert "缺少行业分类" in str(rows[0]["缺失原因"])
    assert "missing_industry_classification" in str(rows[0]["缺失原因"])


class _FakeMetric:
    def __init__(self, label: str, value: object) -> None:
        self.label = label
        self.value = value


class _FakeStage:
    def __init__(self, status: str, metrics: tuple[_FakeMetric, ...], summary: str = "") -> None:
        self.stage_id = "market_features"
        self.status = status
        self.metrics = metrics
        self.summary = summary


def test_a_completed_stage_never_claims_market_data_it_did_not_get() -> None:
    """StageStatus.COMPLETED serializes to "available"; the channel had none."""

    stage = _FakeStage("available", (
        _FakeMetric("Observations available", "0 of 15"),
        _FakeMetric("Market channel", "unavailable"),
    ))
    text = stage_summary_zh(stage)
    assert "未取得任何可用观测（0/15）" in text
    assert "提供可用市场观测" not in text


def test_a_partially_available_market_stage_states_the_real_count() -> None:
    stage = _FakeStage("available", (
        _FakeMetric("Observations available", "7 of 15"),
        _FakeMetric("Market channel", "available"),
    ))
    assert "7/15 项可用观测" in stage_summary_zh(stage)


def test_a_fully_available_market_stage_keeps_the_existing_copy() -> None:
    stage = _FakeStage("available", (
        _FakeMetric("Observations available", "15 of 15"),
        _FakeMetric("Market channel", "available"),
    ))
    assert stage_summary_zh(stage) == (
        "当前案例已经接入受治理的上市前 Market-X，并按 PIT 口径提供可用市场观测。"
    )


def test_stage_status_words_do_not_borrow_the_channel_vocabulary() -> None:
    """A stage that ran is 已完成; only data can be 可用."""

    assert stage_status_label(_FakeStage("available", ())) == "已完成"
    assert stage_status_label(_FakeStage("partial", ())) == "部分完成"
    assert status_label("available") == "可用"
