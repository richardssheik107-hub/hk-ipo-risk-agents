from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from ipo_risk.modeling.dynamic_model_runtime import (
    DynamicFrozenModelPredictionProvider,
    DynamicModelRuntimeError,
)
from scripts.check_frontend_runtime import _load_verified_model_identity


REPO_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = REPO_ROOT / "scripts" / "check_frontend_runtime.py"


def _runtime_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith("IPO_RISK_"):
            env.pop(key)
    env["PYTHONPATH"] = os.pathsep.join(
        (str(REPO_ROOT / "src"), str(REPO_ROOT / "app"))
    )
    return env


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_frontend_runtime_preflight_accepts_current_checkout_and_dynamic_fallback() -> None:
    result = _run(_runtime_environment())

    assert result.returncode == 0, result.stderr
    assert str((REPO_ROOT / "src" / "ipo_risk").resolve()) in result.stdout
    assert "v045_competition_ai.yaml -> CompositeModelPredictionProvider" in result.stdout
    assert "v045_competition_offline.yaml -> CompositeModelPredictionProvider" in result.stdout
    verified_identity = "v045_role_d_v2_promotion_release_v1 sha256=320e810e85dc..."
    assert result.stdout.count("DynamicFrozenModelPredictionProvider (frozen_v2)") == 2
    assert result.stdout.count(verified_identity) == 2


def test_model_identity_helper_rejects_a_corrupted_model_file(tmp_path: Path) -> None:
    model_dir = tmp_path / "role_d_v2"
    shutil.copytree(REPO_ROOT / "models" / "role_d_v2", model_dir)
    model_path = model_dir / "model.txt"
    model_path.write_text(
        model_path.read_text(encoding="utf-8") + "\ncorrupted\n",
        encoding="utf-8",
    )
    provider = DynamicFrozenModelPredictionProvider(
        model_dir=model_dir,
        frozen_dir=REPO_ROOT / "reports" / "frozen",
    )

    with pytest.raises(DynamicModelRuntimeError, match="classifier hash"):
        _load_verified_model_identity(provider)


def test_frontend_runtime_preflight_rejects_unbound_pythonpath(tmp_path: Path) -> None:
    env = _runtime_environment()
    env["PYTHONPATH"] = str(tmp_path)

    result = _run(env)

    assert result.returncode == 2
    assert "PYTHONPATH must begin with this checkout's src and app" in result.stderr


def test_frontend_runtime_preflight_rejects_runtime_override_without_fallback() -> None:
    env = _runtime_environment()
    env["IPO_RISK_MODEL_DYNAMIC_RUNTIME"] = "none"

    result = _run(env)

    assert result.returncode == 2
    assert "resolved model_dynamic_runtime='none'; expected 'frozen_v2'" in result.stderr
