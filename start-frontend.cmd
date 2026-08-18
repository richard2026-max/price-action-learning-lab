@echo off
rem Start frontend dev server. First run: install npm dependencies.
setlocal
cd /d "%~dp0apps\web"

where npm >nul 2>nul
if errorlevel 1 ( echo npm not found. Install Node.js 18+ first. & pause & exit /b 1 )

if not exist node_modules (
    echo [FIRST RUN] Installing frontend dependencies...
    call npm install --no-fund --no-audit
    if errorlevel 1 ( echo FAILED: npm install & pause & exit /b 1 )
)

echo.
echo Frontend dev server starting: http://localhost:5173
echo NOTE: only needed when developing the frontend (hot reload).
echo For daily use, start-backend.cmd alone serves the UI at http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.
call npm run dev
pause
