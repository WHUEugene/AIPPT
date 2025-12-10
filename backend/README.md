# AI-PPT Flow – Backend

FastAPI 服务，负责模板管理、文本大纲生成、Prompt 组装、图片占位生成以及 PPTX 导出。前端 Electron/React 客户端可以通过统一的 REST 接口调用本服务。

## 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # Settings & 路径配置
│   ├── dependencies.py      # Service 单例工厂
│   ├── routers/             # template/outline/slide/export API
│   ├── schemas/             # Pydantic 数据模型
│   └── services/            # Prompt/分析/导出等核心逻辑
├── data/templates.json      # 模版持久化（JSON）
├── generated/               # 占位图片与 PPTX 输出
├── requirements.txt
└── .env.example
```

## 快速启动

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
echo "LLM_API_KEY=sk-..." >> .env    # 将 OpenRouter 提供的 Key 写入此处
uvicorn app.main:app --reload --port 8000
```

启动后，`GET /` 会返回健康检查信息，静态图片可通过 `/assets/<filename>` 访问。

## API 摘要

| Endpoint | Method | 说明 |
| --- | --- | --- |
| `/api/template/analyze` | POST (multipart) | 上传 1~N 张参考图，返回结构化风格 Prompt。|
| `/api/template` | GET | 列出所有保存的模版。|
| `/api/template/save` | POST | 保存模版名称、封面、Style Prompt。|
| `/api/outline/generate` | POST | 根据文本 + 目标页数生成分页大纲，每页包含 `visual_desc`。|
| `/api/slide/generate` | POST | 组合 Style Prompt 与 visual_desc，调用 Gemini 图像模型返回图片 URL。|
| `/api/slide/regenerate` | POST | 同上，通常用于修改 Prompt 后重绘。|
| `/api/export/pptx` | POST | 接收项目 JSON，返回 PPTX 二进制流。|

> 已接入 OpenRouter：`google/gemini-3-pro-preview` 负责风格分析/大纲生成，`google/gemini-3-pro-image-preview` 负责绘图。若缺少 `LLM_API_KEY` 会自动回退到占位算法。

## 数据结构要点

- **Template**：`{ id, name, style_prompt, cover_image?, vis_settings? }`
- **SlideData**：`{ id, page_num, type, title, content_text, visual_desc, final_prompt?, image_url?, status }`
- **ProjectState**：`{ template_id?, template_style_prompt?, title?, slides: SlideData[] }`

`TemplateStore` 使用 `backend/data/templates.json` 作为轻量数据库，线程安全写入。`PPTXExporter` 会读取 `ProjectState` 中的图片 URL（局部 `/assets/...`），并将图像铺满每一页后添加文本框。

## 后续扩展建议

1. 在生产环境使用更可靠的持久化（数据库/对象存储）。
2. 增加调度与排队逻辑，避免 LLM/API 限流。
3. 结合用户体系扩展项目历史、并发管理等能力。
