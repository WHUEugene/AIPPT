@echo off
REM AI-PPT 启动脚本 (Windows)
REM 自动检测环境并启动前端和后端服务

echo 🚀 启动 AI-PPT 系统...

REM 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js 未安装，请先安装 Node.js
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 未安装，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ 环境检查通过

REM 启动后端
echo 🔧 启动后端服务...
cd backend

REM 检查虚拟环境
if not exist "venv" (
    echo 📦 创建 Python 虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 🔌 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
if exist "requirements.txt" (
    echo 📦 安装 Python 依赖...
    pip install -q -r requirements.txt
)

REM 启动后端服务 (新窗口)
echo 🚀 启动后端服务...
start "AI-PPT Backend" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload & pause"

REM 等待后端启动
echo ⏳ 等待后端服务启动...
timeout /t 5 /nobreak >nul

REM 返回项目根目录
cd ..

REM 启动前端
echo 🚀 启动前端服务...
cd frontend

REM 安装前端依赖
if not exist "node_modules" (
    echo 📦 安装前端依赖...
    npm install
)

REM 启动前端开发服务器 (新窗口)
echo 🎨 启动前端开发服务器...
start "AI-PPT Frontend" cmd /c "npm run dev & pause"

cd ..

echo.
echo 🎉 AI-PPT 系统启动完成！
echo.
echo 📍 服务地址:
echo    🖥️  前端: http://localhost:5173
echo    ⚙️  后端: http://localhost:8000
echo    📚 API文档: http://localhost:8000/docs
echo.
echo 🛑 停止服务: 关闭对应的命令行窗口即可
echo.

REM 询问是否打开浏览器
set /p open_browser="是否打开浏览器? (y/n): "
if /i "%open_browser%"=="y" (
    echo 🌐 正在打开浏览器...
    start http://localhost:5173
)

echo.
echo 脚本执行完成！请保持此窗口开启，服务在独立窗口中运行。
echo 按任意键关闭此窗口...
pause >nul