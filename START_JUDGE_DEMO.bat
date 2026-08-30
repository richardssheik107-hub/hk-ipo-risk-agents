@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%CD%\app"
set "IPO_RISK_DEMO_BUNDLE=reports\v045_demo_bundle"
python scripts\check_frontend_runtime.py
if errorlevel 1 (
  echo Judge demo runtime preflight failed. Refusing to use a stale Python checkout.
  exit /b 1
)
python scripts\check_v045_team_clone_ready.py
if errorlevel 1 (
  echo Judge demo preflight failed. Please complete the clone-ready preparation steps before launching.
  exit /b 1
)
python -m streamlit run app\streamlit_app.py
endlocal
