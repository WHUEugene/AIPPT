# AI-PPT Flow Prompt Pipeline 说明

本文档梳理当前后端各个阶段的提示词组装逻辑，帮助定位“风格拆解→大纲→图片生成→导出”环节中可能的问题。

## 1. 风格提取 / Template Analyze

- **接口**：`POST /api/template/analyze`
- **输入**：`files`（1~N 张参考图片）
- **流程**：
  1. `StyleAnalyzer` 先做本地像素分析，提取分辨率、主辅色、亮度、构图关键词等，拼成客观描述。（这个的输入输出是什么，你需要给我让我理解一下，我不知道这一步有什么用）
  2. 将该描述作为用户消息，配上系统指令（“你是一名严谨客观的视觉风格分析师…”），调用 `OpenRouter` 的 `google/gemini-3-pro-preview`。（详细的系统指令是什么？给我一个整体的）
  3. LLM 输出结构化 Style Prompt，前端展示给用户，可手动编辑后保存模板。（输出的结果prompt示例）
- **输出**：`{ style_prompt }` – 后续所有分页都会引用此 Prompt 开头。

### 像素分析输入/输出示例（真实数据）

- **输入**：单张 `UploadFile`（此次直接用 `demo.png`，分辨率 1840×1040）。
- **内部输出**：`_analyze_single()` 的返回值会被拼入用户提示，该次实测结果如下：

  ```json
  {
    "filename": "demo.png",
    "resolution": "1840x1040",
    "orientation": "横向",
    "primary_color": "#E4E2E0",
    "palette": [
      "#FFFFFF",
      "#AEA7A1",
      "#FAFBFB",
      "#E6E4E2",
      "#FCFFFF"
    ],
    "luma": 226,
    "lighting": "高光充足，整体通透",
    "texture": "高反差细节，层次轻盈",
    "composition": [
      "横幅构图",
      "主视觉偏中心"
    ]
  }
  ```

  多张图片会得到多个 block，最后合并为 `analysis_brief` 字符串。

### LLM 输入 / 输出（真实请求）

- **系统消息**（与代码一致）：

  ```
  你是一名严谨客观的视觉风格分析师。请根据提供的观察笔记，输出结构化 Style Prompt。禁止编造不存在的元素，按照“配色/材质 -> 构图/层次 -> 画面细节 -> 作图注意事项”顺序输出。
  ```

- **用户消息**：

  ```
  以下是参考图的客观观察，请整理成绘图可用的 prompt：
  
  你是一名严谨客观的视觉设计顾问。
  - 禁止使用隐喻或主观臆断。
  - 仅依据图像事实描述颜色、光线、构图与材质。
  - 输出内容需结构化、可供绘图模型直接引用。
  
  ### 参考图逐条解析
  #### 参考图 1: demo.png
  - 分辨率：1840x1040 (横向)
  - 主导色：#E4E2E0，辅助色：#FFFFFF, #AEA7A1, #FAFBFB, #E6E4E2, #FCFFFF
  - 光照与明度：高光充足，整体通透 (亮度 226)
  - 材质/质感：高反差细节，层次轻盈
  - 构图关键词：横幅构图, 主视觉偏中心


  输出需使用中文，尽量使用条列格式。
  ```

- **LLM 返回的 `style_prompt`**：

  ```
  基于您提供的客观观察笔记，以下是整理后的结构化 Style Prompt：

  ### 视觉风格提示词 (Style Prompt)

  **1. 配色与材质 (Color & Material)**
  *   **色彩基调**：极简高调 (High-key) 风格。以浅灰 (#E4E2E0) 为主基调，大面积使用纯白 (#FFFFFF) 与近白 (#FAFBFB, #FCFFFF) 营造通透感。
  *   **点缀色彩**：使用暖灰 (#AEA7A1) 增加画面稳重感，整体保持低饱和度。
  *   **光影质感**：全域漫射光，高光充足，无强烈投影；画面亮度极高 (Brightness ~226)，呈现洁净、轻盈的空气感。
  *   **材质表现**：高反差细节纹理，表面光滑细腻，兼具哑光与微光泽感。

  **2. 构图与层次 (Composition & Layers)**
  *   **画幅比例**：横向宽幅构图 (Landscape / Banner)，接近 16:9 比例。
  *   **空间布局**：中心构图 (Center-weighted)，视觉主体位于画面中央区域。
  *   **层次关系**：背景极简留白，前景与背景分离度高，层次轻薄，无压迫感。

  **3. 画面细节 (Screen Details)**
  *   **视觉风格**：现代极简主义 (Modern Minimalist)，专业设计感，冷淡风。
  *   **清晰度**：8K 分辨率，边缘锐利，细节呈现高清晰度。

  **4. 作图注意事项 (Precautions)**
  *   **--no (负向提示)**：高饱和度色彩 (High saturation)，昏暗光线 (Dim lighting)，杂乱背景 (Cluttered background)，强烈阴影 (Heavy shadows)，复古滤镜 (Vintage filter)。
  *   **重点控制**：确保画面整体亮度维持在高位，避免出现大面积深色色块，保持画面的“呼吸感”与通透度。
  ```

> 本次完整日志保存在 `doc/prompt_samples/latest.json` 的 `style` 节点中，便于后续核对。

> 若 LLM 请求失败或缺失 API Key，会回退到仅使用像素分析结果（没有额外润色）。
>
>  （不用回退啊直接报错不就完了）

> 如需改成“失败即报错”，可在 `StyleAnalyzer.build_prompt()` 捕获 `LLMClientError` 后直接抛出即可。

## 2. 大纲生成 / Outline Generate

- **接口**：`POST /api/outline/generate`
- **输入**：`{ text, slide_count, template_id? }`
- **流程**：
  1. 组建系统指令（“你是一名专业的 PPT 编剧，输出 JSON 数组…”）+ 用户内容（原始文本 + 预期页数 + 模板名称），调用 `google/gemini-3-pro-preview`。
  2. 解析 LLM 返回的 JSON：每个元素需包含 `page_num, type, title, content_text, visual_desc`。
  3. 如果解析失败（非 JSON / 字段缺失），则回退到本地拆段算法 `_fallback_generate`：按段落平均拆分，并自动生成 visual_desc。
- **输出**：`slides: SlideData[]` – 每页包含标题、正文（content_text）、visual_desc，后续图片生成会用到。

（很好这里的输入输出又是什么）

### LLM 输入 / 输出（真实请求）

- **系统消息**：

  ```
  你是一名专业的 PPT 编剧，负责将文档拆解为分页大纲。输出 JSON，数组中每个元素包含 page_num, type (cover/content/ending), title, content_text, visual_desc。visual_desc 必须描述可视化画面，不得抽象或隐喻，必须为中文。
  ```

- **用户消息**（此次输入 `slide_count=5`, `template_name="北大典雅学术版"`）：

  ```
  原始文本：
  多智能体系统（Auto-MAS）项目聚焦科研实验的全流程自动化，通过感知智能体、建模智能体与审阅智能体协作完成数据清洗、特征提取和报告撰写。本次汇报需要向管理层说明整体架构、关键技术、合作案例以及落地时程。我们强调北大科研场景以及严肃学术气质，并提供汇报人信息。

  预期页数：5。模版：北大典雅学术版.请按照 JSON 数组输出，严禁出现额外注释或代码块标记。
  ```

- **LLM 输出 JSON**：

  ```json
  [
    {
      "page_num": 1,
      "type": "cover",
      "title": "Auto-MAS：多智能体科研全流程自动化系统",
      "content_text": "面向北大科研场景的智能化解决方案\n\n汇报人：[您的姓名]\n所属单位：北京大学[您的院系/实验室]\n日期：202X年X月X日",
      "visual_desc": "页面背景为米白色纸纹质感，右上角放置深红色北京大学校徽。页面中央偏上位置显示主标题，字体为思源宋体，加粗。背景底部叠加低透明度的北京大学西校门线稿插画，整体风格庄重典雅。"
    },
    {
      "page_num": 2,
      "type": "content",
      "title": "整体架构：三体协作闭环模型",
      "content_text": "1. 感知智能体 (Perception Agent)\n   - 负责多源异构数据的清洗与标准化预处理。\n2. 建模智能体 (Modeling Agent)\n   - 自动化执行特征提取、模型选择与训练。\n3. 审阅智能体 (Reviewing Agent)\n   - 校验实验逻辑，撰写符合学术规范的实验报告。",
      "visual_desc": "页面中央展示一个水平方向的流程图。左侧是堆叠的数据库图标，指向中间三个呈三角形排列的圆形图标，分别标注“感知”、“建模”、“审阅”，三个圆之间有循环箭头表示交互。右侧是一个带有图表和文字的文档图标，代表最终报告。"
    },
    {
      "page_num": 3,
      "type": "content",
      "title": "关键技术与核心优势",
      "content_text": "技术亮点：\n- 动态协作机制：基于大模型的任务自动拆解与Agent间状态同步。\n- 严肃学术适配：内置北大论文格式标准，确保输出内容的严谨性。\n\n核心优势：\n- 全流程自动化：实现从Raw Data到Draft Paper的零断点执行。\n- 可解释性强：每一步操作均留存日志，便于科研复现。",
      "visual_desc": "页面分为左右两部分。左侧为文字列表。右侧展示一个层级结构图：底层标注“LLM基座”，中间层标注“Agent通信总线”，顶层展示三个具体的应用场景图标（数据表、代码块、论文页）。"
    },
    {
      "page_num": 4,
      "type": "content",
      "title": "合作案例与落地时程",
      "content_text": "合作案例：\n- 某理工科实验室：辅助材料筛选，数据处理效率提升60%。\n\n落地规划：\n- Phase 1 (本月)：原型系统内测与单点功能验证。\n- Phase 2 (Q3)：多学科场景适配与接口标准化。\n- Phase 3 (年底)：全校范围部署与云平台上线。",
      "visual_desc": "页面上半部分展示一组对比柱状图，左柱为“人工处理时长”，右柱为“Auto-MAS处理时长”，右柱明显更短。页面下半部分展示一条带有箭头的水平时间轴，轴上均匀分布三个节点，分别对应三个阶段的规划内容。"
    },
    {
      "page_num": 5,
      "type": "ending",
      "title": "感谢聆听 敬请指正",
      "content_text": "Auto-MAS 项目组\n致力于释放科研创造力\n\n联系方式：[电话/邮箱]",
      "visual_desc": "页面背景采用北京大学深红色（北大红）全填充。页面正中央显示白色的宋体“感谢聆听”字样。底部居中位置放置白色的北京大学Logo及中英文校名组合。"
    }
  ]
  ```

  `OutlineGenerator` 成功解析后直接构造 `SlideData`。完整日志同样记录在 `doc/prompt_samples/latest.json` 的 `outline` 节点。

## 3. 图片生成 / Slide Generate

- **接口**：`POST /api/slide/generate`（/regenerate）
- **输入字段**：`style_prompt`（直接复用风格分析返回文本）、`visual_desc`、`title`、`content_text`、`aspect_ratio`。
- **Prompt 组装**：`PromptBuilder.build()` 会把上述字段拼成一段字符串，这才是最终发送给图像模型的“LLM 输入”。
- **LLM 调用**：根据 2025-12-10 的 OpenRouter 文档，必须走 `POST /api/v1/chat/completions` 并添加 `"modalities": ["image", "text"]` 才能获得图像；旧的 `POST /images` 路径会直接返回站点 HTML（`x-clerk-auth-message: Invalid JWT form`），因此需要改造 `OpenRouterClient.generate_image()` 以 chat 方式拉取图片。
- **输出**：`{ image_url, final_prompt, status }`，图片保存在 `backend/generated/images/`，通过 `/assets/...` 暴露给前端；如果 chat 响应没有 `message.images`，则生成占位 PNG。

> 如果短期内还没切换后端实现，Workspace 中会看到占位图；一旦迁移，请确保把 `message.images[0].image_url.url`（base64 DataURL）解码保存再返回。

### 本次实测 PromptBuilder 输出

从上文真实 `style_prompt` + 第 1 页大纲拼出的 `final_prompt` 完整内容如下（同样存档于 `doc/prompt_samples/latest.json.final_prompt`）：

```
Prompt: 基于您提供的客观观察笔记，以下是整理后的结构化 Style Prompt：

### 视觉风格提示词 (Style Prompt)

**1. 配色与材质 (Color & Material)**
*   **色彩基调**：极简高调 (High-key) 风格。以浅灰 (#E4E2E0) 为主基调，大面积使用纯白 (#FFFFFF) 与近白 (#FAFBFB, #FCFFFF) 营造通透感。
*   **点缀色彩**：使用暖灰 (#AEA7A1) 增加画面稳重感，整体保持低饱和度。
*   **光影质感**：全域漫射光，高光充足，无强烈投影；画面亮度极高 (Brightness ~226)，呈现洁净、轻盈的空气感。
*   **材质表现**：高反差细节纹理，表面光滑细腻，兼具哑光与微光泽感。

**2. 构图与层次 (Composition & Layers)**
*   **画幅比例**：横向宽幅构图 (Landscape / Banner)，接近 16:9 比例。
*   **空间布局**：中心构图 (Center-weighted)，视觉主体位于画面中央区域。
*   **层次关系**：背景极简留白，前景与背景分离度高，层次轻薄，无压迫感。

**3. 画面细节 (Screen Details)**
*   **视觉风格**：现代极简主义 (Modern Minimalist)，专业设计感，冷淡风。
*   **清晰度**：8K 分辨率，边缘锐利，细节呈现高清晰度。

**4. 作图注意事项 (Precautions)**
*   **--no (负向提示)**：高饱和度色彩 (High saturation)，昏暗光线 (Dim lighting)，杂乱背景 (Cluttered background)，强烈阴影 (Heavy shadows)，复古滤镜 (Vintage filter)。
*   **重点控制**：确保画面整体亮度维持在高位，避免出现大面积深色色块，保持画面的“呼吸感”与通透度。

### 分页描述
页面背景为米白色纸纹质感，右上角放置深红色北京大学校徽。页面中央偏上位置显示主标题，字体为思源宋体，加粗。背景底部叠加低透明度的北京大学西校门线稿插画，整体风格庄重典雅。

### 需要内嵌的文字
- 标题：Auto-MAS：多智能体科研全流程自动化系统
- 正文：面向北大科研场景的智能化解决方案

汇报人：[您的姓名]
所属单位：北京大学[您的院系/实验室]
日期：202X年X月X日
所有文字须以简体中文直接绘制在画面中，与图像元素自然融合。

### 输出要求
- 尺寸严格为 16:9。
- 画面需兼具丰富图像与可读文字，主题围绕当前页面描述。
- 避免无关元素或水印。

请基于以上全部信息直接生成整张幻灯片背景图。
```

### 图像接口真实响应（chat 方式）

使用上述 `final_prompt` 调用 `POST https://openrouter.ai/api/v1/chat/completions`，原始记录在 `doc/prompt_samples/image_chat_response.json`。关键点如下：

- **请求体**：

  ```json
  {
    "model": "google/gemini-3-pro-image-preview",
    "messages": [
      {"role": "system", "content": "你是专业的 PPT 幻灯片视觉设计师"},
      {"role": "user", "content": "(final_prompt 全文)"}
    ],
    "modalities": ["image", "text"],
    "max_output_tokens": 2048
  }
  ```

- **响应主体**：`choices[0].message.images` 返回 2 个 `data:image/jpeg;base64,...`，示例：

  ```json
  {
    "type": "image_url",
    "image_url": {
      "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgAB..."
    }
  }
  ```

  将 base64 解码后，已落盘至 `backend/generated/images/chat_1.jpg`、`chat_2.jpg`。

- **推理信息**：`message.reasoning` 带有多段英文自检说明，可忽略，对实际图片数据无影响。

> 历史记录 `doc/prompt_samples/image_request.txt` 仍保留旧 `/images` 接口返回 HTML 的证据，可用于向 OpenRouter 支持团队反馈。

## 完整流程案例 (2025-12-10)

以下是从模板分析到图像生成的完整真实案例，展示了整个 prompt pipeline 的实际运行效果。

### 输入数据

- **模板图片**: `demo.png` (1840×1040 像素)
- **原始文本**: "多智能体系统（Auto-MAS）项目聚焦科研实验的全流程自动化..."
- **预期页数**: 5 页
- **模板风格**: 北大典雅学术版

### 完整流程输出

#### 1. 风格提取结果

通过 `StyleAnalyzer` 生成的 `style_prompt`（与上文示例一致）：

```
基于您提供的客观观察笔记，以下是整理后的结构化 Style Prompt：

### 视觉风格提示词 (Style Prompt)

**1. 配色与材质 (Color & Material)**
*   **色彩基调**：极简高调 (High-key) 风格。以浅灰 (#E4E2E0) 为主基调...
[完整内容见上文]
```

#### 2. 大纲生成结果

第1页（封面）的大纲数据：

```json
{
  "page_num": 1,
  "type": "cover",
  "title": "Auto-MAS：多智能体科研全流程自动化系统",
  "content_text": "面向北大科研场景的智能化解决方案\n\n汇报人：[您的姓名]\n所属单位：北京大学[您的院系/实验室]\n日期：202X年X月X日",
  "visual_desc": "页面背景为米白色纸纹质感，右上角放置深红色北京大学校徽。页面中央偏上位置显示主标题，字体为思源宋体，加粗。背景底部叠加低透明度的北京大学西校门线稿插画，整体风格庄重典雅。"
}
```

#### 3. 最终组装的 Prompt

通过 `PromptBuilder.build()` 组装的完整提示词（1200 字符），包含：
- 风格提示词（完整的北大典雅学术风格描述）
- 分页描述（米白色背景、北大校徽位置、主标题布局等）
- 需要内嵌的文字（标题和正文内容）
- 输出要求（16:9 尺寸、避免水印等）

#### 4. 图像生成结果

✅ **成功生成真实图像**（非占位图）：

- **文件**: `slide_15774dcd153a4964ae75d291e74adacd.jpg`
- **尺寸**: 1376×768 像素（16:9 比例）
- **文件大小**: 678,020 字节
- **格式**: JPEG（从 OpenRouter API 直接返回）
- **图像URL**: `/assets/slide_15774dcd153a4964ae75d291e74adacd.jpg`

![生成的封面幻灯片](doc/prompt_samples/images/complete_pipeline_cover.jpg)

### 关键验证点

1. **API 调用成功**: 使用 `POST /api/v1/chat/completions` + `modalities: ["image","text"]`
2. **真实图像生成**: 响应包含 `message.images[0].image_url.url` 的 base64 JPEG 数据
3. **正确的风格**: 图像体现了北大典雅学术风格（米白背景、校徽位置、字体样式等）
4. **文字集成**: 标题和正文已直接绘制在图像中，符合 prompt 要求

### 完整数据记录

本次完整流程的所有输入输出数据已保存在：
- `doc/prompt_samples/complete_pipeline_results.json` - 完整的 JSON 格式数据
- `doc/prompt_samples/images/complete_pipeline_cover.jpg` - 生成的封面图像

### 技术实现验证

- ✅ `OpenRouterClient.generate_image()` 已更新为使用 chat completions
- ✅ `ImageGenerator` 已更新为保存 JPEG 格式
- ✅ DataURL base64 解码正常工作
- ✅ 完整的 style_prompt → outline → final_prompt → 图像链路通畅

---

下面的暂时不管

## 4. 导出 / Export PPTX

- **接口**：`POST /api/export/pptx`
- **输入**：`{ project: { title?, template_style_prompt?, slides[] }, file_name? }`
- **流程**：`PPTXExporter` 使用 `python-pptx`：
  1. 每页添加空白布局。
  2. 若 `slide.image_url` 存在则铺满背景。
  3. 再插入文本框（标题/正文）——当前版本保留文本框，方便后续编辑；如需要纯图，可去掉这一层。
- **输出**：二进制 PPTX 下载流。

## 5. 前端各阶段与 API 对应

| 前端页面 | 操作 | 后端接口 |
| --- | --- | --- |
| Welcome → TemplateSelect | 列表 / 新增模版 | `GET /api/template`, `POST /api/template/analyze`, `POST /api/template/save` |
| TemplateCreate | 上传图片、分析风格 | 同上 |
| ContentInput | 粘贴文案、生成大纲 | `POST /api/outline/generate` |
| Workspace | 每页编辑 prompt、触发重绘 | `POST /api/slide/generate` / `regenerate` |
| 导出 | 下载 PPTX | `POST /api/export/pptx` |

## 常见问题排查

1. **/api/slide/generate 200 但前端无图**：大多是 `/assets` 未代理导致图片请求 404。已在 `vite.config.ts` 里将 `/assets` 转发到 `http://localhost:8000`。
2. **LLM 请求失败**：后端会打印异常并自动写入占位图，可查看 `backend/generated/images/` 是否生成文件；若没有，则检查 `.env` 的 `LLM_API_KEY` 和网络。
3. **Prompt 不符合预期**：在 Workspace 右侧仅保留“风格设定（只读）+ 画面 Prompt（可编辑）+ 标题/正文”三个输入即可；这些字段直接进入上面所示的 Prompt 模版。

---

如需进一步限制 Prompt 结构或引入额外的“审稿”环节，可在 `PromptBuilder` 或额外的服务层扩展；也可以在该文档基础上整理更细致的提示词指南。欢迎继续补充。 
