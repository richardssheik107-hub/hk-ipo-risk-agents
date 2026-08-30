from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _assert_windows_runtime_binding(launcher: str, entrypoint: str) -> None:
    assert 'cd /d "%~dp0"' in launcher
    assert 'set "PYTHONPATH=%CD%\\src;%CD%\\app"' in launcher
    assert "scripts\\check_frontend_runtime.py" in launcher
    assert launcher.index("check_frontend_runtime.py") < launcher.index(
        "check_v045_team_clone_ready.py"
    )
    assert launcher.index("check_v045_team_clone_ready.py") < launcher.index(entrypoint)


def _assert_unix_runtime_binding(launcher: str, entrypoint: str) -> None:
    assert 'cd "$(dirname "$0")"' in launcher
    assert 'export PYTHONPATH="$(pwd)/src:$(pwd)/app"' in launcher
    assert "scripts/check_frontend_runtime.py" in launcher
    assert launcher.index("check_frontend_runtime.py") < launcher.index(
        "check_v045_team_clone_ready.py"
    )
    assert launcher.index("check_v045_team_clone_ready.py") < launcher.index(entrypoint)


def test_windows_judge_launcher_is_clone_ready_and_fail_fast() -> None:
    launcher = (REPO_ROOT / "START_JUDGE_DEMO.bat").read_text(encoding="utf-8")

    _assert_windows_runtime_binding(launcher, "app\\streamlit_app.py")
    assert 'set "IPO_RISK_DEMO_BUNDLE=reports\\v045_demo_bundle"' in launcher
    assert "if errorlevel 1" in launcher


def test_unix_judge_launcher_matches_the_canonical_contract() -> None:
    launcher = (REPO_ROOT / "start_judge_demo.sh").read_text(encoding="utf-8")

    assert launcher.startswith("#!/usr/bin/env sh\nset -eu\n")
    _assert_unix_runtime_binding(launcher, "app/streamlit_app.py")
    assert 'IPO_RISK_DEMO_BUNDLE="reports/v045_demo_bundle"' in launcher
    assert "exit 1" in launcher


def test_standard_launchers_share_the_same_fail_fast_runtime_binding() -> None:
    windows = (REPO_ROOT / "START_DEMO.bat").read_text(encoding="utf-8")
    unix = (REPO_ROOT / "start_demo.sh").read_text(encoding="utf-8")

    _assert_windows_runtime_binding(windows, "app\\streamlit_app.py")
    _assert_unix_runtime_binding(unix, "app/streamlit_app.py")


def test_standard_and_judge_launchers_share_the_canonical_entrypoint() -> None:
    standard_windows = (REPO_ROOT / "START_DEMO.bat").read_text(encoding="utf-8")
    standard_unix = (REPO_ROOT / "start_demo.sh").read_text(encoding="utf-8")
    judge_windows = (REPO_ROOT / "START_JUDGE_DEMO.bat").read_text(encoding="utf-8")
    judge_unix = (REPO_ROOT / "start_judge_demo.sh").read_text(encoding="utf-8")

    assert "app\\streamlit_app.py" in standard_windows
    assert "app/streamlit_app.py" in standard_unix
    assert "app\\streamlit_app.py" in judge_windows
    assert "app/streamlit_app.py" in judge_unix
    assert "app\\judge_streamlit_app.py" not in judge_windows
    assert "app/judge_streamlit_app.py" not in judge_unix
