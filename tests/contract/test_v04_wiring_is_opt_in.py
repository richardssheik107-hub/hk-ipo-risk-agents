"""PR-G channels must be invisible to every configuration that predates them."""
from __future__ import annotations

from dataclasses import fields, replace

import pytest

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import NO_COMPONENT, DependencyContainer, default_registry

LEGACY_CONFIGS = ["configs/mock.yaml", "configs/default.yaml", "configs/real_pdf.yaml",
                  "configs/v03_offline.yaml", "configs/v03_offline_table.yaml",
                  "configs/v03_ai.yaml", "configs/v03_ai_table.yaml"]
V04_CONFIGS = ["configs/v04_offline.yaml", "configs/v04_ai.yaml",
               "configs/v04_offline_table.yaml", "configs/v04_ai_table.yaml"]


def _nodes(config: str) -> set[str]:
    settings = load_settings(config)
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    return set(workflow.graph.get_graph().nodes)


@pytest.mark.parametrize("config", LEGACY_CONFIGS)
def test_legacy_configs_build_no_pr_g_channel(config: str) -> None:
    settings = load_settings(config)
    assert settings.market_context == NO_COMPONENT
    assert settings.final_supervisor == NO_COMPONENT
    assert settings.pr_f_run_dir == ""
    assert not {"market_context", "final_supervisor"} & _nodes(config)


@pytest.mark.parametrize("config", LEGACY_CONFIGS)
def test_legacy_workflows_expose_no_channel_component(config: str) -> None:
    workflow = DependencyContainer(load_settings(config), default_registry()).create_workflow()
    assert workflow.market_context is None
    assert workflow.final_supervisor is None


@pytest.mark.parametrize("config", V04_CONFIGS)
def test_v04_configs_add_exactly_the_two_channel_nodes(config: str) -> None:
    added = _nodes(config) - _nodes("configs/v03_offline.yaml")
    assert added == {"market_context", "final_supervisor"}


def test_v04_places_the_final_supervisor_after_the_predictor() -> None:
    """It consumes the rule prediction, so it cannot run before the predictor."""
    workflow = DependencyContainer(load_settings("configs/v04_offline.yaml"), default_registry()).create_workflow()
    edges = [(edge.source, edge.target) for edge in workflow.graph.get_graph().edges]
    successors = {source: target for source, target in edges}
    assert successors["predictor"] == "final_supervisor"
    assert successors["final_supervisor"] == "report"
    assert successors["load_market_snapshot"] == "market_context"


def test_local_pr_f_handoff_adds_a_model_node_before_final_supervision() -> None:
    settings = replace(load_settings("configs/v04_offline.yaml"), pr_f_run_dir="local-handoff")
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    edges = [(edge.source, edge.target) for edge in workflow.graph.get_graph().edges]
    successors = {source: target for source, target in edges}
    assert successors["predictor"] == "model_prediction"
    assert successors["model_prediction"] == "final_supervisor"


def test_the_historical_nine_positional_arguments_still_construct_a_workflow() -> None:
    """Existing callers build workflows positionally; the channels are keyword-only."""
    from ipo_risk.workflows.enhanced_v2 import EnhancedV2Workflow

    workflow = EnhancedV2Workflow(None, None, [], None, None, None, None, None, None)
    assert workflow.market_context is None
    assert workflow.final_supervisor is None


@pytest.mark.parametrize(
    "plain, table",
    [
        ("configs/v04_offline.yaml", "configs/v04_offline_table.yaml"),
        ("configs/v04_ai.yaml", "configs/v04_ai_table.yaml"),
    ],
)
def test_v04_table_configs_differ_only_in_the_document_path(plain: str, table: str) -> None:
    """v0.4 shipped on the flat-text parser, so the table work was invisible to it.

    The table variants exist to close that gap without touching the frozen v0.4
    configurations: same workflow, same channels, only the two
    document-intelligence components swapped.
    """
    base, tables = load_settings(plain), load_settings(table)
    assert (base.parser, base.financial_extractor) == ("pymupdf", "regex")
    assert (tables.parser, tables.financial_extractor) == ("pymupdf_table", "table")
    differing = {
        field.name
        for field in fields(base)
        if getattr(base, field.name) != getattr(tables, field.name)
    }
    assert differing == {"parser", "financial_extractor"}
