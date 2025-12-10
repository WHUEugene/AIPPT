from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt

from ..schemas.project import ProjectState
from ..utils.logger import get_logger


class PPTXExporter:
    def __init__(self, output_dir: Path, image_dir: Path):
        self.output_dir = Path(output_dir)
        self.image_dir = Path(image_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()
    
    def _get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """获取图片的实际尺寸"""
        try:
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except Exception as e:
            self.logger.error(f"Failed to get image dimensions for {image_path}: {e}")
            raise

    def _calculate_optimal_fit(self, image_width: int, image_height: int, 
                              slide_width: float, slide_height: float) -> Tuple[float, float, float]:
        """计算图片在幻灯片中的最佳适配尺寸和缩放比例"""
        slide_aspect_ratio = slide_width / slide_height
        image_aspect_ratio = image_width / image_height
        
        if abs(image_aspect_ratio - slide_aspect_ratio) < 0.01:
            # 比例几乎相同，可以铺满
            return slide_width, slide_height, 1.0
        else:
            # 比例不同，选择最佳的适配方式
            if image_aspect_ratio > slide_aspect_ratio:
                # 图片更宽，以高度为准
                new_height = slide_height
                new_width = new_height * image_aspect_ratio
                if new_width > slide_width:
                    # 图片超出幻灯片，以宽度为准
                    new_width = slide_width
                    new_height = new_width / image_aspect_ratio
            else:
                # 图片更高，以宽度为准
                new_width = slide_width
                new_height = new_width / image_aspect_ratio
                if new_height > slide_height:
                    # 图片超出幻灯片，以高度为准
                    new_height = slide_height
                    new_width = new_height * image_aspect_ratio
            
            scale_factor = min(new_width / slide_width, new_height / slide_height)
            return new_width, new_height, scale_factor

    def _calculate_center_position(self, image_width: float, image_height: float,
                                   slide_width: float, slide_height: float) -> Tuple[float, float]:
        """计算图片在幻灯片中的中心位置"""
        left = (slide_width - image_width) / 2
        top = (slide_height - image_height) / 2
        return left, top

    def _add_picture_with_protection(self, slide, image_path: Path, slide_width: float, slide_height: float) -> bool:
        """添加图片到幻灯片，使幻灯片尺寸与图片匹配"""
        try:
            # 获取图片实际尺寸
            img_width, img_height = self._get_image_dimensions(image_path)
            
            # ✅ 修正：直接使用 EMU 单位，不进行单位换算
            picture = slide.shapes.add_picture(
                str(image_path), 0, 0,  # 左上角起始位置
                width=int(slide_width), height=int(slide_height)  # 直接使用 EMU 单位
            )
            
            # python-pptx 中没有 zorder 属性，后添加的元素默认就在上层
            # picture.zorder = 0  # 这行代码会导致 AttributeError
            
            # 记录图片调整信息
            self.logger.log_pipeline_step(
                session_id="pptx_export",
                step="image_added",
                details={
                    "image_file": image_path.name,
                    "original_size": f"{img_width}x{img_height}",
                    "slide_size": f"{int(slide_width)}x{int(slide_height)}",
                    "final_size": f"{img_width}x{img_height}",
                    "position": "(0, 0)",
                    "stage": "图片已添加到幻灯片"
                }
            )
            
            return True
            
        except Exception as e:
            print(f"❌ 图片添加失败: {e}")
            import logging
            logging.error(f"Failed to add image to slide: {e}")
            return False

    def build(self, project: ProjectState, session_id: Optional[str] = None) -> Tuple[str, BytesIO]:
        prs = Presentation()
        
        # 获取第一张图片的尺寸来设置幻灯片尺寸
        slide_width = prs.slide_width
        slide_height = prs.slide_height
        
        if project.slides and project.slides[0].image_url:
            first_image_path = self._resolve_image_path(project.slides[0].image_url)
            if first_image_path and first_image_path.exists():
                try:
                    img_width, img_height = self._get_image_dimensions(first_image_path)
                    # 将像素转换为PPTX单位（1英寸=914400 EMU，96 DPI）
                    slide_width = (img_width / 96) * 914400
                    slide_height = (img_height / 96) * 914400
                    prs.slide_width = int(slide_width)
                    prs.slide_height = int(slide_height)
                    self.logger.log_pipeline_step(
                        session_id=session_id or "pptx_export",
                        step="slide_size_adjusted",
                        details={
                            "image_size": f"{img_width}x{img_height}",
                            "slide_width_emu": int(slide_width),
                            "slide_height_emu": int(slide_height),
                            "slide_width_inches": slide_width / 914400,
                            "slide_height_inches": slide_height / 914400
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Failed to adjust slide size: {e}")
        
        slide_width = prs.slide_width
        slide_height = prs.slide_height
        
        if not session_id:
            session_id = self.logger.start_session(
                "pptx_export",
                project_title=project.title,
                slides_count=len(project.slides)
            )

        images_processed = 0
        images_failed = 0

        try:
            for i, slide_data in enumerate(project.slides):
                slide = prs.slides.add_slide(prs.slide_layouts[6])

                # 处理图片
                image_path = self._resolve_image_path(slide_data.image_url)
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="slide_image_check",
                    details={
                        "slide_index": i + 1,
                        "slide_title": slide_data.title,
                        "image_url": slide_data.image_url,
                        "resolved_path": str(image_path) if image_path else "None",
                        "path_exists": image_path.exists() if image_path else False,
                        "stage": f"第{i+1}张幻灯片图片路径检查"
                    }
                )
                
                if image_path and image_path.exists():
                    success = self._add_picture_with_protection(slide, image_path, slide_width, slide_height)
                    self.logger.log_pipeline_step(
                        session_id=session_id,
                        step="slide_image_add_result",
                        details={
                            "slide_index": i + 1,
                            "slide_title": slide_data.title,
                            "success": success,
                            "image_path": str(image_path),
                            "stage": f"第{i+1}张幻灯片图片添加结果: {'成功' if success else '失败'}"
                        }
                    )
                    if success:
                        images_processed += 1
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_image_processed",
                            details={
                                "slide_index": i + 1,
                                "slide_title": slide_data.title,
                                "image_path": str(image_path),
                                "stage": f"第{i+1}张幻灯片图片处理完成"
                            }
                        )
                    else:
                        images_failed += 1
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_image_failed",
                            details={
                                "slide_index": i + 1,
                                "slide_title": slide_data.title,
                                "image_path": str(image_path),
                                "stage": f"第{i+1}张幻灯片图片处理失败"
                            }
                        )
                else:
                    self.logger.log_pipeline_step(
                        session_id=session_id,
                        step="slide_no_image",
                        details={
                            "slide_index": i + 1,
                            "slide_title": slide_data.title,
                            "stage": f"第{i+1}张幻灯片无图片"
                        }
                    )

  
            buffer = BytesIO()
            # Fix encoding issue for Chinese characters
            import tempfile
            import os
            
            # First save to a temporary file to handle encoding properly
            with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Save to temp file first
                prs.save(temp_path)
                
                # Read from temp file into buffer
                with open(temp_path, 'rb') as f:
                    buffer.write(f.read())
                
                buffer.seek(0)
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            filename = self._filename(project)

            self.logger.log_response(
                session_id=session_id,
                stage="pptx_export_complete",
                data={
                    "filename": filename,
                    "total_slides": len(project.slides),
                    "images_processed": images_processed,
                    "images_failed": images_failed,
                    "success_rate": images_processed / len(project.slides) if project.slides else 0
                },
                success=True
            )

            return filename, buffer

        except Exception as e:
            self.logger.log_response(
                session_id=session_id,
                stage="pptx_export_error",
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "images_processed": images_processed,
                    "images_failed": images_failed
                },
                success=False
            )
            raise

    def _resolve_image_path(self, image_url: str | None) -> Path | None:
        if not image_url:
            return None
            
        # 1. 移除可能存在的 http 前缀 (如果前端传的是完整URL)
        if "://" in image_url:
            # 从URL中提取 assets/ 后面的部分
            if "assets/" in image_url:
                file_name = image_url.split("assets/", 1)[1]
                return self.image_dir / file_name
            else:
                return None

        sanitized = image_url.lstrip("/")
        
        # 2. 标准处理 assets 路径
        if sanitized.startswith("assets/"):
            file_name = sanitized.split("assets/", 1)[1]
            return self.image_dir / file_name
            
        # 3. 如果直接传了文件名，检查是否存在
        if (self.image_dir / sanitized).exists():
            return self.image_dir / sanitized

        return Path(sanitized)

    def _filename(self, project: ProjectState) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base = project.title or "AI_PPT_Flow"
        safe = "".join(char for char in base if char.isalnum() or char in ("_", "-"))[:40] or "AI_PPT_Flow"
        return f"{safe}_{timestamp}.pptx"


__all__ = ["PPTXExporter"]
