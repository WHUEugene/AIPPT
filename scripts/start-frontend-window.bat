@echo off
setlocal

set "FRONTEND_DIR=%~1"
set "BACKEND_PORT=%~2"
set "FRONTEND_PORT=%~3"
set "OPEN_MODE=%~4"

if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found: %FRONTEND_DIR%
    exit /b 1
)

cd /d "%FRONTEND_DIR%"
set "AIPPT_BACKEND_PORT=%BACKEND_PORT%"
set "AIPPT_FRONTEND_PORT=%FRONTEND_PORT%"

echo [AI-PPT] Frontend starting on http://127.0.0.1:%FRONTEND_PORT%

if /i "%OPEN_MODE%"=="open" (
    npm run dev -- --open
) else (
    npm run dev
)
