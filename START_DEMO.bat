@echo off
setlocal
cd /d "%~dp0"
set "IPO_RISK_DEMO_BUNDLE=reports\v045_demo_bundle"
python scripts\check_v045_team_clone_ready.py
if errorlevel 1 exit /b %errorlevel%
python -m streamlit run app\streamlit_app.py
