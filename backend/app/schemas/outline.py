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
        le=50,
        description="Expected number of slides in the outline.",
    )
    template_id: Optional[UUID] = None


class OutlineResponse(BaseModel):
    slides: list[SlideData]


class SlideContext(BaseModel):
    page_num: int = Field(..., ge=1)
    type: str
    title: str
    content_text: str
    visual_desc: str


class InsertSlideRequest(BaseModel):
    user_prompt: str = Field(..., min_length=1, description="User description for the inserted slide.")
    insert_after_page_num: int = Field(..., ge=1)
    template_name: Optional[str] = None
    style_prompt: Optional[str] = None
    prev_slide: Optional[SlideContext] = None
    next_slide: Optional[SlideContext] = None


class InsertSlideResponse(BaseModel):
    slide: SlideData


__all__ = [
    "OutlineRequest",
    "OutlineResponse",
    "SlideContext",
    "InsertSlideRequest",
    "InsertSlideResponse",
]
