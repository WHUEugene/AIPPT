# Nano Banana 前后端进度记录

## 2025-05-26

- **Flask 接口**：`nano_banana_frontend_server.py` 现可读取 `config.yaml`，统一设置 OpenRouter API Key、URL、模型名以及服务监听端口，新增 `/generate`、`/` 两个路由。接口支持提示词 + 图片上传，自动构造 OpenRouter 请求，解析返回文本与图片。
- **前端页面**：`frontend/index.html` 提供最小化 UI，含提示词输入、参考图上传、加载状态、错误提示与图片展示，所有交互通过 `fetch('/generate')` 完成。
- **日志与留存**：服务端会把每次请求的信息写入 `logs/generation_log.md`，并把模型返回的第一张图片保存到 `logs/images/`，Markdown 中嵌入图片，方便回溯。
- **配置/依赖**：`config.yaml` 增加 `openrouter`、`server`、`logging` 三段；`requirements.txt` 包含 `flask`、`requests`、`PyYAML`。

> 后续如需扩展：可以在 `config.yaml` 切换模型或端口，或在前端添加历史记录展示。若想保存多张图片，只需放开当前服务端对返回数组的裁剪（`image_urls[:1]`）。
