@echo off
REM Pull one snapshot and upload it to R2, using this folder's .env and .venv (run setup.bat once first).
cd /d "%~dp0"
.venv\Scripts\python scripts\pull_snapshot_to_r2.py
