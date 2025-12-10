from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from .slide import SlideData


class ProjectState(BaseModel):
    template_id: Optional[UUID] = None
    template_style_prompt: Optional[str] = None
    title: Optional[str] = None
    slides: list[SlideData]


__all__ = ["ProjectState"]
