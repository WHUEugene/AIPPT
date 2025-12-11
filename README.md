# AI-PPT Flow 🚀

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-cyan.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Powered by Gemini](https://img.shields.io/badge/AI-Gemini%203%20Pro-purple)](https://deepmind.google/technologies/gemini/)

**AI-PPT Flow** 是一个基于大语言模型 (LLM) 和视觉语言模型 (VLM) 的自动化PPT生成系统。

它不仅仅是生成文字，更能**理解视觉风格**。通过上传一张参考图，系统能自动克隆其配色、构图和材质，并将您的文档内容转化为风格统一、图文并茂的专业 PPT。

---

## ✨ 核心特性

###  🎨视觉风格克隆

拒绝千篇一律的模版。上传任意一张您喜欢的图片作为参考，系统会自动提取其**配色方案、光影质感、构图逻辑**，并将其应用到生成的每一页幻灯片中。

### 📝 智能大纲编剧

输入一段长文档或简单的想法，内置的 AI 编剧会自动将其拆解为结构清晰的幻灯片大纲（封面、目录、内容页、封底），并为每一页设计专属的画面描述。

### 🖼️图文一体化生成

利用最新的 **Google Gemini 3 Pro** 模型，生成的不仅仅是背景图，而是包含**可读文字**和**精准图表**的完整幻灯片画面。文字与图像完美融合，告别"图文分离"的割裂感。

### ⚡️高性能批量渲染

内置**多进程并发引擎**，支持 10+ 页幻灯片同时生成。相比传统串行生成，速度提升 **5-10 倍**。5 页精美 PPT，仅需数十秒。

###  🛠️所见即所得

提供完整的可视化工作区。支持实时修改提示词、重新生成单页、调整幻灯片比例（16:9, 4:3, 手机竖屏等），并一键导出为 `.pptx` 文件。

---

## 🎯 效果展示
<div align="center">
  <img src="./doc/promo/幻灯片1.jpg" alt="幻灯片1 - 封面页" width="45%">
  <img src="./doc/promo/幻灯片2.jpg" alt="幻灯片2 - 目录页" width="45%">
</div>

<div align="center">
  <img src="./doc/promo/幻灯片3.jpg" alt="幻灯片3 - 内容页" width="45%">
  <img src="./doc/promo/幻灯片4.jpg" alt="幻灯片4 - 数据展示" width="45%">
</div>

<div align="center">
  <img src="./doc/promo/幻灯片5.jpg" alt="幻灯片5 - 分析页" width="45%">
  <img src="./doc/promo/幻灯片6.jpg" alt="幻灯片6 - 总结页" width="45%">
</div>

---

## 📸 界面展示

<div align="center">
  <img src="./doc/img/首页.png" alt="首页界面" width="48%">
  <img src="./doc/img/大纲生成.png" alt="大纲生成界面" width="48%">
</div>

<div align="center">
  <img src="./doc/img/新建风格.png" alt="新建风格界面" width="48%">
  <img src="./doc/img/项目展示.png" alt="项目展示界面" width="48%">
</div>

<div align="center">
  <img src="./doc/img/image-20251210192632612.png" alt="配置管理界面" width="48%">
  <img src="./doc/img/界面展示补充.png" alt="界面展示补充" width="48%">
</div>

*上传参考图，AI 自动提取风格特征，并根据文档生成分页大纲。*

*实时预览生成的幻灯片，支持多进程批量并发生成，实时显示进度。*

*可视化的配置管理界面，支持自定义 API Key、模型参数及幻灯片尺寸。*
---

## 🏗️ 系统架构

AI-PPT Flow 采用现代化的前后端分离架构：

*   **前端**: React 18 + TypeScript + Vite + Tailwind CSS (状态管理: Zustand)
*   **后端**: FastAPI + Python 3.10 (ProcessPoolExecutor 多进程架构)
*   **AI 服务**: OpenRouter (Gemini 3 Pro Preview / Image Mode)
*   **核心 Pipeline**:
    1.  `StyleAnalyzer`: 像素分析 + LLM 风格提取
    2.  `OutlineGenerator`: 文本结构化拆解
    3.  `PromptBuilder`: 风格 + 内容 + 约束组装
    4.  `BatchImageGenerator`: 多进程并发图像生成
    5.  `PPTXExporter`: 最终文件合成

---

## 🚀 快速开始

### 前置要求
*   Python 3.10+
*   Node.js 18+
*   OpenRouter API Key (支持 Gemini 3 Pro)

### 1. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (复制 .env.example)
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY / 或者在前端设置界面配置

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:5173` 即可开始使用。

### 🚀 快速启动（推荐）

为了简化启动流程，我们提供了一键启动脚本：

#### Windows 用户
```bash
# 在项目根目录执行
start.bat
```

#### Linux/macOS 用户  
```bash
# 在项目根目录执行
chmod +x start.sh
./start.sh
```

脚本会自动：
- 检查并安装后端依赖
- 启动后端服务（端口 8000）
- 检查并安装前端依赖
- 启动前端开发服务器（端口 5173）

---

## ⚙️ 配置指南

项目支持通过 Web 界面动态修改配置，无需重启服务：

*   **AI 模型**: 支持切换 Chat 模型和 Image 模型。
*   **并发数**: 建议根据服务器性能调整 `Max Workers` (推荐 3-5)。
*   **存储路径**: 自定义图片和项目文件的保存位置。

配置文件默认位于 `backend/data/config.json`。

---

## 🗺️ 开发路线图 (Roadmap)

- [x] **v1.0**: 基础流程跑通 (风格分析 -> 大纲 -> 单图生成 -> 导出)
- [x] **v1.1**: 批量生成 (多进程优化) & 前端体验升级
- [x] **v1.2**: 项目管理 (自动保存/历史记录) & 系统配置中心
- [ ] **v1.3**: 图片ppt——》可编辑PPTX解析
- [ ] **v2.0**: 多人协作编辑 & 更多 AI 模型支持 (Midjourney/DALL-E 3)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。
