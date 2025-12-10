from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .slide import SlideData


class OutlineRequest(BaseModel):
    text: str = Field(..., description="Raw Markdown or plain text content.")
    slide_count: int = Field(
        8,
        ge=1,
        le=40,
        description="Expected number of slides in the outline.",
    )
    template_id: Optional[UUID] = None


class OutlineResponse(BaseModel):
    slides: list[SlideData]


__all__ = ["OutlineRequest", "OutlineResponse"]
