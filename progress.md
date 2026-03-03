# 进度记录

## 2024-05-14
- 更新 `frontend/src/pages/Workspace.tsx` 右侧面板：新增标题/正文可编辑区、提示词只读区，并重排现有设定与比例控制，支持完整编辑生成 prompt。

## 2026-03-03
- 接入 OpenAI 兼容网关能力（ChatFire）：`/chat/completions` 与 `/v1/chat/completions` 自动回退，兼容不同网关路径。
- 保留 OpenRouter 兼容：仅在 OpenRouter 域名下附加 `HTTP-Referer` 与 `X-Title` 请求头。
- 增强 LLM 调用稳定性：对 `429/5xx` 增加轻量重试与更清晰的错误信息输出。
- 完成图像返回兼容解析：支持 `message.images`、`image_url`、Markdown 图片链接、`images/generations` 的 URL 与 Base64。
- 修复配置连接测试流程：前后端支持 `timeout_seconds`，前端按后端 `success` 字段判定测试结果。
- 修复 PPTX 导出崩溃：为 `PipelineLogger` 增加标准日志代理方法（`error/info/warning/exception`），解决导出时 `AttributeError`。
- 本地验证通过：配置测试、文本请求、图像请求、PPTX 导出链路均可执行。
