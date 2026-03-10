from __future__ import annotations

import io
import statistics
from typing import Iterable, List, Optional

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
            raise ValueError("未读取到有效参考图片，无法进行风格分析。")

        # 构建prompt
        aggregate = self._aggregate_analyses(analyses)
        prompt_lines = [
            "你是一名严谨客观的视觉设计顾问。",
            "- 禁止使用隐喻或主观臆断。",
            "- 仅依据图像事实描述颜色、光线、构图与材质。",
            "- 输出内容必须是模板级生图指令，而不是分析报告。",
            "",
            "### 跨参考图汇总",
            f"- 参考图数量：{aggregate['image_count']}",
            f"- 常见画幅：{aggregate['orientation']}",
            f"- 主色板：{', '.join(aggregate['palette'])}",
            f"- 明度趋势：{aggregate['lighting']}",
            f"- 饱和度趋势：{aggregate['saturation_desc']}",
            f"- 对比度趋势：{aggregate['contrast_desc']}",
            f"- 色彩丰富度：{aggregate['colorfulness_desc']}",
            f"- 留白比例：{aggregate['whitespace_desc']}",
            f"- 常见构图：{', '.join(aggregate['composition'])}",
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
                f"- 饱和度：{info['saturation_desc']} (均值 {info['saturation']})",
                f"- 对比度：{info['contrast_desc']} (标准差 {info['contrast']})",
                f"- 色彩丰富度：{info['colorfulness_desc']} (指标 {info['colorfulness']})",
                f"- 留白：{info['whitespace_desc']} (比例 {info['whitespace_ratio']})",
                f"- 材质/质感：{info['texture']}",
                f"- 构图关键词：{', '.join(info['composition'])}",
                "",
            ]
            prompt_lines.extend(block)

        analysis_brief = "\n".join(prompt_lines)
        
        system_prompt = """
你是一名顶级 PPT 视觉总监，负责把参考图观察笔记整理成“可直接用于整套幻灯片生图”的模板风格指令。

你的输出不是分析报告，而是一份可以直接拼进绘图 prompt 的模板级规范。必须满足：
1. 只依据观察笔记，不要编造参考图里没有的视觉母题。
2. 优先输出“版式、留白、图片处理、文字处理、形状语言、配色、禁忌项”。
3. 重点描述整页 PPT 画面的生成规则，而不是单张摄影作品的评论。
4. 要让输出尽量具体，可操作，可复现，避免空泛形容词。
5. 不要写“根据参考图”“观察可见”“建议”等分析腔。

严格按下面结构输出，使用中文：

### 视觉风格与美术指导
- 整体基调
- 版式与构图
- 图像与插画处理
- 文字与标题处理
- 形状、边框与装饰元素
- 配色方案
- 负向约束

要求：
- 每个部分都写成可直接用于生图的规则。
- 尽量包含尺寸关系、对齐方式、留白倾向、图片裁切方式、标题位置、正文表现形式、边框粗细、强调色使用范围。
- 输出里不要出现 JSON、代码块、前言、结语。
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "以下是参考图的客观观察，请整理成绘图可用的 prompt：\n\n"
                    f"{analysis_brief}\n\n"
                    "请特别把以下内容写清楚：\n"
                    "- 页面是重留白还是重铺满\n"
                    "- 标题/正文/数字编号通常如何摆放\n"
                    "- 图片是摄影、插画、线稿、拼贴还是纯图形\n"
                    "- 边框、分割线、色块、角半径、阴影是否存在\n"
                    "- 强调色只出现在哪里，哪些地方必须克制\n"
                    "- 明确列出不应该出现的风格偏差\n"
                    "输出需使用中文，尽量使用短句和条列。"
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
                temperature=0.1,
                session_id=session_id,
                stage="style_analysis"
            )
            final_prompt = response
            
            # 记录最终结果
            self.logger.log_response(
                session_id=session_id,
                stage="style_analysis_complete",
                data={
                    "style_prompt": final_prompt
                },
                success=True
            )
            
            return final_prompt
        except LLMClientError as e:
            self.logger.log_response(
                session_id=session_id,
                stage="style_analysis_error",
                data={
                    "error": str(e)
                },
                success=False
            )
            raise

    def _analyze_single(self, filename: str, img: Image.Image) -> dict:
        rgb_image = img.convert("RGB")
        width, height = rgb_image.size
        thumb = rgb_image.resize((64, 64))
        pixels = list(thumb.getdata())
        avg_channels = tuple(int(sum(channel) / len(pixels)) for channel in zip(*pixels))
        luma = int(0.299 * avg_channels[0] + 0.587 * avg_channels[1] + 0.114 * avg_channels[2])

        palette = self._extract_palette(rgb_image)
        composition = self._composition_hints(width, height)
        saturation = self._saturation_mean(rgb_image)
        contrast = self._contrast_value(rgb_image)
        colorfulness = self._colorfulness(rgb_image)
        whitespace_ratio = self._whitespace_ratio(rgb_image)

        return {
            "filename": filename,
            "resolution": f"{width}x{height}",
            "orientation": self._orientation(width, height),
            "primary_color": _to_hex(avg_channels),
            "palette": palette,
            "luma": luma,
            "lighting": self._lighting_desc(luma),
            "saturation": saturation,
            "saturation_desc": self._saturation_desc(saturation),
            "contrast": contrast,
            "contrast_desc": self._contrast_desc(contrast),
            "colorfulness": colorfulness,
            "colorfulness_desc": self._colorfulness_desc(colorfulness),
            "whitespace_ratio": whitespace_ratio,
            "whitespace_desc": self._whitespace_desc(whitespace_ratio),
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

    def _saturation_mean(self, image: Image.Image) -> int:
        hsv = image.convert("HSV").resize((32, 32))
        saturation = [pixel[1] for pixel in hsv.getdata()]
        return int(sum(saturation) / len(saturation))

    def _saturation_desc(self, saturation: int) -> str:
        if saturation < 40:
            return "极低饱和"
        if saturation < 80:
            return "低饱和克制"
        if saturation < 140:
            return "中等饱和"
        return "高饱和鲜明"

    def _contrast_value(self, image: Image.Image) -> int:
        gray = image.convert("L").resize((32, 32))
        samples = list(gray.getdata())
        return int(statistics.pstdev(samples))

    def _contrast_desc(self, contrast: int) -> str:
        if contrast < 25:
            return "低对比柔和"
        if contrast < 45:
            return "中等对比"
        return "高对比鲜明"

    def _colorfulness(self, image: Image.Image) -> int:
        sample = image.resize((32, 32))
        rg = []
        yb = []
        for r, g, b in sample.getdata():
            rg.append(abs(r - g))
            yb.append(abs(0.5 * (r + g) - b))
        return int(statistics.mean(rg) + statistics.mean(yb))

    def _colorfulness_desc(self, value: int) -> str:
        if value < 35:
            return "偏单色/克制"
        if value < 70:
            return "有限彩度变化"
        return "色彩层次丰富"

    def _whitespace_ratio(self, image: Image.Image) -> float:
        gray = image.convert("L").resize((48, 48))
        pixels = list(gray.getdata())
        bright_pixels = sum(1 for pixel in pixels if pixel >= 235)
        return round(bright_pixels / max(len(pixels), 1), 2)

    def _whitespace_desc(self, ratio: float) -> str:
        if ratio >= 0.45:
            return "大面积留白"
        if ratio >= 0.22:
            return "中等留白"
        return "画面铺满为主"

    def _composition_hints(self, width: int, height: int) -> List[str]:
        ratio = width / height if height else 1
        if ratio > 1.4:
            return ["横幅构图", "主视觉偏中心"]
        if ratio < 0.8:
            return ["竖构图", "上下留白"]
        return ["正方构图", "强调对称"]

    def _aggregate_analyses(self, analyses: List[dict]) -> dict:
        orientations = [item["orientation"] for item in analyses]
        palettes: list[str] = []
        for item in analyses:
            for color in [item["primary_color"], *item["palette"]]:
                if color not in palettes:
                    palettes.append(color)

        composition: list[str] = []
        for item in analyses:
            for hint in item["composition"]:
                if hint not in composition:
                    composition.append(hint)

        mean_luma = int(statistics.mean(item["luma"] for item in analyses))
        mean_saturation = int(statistics.mean(item["saturation"] for item in analyses))
        mean_contrast = int(statistics.mean(item["contrast"] for item in analyses))
        mean_colorfulness = int(statistics.mean(item["colorfulness"] for item in analyses))
        mean_whitespace = round(statistics.mean(item["whitespace_ratio"] for item in analyses), 2)

        return {
            "image_count": len(analyses),
            "orientation": max(set(orientations), key=orientations.count),
            "palette": palettes[:8],
            "lighting": self._lighting_desc(mean_luma),
            "saturation_desc": self._saturation_desc(mean_saturation),
            "contrast_desc": self._contrast_desc(mean_contrast),
            "colorfulness_desc": self._colorfulness_desc(mean_colorfulness),
            "whitespace_desc": self._whitespace_desc(mean_whitespace),
            "composition": composition[:6],
        }


__all__ = ["StyleAnalyzer"]
