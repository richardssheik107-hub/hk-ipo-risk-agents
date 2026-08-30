@echo off
setlocal
cd /d "%~dp0"
python -m streamlit run app\judge_streamlit_app.py
endlocal
