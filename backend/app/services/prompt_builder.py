from __future__ import annotations


class PromptBuilder:
    """Compose final prompts used by the image generation pipeline."""

    def build(
        self,
        style_prompt: str,
        visual_desc: str,
        *,
        title: str | None = None,
        content_text: str | None = None,
        aspect_ratio: str = "16:9",
    ) -> str:
        style_part = style_prompt.strip()
        visual_part = visual_desc.strip()

        text_lines: list[str] = []
        if title or content_text:
            text_lines.append("### 需要内嵌的文字")
            if title:
                text_lines.append(f"- 标题：{title.strip()}")
            if content_text:
                text_lines.append(f"- 正文：{content_text.strip()}")
            text_lines.append("所有文字须以简体中文直接绘制在画面中，与图像元素自然融合。")

        instructions = (
            "### 输出要求\n"
            f"- 尺寸严格为 {aspect_ratio}。\n"
            "- 画面需兼具丰富图像与可读文字，主题围绕当前页面描述。\n"
            "- 避免无关元素或水印。"
        )

        sections = [
            f"Prompt: {style_part}",
            f"### 分页描述\n{visual_part}",
        ]
        if text_lines:
            sections.append("\n".join(text_lines))
        sections.append(instructions)
        sections.append("请基于以上全部信息直接生成整张幻灯片背景图。")
        return "\n\n".join(section for section in sections if section)


__all__ = ["PromptBuilder"]
