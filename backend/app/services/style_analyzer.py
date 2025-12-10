from __future__ import annotations

import io
import statistics
from typing import Iterable, List

from fastapi import UploadFile
from PIL import Image

from .llm_client import LLMClientError, OpenRouterClient
from ..utils.logger import get_logger

def _to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


class StyleAnalyzer:
    """Generate structured prompts based on reference images."""

    def __init__(self, llm_client: OpenRouterClient, chat_model: str) -> None:
        self.llm_client = llm_client
        self.chat_model = chat_model
        self.logger = get_logger()

    async def build_prompt(self, files: Iterable[UploadFile]) -> str:
        return await self._build_prompt_with_session(files)

    async def _build_prompt_with_session(self, files: Iterable[UploadFile], session_id: Optional[str] = None) -> str:
        if session_id is None:
            # 如果没有提供session_id，生成一个临时session用于记录
            session_id = self.logger.start_session("style_analyze", file_count=len(files))
        
        # 记录输入文件信息
        file_info = []
        analyses = []
        for upload in files:
            file_info.append({
                "filename": upload.filename,
                "content_type": upload.content_type,
                "size": getattr(upload, 'size', 'unknown')
            })
            
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="image_analysis_start",
                details={
                    "filename": upload.filename,
                    "stage": "开始像素分析"
                }
            )
            
            raw = await upload.read()
            if not raw:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="image_analysis_empty",
                    details={
                        "filename": upload.filename,
                        "stage": "文件为空，跳过分析"
                    }
                )
                continue
                
            with Image.open(io.BytesIO(raw)) as img:
                analysis = self._analyze_single(upload.filename or "reference", img)
                analyses.append(analysis)
                
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="image_analysis_complete",
                    details={
                        "filename": upload.filename,
                        "analysis": analysis,
                        "stage": "像素分析完成"
                    }
                )

        # 记录分析汇总
        self.logger.log_request(
            session_id=session_id,
            stage="style_analysis_input",
            data={
                "file_count": len(analyses),
                "files": file_info,
                "pixel_analyses": analyses
            }
        )

        if not analyses:
            fallback_prompt = (
                "你是一名严谨的视觉风格分析师。\n"
                "缺少参考图片，请保持理性描述并避免凭空想象。"
            )
            self.logger.log_response(
                session_id=session_id,
                stage="style_analysis_fallback",
                data={"prompt": fallback_prompt, "reason": "no_valid_images"}
            )
            return fallback_prompt

        # 构建prompt
        prompt_lines = [
            "你是一名严谨客观的视觉设计顾问。",
            "- 禁止使用隐喻或主观臆断。",
            "- 仅依据图像事实描述颜色、光线、构图与材质。",
            "- 输出内容需结构化、可供绘图模型直接引用。",
            "",
            "### 参考图逐条解析",
        ]

        for idx, info in enumerate(analyses, start=1):
            palette = ", ".join(info["palette"])
            block = [
                f"#### 参考图 {idx}: {info['filename']}",
                f"- 分辨率：{info['resolution']} ({info['orientation']})",
                f"- 主导色：{info['primary_color']}，辅助色：{palette}",
                f"- 光照与明度：{info['lighting']} (亮度 {info['luma']})",
                f"- 材质/质感：{info['texture']}",
                f"- 构图关键词：{', '.join(info['composition'])}",
                "",
            ]
            prompt_lines.extend(block)

        analysis_brief = "\n".join(prompt_lines)
        
        system_prompt = (
            "你是一名严谨客观的视觉风格分析师。"
            "请根据提供的观察笔记，输出结构化 Style Prompt。"
            "禁止编造不存在的元素，按照配色/材质 -> 构图/层次 -> 画面细节 -> 作图注意事项顺序输出。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "以下是参考图的客观观察，请整理成绘图可用的 prompt：\n\n"
                    f"{analysis_brief}\n\n输出需使用中文，尽量使用条列格式。"
                ),
            },
        ]

        # 记录LLM调用前的prompt构建
        self.logger.log_pipeline_step(
            session_id=session_id,
            step="llm_prompt_built",
            details={
                "analysis_brief": analysis_brief,
                "system_prompt": system_prompt,
                "stage": "LLM prompt构建完成"
            }
        )

        try:
            response = await self.llm_client.chat(
                messages, 
                model=self.chat_model, 
                temperature=0.2,
                session_id=session_id,
                stage="style_analysis"
            )
            final_prompt = response or analysis_brief
            
            # 记录最终结果
            self.logger.log_response(
                session_id=session_id,
                stage="style_analysis_complete",
                data={
                    "style_prompt": final_prompt,
                    "fallback_used": final_prompt == analysis_brief
                },
                success=True
            )
            
            return final_prompt
        except LLMClientError as e:
            # 记录错误并回退
            self.logger.log_response(
                session_id=session_id,
                stage="style_analysis_fallback",
                data={
                    "prompt": analysis_brief,
                    "error": str(e)
                },
                success=False
            )
            return analysis_brief

    def _analyze_single(self, filename: str, img: Image.Image) -> dict:
        rgb_image = img.convert("RGB")
        width, height = rgb_image.size
        thumb = rgb_image.resize((64, 64))
        pixels = list(thumb.getdata())
        avg_channels = tuple(int(sum(channel) / len(pixels)) for channel in zip(*pixels))
        luma = int(0.299 * avg_channels[0] + 0.587 * avg_channels[1] + 0.114 * avg_channels[2])

        palette = self._extract_palette(rgb_image)
        composition = self._composition_hints(width, height)

        return {
            "filename": filename,
            "resolution": f"{width}x{height}",
            "orientation": self._orientation(width, height),
            "primary_color": _to_hex(avg_channels),
            "palette": palette,
            "luma": luma,
            "lighting": self._lighting_desc(luma),
            "texture": self._texture_desc(rgb_image, luma),
            "composition": composition,
        }

    def _extract_palette(self, image: Image.Image) -> List[str]:
        reduced = image.resize((32, 32)).convert("P", palette=Image.ADAPTIVE, colors=5)
        palette = reduced.getpalette()
        color_counts = reduced.getcolors()
        if not color_counts:
            return []

        def palette_color(index: int) -> tuple[int, int, int]:
            base = index * 3
            return tuple(palette[base : base + 3])

        sorted_colors = sorted(color_counts, key=lambda item: item[0], reverse=True)
        seen: list[str] = []
        for _, color_index in sorted_colors:
            rgb = palette_color(color_index)
            hex_value = _to_hex(rgb)
            if hex_value not in seen:
                seen.append(hex_value)
        return seen

    def _orientation(self, width: int, height: int) -> str:
        if width > height:
            return "横向"
        if width < height:
            return "纵向"
        return "正方形"

    def _lighting_desc(self, luma: int) -> str:
        if luma >= 200:
            return "高光充足，整体通透"
        if luma >= 140:
            return "明亮柔和"
        if luma >= 90:
            return "中性光感"
        if luma >= 50:
            return "低调偏暗"
        return "戏剧性暗部"

    def _texture_desc(self, image: Image.Image, luma: int) -> str:
        gray = image.convert("L").resize((32, 32))
        samples = list(gray.getdata())
        variance = statistics.pvariance(samples)
        if variance < 200:
            texture = "磨砂/雾面"
        elif variance < 600:
            texture = "柔焦"
        else:
            texture = "高反差细节"
        depth = "轻盈" if luma > 160 else "厚重" if luma < 80 else "均衡"
        return f"{texture}，层次{depth}"

    def _composition_hints(self, width: int, height: int) -> List[str]:
        ratio = width / height if height else 1
        if ratio > 1.4:
            return ["横幅构图", "主视觉偏中心"]
        if ratio < 0.8:
            return ["竖构图", "上下留白"]
        return ["正方构图", "强调对称"]


__all__ = ["StyleAnalyzer"]
