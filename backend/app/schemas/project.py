from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .slide import SlideData


class ProjectState(BaseModel):
    template_id: Optional[str] = None  # 改为字符串类型，兼容前端
    template_style_prompt: Optional[str] = None
    title: Optional[str] = None
    slides: list[SlideData]


class ProjectSchema(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    template_style_prompt: str  # 保存当时的风格提示词
    slides: list[SlideData]     # 核心数据：包含文字、大纲、图片路径
    thumbnail_url: Optional[str] = None  # 封面图，用于列表展示


class ProjectListItem(BaseModel):
    id: str
    title: str
    updated_at: datetime
    thumbnail_url: Optional[str] = None


__all__ = ["ProjectState", "ProjectSchema", "ProjectListItem"]
