@echo off
setlocal

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

set "CONDA_ENV_NAME=aippt-win"
set "PYTHON_VERSION=3.11"
set "BACKEND_PORT=18000"
set "FRONTEND_PORT=15173"
set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "BACKEND_LAUNCHER=%ROOT_DIR%\scripts\start-backend-window.bat"
set "FRONTEND_LAUNCHER=%ROOT_DIR%\scripts\start-frontend-window.bat"
set "CONDA_CMD="

echo [AI-PPT] Preparing local Windows environment...

if defined CONDA_EXE (
    set "CONDA_CMD=%CONDA_EXE%"
)

if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda.exe 2^>nul') do if not defined CONDA_CMD set "CONDA_CMD=%%I"
)

if not defined CONDA_CMD (
    echo [ERROR] conda.exe was not found in PATH.
    echo Open an Anaconda Prompt or add conda.exe to PATH, then rerun this script.
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js was not found in PATH.
    echo Install Node.js 18+ and rerun this script.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found in PATH.
    echo Install Node.js 18+ and rerun this script.
    pause
    exit /b 1
)

if not exist "%BACKEND_DIR%" (
    echo [ERROR] Missing backend directory: %BACKEND_DIR%
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Missing frontend directory: %FRONTEND_DIR%
    pause
    exit /b 1
)

if not exist "%BACKEND_LAUNCHER%" (
    echo [ERROR] Missing backend launcher: %BACKEND_LAUNCHER%
    pause
    exit /b 1
)

if not exist "%FRONTEND_LAUNCHER%" (
    echo [ERROR] Missing frontend launcher: %FRONTEND_LAUNCHER%
    pause
    exit /b 1
)

"%CONDA_CMD%" run -n %CONDA_ENV_NAME% python --version >nul 2>&1
if errorlevel 1 (
    echo [AI-PPT] Creating conda environment "%CONDA_ENV_NAME%" with Python %PYTHON_VERSION%...
    "%CONDA_CMD%" create -y -n %CONDA_ENV_NAME% python=%PYTHON_VERSION%
    if errorlevel 1 goto :fail
) else (
    echo [AI-PPT] Using existing conda environment "%CONDA_ENV_NAME%".
)

if not exist "%BACKEND_DIR%\generated\images" mkdir "%BACKEND_DIR%\generated\images"
if not exist "%BACKEND_DIR%\generated\pptx" mkdir "%BACKEND_DIR%\generated\pptx"

"%CONDA_CMD%" run -n %CONDA_ENV_NAME% python -c "import fastapi, uvicorn, PIL, pptx, httpx" >nul 2>&1
if errorlevel 1 (
    echo [AI-PPT] Installing backend requirements into "%CONDA_ENV_NAME%"...
    "%CONDA_CMD%" run -n %CONDA_ENV_NAME% python -m pip install --upgrade pip
    if errorlevel 1 goto :fail
    "%CONDA_CMD%" run -n %CONDA_ENV_NAME% python -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if errorlevel 1 goto :fail
) else (
    echo [AI-PPT] Backend Python dependencies already available.
)

if not exist "%FRONTEND_DIR%\node_modules\.bin\vite.cmd" (
    echo [AI-PPT] Installing frontend dependencies...
    pushd "%FRONTEND_DIR%"
    call npm install
    set "NPM_EXIT=%ERRORLEVEL%"
    popd
    if not "%NPM_EXIT%"=="0" goto :fail
) else (
    echo [AI-PPT] Frontend dependencies already available.
)

call :find_free_port BACKEND_PORT
call :find_free_port FRONTEND_PORT

echo [AI-PPT] Selected backend port: %BACKEND_PORT%
echo [AI-PPT] Selected frontend port: %FRONTEND_PORT%

set "FRONTEND_EXTRA_ARGS="
set /p OPEN_BROWSER="Open the frontend automatically after startup? (y/n): "
if /i "%OPEN_BROWSER%"=="y" set "FRONTEND_EXTRA_ARGS=open"

echo [AI-PPT] Launching backend window...
start "AI-PPT Backend" cmd /k ""%BACKEND_LAUNCHER%" "%BACKEND_DIR%" "%CONDA_CMD%" "%CONDA_ENV_NAME%" "%BACKEND_PORT%""

echo [AI-PPT] Waiting for backend to warm up...
timeout /t 3 /nobreak >nul

echo [AI-PPT] Launching frontend window...
start "AI-PPT Frontend" cmd /k ""%FRONTEND_LAUNCHER%" "%FRONTEND_DIR%" "%BACKEND_PORT%" "%FRONTEND_PORT%" "%FRONTEND_EXTRA_ARGS%""

echo.
echo [AI-PPT] Startup windows have been launched.
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo API docs: http://127.0.0.1:%BACKEND_PORT%/docs
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo The frontend window will open the correct URL if you chose auto-open.
echo.
echo Close the backend and frontend windows to stop the services.
pause
exit /b 0

:fail
echo.
echo [ERROR] Startup preparation failed.
echo Fix the message above and rerun start.bat.
pause
exit /b 1

:find_free_port
setlocal EnableDelayedExpansion
set "PORT_VALUE=!%~1!"

:find_free_port_loop
netstat -ano | findstr /R /C:":!PORT_VALUE! .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    set /a PORT_VALUE+=1
    goto :find_free_port_loop
)

endlocal & set "%~1=%PORT_VALUE%"
goto :eof
