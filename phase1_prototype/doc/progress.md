# Nano Banana 前后端进度记录

## 2025-05-26

- **Flask 接口**：`nano_banana_frontend_server.py` 现可读取 `config.yaml`，统一设置 OpenRouter API Key、URL、模型名以及服务监听端口，新增 `/generate`、`/` 两个路由。接口支持提示词 + 图片上传，自动构造 OpenRouter 请求，解析返回文本与图片。
- **前端页面**：`frontend/index.html` 提供最小化 UI，含提示词输入、参考图上传、加载状态、错误提示与图片展示，所有交互通过 `fetch('/generate')` 完成。
- **日志与留存**：服务端会把每次请求的信息写入 `logs/generation_log.md`，并把模型返回的第一张图片保存到 `logs/images/`，Markdown 中嵌入图片，方便回溯。
- **配置/依赖**：`config.yaml` 增加 `openrouter`、`server`、`logging` 三段；`requirements.txt` 包含 `flask`、`requests`、`PyYAML`。

> 后续如需扩展：可以在 `config.yaml` 切换模型或端口，或在前端添加历史记录展示。若想保存多张图片，只需放开当前服务端对返回数组的裁剪（`image_urls[:1]`）。

## 2025-12-28

- **图片编辑链路**：`/generate` 根据是否上传参考图走分支；带图时调用新增的 `call_image_edit_api`，以 multipart/form-data 方式访问 `IMAGE_EDIT_PATH`（默认 `v1/images/edits`），提交 `prompt`、`aspect_ratio`、`resolution`、`size` 等参数并兼容 `openrouter.image_edit_model` 配置。
- **普通生成链路**：纯文本仍沿用 `call_openrouter`，但新增 `openrouter.chat_path` 与 URL 规范化，确保 `base_url` 是否携带 `/v1` 都能正确路由。
- **结果解析**：新增 `parse_image_edit_outputs`，统一抽取返回的 `data[].url`/`b64_json` 并传给前端与日志层；图片仍存入 `logs/images/`。
- **错误追踪**：实现 `logs/error_log.md`，在 HTTP 错误或 JSON 解析失败时记录 Prompt、参考图、请求参数、状态码、响应片段与堆栈，方便排查 502/JSONDecodeError。
