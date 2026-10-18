@echo off
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
echo Starting Study Assistant Backend on http://127.0.0.1:8000 ...
uvicorn app.main:app --reload --port 8000
pause
