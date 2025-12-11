from __future__ import annotations

import asyncio
import hashlib
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from .llm_client import LLMClientError, OpenRouterClient
from ..utils.logger import get_logger
from ..utils.dimension_calculator import calculate_dimensions


@dataclass
class GeneratedImage:
    image_url: str
    file_path: Path
    aspect_ratio: str


class ImageGenerator:
    def __init__(self, output_dir: Path, llm_client: OpenRouterClient, image_model: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.llm_client = llm_client
        self.image_model = image_model
        self.logger = get_logger()

    async def create(self, title: str | None, final_prompt: str, aspect_ratio: str, page_num: Optional[int] = None) -> GeneratedImage:
        return await self._create_with_session(title, final_prompt, aspect_ratio, page_num)

    def create_sync(self, title: str | None, final_prompt: str, aspect_ratio: str, page_num: Optional[int] = None, session_id: Optional[str] = None) -> GeneratedImage:
        """Synchronous version of create for use in thread pools"""
        return asyncio.run(self._create_with_session(title, final_prompt, aspect_ratio, page_num, session_id))

    async def _create_with_session(
        self, 
        title: str | None, 
        final_prompt: str, 
        aspect_ratio: str,
        page_num: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> GeneratedImage:
        if session_id is None:
            session_id = self.logger.start_session(
                "image_generate",
                title=title,
                prompt_length=len(final_prompt),
                aspect_ratio=aspect_ratio
            )

        width, height = self._dimensions(aspect_ratio)
        # 使用页数和UUID生成文件名，格式：slide_{页数}_{UUID}.jpg 或 slide_{UUID}.jpg
        page_prefix = f"{int(page_num):03d}_" if page_num is not None else ""
        filename = f"slide_{page_prefix}{uuid4().hex}.jpg"
        file_path = self.output_dir / filename

        # 记录输入参数
        self.logger.log_request(
            session_id=session_id,
            stage="image_generation_input",
            data={
                "title": title,
                "final_prompt": final_prompt,
                "aspect_ratio": aspect_ratio,
                "width": width,
                "height": height,
                "filename": filename,
                "file_path": str(file_path)
            }
        )

        try:
            image_bytes = await self.llm_client.generate_image(
                final_prompt, 
                self.image_model, 
                width, 
                height,
                session_id=session_id
            )
            
            # 保存图片文件
            file_path.write_bytes(image_bytes)
            file_size = file_path.stat().st_size
            
            # 记录成功生成图片
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="image_saved",
                details={
                    "filename": filename,
                    "file_size": file_size,
                    "width": width,
                    "height": height,
                    "stage": "图片文件保存成功"
                }
            )

            result = GeneratedImage(
                image_url=f"/assets/{filename}", 
                file_path=file_path, 
                aspect_ratio=aspect_ratio
            )

            self.logger.log_response(
                session_id=session_id,
                stage="image_generation_complete",
                data={
                    "image_url": result.image_url,
                    "file_path": str(result.file_path),
                    "file_size": file_size,
                    "aspect_ratio": aspect_ratio,
                    "is_generated": True
                },
                success=True
            )

            return result

        except LLMClientError as e:
            # 生成占位图片
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="placeholder_start",
                details={
                    "error": str(e),
                    "stage": "LLM生成失败，开始生成占位图片"
                }
            )

            placeholder = self._placeholder_image(title, final_prompt, width, height)
            placeholder.save(file_path, format="JPEG")
            file_size = file_path.stat().st_size

            result = GeneratedImage(
                image_url=f"/assets/{filename}", 
                file_path=file_path, 
                aspect_ratio=aspect_ratio
            )

            self.logger.log_response(
                session_id=session_id,
                stage="image_generation_placeholder",
                data={
                    "image_url": result.image_url,
                    "file_path": str(result.file_path),
                    "file_size": file_size,
                    "aspect_ratio": aspect_ratio,
                    "is_generated": False,
                    "error": str(e)
                },
                success=True  # 即使是占位图也是成功响应
            )

            return result

    def _placeholder_image(self, title: str | None, final_prompt: str, width: int, height: int) -> Image.Image:
        bg_color = self._background_color(final_prompt)
        image = Image.new("RGB", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        text_lines = ["AI-PPT Flow", title or "Placeholder Slide"]
        summary = final_prompt[:200].replace("\n", " ")
        text_lines.append(summary)
        text = "\n".join(textwrap.wrap(" · ".join(text_lines), 40))
        draw.multiline_text((40, 40), text, fill=self._text_color(bg_color), font=font, spacing=6)
        return image

    def _dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        # 使用DimensionCalculator计算正确的尺寸
        return calculate_dimensions(aspect_ratio)

    def _background_color(self, prompt: str) -> tuple[int, int, int]:
        digest = hashlib.md5(prompt.encode("utf-8")).hexdigest()
        return tuple(int(digest[i : i + 2], 16) for i in (0, 2, 4))

    def _text_color(self, background: tuple[int, int, int]) -> tuple[int, int, int]:
        luminance = 0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]
        return (20, 20, 20) if luminance > 180 else (240, 240, 240)


__all__ = ["GeneratedImage", "ImageGenerator"]
