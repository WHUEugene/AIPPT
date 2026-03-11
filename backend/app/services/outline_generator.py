from __future__ import annotations

import json
import math
import re
from typing import Any, List, Sequence, Optional

from ..schemas.outline import SlideContext
from ..schemas.slide import SlideData, SlideStatus, SlideType
from .llm_client import LLMClientError, OpenRouterClient
from ..utils.logger import get_logger


class OutlineGenerator:
    """Convert long-form text into structured slide outlines."""

    def __init__(self, llm_client: OpenRouterClient, chat_model: str) -> None:
        self.llm_client = llm_client
        self.chat_model = chat_model
        self.logger = get_logger()

    async def generate(
        self,
        text: str,
        slide_count: int,
        template_name: str | None = None,
    ) -> List[SlideData]:
        return await self._generate_with_session(text, slide_count, template_name)

    async def _generate_with_session(
        self,
        text: str,
        slide_count: int,
        template_name: str | None = None,
        session_id: Optional[str] = None,
    ) -> List[SlideData]:
        if session_id is None:
            session_id = self.logger.start_session(
                "outline_generate", 
                text_length=len(text), 
                slide_count=slide_count, 
                template_name=template_name
            )

        # 记录输入参数
        self.logger.log_request(
            session_id=session_id,
            stage="outline_generation_input",
            data={
                "text": text,
                "slide_count": slide_count,
                "template_name": template_name,
                "text_length": len(text),
                "paragraph_count": len(text.split('\n\n'))
            }
        )

        prompt = self._outline_prompt(text, slide_count, template_name)
        
        # 记录prompt构建
        self.logger.log_pipeline_step(
            session_id=session_id,
            step="llm_prompt_built",
            details={
                "prompt": prompt,
                "stage": "大纲生成prompt构建完成"
            }
        )

        try:
            response_text = await self.llm_client.chat(
                prompt, 
                model=self.chat_model, 
                temperature=0.3,
                session_id=session_id,
                stage="outline_generation"
            )
            
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="llm_response_received",
                details={
                    "response_length": len(response_text),
                    "stage": "收到LLM响应"
                }
            )
            
            slides_data = self._parse_slides_json(response_text, session_id)
            if slides_data:
                # 记录成功解析的大纲
                self.logger.log_response(
                    session_id=session_id,
                    stage="outline_generation_complete",
                    data={
                        "slides_count": len(slides_data),
                        "slides": [
                            {
                                "page_num": slide.page_num,
                                "type": slide.type.value,
                                "title": slide.title[:100],
                                "content_length": len(slide.content_text),
                                "visual_desc": slide.visual_desc[:100]
                            }
                            for slide in slides_data
                        ]
                    },
                    success=True
                )
                return slides_data
        except LLMClientError as e:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="llm_error",
                details={
                    "error": str(e),
                    "stage": "LLM调用失败"
                }
            )
            raise
        except ValueError as e:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="json_parse_error",
                details={
                    "error": str(e),
                    "stage": "JSON解析失败"
                }
            )
            raise

    async def generate_insert_slide(
        self,
        user_prompt: str,
        insert_after_page_num: int,
        prev_slide: SlideContext | None = None,
        next_slide: SlideContext | None = None,
        template_name: str | None = None,
        style_prompt: str | None = None,
    ) -> SlideData:
        session_id = self.logger.start_session(
            "outline_insert_slide",
            user_prompt_length=len(user_prompt),
            insert_after_page_num=insert_after_page_num,
            has_prev_slide=bool(prev_slide),
            has_next_slide=bool(next_slide),
            template_name=template_name,
        )

        self.logger.log_request(
            session_id=session_id,
            stage="insert_slide_request",
            data={
                "user_prompt": user_prompt,
                "insert_after_page_num": insert_after_page_num,
                "template_name": template_name,
                "style_prompt_length": len(style_prompt or ""),
                "prev_slide": prev_slide.model_dump() if prev_slide else None,
                "next_slide": next_slide.model_dump() if next_slide else None,
            }
        )

        prompt = self._insert_slide_prompt(
            user_prompt=user_prompt,
            prev_slide=prev_slide,
            next_slide=next_slide,
            template_name=template_name,
            style_prompt=style_prompt,
        )

        self.logger.log_pipeline_step(
            session_id=session_id,
            step="insert_slide_prompt_built",
            details={
                "stage": "插页提示词构建完成",
                "prompt": prompt,
            }
        )

        try:
            response_text = await self.llm_client.chat(
                prompt,
                model=self.chat_model,
                temperature=0.35,
                session_id=session_id,
                stage="insert_slide_generation"
            )

            slide_type = self._infer_insert_type(prev_slide, next_slide)
            slide = self._parse_single_slide_json(
                response_text,
                page_num=insert_after_page_num + 1,
                default_type=slide_type,
                template_name=template_name,
                session_id=session_id,
            )

            self.logger.log_response(
                session_id=session_id,
                stage="insert_slide_complete",
                data={
                    "page_num": slide.page_num,
                    "type": slide.type.value,
                    "title": slide.title,
                    "content_length": len(slide.content_text),
                    "visual_desc": slide.visual_desc,
                },
                success=True,
            )

            self.logger.end_session(
                session_id=session_id,
                success=True,
                summary={
                    "endpoint": "outline_insert_slide",
                    "page_num": slide.page_num,
                    "title": slide.title,
                }
            )
            return slide
        except Exception as exc:
            self.logger.log_response(
                session_id=session_id,
                stage="insert_slide_error",
                data={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                success=False,
            )
            self.logger.end_session(
                session_id=session_id,
                success=False,
                summary={
                    "endpoint": "outline_insert_slide",
                    "error": str(exc),
                }
            )
            raise

    def _outline_prompt(self, text: str, slide_count: int, template_name: str | None) -> list[dict[str, str]]:
        template_hint = f"模版：{template_name}." if template_name else ""
        system = (
            "你是一名专业的 PPT 编剧，负责将文档拆解为分页大纲。"
            "输出 JSON，数组中每个元素包含 page_num, type (cover/content/ending), title, content_text, visual_desc。"
            "visual_desc 必须描述可视化画面，不得抽象或隐喻，必须为中文。"
        )
        user = (
            f"原始文本：\n{text.strip()}\n\n"
            f"预期页数：{slide_count}。{template_hint}"
            "请按照 JSON 数组输出，严禁出现额外注释或代码块标记。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _insert_slide_prompt(
        self,
        user_prompt: str,
        prev_slide: SlideContext | None,
        next_slide: SlideContext | None,
        template_name: str | None,
        style_prompt: str | None,
    ) -> list[dict[str, str]]:
        system = (
            "你是一名专业的 PPT 编剧，负责在现有演示文稿中插入一页新的内容页。"
            "你必须同时参考用户新增要求、前一页和后一页的内容，让新页在逻辑上顺承自然。"
            "仅输出一个 JSON 对象，字段必须包含 type, title, content_text, visual_desc。"
            "type 优先使用 content；title 要简洁；content_text 要可直接作为页面正文；"
            "visual_desc 必须是中文，明确描述画面主体、布局、前景背景和可视化元素，不得抽象空泛。"
        )
        template_hint = f"模板名称：{template_name}\n" if template_name else ""
        style_hint = f"模板风格提示：{(style_prompt or '').strip()[:600]}\n" if style_prompt else ""
        user = (
            f"{template_hint}"
            f"{style_hint}"
            f"用户希望新增这一页：\n{user_prompt.strip()}\n\n"
            f"前一页：\n{self._format_slide_context(prev_slide)}\n\n"
            f"后一页：\n{self._format_slide_context(next_slide)}\n\n"
            "要求：\n"
            "1. 这一页必须承接前一页并为后一页做铺垫。\n"
            "2. 正文尽量控制为 3-5 条要点，适合 PPT 页面直接使用。\n"
            "3. 画面描述要能支持后续图片生成，明确元素、构图和信息层次。\n"
            "4. 不要输出代码块，不要输出额外解释。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _parse_slides_json(self, payload: str, session_id: Optional[str] = None) -> List[SlideData]:
        text = payload.strip()
        
        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="json_parse_start",
                details={
                    "payload_length": len(text),
                    "stage": "开始JSON解析"
                }
            )

        match = re.search(r"(\[.*\])", text, re.DOTALL)
        target = match.group(1) if match else text
        
        try:
            raw = json.loads(target, strict=False)
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            if session_id:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="json_decode_error",
                    details={
                        "error": error_msg,
                        "target_text": target[:500],
                        "stage": "JSON解码失败"
                    }
                )
            raise ValueError(error_msg) from e

        if not isinstance(raw, list):
            error_msg = "Outline response is not a list"
            if session_id:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="json_type_error",
                    details={
                        "error": error_msg,
                        "actual_type": type(raw).__name__,
                        "stage": "JSON类型验证失败"
                    }
                )
            raise ValueError(error_msg)

        slides: list[SlideData] = []
        for idx, item in enumerate(raw, start=1):
            if not isinstance(item, dict):
                if session_id:
                    self.logger.log_pipeline_step(
                        session_id=session_id,
                        step="skip_invalid_item",
                        details={
                            "index": idx,
                            "type": type(item).__name__,
                            "stage": "跳过非字典项"
                        }
                    )
                continue
                
            slide_type = self._normalize_type(item.get("type"))
            title = (item.get("title") or f"Slide {idx}").strip()
            content = (item.get("content_text") or item.get("content") or "").strip()
            visual_desc = (item.get("visual_desc") or item.get("visual")) or ""
            
            if not visual_desc:
                visual_desc = self._build_visual_desc(title, content, slide_type, None)
                
            slide = SlideData(
                page_num=item.get("page_num") or idx,
                type=slide_type,
                title=title,
                content_text=content or "待完善内容",
                visual_desc=visual_desc,
                status=SlideStatus.pending,
            )
            slides.append(slide)
            
            if session_id:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="slide_parsed",
                    details={
                        "slide_index": idx,
                        "page_num": slide.page_num,
                        "type": slide.type.value,
                        "title": title[:50],
                        "content_length": len(content),
                        "visual_desc": visual_desc[:100] if visual_desc else "empty",
                        "stage": "成功解析幻灯片"
                    }
                )

        if not slides:
            error_msg = "No slides parsed from response"
            if session_id:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="no_slides_parsed",
                    details={
                        "error": error_msg,
                        "raw_items_count": len(raw) if isinstance(raw, list) else 0,
                        "stage": "未解析出任何幻灯片"
                    }
                )
            raise ValueError(error_msg)

        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="json_parse_complete",
                details={
                    "slides_count": len(slides),
                    "stage": "JSON解析完成"
                }
            )

        return slides

    def _parse_single_slide_json(
        self,
        payload: str,
        page_num: int,
        default_type: SlideType,
        template_name: str | None,
        session_id: Optional[str] = None,
    ) -> SlideData:
        text = payload.strip()

        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="single_slide_parse_start",
                details={
                    "payload_length": len(text),
                    "stage": "开始解析插页 JSON",
                }
            )

        obj_match = re.search(r"(\{.*\})", text, re.DOTALL)
        list_match = re.search(r"(\[.*\])", text, re.DOTALL)
        target = obj_match.group(1) if obj_match else list_match.group(1) if list_match else text

        try:
            raw = json.loads(target, strict=False)
        except json.JSONDecodeError as exc:
            raise ValueError(f"插页 JSON 解析失败: {exc}") from exc

        if isinstance(raw, list):
            if not raw or not isinstance(raw[0], dict):
                raise ValueError("插页结果不是有效的 JSON 对象")
            raw = raw[0]

        if not isinstance(raw, dict):
            raise ValueError("插页结果不是 JSON 对象")

        slide_type = self._normalize_type(raw.get("type")) if raw.get("type") else default_type
        title = (raw.get("title") or "新增页面").strip()
        content = (raw.get("content_text") or raw.get("content") or "").strip()
        visual_desc = (raw.get("visual_desc") or raw.get("visual") or "").strip()
        if not content:
            content = "待完善内容"
        if not visual_desc:
            visual_desc = self._build_visual_desc(title, content, slide_type, template_name)

        slide = SlideData(
            page_num=page_num,
            type=slide_type,
            title=title,
            content_text=content,
            visual_desc=visual_desc,
            status=SlideStatus.pending,
        )

        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="single_slide_parse_complete",
                details={
                    "page_num": slide.page_num,
                    "type": slide.type.value,
                    "title": slide.title,
                    "stage": "插页 JSON 解析完成",
                }
            )

        return slide

    def _normalize_type(self, raw_type: Any) -> SlideType:
        if isinstance(raw_type, str):
            raw_type = raw_type.lower()
            if raw_type.startswith("cover"):
                return SlideType.cover
            if raw_type.startswith("end"):
                return SlideType.ending
        return SlideType.content

    def _fallback_generate(self, text: str, slide_count: int, template_name: str | None, session_id: Optional[str] = None) -> List[SlideData]:
        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="fallback_start",
                details={
                    "text_length": len(text),
                    "slide_count": slide_count,
                    "template_name": template_name,
                    "stage": "开始回退方案生成"
                }
            )

        paragraphs = self._split_text(text)
        
        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="text_split",
                details={
                    "paragraph_count": len(paragraphs),
                    "paragraphs": [p[:100] for p in paragraphs[:3]],  # 只记录前3个段落的前100字符
                    "stage": "文本分割完成"
                }
            )

        slide_count = max(1, min(slide_count, 50))
        segments = self._distribute(paragraphs, slide_count)

        slides: list[SlideData] = []
        total = len(segments)
        for idx, chunk in enumerate(segments):
            slide_type = self._infer_type(idx, total)
            title = self._derive_title(chunk, idx)
            content = "\n".join(chunk).strip()
            visual_desc = self._build_visual_desc(title, content, slide_type, template_name)
            slide = SlideData(
                page_num=idx + 1,
                type=slide_type,
                title=title,
                content_text=content,
                visual_desc=visual_desc,
                status=SlideStatus.pending,
            )
            slides.append(slide)
            
            if session_id:
                self.logger.log_pipeline_step(
                    session_id=session_id,
                    step="slide_fallback_created",
                    details={
                        "slide_index": idx,
                        "page_num": slide.page_num,
                        "type": slide.type.value,
                        "title": title[:50],
                        "content_length": len(content),
                        "chunk_size": len(chunk),
                        "stage": "回退方案创建幻灯片"
                    }
                )

        if session_id:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="fallback_complete",
                details={
                    "total_slides": len(slides),
                    "stage": "回退方案生成完成"
                }
            )

        return slides

    def _split_text(self, text: str) -> List[str]:
        trimmed = text.strip()
        if not trimmed:
            return ["用户未提供详细文本，请生成概念占位内容。"]
        paragraphs = [
            block.strip()
            for block in re.split(r"\n\s*\n+", trimmed)
            if block.strip()
        ]
        return paragraphs or [trimmed]

    def _distribute(self, paragraphs: Sequence[str], slide_count: int) -> List[List[str]]:
        if not paragraphs:
            return [["自动占位内容"] for _ in range(slide_count)]

        remaining = list(paragraphs)
        segments: list[list[str]] = []
        for index in range(slide_count):
            slots_left = slide_count - index
            chunk_size = max(1, math.ceil(len(remaining) / max(slots_left, 1)))
            chunk = remaining[:chunk_size]
            remaining = remaining[chunk_size:]
            if not chunk:
                chunk = ["补充要点"]
            segments.append(chunk)
        return segments

    def _infer_type(self, idx: int, total: int) -> SlideType:
        if idx == 0:
            return SlideType.cover
        if idx == total - 1:
            return SlideType.ending
        return SlideType.content

    def _infer_insert_type(
        self,
        prev_slide: SlideContext | None,
        next_slide: SlideContext | None,
    ) -> SlideType:
        if prev_slide is None and next_slide is not None:
            return self._normalize_type(next_slide.type)
        if next_slide is None and prev_slide is not None:
            return self._normalize_type(prev_slide.type)
        return SlideType.content

    def _derive_title(self, chunk: Sequence[str], idx: int) -> str:
        joined = " ".join(chunk).strip()
        if not joined:
            return f"Slide {idx + 1}"
        first_sentence = re.split(r"[。！？!?\n]", joined)[0].strip()
        first_sentence = first_sentence[:80]
        return first_sentence or f"Slide {idx + 1}"

    def _build_visual_desc(
        self,
        title: str,
        content: str,
        slide_type: SlideType,
        template_name: str | None,
    ) -> str:
        keywords = self._keywords(content or title)
        role = "封面" if slide_type is SlideType.cover else "收尾" if slide_type is SlideType.ending else "内容"
        lines = [
            f"{role}画面聚焦主题《{title}》，突出关键元素：{', '.join(keywords)}。",
            "强调真实可落地的场景，不要抽象隐喻。",
            "优先采用 16:9 画幅，留出标题与正文的安全区域。",
        ]
        if template_name:
            lines.append(f"沿用模版《{template_name}》的配色、材质与排版韵律。")
        lines.append("画面需描述清晰主体、前景/背景层次以及光源方向。")
        return "\n".join(lines)

    def _keywords(self, text: str) -> List[str]:
        tokens = [token.strip(" ,.;:。！？!?") for token in re.split(r"\s+", text) if token]
        top = tokens[:5]
        return top or ["核心概念"]

    def _format_slide_context(self, slide: SlideContext | None) -> str:
        if slide is None:
            return "无"
        return (
            f"页码：第 {slide.page_num} 页\n"
            f"类型：{slide.type}\n"
            f"标题：{slide.title}\n"
            f"正文：{slide.content_text}\n"
            f"画面描述：{slide.visual_desc}"
        )


__all__ = ["OutlineGenerator"]
