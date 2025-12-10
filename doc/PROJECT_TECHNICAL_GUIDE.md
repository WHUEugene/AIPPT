# AI-PPT Flow 项目技术文档

## 项目概述

AI-PPT Flow 是一个基于大语言模型（LLM）和视觉语言模型（VLM）的自动化演示文稿生成系统。用户可以通过上传参考模板、输入文档内容，自动生成具有统一视觉风格的PPT幻灯片。

### 核心特性

- 🎨 **风格一致性**: 基于上传模板自动提取视觉风格，保持整个PPT的统一性
- 📝 **智能大纲**: 自动将长文档拆解为结构化的幻灯片大纲
- 🖼️ **图像生成**: 使用最新的 VLM 技术生成高质量的幻灯片背景图
- 🔄 **交互编辑**: 支持实时预览和重新生成，提供所见即所得的编辑体验
- 📄 **多格式导出**: 支持导出为标准的 PowerPoint (.pptx) 格式

## 系统架构

### 整体架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端 (React)   │────│  后端 (FastAPI)  │────│   AI 服务 (OpenRouter)   │
│                 │    │                 │    │                 │
│ - 用户界面      │    │ - REST API      │    │ - Gemini 3 Pro  │
│ - 状态管理      │    │ - 业务逻辑      │    │ - 图像生成      │
│ - 文件上传      │    │ - 数据持久化    │    │ - 文本处理      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 技术栈

#### 前端 (Frontend)
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **UI组件**: 自定义组件 + Lucide React 图标
- **状态管理**: Zustand
- **HTTP客户端**: Fetch API

#### 后端 (Backend)
- **框架**: FastAPI + Python 3.10
- **异步处理**: asyncio + httpx
- **图像处理**: Pillow (PIL)
- **文档生成**: python-pptx
- **配置管理**: pydantic-settings

#### 外部服务 (External Services)
- **AI提供商**: OpenRouter
- **文本模型**: Google Gemini 3 Pro Preview
- **图像模型**: Google Gemini 3 Pro Image Preview

## 核心组件详解

### 1. 风格分析器 (StyleAnalyzer)

**位置**: `backend/app/services/style_analyzer.py`

**功能**: 分析上传的模板图片，提取视觉风格特征

#### 处理流程

1. **像素分析** (`_analyze_single()`)
   ```python
   {
     "filename": "demo.png",
     "resolution": "1840x1040",
     "orientation": "横向",
     "primary_color": "#E4E2E0",
     "palette": ["#FFFFFF", "#AEA7A1", "#FAFBFB", ...],
     "luma": 226,
     "lighting": "高光充足，整体通透",
     "texture": "高反差细节，层次轻盈",
     "composition": ["横幅构图", "主视觉偏中心"]
   }
   ```

2. **LLM风格描述**
   - 系统提示词: "你是一名严谨客观的视觉风格分析师..."
   - 输出结构化的Style Prompt，包含配色、材质、构图、注意事项等

#### 技术细节

- **支持的图片格式**: PNG, JPG, JPEG
- **颜色分析**: 提取主色调和调色板
- **构图检测**: 基于图像特征的构图关键词提取
- **质量控制**: 错误时回退到纯像素分析结果

### 2. 大纲生成器 (OutlineGenerator)

**位置**: `backend/app/services/outline_generator.py`

**功能**: 将长文档智能拆解为结构化的幻灯片大纲

#### 处理流程

1. **LLM请求构建**
   ```python
   system_prompt = "你是一名专业的 PPT 编剧，输出 JSON 数组..."
   user_prompt = f"""
   原始文本：{text}
   预期页数：{slide_count}
   模版：{template_name}
   """
   ```

2. **输出结构**
   ```json
   [
     {
       "page_num": 1,
       "type": "cover",
       "title": "项目标题",
       "content_text": "封面内容",
       "visual_desc": "视觉描述"
     }
   ]
   ```

3. **备用方案**
   - JSON解析失败时启用本地拆分算法 `_fallback_generate()`
   - 按段落平均分配，自动生成视觉描述

#### 技术细节

- **支持页数**: 1-20页（可配置）
- **页面类型**: cover/content/ending
- **模板适配**: 根据模板名称调整生成风格
- **错误处理**: 多层次的容错机制

### 3. 提示词构建器 (PromptBuilder)

**位置**: `backend/app/services/prompt_builder.py`

**功能**: 组装最终的图像生成提示词

#### 组装结构

```text
Prompt: {style_prompt}

### 分页描述
{visual_desc}

### 需要内嵌的文字
- 标题：{title}
- 正文：{content_text}

### 输出要求
- 尺寸严格为 {aspect_ratio}
- 画面需兼具丰富图像与可读文字
- 避免无关元素或水印
```

#### 技术细节

- **风格继承**: 完整保留风格分析的结果
- **文本集成**: 确保文字正确绘制在图像中
- **格式适配**: 支持16:9、4:3等多种宽高比
- **质量要求**: 包含分辨率、风格、内容的详细约束

### 4. 图像生成器 (ImageGenerator)

**位置**: `backend/app/services/image_generator.py`

**功能**: 调用VLM API生成幻灯片图像

#### 核心变更 (2025-12-10)

**旧方案** (已废弃):
```python
# 旧接口 - 返回HTML而非图片
POST /api/v1/images
{
  "model": "google/gemini-3-pro-image-preview",
  "prompt": "...",
  "width": 1920,
  "height": 1080
}
```

**新方案** (当前使用):
```python
# 新接口 - chat completions + modalities
POST /api/v1/chat/completions
{
  "model": "google/gemini-3-pro-image-preview",
  "messages": [
    {"role": "system", "content": "你是专业的 PPT 幻灯片视觉设计师"},
    {"role": "user", "content": final_prompt}
  ],
  "modalities": ["image", "text"],
  "max_output_tokens": 2048
}
```

#### 响应处理

```python
# 解析响应中的图像数据
images = response["choices"][0]["message"]["images"]
image_url = images[0]["image_url"]["url"]  # data:image/jpeg;base64,...

# Base64解码并保存
base64_data = re.match(r"data:image/[^;]+;base64,(.+)", image_url)
image_bytes = base64.b64decode(base64_data.group(1))
```

#### 技术细节

- **图像格式**: JPEG (从API返回的原生格式)
- **分辨率**: 自动计算，保持指定宽高比
- **文件命名**: UUID4避免冲突
- **错误处理**: 生成失败时创建占位图

### 5. PPTX导出器 (PPTXExporter)

**位置**: `backend/app/services/pptx_exporter.py`

**功能**: 将生成的幻灯片导出为PowerPoint格式

#### 处理流程

1. **幻灯片创建**: 每页使用空白布局
2. **背景设置**: 如果有图像则铺满整个页面
3. **文本覆盖**: 添加可编辑的文本框（保留编辑能力）
4. **格式优化**: 保持图像质量和文本可读性

#### 技术细节

- **输出格式**: Microsoft PowerPoint (.pptx)
- **图像质量**: 保持原始分辨率
- **文本格式**: 可编辑的文本框（非纯图）
- **元数据**: 包含项目标题、创建时间等信息

## API接口文档

### 核心端点

#### 1. 模板分析
```
POST /api/template/analyze
Content-Type: multipart/form-data

Body:
- files: 模板图片文件 (1-N张)

Response:
{
  "style_prompt": "基于您提供的客观观察笔记，以下是整理后的结构化 Style Prompt..."
}
```

#### 2. 大纲生成
```
POST /api/outline/generate
Content-Type: application/json

Body:
{
  "text": "原始文档内容",
  "slide_count": 5,
  "template_id": "optional_template_id"
}

Response:
{
  "slides": [
    {
      "page_num": 1,
      "type": "cover",
      "title": "标题",
      "content_text": "内容",
      "visual_desc": "视觉描述"
    }
  ]
}
```

#### 3. 幻灯片生成
```
POST /api/slide/generate
Content-Type: application/json

Body:
{
  "style_prompt": "风格提示词",
  "visual_desc": "视觉描述",
  "title": "幻灯片标题",
  "content_text": "幻灯片内容",
  "aspect_ratio": "16:9"
}

Response:
{
  "image_url": "/assets/slide_xxx.jpg",
  "final_prompt": "最终使用的提示词",
  "status": "done"
}
```

#### 4. 批量幻灯片生成 (2025-12-10新增)
```
POST /api/slide/batch/generate
Content-Type: application/json

Body:
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

Response:
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

#### 5. 批量生成状态查询
```
POST /api/slide/batch/status
Content-Type: application/json

Body:
{
  "batch_id": "uuid"
}

Response:
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

#### 6. 项目管理
```
# 获取项目列表
GET /api/projects

Response:
[
  {
    "id": "项目UUID",
    "title": "项目标题",
    "updated_at": "2025-12-10T18:30:00Z",
    "thumbnail_url": "/assets/slide_xxx.jpg"
  }
]

# 获取项目详情
GET /api/projects/{project_id}

Response:
{
  "id": "项目UUID",
  "title": "项目标题",
  "created_at": "2025-12-10T18:00:00Z",
  "updated_at": "2025-12-10T18:30:00Z",
  "template_style_prompt": "风格提示词",
  "slides": [
    {
      "id": "slide_uuid",
      "page_num": 1,
      "type": "cover",
      "title": "幻灯片标题",
      "content_text": "内容文本",
      "visual_desc": "视觉描述",
      "image_url": "/assets/slide_xxx.jpg",
      "final_prompt": "最终提示词",
      "status": "done"
    }
  ],
  "thumbnail_url": "/assets/slide_xxx.jpg"
}

# 保存项目
POST /api/projects/save
Content-Type: application/json

Body:
{
  "id": "项目UUID",
  "title": "项目标题",
  "template_style_prompt": "风格提示词",
  "slides": [幻灯片数组]
}

Response:
{
  "id": "项目UUID",
  "title": "项目标题",
  "created_at": "2025-12-10T18:00:00Z",
  "updated_at": "2025-12-10T18:30:00Z",
  "template_style_prompt": "风格提示词",
  "slides": [幻灯片数组]
}

# 删除项目
DELETE /api/projects/{project_id}

Response:
{
  "message": "Project deleted successfully"
}
```

#### 7. PPTX导出
```
POST /api/export/pptx
Content-Type: application/json

Body:
{
  "project": {
    "title": "项目标题",
    "template_style_prompt": "风格提示词",
    "slides": [幻灯片数组]
  },
  "file_name": "optional_filename.pptx"
}

Response:
Content-Type: application/vnd.openxmlformats-officedocument.presentationml.presentation
Content-Disposition: attachment; filename="export.pptx"

Body: PPTX文件二进制数据
```

### 错误处理

所有API端点统一错误格式：

```json
{
  "detail": "错误描述信息"
}
```

常见错误码:
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 数据验证失败
- `500 Internal Server Error`: 服务器内部错误
- `503 Service Unavailable`: AI服务不可用

## 数据模型

### 核心数据结构

#### SlideData (幻灯片数据)
```python
{
  "id": str,           # 唯一标识符
  "page_num": int,     # 页码
  "type": str,         # 页面类型: cover/content/ending
  "title": str,        # 标题
  "content_text": str, # 内容文本
  "visual_desc": str,  # 视觉描述
  "image_url": str,    # 生成的图像URL (可选)
  "final_prompt": str, # 最终使用的提示词 (可选)
  "status": str        # 状态: pending/generating/done/error
}
```

#### BatchGenerateResult (批量生成结果)
```python
{
  "batch_id": str,        # 批量任务唯一标识符
  "total_slides": int,    # 总幻灯片数
  "successful": int,      # 成功生成数
  "failed": int,          # 失败数量
  "total_time": float,    # 总耗时(秒)
  "results": [SlideResult] # 每张幻灯片的生成结果
}
```

#### SlideResult (单张幻灯片生成结果)
```python
{
  "slide_id": str,        # 幻灯片ID
  "page_num": int,        # 页码
  "title": str,           # 标题
  "image_url": str,       # 生成的图像URL
  "final_prompt": str,    # 最终使用的提示词
  "status": str,          # 状态: done/error
  "error_message": str,   # 错误信息(如有)
  "generation_time": float # 单张生成耗时(秒)
}
```

#### Template (模板数据)
```python
{
  "id": str,                # 唯一标识符
  "name": str,              # 模板名称
  "style_prompt": str,      # 风格提示词
  "created_at": datetime,   # 创建时间
  "preview_image": str      # 预览图片URL (可选)
}
```

#### ProjectState (项目状态)
```python
{
  "title": str,             # 项目标题
  "template_id": str,       # 当前模板ID
  "slides": List[SlideData] # 幻灯片列表
}
```

#### ProjectSchema (完整项目数据)
```python
{
  "id": str,                     # 项目唯一标识符
  "title": str,                  # 项目标题
  "created_at": datetime,        # 创建时间
  "updated_at": datetime,        # 最后更新时间
  "template_style_prompt": str,  # 风格提示词
  "slides": List[SlideData],     # 幻灯片列表
  "thumbnail_url": str          # 缩略图URL (可选)
}
```

#### ProjectListItem (项目列表项)
```python
{
  "id": str,             # 项目唯一标识符
  "title": str,          # 项目标题
  "updated_at": datetime, # 最后更新时间
  "thumbnail_url": str   # 缩略图URL (可选)
}
```

## 性能分析

### 当前性能特征

#### 图像生成瓶颈

**问题描述**: 
- 顺序单张生成，无批量处理
- 每张图片需要10-30秒生成时间
- 5页PPT需要100-150秒总时间

**性能指标**:
```python
# 单张图片生成时间
平均生成时间: 18.5秒
最快: 12秒
最慢: 45秒
成功率: 92%

# API响应时间
风格分析: 3-5秒
大纲生成: 8-15秒  
图像生成: 15-30秒/张
PPTX导出: 2-5秒
```

#### 资源使用

**内存消耗**:
- 图像生成: ~200MB RAM/请求
- 文件存储: ~1-3MB/幻灯片
- 临时文件: 自动清理

**网络带宽**:
- 上传模板: ~5-10MB
- 下载图像: ~1-3MB/张
- PPTX导出: ~10-50MB

### 前端Workspace优化 (2025-12-10更新)

#### 用户体验改进

**问题描述**:
- 左侧缩略图只显示文字状态，无法预览实际图片
- 右侧编辑区域包含冗余的标题/正文输入框
- 需要手动点击生成每张图片，效率低下

**解决方案**:

1. **智能缩略图展示**
   ```tsx
   // 左侧缩略图直接显示生成的图片
   {slide.image_url ? (
     <img src={slide.image_url} alt={`第${slide.page_num}页`} className="w-full h-full object-cover" />
   ) : (
     <div className="flex items-center justify-center">
       {slide.status === 'generating' ? <LoadingSpinner /> : <span>待生成</span>}
     </div>
   )}
   ```

2. **自动批量生成**
   ```tsx
   // 进入页面后自动检测并批量生成
   useEffect(() => {
     const hasNoImages = slides.length > 0 && slides.every(slide => !slide.image_url);
     const hasTemplate = !!currentTemplate;
     
     if (hasNoImages && hasTemplate && !batchGenerating) {
       setTimeout(() => handleBatchGenerate(), 1000);
     }
   }, [slides, currentTemplate]);
   ```

3. **实时进度显示**
   ```tsx
   // 批量生成进度提示
   {batchProgress && (
     <div className="w-full p-4 bg-blue-50 border border-blue-200 rounded-lg">
       <div className="flex items-center gap-2">
         <LoadingSpinner />
         <span className="text-sm text-blue-700">{batchProgress}</span>
       </div>
     </div>
   )}
   ```

**界面简化**:
- 移除标题和正文输入框（图像本身已包含所有内容）
- 保留画面描述编辑框，支持单独重新生成
- 添加"批量生成所有图片"按钮

**性能提升**:
- 自动触发批量生成，无需手动操作
- 并发处理多张图片，时间从 100-150秒 → 20-45秒
- 实时预览和进度反馈，用户体验大幅改善

### 性能优化建议

#### 1. 批量图像生成 (✅ 已实现)

后端已实现批量生成接口:
```python
@router.post("/slide/batch/generate")
async def batch_generate_slides(request: BatchGenerateRequest):
    # ThreadPoolExecutor实现真正的并发处理
    # 可配置最大并发数（1-10）
    # 详细的日志记录和状态跟踪
```

**实现效果**:
- 5页PPT: 100-150秒 → 20-45秒 (3-7x提升)
- 用户体验: 手动逐页 → 自动批量生成
- 支持实时进度跟踪和错误处理

#### 2. 并发控制优化

```python
# 配置合理的并发限制
MAX_CONCURRENT_GENERATIONS = 3  # 控制并发数
REQUEST_TIMEOUT = 180          # 3分钟超时
RATE_LIMIT = "10/minute"       # API限流
```

#### 3. 缓存策略

```python
# 风格分析结果缓存
@cache.memoize(timeout=3600)
def analyze_template_style(image_hash):
    return style_analyzer.analyze(image)

# 图像生成缓存 (相同prompt)
@cache.memoize(timeout=86400)  
async def generate_image_cached(prompt_hash):
    return image_generator.create(prompt)
```

#### 4. 前端优化

- **预加载**: 提前开始生成过程
- **进度显示**: 实时显示生成进度
- **错误重试**: 自动重试失败的生成任务
- **本地缓存**: 避免重复生成相同内容

## 部署与配置

### 环境要求

#### 后端环境
```bash
Python 3.10+
pip install -r requirements.txt

# 核心依赖
fastapi>=0.104.0
uvicorn>=0.24.0
python-pptx>=0.6.21
Pillow>=10.0.0
pydantic>=2.4.0
```

#### 前端环境
```bash
Node.js 18+
npm install

# 核心依赖
react>=18.2.0
typescript>=5.0.0
vite>=4.4.0
tailwindcss>=3.3.0
```

### 配置文件

#### 后端配置 (.env)
```bash
# AI服务配置
LLM_API_KEY=sk-or-v1-...
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_CHAT_MODEL=google/gemini-3-pro-preview
LLM_IMAGE_MODEL=google/gemini-3-pro-image-preview
LLM_TIMEOUT_SECONDS=120

# 文件存储配置
IMAGE_OUTPUT_DIR=backend/generated/images
PPTX_OUTPUT_DIR=backend/generated/pptx
TEMPLATE_STORE_PATH=backend/data/templates.json

# CORS配置
ALLOWED_ORIGINS=["http://localhost:5173", "https://your-domain.com"]

# 服务配置
API_PREFIX=/api
PROJECT_NAME=AI-PPT Flow Backend
```

#### 前端配置 (vite.config.ts)
```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/assets': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
```

### 部署方式

#### 开发环境
```bash
# 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 启动前端
cd frontend  
npm run dev
```

#### 生产环境 (Docker)
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY frontend/dist/ ./static/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  ai-ppt-flow:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_API_BASE=https://openrouter.ai/api/v1
    volumes:
      - ./generated:/app/backend/generated
      - ./data:/app/backend/data
```

#### 云部署建议

**推荐配置**:
- **CPU**: 4核心以上 (支持并发处理)
- **内存**: 8GB以上 (图像处理需求)
- **存储**: 100GB SSD (文件缓存和生成结果)
- **网络**: 带宽100Mbps以上 (图像传输)

**扩展性考虑**:
- 使用负载均衡器处理高并发
- 配置CDN加速静态资源访问
- 使用对象存储 (S3/MinIO) 存储生成文件
- 设置数据库持久化模板和项目数据

## 安全考虑

### API安全

1. **认证授权**: (未来版本)
   - JWT token认证
   - 用户配额管理
   - API访问限流

2. **输入验证**:
   - 文件类型检查 (仅允许图片格式)
   - 文件大小限制 (单文件10MB)
   - 文本长度限制 (防止过长输入)

3. **数据隐私**:
   - 本地文件自动清理机制
   - 不在日志中记录敏感内容
   - 用户数据隔离存储

### AI服务安全

1. **API密钥管理**:
   - 环境变量存储，不硬编码
   - 定期轮换API密钥
   - 监控API使用量和费用

2. **内容安全**:
   - 输入内容过滤 (检查敏感词)
   - 生成内容审核 (防止不当内容)
   - 使用AI服务的安全策略

## 监控与日志

### 应用监控

#### 关键指标
```python
# 性能指标
request_duration_seconds = Histogram('request_duration_seconds')
request_count_total = Counter('request_count_total')
active_generations = Gauge('active_generations')

# 业务指标  
slides_generated_total = Counter('slides_generated_total')
templates_analyzed_total = Counter('templates_analyzed_total')
pptx_exported_total = Counter('pptx_exported_total')
```

#### 日志格式
```python
import structlog

logger = structlog.get_logger()

# 结构化日志示例
logger.info(
    "slide_generated",
    slide_id=slide_id,
    generation_time=duration,
    file_size=file_size,
    user_id=user_id
)
```

### 错误追踪

#### 异常处理
```python
try:
    result = await generate_image(prompt)
except LLMClientError as e:
    logger.error("llm_api_error", error=str(e), prompt_hash=hash(prompt))
    # 返回用户友好的错误信息
except Exception as e:
    logger.exception("unexpected_error", prompt_hash=hash(prompt))
    # 生成占位图，确保流程继续
```

## 测试策略

### 单元测试

```python
# 示例测试
import pytest
from app.services.prompt_builder import PromptBuilder

def test_prompt_builder():
    builder = PromptBuilder()
    result = builder.build(
        style_prompt="极简风格",
        visual_desc="蓝色背景",
        title="测试标题",
        content_text="测试内容",
        aspect_ratio="16:9"
    )
    
    assert "极简风格" in result
    assert "蓝色背景" in result
    assert "测试标题" in result
    assert "16:9" in result
```

### 集成测试

```python
# API测试
import httpx
from fastapi.testclient import TestClient

def test_generate_outline():
    client = TestClient(app)
    response = client.post("/api/outline/generate", json={
        "text": "测试文档内容",
        "slide_count": 3
    })
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["slides"]) == 3
    assert data["slides"][0]["type"] == "cover"
```

### 性能测试

```python
# 性能基准测试
import time
import asyncio

async def benchmark_image_generation():
    start_time = time.time()
    result = await image_generator.create(prompt, "16:9")
    duration = time.time() - start_time
    
    print(f"Generation time: {duration:.2f}s")
    assert duration < 30, "Generation took too long"
```

## 版本历史

### v1.1.0 (2025-12-10 发布)
- ✅ **前端Workspace重大优化**
  - 智能缩略图展示，直接预览生成的图片
  - 自动批量生成，进入页面后智能触发
  - 实时进度显示和状态管理
  - 界面简化，移除冗余输入框
- ✅ **批量图像生成系统**
  - 后端多进程并发处理 (`/api/slide/batch/generate`)
  - 实时状态查询接口 (`/api/slide/batch/status`)
  - 详细日志记录和错误处理
  - 性能提升 3-7倍 (100-150秒 → 20-45秒)
- ✅ **API接口扩展**
  - 完整的批量生成接口文档
  - 新增数据模型和类型定义
  - 前端API客户端封装

### v1.0.0 (基础版本)
- ✅ 基础的端到端PPT生成流程
- ✅ 风格分析和提取
- ✅ 智能大纲生成  
- ✅ 单张图像生成 (基于Gemini 3 Pro)
- ✅ PPTX导出功能
- ✅ React前端界面

### v1.2.0 (2025-12-10 发布)
- ✅ **项目管理功能**
  - 自动保存机制：批量生成后自动保存项目
  - 编辑时自动保存：修改内容后5分钟自动保存
  - 项目历史记录：查看和继续编辑历史项目
  - 页面关闭提醒：未保存更改时提醒用户
- ✅ **存储系统**
  - 项目数据持久化到 `backend/data/projects/`
  - 自动生成项目ID和元数据
  - 缩略图和项目信息管理
  - 项目删除和恢复功能
- ✅ **前端用户体验**
  - History页面：查看所有历史项目
  - 项目缩略图预览
  - 项目创建时间和最后更新时间显示
  - 一键打开历史项目继续编辑

### v1.3.0 (计划中)
- 🔄 用户认证和权限管理
- 🔄 更多导出格式支持
- 🔄 WebSocket实时推送
- 🔄 AI模型选择和配置

### v2.0.0 (未来规划)
- 📋 多人协作编辑
- 📋 实时预览和同步
- 📋 更多AI模型选择
- 📋 移动端适配
- 📋 API开放平台

## 故障排除

### 常见问题

#### 1. 图像生成失败
```
错误: LLMClientError: Image generation request failed
解决: 检查API密钥和网络连接，确认模型可用性
```

#### 2. 文件上传问题  
```
错误: File too large
解决: 检查文件大小限制，压缩图片或增加限制
```

#### 3. PPTX导出错误
```
错误: python-pptx exception
解决: 检查图像文件格式和路径，确认权限设置
```

### 调试技巧

#### 启用详细日志
```bash
# 后端调试模式
uvicorn app.main:app --reload --log-level debug

# 前端调试
npm run dev -- --debug
```

#### 检查AI服务状态
```python
# 测试API连接
async def test_ai_service():
    client = OpenRouterClient(api_key, base_url)
    try:
        response = await client.chat("测试", "google/gemini-3-pro-preview")
        print("AI服务正常:", response[:100])
    except Exception as e:
        print("AI服务异常:", str(e))
```

## 贡献指南

### 开发流程
1. Fork项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

### 代码规范
- Python: 遵循PEP 8，使用black格式化
- TypeScript: 使用ESLint + Prettier
- 提交信息: 遵循Conventional Commits规范

### 测试要求
- 新功能必须包含单元测试
- API变更需要更新集成测试
- 性能变更需要包含基准测试

---

**文档版本**: 1.0.0  
**最后更新**: 2025-12-10  
**维护者**: AI-PPT Flow 开发团队