from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_image_generator, get_prompt_builder, get_settings
from ..schemas.generation import (
    SlideGenerateRequest,
    SlideGenerateResponse,
    SlideRegenerateRequest,
    BatchGenerateRequest,
    BatchGenerateResponse,
    BatchStatusRequest,
    BatchStatusResponse,
)
from ..schemas.slide import SlideStatus
from ..utils.logger import get_logger

router = APIRouter(prefix="/slide", tags=["slide"])


async def _create_image_response(
    payload: SlideGenerateRequest,
    prompt_builder,
    image_generator,
    endpoint_name: str = "/slide/generate"
) -> SlideGenerateResponse:
    logger = get_logger()
    
    # 开始会话记录
    session_id = logger.start_session(
        endpoint_name,
        title=payload.title,
        aspect_ratio=payload.aspect_ratio,
        style_prompt_length=len(payload.style_prompt),
        visual_desc_length=len(payload.visual_desc),
        content_text_length=len(payload.content_text)
    )
    
    try:
        # 记录请求输入
        logger.log_request(
            session_id=session_id,
            stage="slide_generate_request",
            data={
                "title": payload.title,
                "style_prompt": payload.style_prompt,
                "visual_desc": payload.visual_desc,
                "content_text": payload.content_text,
                "aspect_ratio": payload.aspect_ratio
            }
        )
        
        # 记录prompt构建过程
        logger.log_pipeline_step(
            session_id=session_id,
            step="prompt_building_start",
            details={
                "stage": "开始构建最终prompt"
            }
        )
        
        final_prompt = prompt_builder.build(
            payload.style_prompt,
            payload.visual_desc,
            title=payload.title,
            content_text=payload.content_text,
            aspect_ratio=payload.aspect_ratio,
        )
        
        logger.log_pipeline_step(
            session_id=session_id,
            step="prompt_built",
            details={
                "final_prompt_length": len(final_prompt),
                "final_prompt": final_prompt[:1000],  # 记录前1000字符
                "stage": "最终prompt构建完成"
            }
        )
        
        # 使用带session的图片生成方法
        generated = await image_generator._create_with_session(
            payload.title, 
            final_prompt, 
            payload.aspect_ratio,
            session_id
        )
        
        # 记录最终响应
        logger.log_response(
            session_id=session_id,
            stage="slide_generate_complete",
            data={
                "image_url": generated.image_url,
                "file_path": str(generated.file_path),
                "final_prompt": final_prompt,
                "aspect_ratio": generated.aspect_ratio
            },
            success=True
        )
        
        logger.end_session(
            session_id=session_id,
            success=True,
            summary={
                "endpoint": endpoint_name,
                "title": payload.title,
                "image_generated": True,
                "prompt_length": len(final_prompt)
            }
        )
        
        return SlideGenerateResponse(
            image_url=generated.image_url,
            final_prompt=final_prompt,
            revised_prompt=final_prompt,
            status=SlideStatus.done,
        )
        
    except Exception as e:
        logger.log_response(
            session_id=session_id,
            stage="slide_generate_error",
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
                "endpoint": endpoint_name,
                "error": str(e)
            }
        )
        
        raise


@router.post("/generate", response_model=SlideGenerateResponse)
async def generate_slide(
    payload: SlideGenerateRequest,
    prompt_builder=Depends(get_prompt_builder),
    image_generator=Depends(get_image_generator),
):
    return await _create_image_response(payload, prompt_builder, image_generator, "/slide/generate")


@router.post("/regenerate", response_model=SlideGenerateResponse)
async def regenerate_slide(
    payload: SlideRegenerateRequest,
    prompt_builder=Depends(get_prompt_builder),
    image_generator=Depends(get_image_generator),
):
    return await _create_image_response(payload, prompt_builder, image_generator, "/slide/regenerate")


# 创建全局批量生成器实例
_batch_generator = None

def get_batch_generator(
    image_generator=Depends(get_image_generator),
    prompt_builder=Depends(get_prompt_builder),
    settings=Depends(get_settings)
):
    """获取批量图片生成器实例"""
    global _batch_generator
    if _batch_generator is None:
        from ..services.batch_image_generator import BatchImageGenerator
        _batch_generator = BatchImageGenerator(
            image_generator, 
            prompt_builder,
            max_concurrent_batches=settings.batch_max_concurrent
        )
    return _batch_generator


@router.post("/batch/generate", response_model=BatchGenerateResponse)
async def batch_generate_slides(
    payload: BatchGenerateRequest,
    batch_generator=Depends(get_batch_generator),
    settings=Depends(get_settings),
):
    """
    批量生成幻灯片图片
    
    Args:
        payload: 批量生成请求，包含幻灯片列表和配置参数
        
    Returns:
        BatchGenerateResponse: 批量生成结果，包含所有幻灯片的生成状态
    """
    logger = get_logger()
    
    # 验证并发数不超过配置限制
    if payload.max_workers > settings.batch_max_workers:
        raise HTTPException(
            status_code=400,
            detail=f"max_workers exceeds maximum allowed: {settings.batch_max_workers}"
        )
    
    # 开始会话记录
    session_id = logger.start_session(
        "/slide/batch/generate",
        total_slides=len(payload.slides),
        max_workers=payload.max_workers,
        aspect_ratio=payload.aspect_ratio,
        style_prompt_length=len(payload.style_prompt)
    )
    
    try:
        # 记录批量生成请求
        logger.log_request(
            session_id=session_id,
            stage="batch_generate_request",
            data={
                "slides_count": len(payload.slides),
                "max_workers": payload.max_workers,
                "aspect_ratio": payload.aspect_ratio,
                "style_prompt": payload.style_prompt[:500],  # 只记录前500字符
                "slides": [
                    {
                        "id": str(slide.id),
                        "page_num": slide.page_num,
                        "title": slide.title[:50],
                        "type": slide.type.value,
                        "visual_desc": slide.visual_desc[:100]
                    }
                    for slide in payload.slides
                ]
            }
        )
        
        # 创建批量生成任务
        batch_id = batch_generator.create_batch(
            slides=payload.slides,
            style_prompt=payload.style_prompt,
            max_workers=payload.max_workers,
            aspect_ratio=payload.aspect_ratio
        )
        
        # 等待批量任务完成（实际应用中可能需要异步处理）
        import asyncio
        max_wait_time = 300  # 最大等待时间5分钟
        wait_interval = 2    # 检查间隔2秒
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status = batch_generator.get_batch_status(batch_id)
            if status and status.status in ["completed", "completed_with_errors", "failed"]:
                break
            await asyncio.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # 获取最终结果
        final_status = batch_generator.get_batch_status(batch_id)
        if not final_status:
            raise HTTPException(status_code=500, detail="Batch generation failed to start")
        
        total_time = elapsed_time
        
        # 构建响应
        response = BatchGenerateResponse(
            batch_id=batch_id,
            total_slides=len(payload.slides),
            successful=final_status.successful,
            failed=final_status.failed,
            total_time=total_time,
            results=final_status.results
        )
        
        # 记录最终响应
        logger.log_response(
            session_id=session_id,
            stage="batch_generate_complete",
            data={
                "batch_id": str(batch_id),
                "status": final_status.status,
                "total_slides": len(payload.slides),
                "successful": final_status.successful,
                "failed": final_status.failed,
                "total_time": total_time,
                "success_rate": response.success_rate,
                "results": [
                    {
                        "slide_id": str(result.slide_id),
                        "page_num": result.page_num,
                        "title": result.title,
                        "status": result.status.value,
                        "image_url": result.image_url,
                        "error_message": result.error_message,
                        "generation_time": result.generation_time
                    }
                    for result in final_status.results
                ]
            },
            success=final_status.successful > 0
        )
        
        logger.end_session(
            session_id=session_id,
            success=final_status.successful > 0,
            summary={
                "endpoint": "/slide/batch/generate",
                "batch_id": str(batch_id),
                "total_slides": len(payload.slides),
                "successful": final_status.successful,
                "failed": final_status.failed,
                "total_time": total_time,
                "success_rate": response.success_rate
            }
        )
        
        return response
        
    except Exception as e:
        logger.log_response(
            session_id=session_id,
            stage="batch_generate_error",
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
                "endpoint": "/slide/batch/generate",
                "error": str(e)
            }
        )
        
        raise HTTPException(status_code=500, detail=f"Batch generation failed: {str(e)}")


@router.post("/batch/status", response_model=BatchStatusResponse)
async def get_batch_status(
    payload: BatchStatusRequest,
    batch_generator=Depends(get_batch_generator),
):
    """
    查询批量生成状态
    
    Args:
        payload: 包含批量任务ID的请求
        
    Returns:
        BatchStatusResponse: 批量任务状态信息
    """
    logger = get_logger()
    
    try:
        status = batch_generator.get_batch_status(payload.batch_id)
        if not status:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # 记录状态查询
        logger.logger.info(f"Batch status queried: {payload.batch_id}, status: {status.status}, progress: {status.progress:.1%}")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"Error getting batch status {payload.batch_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.get("/batch/active-count")
async def get_active_batches_count(
    batch_generator=Depends(get_batch_generator),
):
    """
    获取当前活跃的批量任务数量
    
    Returns:
        dict: 包含活跃任务数量的字典
    """
    count = batch_generator.get_active_batches_count()
    return {"active_batches": count}


@router.get("/batch/config/validate")
async def validate_batch_config(
    settings=Depends(get_settings)
):
    """
    验证当前批量生成配置
    
    Returns:
        dict: 配置验证结果和建议
    """
    from ..utils.batch_config import validate_batch_config
    return validate_batch_config(settings)


@router.get("/batch/config/optimal")
async def get_optimal_config(
    slides_count: int,
    settings=Depends(get_settings)
):
    """
    根据幻灯片数量获取最优批量生成配置建议
    
    Args:
        slides_count: 幻灯片数量
        
    Returns:
        dict: 最优配置建议
    """
    from ..utils.batch_config import get_optimal_config
    return get_optimal_config(slides_count, settings)
