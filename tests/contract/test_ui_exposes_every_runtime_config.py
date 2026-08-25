"""Every shipped runtime config must be reachable from the UI scenario picker.

The v0.4 table configs shipped without a scenario entry, so the whole
table document path stayed invisible to anyone driving the product through
Streamlit: picking "v0.4 AI 模式 + Final Supervisor" silently kept the flat-text
parser and the regex extractor. A config that no scenario names is a config
that only scripts can reach, which is how that gap survived review.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from ipo_risk.core.config import Settings, load_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
STREAMLIT_APP = REPO_ROOT / "app" / "streamlit_app.py"

# `default.yaml` is the fallback `load_settings()` reads with no argument, not a
# scenario a user picks.
NON_SCENARIO_CONFIGS = {"default.yaml"}


def _is_runtime_config(path: Path) -> bool:
    """Distinguish runtime Settings files from frozen policy data.

    `configs/` also holds non-Settings YAML such as the frozen v0.3 risk-rule
    thresholds, which no scenario should ever name.
    """
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return bool(set(document) & {field.name for field in fields(Settings)})


def _scenario_configs() -> dict[str, str]:
    """Read the SCENARIOS mapping without importing the Streamlit script.

    ``streamlit_app.py`` renders at import time, so importing it here would run
    the UI. Parsing keeps this a pure wiring assertion.
    """
    module = ast.parse(STREAMLIT_APP.read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    scenarios: dict[str, str] | None = None

    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            constants[target.id] = node.value.value
        elif target.id == "SCENARIOS" and isinstance(node.value, ast.Dict):
            scenarios = {}
            for key, value in zip(node.value.keys, node.value.values, strict=True):
                if isinstance(key, ast.Constant):
                    label = key.value
                elif isinstance(key, ast.Name):
                    label = constants[key.id]
                else:  # pragma: no cover - guards an unexpected key form
                    raise AssertionError(f"unsupported SCENARIOS key: {ast.dump(key)}")
                assert isinstance(value, ast.Tuple), "each scenario is (config_path, needs_pdf)"
                config = value.elts[0]
                assert isinstance(config, ast.Constant), "config path must be a literal"
                scenarios[label] = config.value

    assert scenarios, "SCENARIOS mapping not found in app/streamlit_app.py"
    return scenarios


def test_every_scenario_names_a_config_that_exists() -> None:
    for label, config in _scenario_configs().items():
        assert (REPO_ROOT / config).is_file(), f"scenario {label!r} points at a missing {config}"


def test_every_shipped_config_is_reachable_from_the_ui() -> None:
    on_disk = {
        path.name
        for path in (REPO_ROOT / "configs").glob("*.yaml")
        if path.name not in NON_SCENARIO_CONFIGS and _is_runtime_config(path)
    }
    wired = {Path(config).name for config in _scenario_configs().values()}
    assert on_disk - wired == set(), "shipped configs with no UI scenario"


@pytest.mark.parametrize(
    "label, parser, extractor",
    [
        ("v0.4 离线模式（表格）+ Final Supervisor", "pymupdf_table", "table"),
        ("v0.4 AI 模式（表格）+ Final Supervisor", "pymupdf_table", "table"),
        ("v0.4 离线模式 + Final Supervisor", "pymupdf", "regex"),
        ("v0.4 AI 模式 + Final Supervisor", "pymupdf", "regex"),
    ],
)
def test_v04_scenarios_select_the_document_path_their_label_promises(
    label: str, parser: str, extractor: str
) -> None:
    """The label is the only thing a judge sees, so it must match the wiring."""
    settings = load_settings(_scenario_configs()[label])
    assert (settings.parser, settings.financial_extractor) == (parser, extractor)
