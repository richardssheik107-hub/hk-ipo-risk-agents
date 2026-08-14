"""Safety contracts for the staged four-case pilot runner."""

from __future__ import annotations

import inspect

from scripts import run_retriever_v2_four_case_pilot as runner


def test_case_split_keeps_1961_as_only_holdout() -> None:
    assert runner.DEVELOPMENT_CASES == (
        "ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408"
    )
    assert runner.HOLDOUT_CASES == ("ipo_2020_01961",)


def test_runner_has_no_downstream_component_imports() -> None:
    source = inspect.getsource(runner)
    for forbidden in (
        "ipo_risk.agents", "ipo_risk.verifiers", "ipo_risk.workflows",
        "ipo_risk.predictors", "ipo_risk.providers", "generate_structured", ".analyze(",
    ):
        assert forbidden not in source


def test_holdout_requires_unchanged_v2_hashes() -> None:
    source = inspect.getsource(runner._holdout)
    assert "V2_CHANGED_AFTER_FREEZE" in source
    assert "source_sha256" in source
    assert "query_plan_sha256" in source
