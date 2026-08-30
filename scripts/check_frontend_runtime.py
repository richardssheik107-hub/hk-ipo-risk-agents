"""Fail-fast guard for the Python environment used by the frontend launchers.

The launchers intentionally bind ``src`` and ``app`` from this checkout before
running this script, the clone-ready preflight, and Streamlit.  This guard makes
that binding observable and refuses to launch when an unrelated editable install
would supply ``ipo_risk`` or when the formal competition configs lose the
generalized frozen-model fallback.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
FORMAL_CONFIGS = (
    REPO_ROOT / "configs" / "v045_competition_ai.yaml",
    REPO_ROOT / "configs" / "v045_competition_offline.yaml",
)
EXPECTED_DYNAMIC_RUNTIME = "frozen_v2"


class FrontendRuntimePreflightError(RuntimeError):
    """The frontend process would not use the governed runtime from this repo."""


def _resolved_pythonpath() -> tuple[Path, ...]:
    raw = os.environ.get("PYTHONPATH", "")
    return tuple(
        Path(entry).resolve()
        for entry in raw.split(os.pathsep)
        if entry.strip()
    )


def _require_within(path: Path, parent: Path, *, label: str) -> None:
    try:
        path.relative_to(parent)
    except ValueError as exc:
        raise FrontendRuntimePreflightError(
            f"{label} resolved outside this repository: {path} (expected under {parent})"
        ) from exc


def _validate_checkout_binding() -> dict[str, str]:
    expected_src = (REPO_ROOT / "src").resolve()
    expected_app = (REPO_ROOT / "app").resolve()
    if Path.cwd().resolve() != REPO_ROOT:
        raise FrontendRuntimePreflightError(
            f"frontend must start from the repository root: {REPO_ROOT}"
        )

    pythonpath = _resolved_pythonpath()
    expected_prefix = (expected_src, expected_app)
    if pythonpath[:2] != expected_prefix:
        rendered = os.pathsep.join(str(path) for path in pythonpath) or "<unset>"
        raise FrontendRuntimePreflightError(
            "PYTHONPATH must begin with this checkout's src and app directories; "
            f"got {rendered}"
        )

    package = importlib.import_module("ipo_risk")
    package_file = getattr(package, "__file__", None)
    if not package_file:
        raise FrontendRuntimePreflightError("ipo_risk.__file__ is unavailable")
    package_path = Path(package_file).resolve()
    _require_within(
        package_path,
        expected_src / "ipo_risk",
        label="ipo_risk.__file__",
    )

    app_spec = importlib.util.find_spec("competition_ui")
    if app_spec is None or not app_spec.origin:
        raise FrontendRuntimePreflightError(
            "the current repository app directory does not expose competition_ui"
        )
    app_module_path = Path(app_spec.origin).resolve()
    _require_within(
        app_module_path,
        expected_app,
        label="competition_ui module",
    )
    return {
        "ipo_risk": str(package_path),
        "competition_ui": str(app_module_path),
    }


def _load_verified_model_identity(dynamic_provider: object) -> dict[str, str]:
    from ipo_risk.modeling.dynamic_model_runtime import load_frozen_model_bundle

    bundle = load_frozen_model_bundle(
        model_dir=dynamic_provider.model_dir,
        frozen_dir=dynamic_provider.frozen_dir,
    )
    identity = bundle.identity
    return {
        "model_version": str(identity["model_version"]),
        "classifier_model_sha256": str(identity["classifier_model_sha256"]),
        "model_file_sha256": str(identity["model_file_sha256"]),
        "feature_manifest_hash": str(identity["feature_manifest_hash"]),
        "alert_policy_hash": str(identity["alert_policy_hash"]),
    }


def _validate_model_fallbacks() -> list[dict[str, str]]:
    from ipo_risk.core.config import load_settings
    from ipo_risk.core.container import DependencyContainer, default_registry
    from ipo_risk.modeling.dynamic_model_runtime import (
        CompositeModelPredictionProvider,
        DynamicFrozenModelPredictionProvider,
    )
    from ipo_risk.modeling.frozen_model_evidence import FrozenModelPredictionProvider

    checks: list[dict[str, str]] = []
    for config_path in FORMAL_CONFIGS:
        if not config_path.is_file():
            raise FrontendRuntimePreflightError(
                f"formal competition config is missing: {config_path}"
            )
        settings = load_settings(str(config_path))
        if settings.model_dynamic_runtime != EXPECTED_DYNAMIC_RUNTIME:
            raise FrontendRuntimePreflightError(
                f"{config_path.name} resolved model_dynamic_runtime="
                f"{settings.model_dynamic_runtime!r}; expected "
                f"{EXPECTED_DYNAMIC_RUNTIME!r}"
            )

        provider = DependencyContainer(settings, default_registry())._model_prediction_provider()
        if not isinstance(provider, CompositeModelPredictionProvider):
            raise FrontendRuntimePreflightError(
                f"{config_path.name} did not assemble a composite model provider; "
                f"got {type(provider).__name__}"
            )
        if not isinstance(provider.primary, FrozenModelPredictionProvider):
            raise FrontendRuntimePreflightError(
                f"{config_path.name} lost its receipt-bound primary model provider"
            )
        if not isinstance(provider.dynamic, DynamicFrozenModelPredictionProvider):
            raise FrontendRuntimePreflightError(
                f"{config_path.name} has no dynamic frozen-model fallback"
            )

        dynamic_model_dir = provider.dynamic.model_dir.resolve()
        _require_within(
            dynamic_model_dir,
            REPO_ROOT,
            label=f"{config_path.name} dynamic model directory",
        )
        verified_identity = _load_verified_model_identity(provider.dynamic)
        checks.append(
            {
                "config": config_path.name,
                "model_dynamic_runtime": settings.model_dynamic_runtime,
                "provider": type(provider).__name__,
                "fallback": type(provider.dynamic).__name__,
                "model_dir": str(dynamic_model_dir),
                **verified_identity,
            }
        )
    return checks


def validate_frontend_runtime() -> dict[str, object]:
    return {
        "checkout": _validate_checkout_binding(),
        "configs": _validate_model_fallbacks(),
    }


def main() -> int:
    try:
        result = validate_frontend_runtime()
    except (FrontendRuntimePreflightError, ImportError, OSError, ValueError) as exc:
        print(f"FAIL frontend runtime preflight: {exc}", file=sys.stderr)
        return 2

    checkout = result["checkout"]
    print(f"PASS frontend backend import -> {checkout['ipo_risk']}")
    print(f"PASS frontend app import -> {checkout['competition_ui']}")
    for check in result["configs"]:
        print(
            "PASS "
            f"{check['config']} -> {check['provider']} with {check['fallback']} "
            f"({check['model_dynamic_runtime']}); verified model "
            f"{check['model_version']} sha256="
            f"{check['classifier_model_sha256'][:12]}..."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
