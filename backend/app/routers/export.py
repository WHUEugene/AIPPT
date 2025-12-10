from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..dependencies import get_pptx_exporter
from ..schemas.export import ExportRequest
from ..utils.logger import get_logger

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/pptx")
async def export_pptx(
    payload: ExportRequest,
    exporter=Depends(get_pptx_exporter),
):
    logger = get_logger()
    
    # 开始导出会话记录
    session_id = logger.start_session(
        "pptx_export",
        project_title=payload.project.title,
        slides_count=len(payload.project.slides),
        file_name=payload.file_name
    )
    
    # 记录导出请求
    logger.log_request(
        session_id=session_id,
        stage="pptx_export_request",
        data={
            "project_title": payload.project.title,
            "slides_count": len(payload.project.slides),
            "file_name": payload.file_name,
            "template_style": payload.project.template_style_prompt,
            "slides": [
                {
                    "page_num": slide.page_num,
                    "title": slide.title,
                    "has_image": bool(slide.image_url),
                    "content_length": len(slide.content_text or "")
                }
                for slide in payload.project.slides
            ]
        }
    )
    
    try:
        filename, buffer = exporter.build(payload.project, session_id=session_id)
        final_name = payload.file_name or filename
        
        # 记录导出成功
        logger.log_response(
            session_id=session_id,
            stage="pptx_export_success",
            data={
                "final_filename": final_name,
                "original_filename": filename,
                "file_size_bytes": buffer.tell() if hasattr(buffer, 'tell') else "unknown",
                "slides_processed": len(payload.project.slides)
            },
            success=True
        )
        
        # 重置buffer位置以便读取
        buffer.seek(0)
        
        # 处理文件名的中文编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(final_name)
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers=headers,
        )
        
    except Exception as e:
        # 记录导出失败
        logger.log_response(
            session_id=session_id,
            stage="pptx_export_error",
            data={
                "error": str(e),
                "error_type": type(e).__name__,
                "project_title": payload.project.title,
                "slides_count": len(payload.project.slides)
            },
            success=False
        )
        raise
