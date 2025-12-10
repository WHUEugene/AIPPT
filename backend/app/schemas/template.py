from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TemplateBase(BaseModel):
    name: str
    style_prompt: str
    cover_image: Optional[str] = None
    vis_settings: Optional[Dict[str, Any]] = None


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
