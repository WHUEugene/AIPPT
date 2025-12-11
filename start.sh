#!/bin/bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   项目一键启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查是否在项目根目录
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}错误: 请在项目根目录下运行此脚本${NC}"
    exit 1
fi

# ========== 后端设置 ==========
echo -e "\n${YELLOW}[1/4] 设置后端环境...${NC}"
cd backend

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3，请先安装${NC}"
    exit 1
fi

# 安装后端依赖
echo -e "${YELLOW}安装后端依赖...${NC}"
pip install -r requirements.txt

# 配置环境变量
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}创建 .env 文件...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ .env 文件已创建，请编辑填入 API Key${NC}"
    else
        echo -e "${RED}警告: 未找到 .env.example 文件${NC}"
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi

cd ..

# ========== 前端设置 ==========
echo -e "\n${YELLOW}[2/4] 设置前端环境...${NC}"
cd frontend

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}错误: 未找到 Node.js，请先安装${NC}"
    exit 1
fi

# 安装前端依赖
echo -e "${YELLOW}安装前端依赖...${NC}"
npm install

cd ..

# ========== 启动服务 ==========
echo -e "\n${YELLOW}[3/4] 启动后端服务...${NC}"
cd backend
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✓ 后端服务已启动 (PID: $BACKEND_PID)${NC}"

# 等待后端启动
sleep 3

echo -e "\n${YELLOW}[4/4] 启动前端服务...${NC}"
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"

# ========== 完成 ==========
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   启动完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "后端服务: ${YELLOW}http://localhost:8000${NC}"
echo -e "前端服务: ${YELLOW}http://localhost:5173${NC}"
echo -e "\n按 ${RED}Ctrl+C${NC} 停止所有服务\n"

# 保存 PID 到文件，方便后续停止
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

# 等待用户中断
wait
