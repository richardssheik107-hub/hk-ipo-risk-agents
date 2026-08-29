#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
export IPO_RISK_DEMO_BUNDLE="reports/v045_demo_bundle"
python scripts/check_v045_team_clone_ready.py
exec python -m streamlit run app/streamlit_app.py
