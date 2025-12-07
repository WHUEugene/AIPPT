"""Minimal Flask frontend proxy for OpenRouter nano banana demos."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import pathlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml
from flask import Flask, jsonify, request, send_from_directory


app = Flask(__name__, static_folder="frontend", static_url_path="")


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"找不到配置文件 {path}. 请复制 config.yaml.example 或创建该文件。"
        )

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError("配置文件内容必须是字典结构。")

    return data


CONFIG_PATH = pathlib.Path(os.getenv("NANO_BANANA_CONFIG", "config.yaml"))
CONFIG = load_config(CONFIG_PATH)

OPENROUTER_CFG = CONFIG.get("openrouter", {})
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or OPENROUTER_CFG.get("api_key")
OPENAI_BASE_URL = (
    os.getenv("OPENAI_BASE_URL")
    or OPENROUTER_CFG.get("base_url")
    or "https://openrouter.ai/api/v1"
)
MODEL_NAME = (
    os.getenv("MODEL_NAME")
    or OPENROUTER_CFG.get("model")
    or "google/gemini-3-pro-image-preview"
)

SERVER_CFG = CONFIG.get("server", {})
HOST = os.getenv("HOST") or SERVER_CFG.get("host", "0.0.0.0")
PORT = int(os.getenv("PORT") or SERVER_CFG.get("port", 7860))

LOG_CFG = CONFIG.get("logging", {})
LOG_MARKDOWN_PATH = pathlib.Path(
    LOG_CFG.get("markdown_file", "logs/generation_log.md")
)
LOG_IMAGES_DIR = pathlib.Path(LOG_CFG.get("images_dir", "logs/images"))


def build_message_content(prompt: str, image_data_url: Optional[str]) -> Any:
    """Return the OpenAI-style content payload."""

    prompt = prompt.strip()
    if not prompt and not image_data_url:
        raise ValueError("请至少输入提示词或上传参考图像。")

    if image_data_url:
        content: List[Dict[str, Any]] = []
        if prompt:
            content.append({"type": "text", "text": prompt})
        content.append({"type": "input_image", "image_url": {"url": image_data_url}})
        return content

    return prompt


def encode_upload_to_data_url(upload) -> str:
    """Convert an uploaded FileStorage to a data URL."""

    data = upload.read()
    if not data:
        raise ValueError("上传的文件为空。")

    mime_type = upload.mimetype or mimetypes.guess_type(upload.filename or "")[0]
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def call_openrouter(content: Any) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("请先设置 OPENAI_API_KEY 环境变量。")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openrouter.ai",
        "X-Title": "Nano Banana Frontend",
    }

    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "max_output_tokens": 2048,
    }

    response = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=120
    )
    response.raise_for_status()
    return response.json()


def parse_message_outputs(message: Dict[str, Any]) -> Tuple[str, List[str]]:
    text_chunks: List[str] = []
    images: List[str] = []
    seen: set[str] = set()

    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            block_type = block.get("type")
            if block_type in {"text", "output_text"}:
                text_value = block.get("text")
                if text_value:
                    text_chunks.append(text_value)
            elif block_type in {"image_url", "input_image", "output_image"}:
                url = (block.get("image_url") or {}).get("url")
                if url and url not in seen:
                    seen.add(url)
                    images.append(url)
    elif isinstance(content, str):
        text_chunks.append(content)

    raw_images: List[Dict[str, Any]] = message.get("images") or []
    for img in raw_images:
        url = (img.get("image_url") or {}).get("url")
        if url and url not in seen:
            seen.add(url)
            images.append(url)

    text_response = "\n\n".join(text_chunks).strip()
    return text_response, images


def ensure_log_dirs() -> None:
    LOG_MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def _guess_extension(mime_type: str) -> str:
    if not mime_type:
        return ".png"
    ext = mimetypes.guess_extension(mime_type)
    if ext:
        return ext
    if "jpeg" in mime_type:
        return ".jpg"
    if "png" in mime_type:
        return ".png"
    return ".bin"


def fetch_image_data(image_url: str) -> Optional[Tuple[bytes, str]]:
    try:
        if image_url.startswith("data:"):
            header, base64_part = image_url.split(",", 1)
            mime_type = header.split(";")[0].split(":", 1)[1]
            data = base64.b64decode(base64_part)
            return data, mime_type
        if image_url.startswith("http://") or image_url.startswith("https://"):
            resp = requests.get(image_url, timeout=60)
            resp.raise_for_status()
            data = resp.content
            mime_type = resp.headers.get("Content-Type", "image/png")
            return data, mime_type
        return None
    except Exception:
        return None


def save_image_bytes(data: bytes, mime_type: str, timestamp_slug: str, idx: int) -> Optional[pathlib.Path]:
    try:
        ensure_log_dirs()
        extension = _guess_extension(mime_type)
        filename = f"{timestamp_slug}_{idx}{extension}"
        output_path = LOG_IMAGES_DIR / filename
        output_path.write_bytes(data)
        return output_path
    except Exception:
        return None


def format_path_for_markdown(path: pathlib.Path) -> str:
    try:
        relative = path.relative_to(LOG_MARKDOWN_PATH.parent)
        return relative.as_posix()
    except ValueError:
        return path.as_posix()


def append_markdown_log(
    timestamp: datetime,
    prompt: str,
    text_response: str,
    saved_paths: List[pathlib.Path],
    attachment_name: Optional[str],
    total_images: int,
) -> None:
    ensure_log_dirs()
    timestamp_str = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    slug = timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        f"## {timestamp_str}",
        "",
        f"- **Prompt**: {prompt or '(空)'}",
        f"- **参考图片**: {attachment_name or '(无)'}",
        f"- **模型文本**: {text_response or '(无)'}",
        f"- **返回图片数量**: {total_images}",
        "",
    ]

    if saved_paths:
        lines.append("**保存的图片：**")
        lines.append("")
        for path in saved_paths:
            lines.append(f"![Generated {slug}]({format_path_for_markdown(path)})")
        lines.append("")
    else:
        lines.append("_未保存任何图片。_")
        lines.append("")

    with LOG_MARKDOWN_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


@app.post("/generate")
def generate() -> Any:
    try:
        prompt = request.form.get("prompt", "")
        upload = request.files.get("image")
        image_data_url: Optional[str] = None
        if upload and upload.filename:
            image_data_url = encode_upload_to_data_url(upload)

        content = build_message_content(prompt, image_data_url)
        data = call_openrouter(content)
        message: Dict[str, Any] = data["choices"][0]["message"]
        text_response, image_urls = parse_message_outputs(message)
        image_urls = image_urls[:1]

        timestamp = datetime.now(timezone.utc)
        timestamp_slug = timestamp.strftime("%Y%m%dT%H%M%SZ")
        saved_paths: List[pathlib.Path] = []
        for idx, image_url in enumerate(image_urls, start=1):
            blob = fetch_image_data(image_url)
            if not blob:
                continue
            data_bytes, mime_type = blob
            saved_path = save_image_bytes(data_bytes, mime_type, timestamp_slug, idx)
            if saved_path:
                saved_paths.append(saved_path)

        append_markdown_log(
            timestamp=timestamp,
            prompt=prompt,
            text_response=text_response,
            saved_paths=saved_paths,
            attachment_name=upload.filename if upload and upload.filename else None,
            total_images=len(image_urls),
        )

        return jsonify({"text": text_response, "images": image_urls, "raw": data})
    except requests.HTTPError as exc:
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text if exc.response is not None else str(exc)
        return jsonify({"error": "OpenRouter 请求失败", "detail": body}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
