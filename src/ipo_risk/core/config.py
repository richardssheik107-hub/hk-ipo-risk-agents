"""Configuration precedence: environment variables > YAML > code defaults."""
from dataclasses import dataclass, field, fields
from pathlib import Path
import os
import yaml

class ComponentConfigurationError(ValueError): pass

@dataclass(frozen=True)
class Settings:
    workflow_version: str = "mvp_v1"; use_mock: bool = True; enable_verifier: bool = True
    runtime_mode: str = "mock"
    parser: str = "mock"; retriever: str = "mock"; financial_agent: str = "mock"
    financial_extractor: str = "regex"
    legal_agent: str = "mock"; business_agent: str = "mock"; market_agent: str = "mock"
    verifier: str = "rule"; supervisor: str = "rule"; predictor: str = "rule_based"
    llm_provider: str = "mock"; market_data_provider: str = "mock"; ipo_data_provider: str = "mock"
    llm_api_key: str = field(default="", repr=False)
    llm_base_url: str = ""; llm_model: str = ""
    llm_timeout_seconds: int = 60; llm_max_retries: int = 2
    repository: str = "json"; report_generator: str = "mock"
    # PR-G channels. "none" builds nothing, so every pre-v0.4 config is unchanged.
    market_context: str = "none"; final_supervisor: str = "none"
    # Local-only path to a PR-F run directory; never committed non-empty.
    pr_f_run_dir: str = ""
    # Governed PR-B product projection. Relative defaults are portable and
    # contain no licensed raw market data.
    market_feature_dir: str = "reports/v04_pr_b/core_features"
    market_official_bridge: str = "data/catalog/ipo_official_master_bridge.csv"
    # Optional governed local C-lane projection; raw/large audit rows stay uncommitted.
    market_extended_readiness: str = ""
    # Dynamic Market-X for IPOs outside the frozen PR-B universe. "none" keeps
    # the honest unconfigured placeholder; "pit_bridge" recomputes Market-X Core
    # from the committed official prior-IPO universe.
    market_dynamic_context: str = "none"
    # Optional local licensed-derived prior-IPO outcome pack. Absent, the
    # dynamic outcome families stay explicitly missing instead of zero-filled.
    market_dynamic_outcome_pack: str = ""
    # Optional local licensed CSMAR HSI / HKEX turnover caches. Both are needed
    # for dynamic Market-X Extended; absent, no Extended name is emitted at all.
    market_dynamic_extended_hsi_csv: str = ""
    market_dynamic_extended_turnover_csv: str = ""
    data_dir: str = "data"; report_dir: str = "reports"; log_level: str = "INFO"

def _coerce(value: str, current):
    if isinstance(current, bool):
        return value.lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int):
        return int(value)
    return value

def load_settings(path: str | None = None) -> Settings:
    config_path = Path(path or os.getenv("IPO_RISK_CONFIG", "configs/mock.yaml"))
    values = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    defaults = Settings()
    for item in fields(Settings):
        env = os.getenv(f"IPO_RISK_{item.name.upper()}")
        if env is not None: values[item.name] = _coerce(env, getattr(defaults, item.name))
    return Settings(**{item.name: values.get(item.name, getattr(defaults, item.name)) for item in fields(Settings)})
