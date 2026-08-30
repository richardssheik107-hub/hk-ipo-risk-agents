#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)/src:$(pwd)/app"
export IPO_RISK_DEMO_BUNDLE="reports/v045_demo_bundle"
if ! python scripts/check_frontend_runtime.py; then
  echo "Judge demo runtime preflight failed. Refusing to use a stale Python checkout." >&2
  exit 1
fi
if ! python scripts/check_v045_team_clone_ready.py; then
  echo "Judge demo preflight failed. Please complete the clone-ready preparation steps before launching." >&2
  exit 1
fi
exec python -m streamlit run app/judge_streamlit_app.py
