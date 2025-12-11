@echo off
chcp 65001 >nul
color 0A

echo ========================================
echo    AI-PPT Flow 一键启动脚本 (Windows)
echo ========================================

REM 检查是否在项目根目录
if not exist "backend" (
    echo [错误] 未找到 backend 目录
    goto :error
)
if not exist "frontend" (
    echo [错误] 未找到 frontend 目录
    goto :error
)

REM ========== 后端设置 ==========
echo.
echo [1/4] 设置后端环境...
cd backend

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    goto :error
)

REM 安装后端依赖
echo [后端] 安装依赖包...
pip install -r requirements.txt

REM 配置环境变量
if not exist ".env" (
    echo [后端] 创建 .env 文件...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [完成] .env 文件已创建，请编辑填入 OpenRouter API Key
        echo [提示] 也可以在前端设置界面配置 API Key
    ) else (
        echo [警告] 未找到 .env.example 文件
    )
) else (
    echo [完成] .env 文件已存在
)

cd ..

REM ========== 前端设置 ==========
echo.
echo [2/4] 设置前端环境...
cd frontend

REM 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    goto :error
)

REM 安装前端依赖
echo [前端] 安装依赖包...
call npm install

cd ..

REM ========== 启动服务 ==========
echo.
echo [3/4] 启动后端服务...
echo [后端] 启动在 http://localhost:8000
start "AI-PPT Backend" cmd /k "cd backend && uvicorn app.main:app --reload --port 8000"

REM 等待后端启动
timeout /t 3 /nobreak >nul

echo.
echo [4/4] 启动前端服务...
echo [前端] 启动在 http://localhost:5173
start "AI-PPT Frontend" cmd /k "cd frontend && npm run dev"

REM ========== 完成 ==========
echo.
echo ========================================
echo    🎉 启动完成！
echo ========================================
echo 📍 访问地址: http://localhost:5173
echo 📍 API 地址: http://localhost:8000
echo.
echo 💡 关闭此窗口不会停止服务
echo 🛑 请关闭对应的服务窗口来停止服务
echo 📝 首次使用请在前端设置界面配置 OpenRouter API Key
echo ========================================
echo.
echo 按任意键退出...
pause >nul
exit

:error
echo.
echo ========================================
echo    ❌ 启动失败
echo ========================================
echo 💡 请检查:
echo 1. 是否已安装 Python 3.10+
echo 2. 是否已安装 Node.js 18+
echo 3. 是否在项目根目录执行此脚本
echo.
echo 按任意键退出...
pause >nul
exit /b 1