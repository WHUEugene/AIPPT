这是一个根据项目设计与开发演进顺序重新整理的综合技术文档。该文档将项目从基础架构搭建、核心功能实现、性能优化到系统配置管理的完整开发历程进行了逻辑串联。

---

# AI-PPT Flow 项目设计与开发演进文档

**版本**: 1.2.0 (综合版)  
**最后更新**: 2025-12-10

## 目录

1.  [第一阶段：核心架构与MVP基础 (Foundation)](#第一阶段核心架构与mvp基础-foundation)
2.  [第二阶段：数据持久化与项目管理 (Project Management)](#第二阶段数据持久化与项目管理-project-management)
3.  [第三阶段：批量生成功能与并发设计 (Batch Generation)](#第三阶段批量生成功能与并发设计-batch-generation)
4.  [第四阶段：性能重构 - 多进程优化 (Performance Optimization)](#第四阶段性能重构---多进程优化-performance-optimization)
5.  [第五阶段：高级配置与自定义功能 (Configuration & Customization)](#第五阶段高级配置与自定义功能-configuration--customization)
6.  [附录：系统部署与API参考](#附录系统部署与api参考)

---

## 第一阶段：核心架构与MVP基础 (Foundation)

### 1.1 项目概述
AI-PPT Flow 是一个基于大语言模型（LLM）和视觉语言模型（VLM）的自动化演示文稿生成系统。项目旨在通过用户上传的参考模板和文档内容，自动生成风格统一、结构清晰的PPT。

### 1.2 系统架构
采用前后端分离架构：
*   **前端**: React 18 + TypeScript + Vite + Tailwind CSS (状态管理: Zustand)
*   **后端**: FastAPI + Python 3.10 (异步处理: asyncio)
*   **AI服务**: OpenRouter (Google Gemini 3 Pro / Image Preview)

### 1.3 核心组件设计
MVP阶段确立了五个核心服务组件：

1.  **风格分析器 (StyleAnalyzer)**
    *   **功能**: 分析上传的模板图片，提取视觉风格（配色、构图、材质）。
    *   **技术**: 结合像素级分析（OpenCV/PIL）与 LLM 视觉理解，输出结构化的 Style Prompt。

2.  **大纲生成器 (OutlineGenerator)**
    *   **功能**: 将长文档拆解为 JSON 格式的幻灯片大纲（封面、目录、内容页）。
    *   **技术**: 使用 LLM 进行文本摘要和结构化提取，包含备用的本地拆分算法。

3.  **提示词构建器 (PromptBuilder)**
    *   **功能**: 组装用于绘图的最终提示词。
    *   **逻辑**: `Style Prompt` + `Visual Description` + `Content Text` + `Aspect Ratio Constraint`。

4.  **图像生成器 (ImageGenerator)**
    *   **功能**: 调用 VLM API 生成幻灯片背景图。
    *   **演进**: 从旧版 `generate_image` 接口迁移至新的 Chat Completions 接口（支持 modalities: ["image", "text"]），直接返回 Base64 或 URL。

5.  **PPTX导出器 (PPTXExporter)**
    *   **功能**: 使用 `python-pptx` 将生成的图片和文本合成为可编辑的 `.pptx` 文件。

---

## 第二阶段：数据持久化与项目管理 (Project Management)

随着基础生成功能的跑通，系统引入了项目状态管理和数据持久化能力。

### 2.1 存储系统设计
*   **本地存储**: 项目数据持久化到 `backend/data/projects/`。
*   **数据结构**:
    *   `ProjectSchema`: 包含项目ID、标题、创建/更新时间、模板信息及幻灯片列表。
    *   自动生成项目缩略图和元数据。

### 2.2 功能实现
*   **自动保存**:
    *   批量生成完成后自动保存。
    *   编辑内容后 5 分钟自动保存。
*   **历史记录 (History)**:
    *   前端新增 History 页面，支持查看、继续编辑和删除历史项目。
    *   支持项目恢复和页面关闭前的未保存提醒。

---

## 第三阶段：批量生成功能与并发设计 (Batch Generation)

为了解决单张生成效率低下的问题（单张需15-30秒，5页需2分钟以上），开发了批量生成系统。

### 3.1 接口设计
新增 `POST /api/slide/batch/generate` 接口：
```json
{
  "slides": [...],
  "style_prompt": "...",
  "max_workers": 3,
  "aspect_ratio": "16:9"
}
```
以及状态查询接口 `POST /api/slide/batch/status`，支持前端轮询进度。

### 3.2 初始并发策略 (基于线程池)
最初版本使用 `ThreadPoolExecutor` 配合 `asyncio`。
*   **并发控制**: 允许配置 `max_workers` (1-10)。
*   **状态跟踪**: 引入 `session_id`，记录每个幻灯片的生成状态（pending/generating/done/failed）。
*   **前端优化**: 进入页面自动检测并触发批量生成，实时显示进度条。

### 3.3 并发配置指南
制定了不同负载下的配置建议：
*   **1-3张**: 2-3 并发
*   **4-10张**: 5-8 并发 (最佳性能区间)
*   **20+张**: 建议分批处理或使用 12-20 并发 (需注意 API Rate Limit)

---

## 第四阶段：性能重构 - 多进程优化 (Performance Optimization)

在批量功能上线后，发现性能瓶颈：设置多个 workers 但速度提升不明显。

### 4.1 问题诊断
*   **现象**: `ThreadPoolExecutor` + `asyncio.run()` 导致任务实际上是串行或伪并发执行。
*   **根因**: Python 的 **GIL (全局解释器锁)** 限制了同一时刻只能有一个线程执行 Python 字节码。虽然网络 I/O 会释放 GIL，但在处理大量胶水逻辑和对象创建时，线程竞争导致效率低下。

### 4.2 架构重构 (Threading -> Multiprocessing)
将 `ThreadPoolExecutor` 替换为 `ProcessPoolExecutor`，实现真正的并行计算。

**核心改动**:
1.  **独立 Worker 函数**:
    创建模块级函数 `_generate_slide_worker`，在每个进程中独立初始化 `OpenRouterClient` 和 `ImageGenerator`，避免跨进程共享对象的复杂性。
    ```python
    def _generate_slide_worker(slide_data, style_prompt, ...):
        # 每个进程独立的事件循环
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(generate_image())
        return result
    ```

2.  **数据序列化**:
    *   将 `SlideData` 对象转换为字典进行进程间传递。
    *   配置信息序列化传递，结果反序列化。

3.  **智能并发配置**:
    ```python
    # 自动优化：1-10页使用页数个worker，上限为10
    if max_workers is None:
        max_workers = min(len(slides), 10)
    ```

### 4.3 优化成果
*   **性能提升**: 理论提升 5-10 倍。总耗时从"所有幻灯片生成时间之和"缩短为"最慢那张幻灯片的生成时间"。
*   **资源利用**: 充分利用多核 CPU。

---

## 第五阶段：高级配置与自定义功能 (Configuration & Customization)

为了提升系统的灵活性和易用性，最近（2025-12-10）增加了系统级配置和画面比例控制。

### 5.1 模版比例与尺寸设定
*   **后端**:
    *   `DimensionCalculator` 工具类：支持 16:9, 4:3, 1:1, 9:16, 21:9 等标准比例及自定义尺寸计算。
    *   PromptBuilder 适配：将尺寸约束写入提示词。
*   **前端**:
    *   新增 `AspectRatioSelector` 组件。
    *   支持在 Workspace 实时修改比例，触发重新生成。

### 5.2 系统配置管理 (Config Manager)
实现了完整的配置管理系统，允许用户通过 UI 修改后端参数。

*   **架构**:
    *   `ConfigManager`: 处理配置的读取、更新、验证和重置。
    *   配置文件: `backend/data/config.json` (含备份机制)。
*   **功能**:
    *   **API 设置**: 动态修改 OpenRouter Key、Base URL、模型名称。
    *   **连接测试**: UI 增加"测试连接"按钮，验证 AI 服务连通性。
    *   **安全**: API Key 前端脱敏显示。

---

## 附录：系统部署与API参考

### 部署环境
*   **Backend**: Python 3.10+, FastAPI, Uvicorn
*   **Frontend**: Node.js 18+, React, Vite
*   **Docker**: 支持 Docker Compose 一键部署

### 关键 API 概览

| 功能     | 方法 | 路径                        | 描述               |
| :------- | :--- | :-------------------------- | :----------------- |
| **生成** | POST | `/api/slide/batch/generate` | 多进程批量生成图片 |
| **状态** | POST | `/api/slide/batch/status`   | 查询批量任务进度   |
| **配置** | GET  | `/api/config/`              | 获取当前系统配置   |
| **配置** | POST | `/api/config/update`        | 更新系统配置       |
| **项目** | POST | `/api/projects/save`        | 保存项目状态       |
| **导出** | POST | `/api/export/pptx`          | 导出 PPTX 文件     |

### 监控与调试
*   **日志位置**: `logs/pipeline_YYYYMMDD.log`
*   **性能指标**:
    *   查看批量任务统计: `grep "batch_generate_complete" logs/...`
    *   查看单页生成时间: `grep "slide_completed" logs/...`