from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..dependencies import get_outline_generator, get_template_store
from ..schemas.outline import OutlineRequest, OutlineResponse
from ..utils.logger import get_logger

router = APIRouter(prefix="/outline", tags=["outline"])


@router.post("/generate", response_model=OutlineResponse)
async def generate_outline(
    payload: OutlineRequest,
    generator=Depends(get_outline_generator),
    store=Depends(get_template_store),
):
    logger = get_logger()
    
    # 开始会话记录
    session_id = logger.start_session(
        "/outline/generate",
        text_length=len(payload.text),
        slide_count=payload.slide_count,
        template_id=payload.template_id
    )
    
    try:
        # 记录请求输入
        logger.log_request(
            session_id=session_id,
            stage="outline_generate_request",
            data={
                "text": payload.text,
                "slide_count": payload.slide_count,
                "template_id": payload.template_id
            }
        )
        
        template_name = None
        if payload.template_id:
            template = store.get_template(payload.template_id)
            if not template:
                logger.log_response(
                    session_id=session_id,
                    stage="template_not_found",
                    data={
                        "template_id": payload.template_id,
                        "error": "Template not found"
                    },
                    success=False
                )
                logger.end_session(
                    session_id=session_id,
                    success=False,
                    summary={"error": "Template not found"}
                )
                raise HTTPException(status_code=404, detail="Template not found")
            template_name = template.name
            
            logger.log_pipeline_step(
                session_id=session_id,
                step="template_found",
                details={
                    "template_id": payload.template_id,
                    "template_name": template_name,
                    "stage": "成功找到模板"
                }
            )

        # 使用带session的大纲生成方法
        slides = await generator._generate_with_session(
            payload.text, 
            payload.slide_count, 
            template_name, 
            session_id
        )
        
        # 记录最终响应
        logger.log_response(
            session_id=session_id,
            stage="outline_generate_complete",
            data={
                "slides_count": len(slides),
                "slides": [
                    {
                        "page_num": slide.page_num,
                        "type": slide.type.value,
                        "title": slide.title[:100],
                        "content_length": len(slide.content_text)
                    }
                    for slide in slides
                ]
            },
            success=True
        )
        
        logger.end_session(
            session_id=session_id,
            success=True,
            summary={
                "endpoint": "/outline/generate",
                "slides_generated": len(slides),
                "template_used": template_name
            }
        )
        
        return OutlineResponse(slides=slides)
        
    except Exception as e:
        logger.log_response(
            session_id=session_id,
            stage="outline_generate_error",
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
                "endpoint": "/outline/generate",
                "error": str(e)
            }
        )
        
        raise


@router.post("/generate-stream")
async def generate_outline_stream(
    payload: OutlineRequest,
    generator=Depends(get_outline_generator),
    store=Depends(get_template_store),
):
    """流式生成大纲接口，支持实时进度反馈"""
    logger = get_logger()
    
    # 开始会话记录
    session_id = logger.start_session(
        "/outline/generate-stream",
        text_length=len(payload.text),
        slide_count=payload.slide_count,
        template_id=payload.template_id
    )
    
    async def generate_stream():
        try:
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始生成大纲...', 'slide_count': payload.slide_count}, ensure_ascii=False)}\n\n"
            
            # 查找模板
            template_name = None
            if payload.template_id:
                yield f"data: {json.dumps({'type': 'progress', 'message': '正在查找模板...'}, ensure_ascii=False)}\n\n"
                
                template = store.get_template(payload.template_id)
                if not template:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Template not found'}, ensure_ascii=False)}\n\n"
                    return
                template_name = template.name
                
                yield f"data: {json.dumps({'type': 'progress', 'message': f'已找到模板: {template_name}'}, ensure_ascii=False)}\n\n"

            # 构建提示词
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在构建生成提示词...'}, ensure_ascii=False)}\n\n"
            prompt = generator._outline_prompt(payload.text, payload.slide_count, template_name)
            
            # 记录输入参数
            logger.log_request(
                session_id=session_id,
                stage="outline_generate_stream_request",
                data={
                    "text": payload.text,
                    "slide_count": payload.slide_count,
                    "template_id": payload.template_id,
                    "template_name": template_name
                }
            )
            
            # 调用LLM生成
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在调用AI生成大纲...'}, ensure_ascii=False)}\n\n"
            
            try:
                response_text = await generator.llm_client.chat(
                    prompt, 
                    model=generator.chat_model, 
                    temperature=0.3,
                    session_id=session_id,
                    stage="outline_generation_stream"
                )
                
                # 解析JSON响应
                yield f"data: {json.dumps({'type': 'progress', 'message': '正在解析AI响应...'}, ensure_ascii=False)}\n\n"
                slides_data = generator._parse_slides_json(response_text, session_id)
                
                if slides_data:
                    # 逐个发送幻灯片数据
                    for i, slide in enumerate(slides_data):
                        slide_data = {
                            'type': 'slide',
                            'slide': {
                                'page_num': slide.page_num,
                                'type': slide.type.value,
                                'title': slide.title,
                                'content_text': slide.content_text,
                                'visual_desc': slide.visual_desc,
                                'status': slide.status.value
                            },
                            'progress': f'{i + 1}/{len(slides_data)}',
                            'current_slide': i + 1,
                            'total_slides': len(slides_data)
                        }
                        yield f"data: {json.dumps(slide_data, ensure_ascii=False)}\n\n"
                    
                    # 发送完成信号
                    yield f"data: {json.dumps({'type': 'complete', 'message': '大纲生成完成', 'total_slides': len(slides_data)}, ensure_ascii=False)}\n\n"
                    
                    # 记录成功
                    logger.log_response(
                        session_id=session_id,
                        stage="outline_generate_stream_complete",
                        data={
                            "slides_count": len(slides_data),
                            "slides": [
                                {
                                    "page_num": slide.page_num,
                                    "type": slide.type.value,
                                    "title": slide.title[:100],
                                    "content_length": len(slide.content_text)
                                }
                                for slide in slides_data
                            ]
                        },
                        success=True
                    )
                    
                    logger.end_session(
                        session_id=session_id,
                        success=True,
                        summary={
                            "endpoint": "/outline/generate-stream",
                            "slides_generated": len(slides_data),
                            "template_used": template_name
                        }
                    )
                else:
                    raise ValueError("No slides parsed from response")
                    
            except Exception as llm_error:
                # 使用回退方案
                yield f"data: {json.dumps({'type': 'progress', 'message': 'AI生成失败，使用智能回退方案...'}, ensure_ascii=False)}\n\n"
                
                fallback_slides = generator._fallback_generate(
                    payload.text, 
                    payload.slide_count, 
                    template_name, 
                    session_id
                )
                
                # 逐个发送回退方案的幻灯片
                for i, slide in enumerate(fallback_slides):
                    slide_data = {
                        'type': 'slide',
                        'slide': {
                            'page_num': slide.page_num,
                            'type': slide.type.value,
                            'title': slide.title,
                            'content_text': slide.content_text,
                            'visual_desc': slide.visual_desc,
                            'status': slide.status.value
                        },
                        'progress': f'{i + 1}/{len(fallback_slides)}',
                        'current_slide': i + 1,
                        'total_slides': len(fallback_slides)
                    }
                    yield f"data: {json.dumps(slide_data, ensure_ascii=False)}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'complete', 'message': '大纲生成完成（使用回退方案）', 'total_slides': len(fallback_slides)}, ensure_ascii=False)}\n\n"
                
                logger.log_response(
                    session_id=session_id,
                    stage="outline_generate_stream_fallback",
                    data={
                        "slides_count": len(fallback_slides),
                        "fallback_used": True
                    },
                    success=True
                )
                
        except Exception as e:
            error_data = {
                'type': 'error',
                'message': f'生成失败: {str(e)}',
                'error_type': type(e).__name__
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            logger.log_response(
                session_id=session_id,
                stage="outline_generate_stream_error",
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
                    "endpoint": "/outline/generate-stream",
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
