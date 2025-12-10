from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .slide import SlideStatus, SlideData


class SlideGenerateRequest(BaseModel):
    style_prompt: str
    visual_desc: str
    aspect_ratio: str = Field("16:9", pattern=r"^\d{1,2}:\d{1,2}$")
    page_num: Optional[int] = None
    title: Optional[str] = None
    content_text: Optional[str] = None


class SlideGenerateResponse(BaseModel):
    image_url: str
    final_prompt: str
    revised_prompt: str
    status: SlideStatus = SlideStatus.done


SlideRegenerateRequest = SlideGenerateRequest


class BatchGenerateRequest(BaseModel):
    """批量生成幻灯片的请求"""
    slides: List[SlideData]  # 幻灯片数据列表
    style_prompt: str  # 统一的风格提示词
    max_workers: int = Field(default=5, ge=1, le=100)  # 最大并发数，默认5，最大100
    aspect_ratio: str = Field(default="16:9", pattern=r"^\d{1,2}:\d{1,2}$")


class BatchGenerateItem(BaseModel):
    """批量生成中单个幻灯片的结果"""
    slide_id: UUID
    page_num: int
    title: str
    image_url: Optional[str] = None
    final_prompt: Optional[str] = None
    status: SlideStatus
    error_message: Optional[str] = None
    generation_time: Optional[float] = None  # 生成时间（秒）


class BatchGenerateResponse(BaseModel):
    """批量生成的响应"""
    batch_id: UUID
    total_slides: int
    successful: int
    failed: int
    total_time: float  # 总生成时间（秒）
    results: List[BatchGenerateItem]
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_slides) * 100 if self.total_slides > 0 else 0


class BatchStatusRequest(BaseModel):
    """查询批量生成状态的请求"""
    batch_id: UUID


class BatchStatusResponse(BaseModel):
    """批量生成状态响应"""
    batch_id: UUID
    status: str  # "running", "completed", "failed"
    progress: float  # 0.0 - 1.0
    total_slides: int
    completed_slides: int
    successful: int
    failed: int
    estimated_remaining_time: Optional[float] = None  # 秒
    results: List[BatchGenerateItem] = []


__all__ = [
    "SlideGenerateRequest",
    "SlideGenerateResponse", 
    "SlideRegenerateRequest",
    "BatchGenerateRequest",
    "BatchGenerateResponse",
    "BatchGenerateItem",
    "BatchStatusRequest",
    "BatchStatusResponse",
]
