from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SlideType(str, Enum):
    cover = "cover"
    content = "content"
    ending = "ending"


class SlideStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    done = "done"
    error = "error"


class SlideData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))  # 改为字符串类型
    page_num: int = Field(..., ge=1)
    type: SlideType = SlideType.content
    title: str
    content_text: str
    visual_desc: str
    final_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: SlideStatus = SlideStatus.pending


__all__ = ["SlideData", "SlideStatus", "SlideType"]
