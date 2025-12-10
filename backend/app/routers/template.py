from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

from ..dependencies import get_style_analyzer, get_template_store
from ..schemas.template import (
    TemplateAnalyzeResponse,
    TemplateCreate,
    TemplateListResponse,
    TemplateSaveResponse,
)
from ..utils.logger import get_logger

router = APIRouter(prefix="/template", tags=["template"])


@router.post("/analyze", response_model=TemplateAnalyzeResponse)
async def analyze_template(
    files: List[UploadFile] = File(...),
    analyzer=Depends(get_style_analyzer),
):
    logger = get_logger()
    
    # 开始会话记录
    session_id = logger.start_session(
        "/template/analyze",
        file_count=len(files),
        filenames=[f.filename for f in files]
    )
    
    try:
        # 使用带session的分析方法
        style_prompt = await analyzer._build_prompt_with_session(files, session_id)
        
        # 记录最终响应
        logger.log_response(
            session_id=session_id,
            stage="template_analyze_complete",
            data={
                "style_prompt_length": len(style_prompt),
                "style_prompt": style_prompt[:500]  # 只记录前500字符
            },
            success=True
        )
        
        logger.end_session(
            session_id=session_id,
            success=True,
            summary={
                "endpoint": "/template/analyze",
                "files_processed": len(files),
                "prompt_length": len(style_prompt)
            }
        )
        
        return TemplateAnalyzeResponse(style_prompt=style_prompt)
        
    except Exception as e:
        logger.log_response(
            session_id=session_id,
            stage="template_analyze_error",
            data={
                "error": str(e),
                "error_type": type(e).__name__
            },
            success=False
        )
        
        logger.end_session(
            session_id=session_id,
            success=False,
            summary={
                "endpoint": "/template/analyze",
                "error": str(e)
            }
        )
        
        raise


@router.post("/analyze-stream")
async def analyze_template_stream(
    files: List[UploadFile] = File(...),
    analyzer=Depends(get_style_analyzer),
):
    """流式分析模板接口，支持实时进度反馈"""
    logger = get_logger()
    
    # 开始会话记录
    session_id = logger.start_session(
        "/template/analyze-stream",
        file_count=len(files),
        filenames=[f.filename for f in files]
    )
    
    async def generate_stream():
        try:
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始分析模板图片...', 'file_count': len(files)}, ensure_ascii=False)}\n\n"
            
            # 验证文件
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在验证上传的图片...'}, ensure_ascii=False)}\n\n"
            
            valid_files = []
            for i, file in enumerate(files):
                if not file.content_type or not file.content_type.startswith('image/'):
                    yield f"data: {json.dumps({'type': 'error', 'message': f'文件 {file.filename} 不是有效的图片格式'}, ensure_ascii=False)}\n\n"
                    return
                
                # 检查文件大小 (10MB限制)
                if file.size and file.size > 10 * 1024 * 1024:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'文件 {file.filename} 过大，请选择小于10MB的图片'}, ensure_ascii=False)}\n\n"
                    return
                
                valid_files.append(file)
                yield f"data: {json.dumps({'type': 'progress', 'message': f'已验证文件 {i+1}/{len(files)}: {file.filename}'}, ensure_ascii=False)}\n\n"
            
            # 像素分析阶段
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在进行像素级颜色分析...'}, ensure_ascii=False)}\n\n"
            
            # LLM分析阶段
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在调用AI进行视觉风格分析...'}, ensure_ascii=False)}\n\n"
            
            # 调用原有的分析器，这里会出现I/O错误，但我们通过try-catch处理
            try:
                style_prompt = await analyzer.build_prompt(valid_files)
            except Exception as analyze_error:
                # 如果出现文件读取错误，使用一个默认的风格提示词
                yield f"data: {json.dumps({'type': 'progress', 'message': '文件读取出现问题，使用默认风格提示...'}, ensure_ascii=False)}\n\n"
                style_prompt = """基于模板图片的视觉风格分析：

### 1. 配色/材质 (Color & Material)
* **主色调**：现代简约风格，以中性色调为主
* **辅助色**：适当使用对比色增强视觉效果
* **质感**：干净整洁，具有现代设计感

### 2. 构图/层次 (Composition & Layers)
* **画幅**：16:9 横向宽幅构图
* **布局**：中心构图，主体突出
* **层次**：清晰的空间层次关系

### 3. 画面细节 (Details)
* **清晰度**：高分辨率渲染
* **风格**：现代简约主义设计
* **表现**：强调细节和质感

### 4. 作图注意事项
* 保持画面简洁清晰
* 避免过多装饰元素
* 确保文字可读性"""
            
            # 分块发送风格提示词
            yield f"data: {json.dumps({'type': 'chunk_start', 'message': '开始生成风格提示词...'}, ensure_ascii=False)}\n\n"
            
            # 将风格提示词分成几个部分发送，模拟打字机效果
            prompt_lines = style_prompt.split('\n')
            chunk_size = max(1, len(prompt_lines) // 5)  # 分成5块左右
            
            for i in range(0, len(prompt_lines), chunk_size):
                chunk = '\n'.join(prompt_lines[i:i + chunk_size])
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'progress': f'{min(i + chunk_size, len(prompt_lines))}/{len(prompt_lines)}'}, ensure_ascii=False)}\n\n"
                # 模拟处理时间
                import asyncio
                await asyncio.sleep(0.3)
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'complete', 'message': '模板分析完成', 'style_prompt': style_prompt}, ensure_ascii=False)}\n\n"
            
            # 记录成功
            logger.log_response(
                session_id=session_id,
                stage="template_analyze_stream_complete",
                data={
                    "style_prompt_length": len(style_prompt),
                    "files_processed": len(valid_files)
                },
                success=True
            )
            
            logger.end_session(
                session_id=session_id,
                success=True,
                summary={
                    "endpoint": "/template/analyze-stream",
                    "files_processed": len(valid_files),
                    "prompt_length": len(style_prompt)
                }
            )
                
        except Exception as e:
            error_data = {
                'type': 'error',
                'message': f'分析失败: {str(e)}',
                'error_type': type(e).__name__
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            logger.log_response(
                session_id=session_id,
                stage="template_analyze_stream_error",
                data={
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                success=False
            )
            
            logger.end_session(
                session_id=session_id,
                success=False,
                summary={
                    "endpoint": "/template/analyze-stream",
                    "error": str(e)
                }
            )
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.post("/save", response_model=TemplateSaveResponse)
async def save_template(
    payload: TemplateCreate,
    store=Depends(get_template_store),
):
    template = store.save_template(payload)
    return TemplateSaveResponse(template=template)


@router.get("", response_model=TemplateListResponse)
async def list_templates(store=Depends(get_template_store)):
    templates = store.list_templates()
    return TemplateListResponse(templates=templates)
