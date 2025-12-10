from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List, Optional

import httpx

from ..utils.logger import get_logger


class LLMClientError(RuntimeError):
    pass


class OpenRouterClient:
    """Thin wrapper around OpenRouter's chat and image endpoints."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        timeout_seconds: int = 120,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.logger = get_logger()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMClientError("LLM API key is not configured. Set LLM_API_KEY in the environment.")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-ppt-flow.local",
            "X-Title": "AI-PPT Flow",
        }

    async def chat(
        self,
        messages: Iterable[dict[str, Any]],
        model: str,
        temperature: float = 0.4,
        max_output_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
        stage: str = "chat"
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if max_output_tokens is not None:
            payload["max_output_tokens"] = max_output_tokens

        # 记录LLM请求开始
        if session_id:
            self.logger.log_llm_call(
                session_id=session_id,
                stage=stage,
                model=model,
                messages=list(messages),
                temperature=temperature,
                max_tokens=max_output_tokens
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # pragma: no cover - network fallback
            error_msg = f"Chat completion request failed: {str(exc)}"
            if session_id:
                self.logger.log_llm_call(
                    session_id=session_id,
                    stage=stage,
                    model=model,
                    messages=list(messages),
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    error=error_msg
                )
            raise LLMClientError(error_msg) from exc
        
        choices = data.get("choices") or []
        if not choices:
            error_msg = "No choices returned from LLM chat API."
            if session_id:
                self.logger.log_llm_call(
                    session_id=session_id,
                    stage=stage,
                    model=model,
                    messages=list(messages),
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    error=error_msg
                )
            raise LLMClientError(error_msg)
            
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text = content or ""
        
        response_text = text.strip()
        
        # 记录LLM响应
        if session_id:
            self.logger.log_llm_call(
                session_id=session_id,
                stage=stage,
                model=model,
                messages=list(messages),
                temperature=temperature,
                max_tokens=max_output_tokens,
                response=response_text
            )
        
        return response_text

    async def generate_image(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        session_id: Optional[str] = None,
    ) -> bytes:
        messages = [
            {"role": "system", "content": "你是专业的 PPT 幻灯片视觉设计师"},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "modalities": ["image", "text"],
            "max_output_tokens": 2048
        }
        
        # 记录图片生成请求开始
        if session_id:
            self.logger.log_image_generation(
                session_id=session_id,
                prompt=prompt,
                model=model,
                width=width,
                height=height
            )
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # pragma: no cover
            error_msg = f"Image generation request failed: {str(exc)}"
            if session_id:
                self.logger.log_image_generation(
                    session_id=session_id,
                    prompt=prompt,
                    model=model,
                    width=width,
                    height=height,
                    error=error_msg
                )
            raise LLMClientError(error_msg) from exc
            
        choices = data.get("choices") or []
        if not choices:
            error_msg = "No choices returned from image generation API."
            if session_id:
                self.logger.log_image_generation(
                    session_id=session_id,
                    prompt=prompt,
                    model=model,
                    width=width,
                    height=height,
                    error=error_msg
                )
            raise LLMClientError(error_msg)
            
        message = choices[0].get("message", {})
        images = message.get("images") or []
        
        if not images:
            error_msg = "No images returned from image generation API."
            if session_id:
                self.logger.log_image_generation(
                    session_id=session_id,
                    prompt=prompt,
                    model=model,
                    width=width,
                    height=height,
                    error=error_msg
                )
            raise LLMClientError(error_msg)
            
        first_image = images[0]
        if first_image.get("type") == "image_url":
            image_url = first_image.get("image_url", {}).get("url", "")
            if image_url.startswith("data:image/"):
                # Extract base64 data from DataURL
                import re
                match = re.match(r"data:image/[^;]+;base64,(.+)", image_url)
                if match:
                    image_bytes = base64.b64decode(match.group(1))
                    # 记录成功生成图片
                    if session_id:
                        self.logger.log_image_generation(
                            session_id=session_id,
                            prompt=prompt,
                            model=model,
                            width=width,
                            height=height,
                            image_path=f"Generated {len(image_bytes)} bytes"
                        )
                    return image_bytes
        
        error_msg = "Image API returned an unsupported payload format."
        if session_id:
            self.logger.log_image_generation(
                session_id=session_id,
                prompt=prompt,
                model=model,
                width=width,
                height=height,
                error=error_msg
            )
        raise LLMClientError(error_msg)


__all__ = ["LLMClientError", "OpenRouterClient"]
