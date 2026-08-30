from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
for source_dir in (ROOT / "src", ROOT / "app"):
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

from competition_ui import (  # noqa: E402
    reader_article_markdown,
    reader_article_projection,
    reader_markdown_report,
)
from ipo_risk.runtime.demo_replay import load_recorded_case  # noqa: E402
from ipo_risk.schemas import IPOAnalysisResult  # noqa: E402
from presenters import result_payload  # noqa: E402


BUNDLE = ROOT / "reports" / "v045_demo_bundle"


@lru_cache(maxsize=3)
def _canonical_payload(case_id: str) -> dict[str, object]:
    recorded = load_recorded_case(BUNDLE / case_id)
    result = IPOAnalysisResult.model_validate(recorded.result)
    return result_payload(result)


CANONICAL_CASES = {
    "ipo_2024_01318": {
        "company": "毛戈平",
        "overall": "中",
        "rule": "低",
        "risks": (
            {
                "title": "客户集中度",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["263", "268", "20"],
                "fragments": (
                    "报告期与数值数量未能一一对应",
                    "同一报告期出现相互冲突的候选数值",
                    "缺少可复算的确定性计算",
                    "尚未完成口径一致的集中度复算",
                    "不能据此判断集中程度或风险等级",
                ),
            },
            {
                "title": "重大诉讼与合规",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["76", "273", "274"],
                "fragments": (
                    "社会保险及住房公积金缴纳不足",
                    "事项是否持续、整改是否完成和重大性仍待复核",
                ),
            },
        ),
        "market_title": "近期新股市场热度中性，结论来自上市日前可用样本",
        "market_fragments": (
            "近 30 日有 6 宗前序 IPO",
            "近 60 日有 14 宗前序 IPO",
            "首日破发率为 42.9%（14 宗样本）",
            "上市后五个交易日平均回报为 2.2%（12 宗样本）",
            "近 180 日没有可用的同业前序 IPO 样本",
        ),
        "coverage": "Market-X 核心观测取得 13/15 项。未取得 2/15 项",
        "review": "智能综合审阅为中风险，规则筛选参考为低风险。本次有 2 项风险仍待复核、5 项跨通道分歧",
    },
    "ipo_2024_02410": {
        "company": "同源康医药─B",
        "overall": "极高",
        "rule": "极高",
        "risks": (
            {
                "title": "现金可支撑期",
                "level": "极高",
                "status": "已验证",
                "pages": ["563", "562"],
                "fragments": (
                    "现金及现金等价物人民币 77,208 千元",
                    "3 个月经营活动净流出人民币 83,918 千元",
                    "现金可支撑期约为 2.76 个月",
                    "确定性计算，不是风险发生概率",
                ),
            },
            {
                "title": "特殊股东权利 / 赎回安排",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["604", "250", "251"],
                "fragments": (
                    "首次公开发售前投资者",
                    "所有其他特殊权利",
                    "自动恢复",
                ),
            },
            {
                "title": "重大诉讼与合规",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["402", "107", "108"],
                "fragments": (
                    "社会保险",
                    "住房公积金",
                    "事项是否持续、整改是否完成和重大性仍待复核",
                ),
            },
        ),
        "market_title": "近期新股市场热度偏冷，结论来自上市日前可用样本",
        "market_fragments": (
            "近 30 日有 2 宗前序 IPO",
            "近 60 日有 15 宗前序 IPO",
            "首日破发率为 60.0%（15 宗样本）",
            "上市后五个交易日平均回报为 -9.2%（15 宗样本）",
            "近 180 日有 3 宗同业前序 IPO",
            "五个交易日平均回报 -11.1%",
        ),
        "coverage": "Market-X 核心观测取得 15/15 项。",
        "review": "智能综合审阅为极高风险，规则筛选参考为极高风险。本次有 2 项风险仍待复核、7 项跨通道分歧",
    },
    "ipo_2024_02460": {
        "company": "华润饮料",
        "overall": "中",
        "rule": "低",
        "risks": (
            {
                "title": "特殊股东权利 / 赎回安排",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["159", "160"],
                "fragments": (
                    "Plateau（首次公开发售前投资者）",
                    "自动恢复",
                    "2025年11月1日前上市",
                ),
            },
            {
                "title": "重大诉讼与合规",
                "level": "暂定中等",
                "status": "待复核",
                "pages": ["269"],
                "fragments": (
                    "永隆土地",
                    "土地使用权",
                    "1.1%–2.3%",
                    "事项是否持续、整改是否完成和重大性仍待复核",
                ),
            },
        ),
        "market_title": "近期新股市场热度偏冷，结论来自上市日前可用样本",
        "market_fragments": (
            "近 30 日有 4 宗前序 IPO",
            "近 60 日有 6 宗前序 IPO",
            "首日破发率为 66.7%（6 宗样本）",
            "上市后五个交易日平均回报为 -25.0%（6 宗样本）",
            "近 180 日没有可用的同业前序 IPO 样本",
        ),
        "coverage": "Market-X 核心观测取得 13/15 项。未取得 2/15 项",
        "review": "智能综合审阅为中风险，规则筛选参考为低风险。本次有 2 项风险仍待复核、5 项跨通道分歧",
    },
}


@pytest.mark.parametrize("case_id", tuple(CANONICAL_CASES))
def test_canonical_reader_projection_preserves_real_risk_findings(case_id: str) -> None:
    expected = CANONICAL_CASES[case_id]
    article = reader_article_projection(_canonical_payload(case_id))

    assert article["profile"]["company_name"] == expected["company"]
    assert article["overall_level"] == expected["overall"]
    assert article["rule_level"] == expected["rule"]
    assert len(article["risks"]) == len(expected["risks"])

    for risk, expected_risk in zip(article["risks"], expected["risks"], strict=True):
        assert risk["title"] == expected_risk["title"]
        assert risk["level"] == expected_risk["level"]
        assert risk["status"] == expected_risk["status"]
        assert risk["pages"] == expected_risk["pages"]
        assert risk["evidence"]
        assert all(item.get("page") and item.get("text") for item in risk["evidence"])
        assert "该风险项尚未形成足够" not in risk["conclusion"]
        for fragment in expected_risk["fragments"]:
            assert fragment in risk["conclusion"]


@pytest.mark.parametrize("case_id", tuple(CANONICAL_CASES))
def test_canonical_reader_projection_explains_market_and_model_for_judges(case_id: str) -> None:
    expected = CANONICAL_CASES[case_id]
    article = reader_article_projection(_canonical_payload(case_id))

    assert article["market_title"] == expected["market_title"]
    for fragment in expected["market_fragments"]:
        assert fragment in article["market_body"]
    assert expected["coverage"] in article["market_coverage"]
    assert "缺失项不会被补成 0" in article["market_coverage"] or "15/15" in article["market_coverage"]
    assert "用于判断整体市场状态的恒指、波动或成交额等扩展信息仍不可用" in article["market_coverage"]

    assert article["model_title"] == "模型已形成信号，但与招股书判断存在未解决分歧"
    assert "本次记录 1 项模型方向与文档结论的分歧" in article["model_body"]
    assert "模型分数未经概率校准" in article["model_body"]
    assert "具体分数与影响因素保留在后台核验" in article["model_body"]
    assert expected["review"] in article["review_guidance"]
    assert "先看逐项结论和原文证据" in article["review_guidance"]


@pytest.mark.parametrize("case_id", tuple(CANONICAL_CASES))
def test_canonical_reader_report_is_one_continuous_article_with_exact_quotes(case_id: str) -> None:
    payload = _canonical_payload(case_id)
    article = reader_article_projection(payload)
    screen = reader_article_markdown(payload)
    download = reader_markdown_report(payload)

    headings = (
        "## 案例与综合判断",
        "## 招股书重点风险分析",
        "## 上市前市场环境",
        "## 模型信号及其边界",
        "## 评审结论与复核顺序",
    )
    for heading in headings:
        assert screen.count(heading) == 1
    assert "<details" not in screen
    assert "```json" not in screen
    assert "#### " not in screen
    assert screen in download
    assert "## 原文证据附录" in download

    for risk in article["risks"]:
        assert f"### {risk['title']}｜{risk['level']}风险 · {risk['status']}" in screen
        assert risk["conclusion"] in screen

    first_evidence = article["risks"][0]["evidence"][0]
    quote = str(first_evidence["text"])
    rendered_quote = "\n".join(f"> {line}" for line in quote.splitlines())
    assert rendered_quote in download


@pytest.mark.parametrize("case_id", tuple(CANONICAL_CASES))
def test_canonical_reader_outputs_do_not_leak_runtime_or_model_fields(case_id: str) -> None:
    payload = _canonical_payload(case_id)
    rendered = reader_article_markdown(payload) + "\n" + reader_markdown_report(payload)
    final = payload.get("final_supervision") or {}
    model = final.get("model_prediction") or payload.get("model_prediction") or {}
    formal_risks = [
        risk
        for domain in (payload.get("domains") or {}).values()
        for risk in (domain.get("risks") or [])
        if risk.get("verification_status") != "rejected"
    ]

    raw_values = [
        str(model.get("score") or ""),
        str(model.get("model_version") or ""),
        str(((payload.get("profile") or {}).get("metadata") or {}).get("prospectus_sha256") or ""),
    ]
    raw_values.extend(str(driver.get("feature") or "") for driver in model.get("drivers") or [])
    raw_values.extend(
        str(driver["shap_value"])
        for driver in model.get("drivers") or []
        if driver.get("shap_value") is not None
    )
    raw_values.extend(str(risk.get("risk_id") or "") for risk in formal_risks)
    raw_values.extend(
        str(evidence.get("evidence_id") or "")
        for risk in formal_risks
        for evidence in risk.get("evidence") or []
    )
    assert all(raw_values)
    for raw_value in raw_values:
        assert raw_value not in rendered

    for raw_key_or_code in (
        "component_diagnostics",
        "prospectus_sha256",
        "model_version",
        "shap_value",
        "market_core__",
        "insufficient_governed_prelisting_history",
        "openai_responses",
        "v04_final_supervision_v3",
    ):
        assert raw_key_or_code not in rendered
