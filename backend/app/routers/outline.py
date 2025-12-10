from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

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
