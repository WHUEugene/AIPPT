from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, UploadFile

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
