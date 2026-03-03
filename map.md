# 项目地图（2026-03-03）

## 核心后端
- `backend/app/services/llm_client.py`
  - 统一封装聊天与出图请求。
  - 兼容 OpenRouter 与 OpenAI 兼容网关（含 `/v1` 路径回退）。
  - 负责响应解析、错误聚合、重试策略。
- `backend/app/routers/config.py`
  - 配置读取、更新、连接测试接口。
  - `/api/config/test` 支持传入超时时间并做联通性探测。
- `backend/app/schemas/config.py`
  - 配置与连接测试请求/响应数据结构定义。
- `backend/app/routers/export.py`
  - PPTX 导出入口 `/api/export/pptx`。
- `backend/app/services/pptx_exporter.py`
  - 将项目结构转为 PPTX 二进制。
  - 处理页面与图片装配。
- `backend/app/utils/logger.py`
  - Pipeline 级日志工具。
  - 当前已提供标准 logging 风格代理方法，避免调用不一致导致崩溃。

## 核心前端
- `frontend/src/pages/Settings.tsx`
  - AI 配置页面、连接测试交互。
  - 连接测试请求已携带 `timeout_seconds`，并按后端 `success` 展示结果。
- `frontend/src/store/useConfigStore.ts`
  - 配置状态管理与持久化调用。
  - 测试连接接口调用逻辑与页面保持一致。

## 运行与数据
- `backend/data/config.json`
  - 当前运行中的本地配置（含 API 地址、模型、超时）。
- `backend/data/projects/*.json`
  - 每个项目的状态快照与生成结果记录。
- `logs/`
  - Pipeline 与会话级日志输出目录。
