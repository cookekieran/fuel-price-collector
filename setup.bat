@echo off
REM One-off: create a virtual environment in this folder and install what the collector needs.
cd /d "%~dp0"
py -3 -m venv .venv || python -m venv .venv
.venv\Scripts\python -m pip install --disable-pip-version-check -r requirements.txt
