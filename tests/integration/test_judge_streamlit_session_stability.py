"""Session bundles in the judge entrypoint fail closed and replace atomically."""

from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import sys

import pytest
from streamlit.testing.v1 import AppTest


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = REPO_ROOT / "app"
SRC_DIR = REPO_ROOT / "src"
APP_PATH = APP_DIR / "judge_streamlit_app.py"
DEMO_BUNDLE = REPO_ROOT / "reports" / "v045_demo_bundle"

for source_dir in (APP_DIR, SRC_DIR):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from ipo_risk.runtime.demo_replay import load_recorded_case  # noqa: E402
from ipo_risk.schemas import IPOAnalysisResult, TaskStatus  # noqa: E402
from ipo_risk.services.analysis_service import IPOAnalysisService  # noqa: E402


@lru_cache(maxsize=1)
def _canonical_result() -> IPOAnalysisResult:
    recorded = load_recorded_case(DEMO_BUNDLE / "ipo_2024_01318")
    return IPOAnalysisResult.model_validate(recorded.result)


def _run_app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.chdir(REPO_ROOT)
    app = AppTest.from_file(str(APP_PATH), default_timeout=60).run()
    assert not app.exception
    return app


def _button(app: AppTest, label: str):
    return next(button for button in app.button if button.label == label)


def _tab(app: AppTest, label: str):
    return next(tab for tab in app.tabs if tab.label == label)


def _markdown_text(container) -> str:
    return "\n".join(str(block.value) for block in container.markdown)


@pytest.mark.skipif(not DEMO_BUNDLE.is_dir(), reason="canonical replay bundle is unavailable")
def test_failed_result_preserves_the_previous_judge_case_and_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    good_result = _canonical_result()
    monkeypatch.setattr(
        IPOAnalysisService,
        "analyze",
        lambda *_args, **_kwargs: good_result,
    )
    app = _run_app(monkeypatch)
    first_pdf = b"%PDF-1.4\nfirst-case\n%%EOF"
    app.get("file_uploader")[0].upload(
        "first.pdf", first_pdf, "application/pdf"
    ).run()
    _button(app, "开始风险研判").click().run()

    assert not app.exception
    assert app.session_state["judge_result"].analysis_id == good_result.analysis_id
    assert app.session_state["judge_prospectus_bytes"] == first_pdf
    fingerprint = dict(app.session_state["judge_result_fingerprint"])
    assert fingerprint["scenario"] == "比赛演示（离线，可复现）"

    failed_result = good_result.model_copy(
        update={"analysis_id": "failed-replacement", "status": TaskStatus.FAILED}
    )
    monkeypatch.setattr(
        IPOAnalysisService,
        "analyze",
        lambda *_args, **_kwargs: failed_result,
    )
    app.get("file_uploader")[0].upload(
        "replacement.pdf", b"%PDF-1.4\nreplacement\n%%EOF", "application/pdf"
    ).run()
    _button(app, "开始风险研判").click().run()

    assert not app.exception
    assert app.session_state["judge_result"].analysis_id == good_result.analysis_id
    assert dict(app.session_state["judge_result_fingerprint"]) == fingerprint
    assert app.session_state["judge_prospectus_bytes"] == first_pdf
    assert any("未被本次失败运行覆盖" in item.value for item in app.error)


@pytest.mark.skipif(not DEMO_BUNDLE.is_dir(), reason="canonical replay bundle is unavailable")
def test_judge_entrypoint_does_not_render_a_truthy_model_error_as_a_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _canonical_result()
    monkeypatch.setattr(
        IPOAnalysisService,
        "analyze",
        lambda *_args, **_kwargs: result,
    )
    app = _run_app(monkeypatch)
    app.get("file_uploader")[0].upload(
        "case.pdf", b"%PDF-1.4\ncase\n%%EOF", "application/pdf"
    ).run()
    _button(app, "开始风险研判").click().run()

    metadata = deepcopy(result.metadata)
    error_model = {
        "status": "unavailable_error",
        "reason": "controlled_model_failure",
        "score": 0.99,
        "drivers": [{"feature": "must_not_render", "shap_value": 42}],
    }
    metadata["model_prediction"] = error_model
    metadata["final_supervision"] = {
        **metadata["final_supervision"],
        "model_prediction": error_model,
    }
    app.session_state["judge_result"] = result.model_copy(update={"metadata": metadata})
    app.run()

    assert not app.exception
    market_model = _tab(app, "市场与模型")
    assert "模型评分" not in {metric.label for metric in market_model.metric}
    copy = _markdown_text(market_model)
    assert "冻结模型结果不可用" in copy
    assert "must_not_render" not in copy


def test_judge_mode_switch_resets_case_specific_issuer_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _run_app(monkeypatch)
    company = next(widget for widget in app.text_input if widget.label == "公司名称")
    company.set_value("上一案例发行人").run()
    scenario = next(widget for widget in app.selectbox if widget.label == "分析模式")
    scenario.set_value("AI 增强分析").run()

    assert not app.exception
    assert app.session_state["judge_company"] == "Demo Biotech"
    assert app.session_state["judge_code"] == "9999.HK"
