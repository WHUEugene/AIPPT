# 批量图片生成接口使用说明

## 概述

新的批量图片生成接口支持多进程并发生成所有幻灯片图片，大幅提升生成效率。接口设计基于现有的单个图片生成逻辑，并添加了详细的日志记录和状态跟踪。

## 新增的接口

### 1. 批量生成接口 `POST /api/slide/batch/generate`

**请求体**：
```json
{
  "slides": [
    {
      "id": "uuid",
      "page_num": 1,
      "type": "cover",
      "title": "封面标题",
      "content_text": "封面内容",
      "visual_desc": "视觉描述"
    }
  ],
  "style_prompt": "统一的风格提示词...",
  "max_workers": 3,
  "aspect_ratio": "16:9"
}
```

**响应体**：
```json
{
  "batch_id": "uuid",
  "total_slides": 5,
  "successful": 4,
  "failed": 1,
  "total_time": 45.2,
  "results": [
    {
      "slide_id": "uuid",
      "page_num": 1,
      "title": "幻灯片标题",
      "image_url": "/assets/slide_xxx.jpg",
      "final_prompt": "生成的完整提示词...",
      "status": "done",
      "error_message": null,
      "generation_time": 8.5
    }
  ]
}
```

### 2. 批量状态查询接口 `POST /api/slide/batch/status`

**请求体**：
```json
{
  "batch_id": "uuid"
}
```

**响应体**：
```json
{
  "batch_id": "uuid",
  "status": "completed",
  "progress": 1.0,
  "total_slides": 5,
  "completed_slides": 5,
  "successful": 4,
  "failed": 1,
  "estimated_remaining_time": null,
  "results": [...]
}
```

### 3. 活跃批量任务数量查询 `GET /api/slide/batch/active-count`

**响应体**：
```json
{
  "active_batches": 2
}
```

## 核心特性

### 1. 多进程并发生成
- 使用 `ThreadPoolExecutor` 实现真正的并发处理
- 可配置最大并发数（1-10）
- 每个幻灯片独立生成，互不影响

### 2. 详细日志记录
- 每个批量任务都有唯一的 `session_id`
- 记录每个幻灯片的生成状态和时间
- 错误信息和异常详情完整记录
- 支持按会话查询日志文件

### 3. 状态跟踪
- 实时进度跟踪（0.0 - 1.0）
- 预计剩余时间计算
- 成功/失败统计
- 支持任务完成后的状态查询

### 4. 错误处理
- 单个幻灯片失败不影响其他幻灯片生成
- 详细的错误信息记录
- 支持部分成功的场景

## 性能优化

### 1. 并发控制
```python
# 默认并发数为3，可根据API限制调整
max_workers = 3  # 建议值：3-5

# API限制考虑
# - OpenRouter API 有并发限制
# - 建议不超过API的速率限制
```

### 2. 超时处理
```python
# 批量任务最大等待时间
max_wait_time = 300  # 5分钟

# 状态查询间隔
wait_interval = 2    # 2秒
```

### 3. 内存管理
- 自动清理已完成的批量任务（默认24小时）
- 结果按需获取，避免内存泄漏

## 使用示例

### Python 客户端示例
```python
import requests
import json

# 1. 批量生成
batch_request = {
    "slides": [
        {
            "id": "slide-1",
            "page_num": 1,
            "type": "cover",
            "title": "项目汇报",
            "content_text": "AI-PPT Flow 项目进展",
            "visual_desc": "现代简约风格，科技感背景"
        },
        # ... 更多幻灯片
    ],
    "style_prompt": "现代科技风格，蓝色调，简洁专业",
    "max_workers": 3,
    "aspect_ratio": "16:9"
}

response = requests.post(
    "http://localhost:8000/api/slide/batch/generate",
    json=batch_request
)

result = response.json()
print(f"批量任务ID: {result['batch_id']}")
print(f"成功: {result['successful']}, 失败: {result['failed']}")
print(f"总耗时: {result['total_time']}秒")

# 2. 查询状态（可选，因为接口会等待完成）
status_request = {
    "batch_id": result['batch_id']
}

status_response = requests.post(
    "http://localhost:8000/api/slide/batch/status",
    json=status_request
)

status = status_response.json()
print(f"进度: {status['progress']:.1%}")
print(f"状态: {status['status']}")
```

### 前端集成示例
```javascript
// 批量生成
async function batchGenerateSlides(slides, stylePrompt) {
  const response = await fetch('/api/slide/batch/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      slides: slides,
      style_prompt: stylePrompt,
      max_workers: 3,
      aspect_ratio: '16:9'
    })
  });
  
  const result = await response.json();
  return result;
}

// 轮询状态（如果使用异步模式）
async function pollBatchStatus(batchId) {
  const checkStatus = async () => {
    const response = await fetch('/api/slide/batch/status', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ batch_id: batchId })
    });
    
    const status = await response.json();
    
    if (status.status === 'completed' || status.status === 'failed') {
      return status;
    }
    
    // 继续轮询
    await new Promise(resolve => setTimeout(resolve, 2000));
    return checkStatus();
  };
  
  return checkStatus();
}
```

## 监控和调试

### 1. 日志文件位置
- 主日志：`logs/pipeline_YYYYMMDD.log`
- 会话日志：`logs/sessions/{session_id}_{action}.json`

### 2. 日志内容
- 批量任务开始和结束
- 每个幻灯片的生成状态
- LLM API 调用详情
- 错误信息和异常堆栈

### 3. 性能指标
```bash
# 查看批量任务统计
grep "batch_generate_complete" logs/pipeline_$(date +%Y%m%d).log | \
  jq '.summary | {total_slides, successful, failed, success_rate: (.successful/.total_slides*100)}'

# 查看平均生成时间
grep "slide_completed" logs/pipeline_$(date +%Y%m%d).log | \
  jq '.details.generation_time' | awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'
```

## 配置建议

### 1. 并发数设置
- **开发环境**: 1-2 个并发
- **生产环境**: 3-5 个并发
- **考虑因素**: API 限制、服务器性能、网络带宽

### 2. 超时设置
- 单个幻灯片生成: 60-120秒
- 批量任务总超时: 300-600秒
- 根据幻灯片数量和复杂度调整

### 3. 错误重试
- 目前实现中没有自动重试
- 可以在前端实现失败幻灯片的单独重试
- 建议对网络错误进行重试

## 与现有接口的兼容性

- 完全兼容现有的单个图片生成接口
- 可以混合使用单个和批量生成接口
- 共享相同的图片生成逻辑和配置
- 使用相同的图片存储路径和URL规则

## 未来改进方向

1. **异步任务队列**: 使用 Redis/RQ 实现真正的异步处理
2. **WebSocket 实时推送**: 实时进度更新
3. **智能调度**: 根据API负载动态调整并发数
4. **结果缓存**: 缓存相似请求的生成结果
5. **断点续传**: 支持中断后从失败点继续生成