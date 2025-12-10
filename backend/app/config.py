from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the AI-PPT Flow backend."""

    project_name: str = "AI-PPT Flow Backend"
    api_prefix: str = "/api"

    llm_api_key: str | None = None
    llm_api_base: str = "https://openrouter.ai/api/v1"
    llm_chat_model: str = "google/gemini-3-pro-preview"
    llm_image_model: str = "google/gemini-3-pro-image-preview"
    llm_timeout_seconds: int = 120

    # 批量生成配置
    batch_default_workers: int = Field(
        default=10,
        ge=1,
        le=50,
        description="默认的批量生成并发数"
    )
    batch_max_workers: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大允许的批量生成并发数"
    )
    batch_max_concurrent: int = Field(
        default=10,
        ge=1,
        le=50,
        description="同时进行的批量任务最大数量"
    )
    batch_cleanup_hours: int = Field(
        default=24,
        ge=1,
        description="批量任务结果保留时间（小时）"
    )

    def _get_default_data_path() -> Path:
        """Get default data directory - use user data dir for desktop app, ensure paths exist."""
        # 桌面应用环境，直接使用用户数据目录
        home = Path.home()
        data_dir = home / ".aippt-flow" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    def _get_default_generated_path() -> Path:
        """Get default generated directory - use user data dir for desktop app, ensure paths exist."""
        # 桌面应用环境，直接使用用户数据目录
        home = Path.home()
        gen_dir = home / ".aippt-flow" / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        return gen_dir

    template_store_path: Path = Field(
        default_factory=lambda: _get_default_data_path() / "templates.json",
        description="Location used to persist template definitions.",
    )
    image_output_dir: Path = Field(
        default_factory=lambda: _get_default_generated_path() / "images",
        description="Directory where generated slide assets are written.",
    )
    pptx_output_dir: Path = Field(
        default_factory=lambda: _get_default_generated_path() / "pptx",
        description="Directory for temporary PPTX exports.",
    )

    allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        description="CORS origins permitted to access the API.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    def ensure_runtime_paths(self) -> None:
        """Create directories and data files required by the app."""

        self.template_store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.template_store_path.exists():
            self.template_store_path.write_text("[]\n", encoding="utf-8")

        self.image_output_dir.mkdir(parents=True, exist_ok=True)
        self.pptx_output_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["Settings"]
