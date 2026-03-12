@echo off
setlocal

set "BACKEND_DIR=%~1"
set "CONDA_CMD=%~2"
set "CONDA_ENV_NAME=%~3"
set "BACKEND_PORT=%~4"

if not exist "%BACKEND_DIR%" (
    echo [ERROR] Backend directory not found: %BACKEND_DIR%
    exit /b 1
)

cd /d "%BACKEND_DIR%"
echo [AI-PPT] Backend starting on http://127.0.0.1:%BACKEND_PORT%
"%CONDA_CMD%" run -n %CONDA_ENV_NAME% python -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT%
