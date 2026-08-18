@echo off
rem Start backend. First run: create venv, install deps, init DB, seed demo data.
setlocal
cd /d "%~dp0apps\api"

if not exist .venv\Scripts\python.exe (
    echo [FIRST RUN] Creating venv and installing dependencies...
    python -m venv .venv
    .venv\Scripts\python -m pip install --quiet --upgrade pip
    .venv\Scripts\pip install --quiet -e ".[dev]"
    if errorlevel 1 ( echo FAILED: dependency install. Check python in PATH. & pause & exit /b 1 )
)

if not exist "%~dp0data\app.sqlite" (
    echo [FIRST RUN] Initializing database...
    .venv\Scripts\alembic upgrade head
)

if not exist "%~dp0data\market\manifests\synthetic_SPY_5m.json" (
    echo [FIRST RUN] Seeding demo data ^(SPY 2024-01-02 to 2024-03-28^)...
    .venv\Scripts\python -m app.cli data seed --start 2024-01-02 --end 2024-03-28
)

echo.
echo Backend + Web UI starting: http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/api/docs
echo Press Ctrl+C to stop.
echo.
.venv\Scripts\python -m uvicorn app.main:app --port 8000
pause
