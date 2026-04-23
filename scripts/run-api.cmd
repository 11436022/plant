@echo off
call "%~dp0use-portable-python.cmd" || exit /b 1
cd /d "%~dp0.."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
