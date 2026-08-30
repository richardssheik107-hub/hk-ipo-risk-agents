from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_windows_judge_launcher_is_clone_ready_and_fail_fast() -> None:
    launcher = (REPO_ROOT / "START_JUDGE_DEMO.bat").read_text(encoding="utf-8")

    assert 'cd /d "%~dp0"' in launcher
    assert 'set "IPO_RISK_DEMO_BUNDLE=reports\\v045_demo_bundle"' in launcher
    assert "scripts\\check_v045_team_clone_ready.py" in launcher
    assert "if errorlevel 1" in launcher
    assert launcher.index("check_v045_team_clone_ready.py") < launcher.index(
        "app\\judge_streamlit_app.py"
    )


def test_unix_judge_launcher_matches_the_canonical_contract() -> None:
    launcher = (REPO_ROOT / "start_judge_demo.sh").read_text(encoding="utf-8")

    assert launcher.startswith("#!/usr/bin/env sh\nset -eu\n")
    assert 'cd "$(dirname "$0")"' in launcher
    assert 'IPO_RISK_DEMO_BUNDLE="reports/v045_demo_bundle"' in launcher
    assert "scripts/check_v045_team_clone_ready.py" in launcher
    assert "exit 1" in launcher
    assert launcher.index("check_v045_team_clone_ready.py") < launcher.index(
        "app/judge_streamlit_app.py"
    )


def test_standard_and_judge_launchers_keep_distinct_entrypoints() -> None:
    standard_windows = (REPO_ROOT / "START_DEMO.bat").read_text(encoding="utf-8")
    standard_unix = (REPO_ROOT / "start_demo.sh").read_text(encoding="utf-8")
    judge_windows = (REPO_ROOT / "START_JUDGE_DEMO.bat").read_text(encoding="utf-8")
    judge_unix = (REPO_ROOT / "start_judge_demo.sh").read_text(encoding="utf-8")

    assert "app\\streamlit_app.py" in standard_windows
    assert "app/streamlit_app.py" in standard_unix
    assert "app\\judge_streamlit_app.py" in judge_windows
    assert "app/judge_streamlit_app.py" in judge_unix
    assert "app\\streamlit_app.py" not in judge_windows
    assert "app/streamlit_app.py" not in judge_unix
