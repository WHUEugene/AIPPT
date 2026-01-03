"""Minimal Flask frontend proxy for OpenRouter nano banana demos."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import pathlib
from datetime import datetime, timezone
import traceback
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
CHAT_COMPLETIONS_PATH = OPENROUTER_CFG.get("chat_path", "v1/chat/completions")
IMAGE_EDIT_PATH = OPENROUTER_CFG.get("image_edit_path", "v1/images/edits")
IMAGE_EDIT_MODEL = OPENROUTER_CFG.get("image_edit_model")

SERVER_CFG = CONFIG.get("server", {})
HOST = os.getenv("HOST") or SERVER_CFG.get("host", "0.0.0.0")
PORT = int(os.getenv("PORT") or SERVER_CFG.get("port", 7860))

LOG_CFG = CONFIG.get("logging", {})
LOG_MARKDOWN_PATH = pathlib.Path(
    LOG_CFG.get("markdown_file", "logs/generation_log.md")
)
LOG_IMAGES_DIR = pathlib.Path(LOG_CFG.get("images_dir", "logs/images"))
ERROR_LOG_PATH = pathlib.Path(
    LOG_CFG.get("error_file", "logs/error_log.md")
)


def build_api_url(path: str) -> str:
    base = OPENAI_BASE_URL.rstrip("/")
    suffix = path.lstrip("/")
    if base.endswith("/v1") and suffix.startswith("v1/"):
        suffix = suffix[3:]
    return f"{base}/{suffix}"


def build_message_content(prompt: str, image_data_url: Optional[str]) -> Any:
    """Return the OpenAI-style content payload."""

    prompt = prompt.strip()
    if not prompt and not image_data_url:
        raise ValueError("请至少输入提示词或上传参考图像。")

    if image_data_url:
        content: List[Dict[str, Any]] = []
        if prompt:
            content.append({"type": "text", "text": prompt})
        content.append({"type": "image_url", "image_url": {"url": image_data_url}})
        return content

    return prompt


def _parse_event_stream_response(body: str) -> Dict[str, Any]:
    """Parse a text/event-stream body into a chat.completions-style payload."""

    events: List[Dict[str, Any]] = []
    for raw_event in body.split("\n\n"):
        raw_event = raw_event.strip()
        if not raw_event:
            continue
        for line in raw_event.splitlines():
            if not line.startswith("data:"):
                continue
            data = line[len("data:") :].strip()
            if not data or data == "[DONE]":
                continue
            try:
                events.append(json.loads(data))
            except json.JSONDecodeError:
                continue

    if not events:
        raise ValueError("OpenRouter 返回了空的流式响应。")

    aggregated_content: Dict[int, List[Dict[str, Any]]] = {}
    roles: Dict[int, str] = {}
    finish_reasons: Dict[int, Optional[str]] = {}

    for event in events:
        for choice in event.get("choices") or []:
            idx = choice.get("index", 0)
            delta = choice.get("delta") or {}
            role = delta.get("role")
            if isinstance(role, str):
                roles[idx] = role
            blocks = delta.get("content")
            if isinstance(blocks, list) and blocks:
                aggregated_content.setdefault(idx, []).extend(blocks)
            finish_reason = choice.get("finish_reason")
            if finish_reason:
                finish_reasons[idx] = finish_reason

    final_event = events[-1]
    final_choices = final_event.get("choices") or [{}]
    normalized_choices: List[Dict[str, Any]] = []

    for choice in final_choices:
        idx = choice.get("index", 0)
        message = choice.get("message") or {"role": roles.get(idx, "assistant")}
        content_blocks = aggregated_content.get(idx)
        if content_blocks:
            message["content"] = content_blocks
        # 确保 message 至少是一个字典，方便下游解析
        choice["message"] = message
        finish_reason = finish_reasons.get(idx)
        if finish_reason:
            choice["finish_reason"] = finish_reason
        normalized_choices.append(choice)

    final_event["choices"] = normalized_choices
    return final_event


def call_openrouter(content: Any, aspect_ratio: str = "9:16", resolution: str = "4K") -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("请先设置 OPENAI_API_KEY 环境变量。")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai",
        "X-Title": "Nano Banana Frontend",
    }

    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "max_output_tokens": 2048,
        "extra_body": {
            "aspect_ratio": aspect_ratio,
            "resolution": resolution
        },
        "stream": False,
    }

    response = requests.post(
        build_api_url(CHAT_COMPLETIONS_PATH), headers=headers, json=payload, timeout=120
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "text/event-stream" in content_type:
        return _parse_event_stream_response(response.text)

    try:
        return response.json()
    except (json.JSONDecodeError, requests.exceptions.JSONDecodeError) as exc:
        body = response.text.strip()
        if body.startswith("data:"):
            return _parse_event_stream_response(body)
        snippet = body[:200]
        raise ValueError(f"无法解析 OpenRouter 响应: {snippet}") from exc


def _map_resolution_to_size(resolution: Optional[str]) -> Optional[str]:
    if not resolution:
        return None
    if not isinstance(resolution, str):
        return None
    lookup = {
        "HD": "512x512",
        "FHD": "1024x1024",
        "4K": "1024x1024",
        "8K": "1024x1024",
    }
    return lookup.get(resolution.upper())


def call_image_edit_api(
    prompt: str,
    upload,
    aspect_ratio: str = "9:16",
    resolution: str = "4K",
) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("请先设置 OPENAI_API_KEY 环境变量。")

    prompt_text = (prompt or "").strip() or "请根据参考图片进行编辑。"
    try:
        upload.stream.seek(0)
    except Exception:
        pass
    data_bytes = upload.read()
    if not data_bytes:
        raise ValueError("上传的文件为空。")

    filename = upload.filename or "image.png"
    mime_type = upload.mimetype or mimetypes.guess_type(filename)[0] or "image/png"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Accept": "application/json",
        "HTTP-Referer": "https://openrouter.ai",
        "X-Title": "Nano Banana Frontend",
    }

    edit_model = IMAGE_EDIT_MODEL or MODEL_NAME
    form_data: Dict[str, Any] = {
        "prompt": prompt_text,
        "model": edit_model,
        "n": "1",
        "response_format": "url",
    }

    size_value = _map_resolution_to_size(resolution)
    if size_value:
        form_data["size"] = size_value
    if aspect_ratio:
        form_data["aspect_ratio"] = aspect_ratio
    if resolution:
        form_data["resolution"] = resolution

    files = {
        "image": (filename, data_bytes, mime_type)
    }

    response = requests.post(
        build_api_url(IMAGE_EDIT_PATH),
        headers=headers,
        data=form_data,
        files=files,
        timeout=180,
    )
    response.raise_for_status()

    try:
        return response.json()
    except (json.JSONDecodeError, requests.exceptions.JSONDecodeError) as exc:
        snippet = response.text.strip()[:200]
        raise ValueError(f"无法解析图像编辑响应: {snippet}") from exc


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


def parse_image_edit_outputs(payload: Dict[str, Any]) -> Tuple[str, List[str]]:
    images: List[str] = []
    for item in payload.get("data") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if url:
            images.append(url)
            continue
        b64_value = item.get("b64_json")
        if b64_value:
            images.append(f"data:image/png;base64,{b64_value}")

    message = (
        payload.get("status")
        or payload.get("message")
        or payload.get("detail")
        or (f"图像编辑完成，共 {len(images)} 张" if images else "图像编辑完成")
    )
    return message, images


def ensure_log_dirs() -> None:
    LOG_MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


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


def append_error_log(
    timestamp: datetime,
    prompt: str,
    attachment_name: Optional[str],
    aspect_ratio: str,
    resolution: str,
    error_type: str,
    message: str,
    detail: Optional[str] = None,
    status_code: Optional[int] = None,
) -> None:
    ensure_log_dirs()
    timestamp_str = timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    slug = timestamp.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        f"## {timestamp_str} ({slug})",
        "",
        f"- **Prompt**: {prompt or '(空)'}",
        f"- **参考图片**: {attachment_name or '(无)'}",
        f"- **参数**: aspect_ratio={aspect_ratio}, resolution={resolution}",
        f"- **错误类型**: {error_type}",
        f"- **状态码**: {status_code if status_code is not None else '(未知)'}",
        f"- **错误信息**: {message}",
        "",
    ]

    if detail:
        lines.append("```")
        lines.append(detail)
        lines.append("```")
        lines.append("")

    with ERROR_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


@app.post("/generate")
def generate() -> Any:
    timestamp = datetime.now(timezone.utc)
    prompt = ""
    aspect_ratio = "9:16"
    resolution = "4K"
    upload = None
    try:
        prompt = request.form.get("prompt", "")
        upload = request.files.get("image")

        # 获取图片生成参数
        aspect_ratio = request.form.get("aspect_ratio", "9:16")
        resolution = request.form.get("resolution", "4K")
        has_upload = bool(upload and upload.filename)

        if has_upload:
            data = call_image_edit_api(prompt, upload, aspect_ratio, resolution)
            text_response, image_urls = parse_image_edit_outputs(data)
        else:
            content = build_message_content(prompt, None)
            data = call_openrouter(content, aspect_ratio, resolution)
            message: Dict[str, Any] = data["choices"][0]["message"]
            text_response, image_urls = parse_message_outputs(message)
            image_urls = image_urls[:1]

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

        attachment_name = upload.filename if upload and upload.filename else None

        append_markdown_log(
            timestamp=timestamp,
            prompt=prompt,
            text_response=text_response,
            saved_paths=saved_paths,
            attachment_name=attachment_name,
            total_images=len(image_urls),
        )

        return jsonify({
            "text": text_response, 
            "images": image_urls, 
            "raw": data,
            "params": {
                "aspect_ratio": aspect_ratio,
                "resolution": resolution
            }
        })
    except requests.HTTPError as exc:
        try:
            body = exc.response.json()
        except Exception:
            body = exc.response.text if exc.response is not None else str(exc)

        attachment_name = upload.filename if upload and upload.filename else None
        detail_text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        status_code = exc.response.status_code if exc.response is not None else None
        append_error_log(
            timestamp=timestamp,
            prompt=prompt,
            attachment_name=attachment_name,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            error_type="HTTPError",
            message=str(exc),
            detail=detail_text,
            status_code=status_code,
        )
        return jsonify({"error": "OpenRouter 请求失败", "detail": body}), 502
    except Exception as exc:
        attachment_name = upload.filename if upload and upload.filename else None
        append_error_log(
            timestamp=timestamp,
            prompt=prompt,
            attachment_name=attachment_name,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            error_type=exc.__class__.__name__,
            message=str(exc),
            detail=traceback.format_exc(),
            status_code=None,
        )
        return jsonify({"error": str(exc)}), 400


@app.get("/config")
def get_config() -> Any:
    # 获取当前完整配置
    current_config = load_config(CONFIG_PATH)
    openrouter_cfg = current_config.get("openrouter", {})
    
    return jsonify({
        "api_key": OPENAI_API_KEY or "",
        "base_url": OPENAI_BASE_URL,
        "model": MODEL_NAME,
        "available_models": openrouter_cfg.get("available_models", [])
    })

@app.post("/config")
def update_config() -> Any:
    try:
        data = request.get_json()
        
        # 读取现有配置
        current_config = load_config(CONFIG_PATH)
        
        # 更新当前使用的模型配置
        if "openrouter" not in current_config:
            current_config["openrouter"] = {}
        
        current_config["openrouter"].update({
            "model": data.get("model", MODEL_NAME),
            "api_key": data.get("api_key", ""),
            "base_url": data.get("base_url", OPENAI_BASE_URL)
        })
        
        # 写回配置文件
        with CONFIG_PATH.open("w", encoding="utf-8") as fh:
            yaml.dump(current_config, fh, default_flow_style=False, allow_unicode=True)
        
        return jsonify({"message": "配置已更新", "config": data})
        
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

@app.get("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
