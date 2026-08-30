"""The reader workspace and the technical backend stay separate in Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
SRC_DIR = REPO_ROOT / "src"
APP_PATH = APP_DIR / "streamlit_app.py"
DEMO_BUNDLE = REPO_ROOT / "reports" / "v045_demo_bundle"

for source_dir in (APP_DIR, SRC_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from ipo_risk.services.analysis_service import IPOAnalysisService  # noqa: E402


def _run_app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.chdir(REPO_ROOT)
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    assert not app.exception
    return app


def _tab_labels(app: AppTest) -> list[str]:
    return [tab.label for tab in app.tabs]


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def _tab(app: AppTest, label: str):
    return next(tab for tab in app.tabs if tab.label == label)


def _markdown_text(container) -> str:
    return "\n".join(str(block.value) for block in container.markdown)


def test_primary_navigation_has_four_reader_or_admin_destinations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)

    navigation = app.segmented_control[0]
    assert list(navigation.options) == ["首页", "新建分析", "案例工作台", "后台"]
    assert navigation.value == "首页"
    assert "运行与回放" not in _tab_labels(app)
    assert not app.selectbox
    assert not app.json


def test_new_session_defaults_to_latest_competition_ai_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)

    assert app.session_state["runtime_scenario"] == "v0.4.5 比赛版（AI）"

    app.segmented_control[0].set_value("后台").run()
    runtime_picker = next(widget for widget in app.selectbox if widget.label == "运行模式")
    assert runtime_picker.value == "v0.4.5 比赛版（AI）"


@pytest.mark.skipif(not DEMO_BUNDLE.is_dir(), reason="canonical replay bundle is unavailable")
def test_replay_moves_to_reader_workspace_without_leaking_backend_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)

    app.segmented_control[0].set_value("后台").run()
    assert not app.exception
    assert "运行与回放" in _tab_labels(app)
    assert any(widget.label == "运行模式" for widget in app.selectbox)
    assert any(button.label == "载入回放" for button in app.button)

    _button(app, "载入回放").click().run()
    assert not app.exception
    assert app.segmented_control[0].value == "案例工作台"
    assert "analysis_result" in app.session_state

    reader_tabs = _tab_labels(app)
    for label in ("案例概览", "原文证据", "市场与模型", "综合结论与报告"):
        assert label in reader_tabs
    for backend_label in ("运行与回放", "数据审计", "轨迹与冲突", "复核与产物", "系统诊断"):
        assert backend_label not in reader_tabs
    assert not any(widget.label == "运行模式" for widget in app.selectbox)
    assert not any(button.label == "载入回放" for button in app.button)
    assert not any(button.label == "下载结构化 JSON" for button in app.get("download_button"))
    assert not app.json

    market_model_tab = _tab(app, "市场与模型")
    market_model_copy = _markdown_text(market_model_tab)
    assert "市场与模型解读" in market_model_copy
    assert "未经概率校准" in market_model_copy
    assert "不能理解为风险发生概率" in market_model_copy
    assert not market_model_tab.metric
    assert not market_model_tab.dataframe
    for machine_detail in ("模型评分", "规则评分", "SHAP"):
        assert machine_detail not in market_model_copy

    evidence_copy = _markdown_text(_tab(app, "原文证据"))
    for reasoning_label in ("推理注释", "形成依据", "判断边界", "复核重点"):
        assert reasoning_label in evidence_copy

    # Native navigation reruns the script without dropping the governed result.
    app.segmented_control[0].set_value("后台").run()
    assert not app.exception
    assert "analysis_result" in app.session_state
    assert "运行与回放" in _tab_labels(app)
    assert any(button.label == "下载结构化 JSON" for button in app.get("download_button"))
    assert app.json

    data_audit_tab = _tab(app, "数据审计")
    audit_metrics = {metric.label: metric.value for metric in data_audit_tab.metric}
    assert "模型评分" in audit_metrics
    assert "规则评分" in audit_metrics
    assert "主要驱动因素（SHAP）" in _markdown_text(data_audit_tab)
    assert data_audit_tab.dataframe


def test_successful_no_pdf_run_clears_an_older_case_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)
    app.session_state["prospectus_bytes"] = b"old-case-pdf"

    app.segmented_control[0].set_value("后台").run()
    runtime_picker = next(widget for widget in app.selectbox if widget.label == "运行模式")
    runtime_picker.set_value("Mock 架构演示").run()
    app.segmented_control[0].set_value("新建分析").run()
    _button(app, "开始分析").click().run()

    assert not app.exception
    assert app.segmented_control[0].value == "案例工作台"
    assert "analysis_result" in app.session_state
    assert "prospectus_bytes" not in app.session_state


@pytest.mark.skipif(not DEMO_BUNDLE.is_dir(), reason="canonical replay bundle is unavailable")
def test_failed_pdf_run_keeps_the_previous_result_and_its_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)
    app.segmented_control[0].set_value("后台").run()
    _button(app, "载入回放").click().run()
    previous_result = app.session_state["analysis_result"]
    previous_pdf = b"previous-case-pdf"
    app.session_state["prospectus_bytes"] = previous_pdf

    def fail_analysis(*_args, **_kwargs):
        raise RuntimeError("controlled test failure")

    monkeypatch.setattr(IPOAnalysisService, "analyze", fail_analysis)
    app.segmented_control[0].set_value("新建分析").run()
    uploader = app.get("file_uploader")[0]
    uploader.upload("new-case.pdf", b"%PDF-1.4\n%%EOF", "application/pdf").run()
    _button(app, "开始分析").click().run()

    assert not app.exception
    assert app.session_state["analysis_result"].analysis_id == previous_result.analysis_id
    assert app.session_state["prospectus_bytes"] == previous_pdf
    assert any("controlled test failure" in item.value for item in app.error)
