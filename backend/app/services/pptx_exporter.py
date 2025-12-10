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
        """添加图片到幻灯片，带有尺寸保护"""
        try:
            # 获取图片实际尺寸
            img_width, img_height = self._get_image_dimensions(image_path)
            
            # 计算最佳适配
            opt_width, opt_height, scale = self._calculate_optimal_fit(
                img_width, img_height, slide_width, slide_height
            )
            
            # 计算居中位置
            left, top = self._calculate_center_position(opt_width, opt_height, slide_width, slide_height)
            
            # 转换为PPTX使用的单位（Inches）
            left_inch = left / 96  # 1 inch = 96 pixels
            top_inch = top / 96
            width_inch = opt_width / 96
            height_inch = opt_height / 96
            
            # 添加图片
            picture = slide.shapes.add_picture(
                str(image_path), left_inch, top_inch, 
                width=width_inch, height=height_inch
            )
            
            # 记录图片调整信息
            self.logger.log_pipeline_step(
                session_id="pptx_export",
                step="image_added",
                details={
                    "image_file": image_path.name,
                    "original_size": f"{img_width}x{img_height}",
                    "slide_size": f"{int(slide_width)}x{int(slide_height)}",
                    "final_size": f"{int(opt_width)}x{int(opt_height)}",
                    "scale_factor": scale,
                    "position": f"({left:.0f}, {top:.0f})",
                    "stage": "图片已添加到幻灯片"
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add image to slide: {e}")
            return False

    def build(self, project: ProjectState, session_id: Optional[str] = None) -> Tuple[str, BytesIO]:
        prs = Presentation()
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
                if image_path and image_path.exists():
                    success = self._add_picture_with_protection(slide, image_path, slide_width, slide_height)
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

                # 添加文本
                textbox = slide.shapes.add_textbox(Inches(0.6), Inches(0.5), slide_width - Inches(1.2), Inches(2.5))
                text_frame = textbox.text_frame
                text_frame.clear()
                
                if slide_data.title:
                    title_paragraph = text_frame.paragraphs[0]
                    title_paragraph.text = slide_data.title
                    title_paragraph.font.size = Pt(32)
                    title_paragraph.font.bold = True

                if slide_data.content_text:
                    body = text_frame.add_paragraph()
                    body.text = slide_data.content_text
                    body.font.size = Pt(18)

            buffer = BytesIO()
            prs.save(buffer)
            buffer.seek(0)
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
        sanitized = image_url.lstrip("/")
        if sanitized.startswith("assets/"):
            file_name = sanitized.split("assets/", 1)[1]
            return self.image_dir / file_name
        return Path(sanitized)

    def _filename(self, project: ProjectState) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base = project.title or "AI_PPT_Flow"
        safe = "".join(char for char in base if char.isalnum() or char in ("_", "-"))[:40] or "AI_PPT_Flow"
        return f"{safe}_{timestamp}.pptx"


__all__ = ["PPTXExporter"]
