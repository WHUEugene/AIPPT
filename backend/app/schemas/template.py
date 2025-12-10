from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    name: str
    style_prompt: str
    cover_image: Optional[str] = None
    vis_settings: Optional[Dict[str, Any]] = None
    # 新增比例和尺寸相关字段
    aspect_ratios: List[str] = Field(default_factory=lambda: ["16:9", "4:3", "1:1"], description="支持的比例列表")
    default_aspect_ratio: str = Field(default="16:9", pattern=r"^\d{1,2}:\d{1,2}$", description="默认比例")
    custom_dimensions: Optional[Dict[str, int]] = Field(default=None, description="自定义尺寸 {width, height}")


class TemplateCreate(TemplateBase):
    pass


class Template(TemplateBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateAnalyzeResponse(BaseModel):
    style_prompt: str


class TemplateListResponse(BaseModel):
    templates: list[Template]


class TemplateSaveResponse(BaseModel):
    template: Template


__all__ = [
    "Template",
    "TemplateAnalyzeResponse",
    "TemplateCreate",
    "TemplateListResponse",
    "TemplateSaveResponse",
]
