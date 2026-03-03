from __future__ import annotations

import asyncio
import base64
import re
from typing import Any, Iterable, Optional

import httpx

from ..utils.logger import get_logger


class LLMClientError(RuntimeError):
    pass


class OpenRouterClient:
    """
    LLM client compatible with OpenRouter and OpenAI-style gateways.

    Keeps OpenRouter behavior while supporting providers that require `/v1/*`
    paths (for example: `https://api.xxx.com/v1/chat/completions`).
    """

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

    def _is_openrouter(self) -> bool:
        return "openrouter.ai" in self.base_url.lower()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMClientError("LLM API key is not configured. Set LLM_API_KEY in the environment.")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # OpenRouter-specific headers retained for compatibility.
        if self._is_openrouter():
            headers["HTTP-Referer"] = "https://ai-ppt-flow.local"
            headers["X-Title"] = "AI-PPT Flow"
        return headers

    def _endpoint_candidates(self, path: str) -> list[str]:
        normalized_path = path if path.startswith("/") else f"/{path}"
        base = self.base_url.rstrip("/")

        candidates = [f"{base}{normalized_path}"]
        # Some gateways are rooted at domain and only expose /v1/*.
        if "/v1" not in base.lower():
            candidates.append(f"{base}/v1{normalized_path}")

        seen: set[str] = set()
        unique: list[str] = []
        for url in candidates:
            if url not in seen:
                unique.append(url)
                seen.add(url)
        return unique

    def _response_snippet(self, response: httpx.Response, limit: int = 240) -> str:
        body = (response.text or "").replace("\n", " ").strip()
        if len(body) > limit:
            body = body[:limit] + "..."
        return body

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        request_name: str,
    ) -> dict[str, Any]:
        errors: list[str] = []
        max_attempts = 3

        for url in self._endpoint_candidates(path):
            for attempt in range(1, max_attempts + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(
                            url,
                            json=payload,
                            headers=self._headers(),
                        )
                except Exception as exc:
                    errors.append(
                        f"{url} [try {attempt}/{max_attempts}] -> network error: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(min(2 ** (attempt - 1), 3))
                        continue
                    break

                if response.status_code >= 400:
                    errors.append(
                        f"{url} [try {attempt}/{max_attempts}] -> HTTP {response.status_code}, body: {self._response_snippet(response)}"
                    )
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
                        retry_after = response.headers.get("retry-after")
                        try:
                            wait = float(retry_after) if retry_after else min(2 ** (attempt - 1), 3)
                        except ValueError:
                            wait = min(2 ** (attempt - 1), 3)
                        await asyncio.sleep(max(wait, 0.5))
                        continue
                    break

                try:
                    data = response.json()
                except Exception as exc:
                    content_type = response.headers.get("content-type", "unknown")
                    errors.append(
                        f"{url} -> non-JSON response (content-type={content_type}): "
                        f"{self._response_snippet(response)} ({exc})"
                    )
                    break

                if isinstance(data, dict):
                    return data
                errors.append(f"{url} -> unexpected JSON type: {type(data).__name__}")
                break

        raise LLMClientError(f"{request_name} failed. Attempts: {' | '.join(errors)}")

    def _extract_text_from_chat_response(self, data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise LLMClientError("No choices returned from LLM chat API.")

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
            return text.strip()

        if isinstance(content, str):
            return content.strip()

        raise LLMClientError("Chat API returned empty content.")

    def _decode_data_url(self, value: str) -> bytes | None:
        if not value.startswith("data:image/"):
            return None
        match = re.match(r"data:image/[^;]+;base64,(.+)", value, re.DOTALL)
        if not match:
            return None
        return base64.b64decode(match.group(1))

    async def _resolve_image_ref_to_bytes(self, image_ref: str) -> bytes:
        data = self._decode_data_url(image_ref)
        if data is not None:
            return data

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(image_ref)
        response.raise_for_status()
        return response.content

    def _extract_url_from_text(self, text: str) -> str | None:
        # Markdown image: ![alt](https://...)
        md_match = re.search(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", text)
        if md_match:
            return md_match.group(1)
        # Plain URL fallback.
        url_match = re.search(r"(https?://\S+)", text)
        if url_match:
            return url_match.group(1).rstrip(").,;\"'")
        return None

    def _extract_image_ref_from_chat_response(self, data: dict[str, Any]) -> str | None:
        choices = data.get("choices") or []
        if not choices:
            return None

        message = choices[0].get("message", {})

        # OpenRouter style: choices[0].message.images
        images = message.get("images") or []
        if images:
            first = images[0]
            if isinstance(first, dict):
                image_url = first.get("image_url")
                if isinstance(image_url, dict) and image_url.get("url"):
                    return str(image_url["url"])
                if isinstance(image_url, str) and image_url:
                    return image_url
                if isinstance(first.get("url"), str) and first.get("url"):
                    return str(first["url"])
            elif isinstance(first, str):
                return first

        # OpenAI-style content parts with image_url
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "image_url":
                    # Some providers return text parts with markdown image links.
                    part_text = part.get("text")
                    if isinstance(part_text, str):
                        found = self._extract_url_from_text(part_text)
                        if found:
                            return found
                    continue
                image_url = part.get("image_url")
                if isinstance(image_url, dict) and image_url.get("url"):
                    return str(image_url["url"])
                if isinstance(image_url, str) and image_url:
                    return image_url

        # Some providers return markdown links directly in content string.
        if isinstance(content, str):
            found = self._extract_url_from_text(content)
            if found:
                return found

        return None

    async def _extract_image_bytes_from_images_endpoint(self, data: dict[str, Any]) -> bytes:
        items = data.get("data") or []
        if not items:
            raise LLMClientError("No images returned from images endpoint.")

        first = items[0]
        if not isinstance(first, dict):
            raise LLMClientError("Unsupported image payload type from images endpoint.")

        b64_value = first.get("b64_json")
        if isinstance(b64_value, str) and b64_value:
            return base64.b64decode(b64_value)

        for field in ("url", "image_url"):
            ref = first.get(field)
            if isinstance(ref, str) and ref:
                return await self._resolve_image_ref_to_bytes(ref)

        raise LLMClientError("Images endpoint returned unsupported image payload format.")

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
            payload["max_tokens"] = max_output_tokens
            if self._is_openrouter():
                payload["max_output_tokens"] = max_output_tokens

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
            data = await self._post_json(
                "/chat/completions",
                payload,
                "Chat completion request",
            )
        except Exception as exc:  # pragma: no cover
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

        response_text = self._extract_text_from_chat_response(data)

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
            "max_tokens": 2048,
        }
        if self._is_openrouter():
            payload["max_output_tokens"] = 2048

        if session_id:
            self.logger.log_image_generation(
                session_id=session_id,
                prompt=prompt,
                model=model,
                width=width,
                height=height
            )

        errors: list[str] = []

        # Strategy 1: chat/completions image response
        try:
            chat_data = await self._post_json(
                "/chat/completions",
                payload,
                "Image generation (chat/completions)",
            )
            image_ref = self._extract_image_ref_from_chat_response(chat_data)
            if image_ref:
                image_bytes = await self._resolve_image_ref_to_bytes(image_ref)
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
            errors.append("chat/completions returned no image reference")
        except Exception as exc:  # pragma: no cover
            errors.append(f"chat/completions failed: {exc}")

        # Strategy 2: images/generations endpoint
        image_payload = {
            "model": model,
            "prompt": prompt,
            "size": f"{width}x{height}",
        }
        try:
            image_data = await self._post_json(
                "/images/generations",
                image_payload,
                "Image generation (images/generations)",
            )
            image_bytes = await self._extract_image_bytes_from_images_endpoint(image_data)
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
        except Exception as exc:  # pragma: no cover
            errors.append(f"images/generations failed: {exc}")

        error_msg = f"Image generation request failed: {' | '.join(errors)}"
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
