# 项目地图（2026-03-10）

## 后端核心
- `backend/app/services/llm_client.py`
  - 统一封装文本与图像网关调用。
  - 支持 OpenRouter 和 OpenAI 兼容网关，自动补 `/v1`，并区分文本/图片路由。
- `backend/app/dependencies.py`
  - 统一装配文本 LLM、图片 LLM、导出器、模板存储。
  - 当前已支持图片网关独立配置与缓存清理。
- `backend/app/services/image_generator.py`
  - 单页生图入口。
  - 实际图片输出目录由运行配置决定，目前会写到 `generated/images/`。
- `backend/app/services/batch_image_generator.py`
  - 批量生图调度。
  - 默认并发已改为按图片数量开满，由路由层做上限约束。
- `backend/app/services/pptx_exporter.py`
  - PPTX 导出核心。
  - 当前按首张有效图片比例决定整套页面尺寸，并在导出前做高质量重编码。
- `backend/app/services/style_analyzer.py`
  - 模板图片风格分析。
  - 当前会汇总多图客观统计，并输出更偏 PPT 生图规则的模板级 `style_prompt`。
- `backend/app/services/template_store.py`
  - 模板 JSON 存储。
  - 已支持模板新增、查询、更新。

## 后端接口
- `backend/app/routers/slide.py`
  - 单页重绘、批量生图接口。
  - 批量生图已按请求页数并发执行。
- `backend/app/routers/template.py`
  - 模板分析、模板列表、模板保存、模板更新。
- `backend/app/routers/config.py`
  - 配置读取、保存、测试连接。
  - 配置更新后会清理依赖缓存，确保新网关即时生效。
- `backend/app/routers/export.py`
  - PPTX 导出入口。

## 前端核心页面
- `frontend/src/pages/TemplateSelect.tsx`
  - 模板选择页。
  - 已支持模板编辑入口和无封面模板的一键生成示例图。
- `frontend/src/pages/TemplateCreate.tsx`
  - 新建/编辑模板共用页。
  - 已支持修改模板名称、提示词、参考图和封面示例图。
- `frontend/src/pages/ContentInput.tsx`
  - 文档导入、大纲生成入口。
- `frontend/src/pages/Workspace.tsx`
  - 幻灯片编辑、单页重绘、批量生图、导出。
  - 单页重绘已支持最多 3 张并发，并带顶部状态条。
- `frontend/src/pages/Settings.tsx`
  - 网关与模型配置页面。
  - 已支持图像网关独立覆盖字段。

## 前端状态与服务
- `frontend/src/services/api.ts`
  - 封装模板、配置、大纲、生图、导出接口。
  - 已支持模板更新接口。
- `frontend/src/store/useProjectStore.ts`
  - 项目、幻灯片、模板的本地状态。
  - 已支持模板 `upsert`，便于编辑后就地覆盖。
- `frontend/src/store/useConfigStore.ts`
  - 配置读取与保存。

## 数据与运行目录
- `backend/data/templates.json`
  - 当前主模板库。
- `backend/data/projects/*.json`
  - 已保存项目快照。
- `generated/images/`
  - 当前运行配置下的图片输出目录。
- `backend/generated/pptx/`
  - 导出的 PPTX 文件目录。
