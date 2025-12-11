#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 切换到后端目录
cd "$SCRIPT_DIR/../backend"

# 创建必要的目录
mkdir -p generated/images generated/pptx

# 启动后端
python main.py
