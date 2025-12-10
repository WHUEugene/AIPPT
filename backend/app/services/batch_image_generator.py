from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from ..schemas.generation import BatchGenerateItem, BatchStatusResponse
from ..schemas.slide import SlideData, SlideStatus
from ..utils.logger import get_logger
from .image_generator import ImageGenerator
from .llm_client import LLMClientError
from .prompt_builder import PromptBuilder


@dataclass
class BatchTask:
    """批量生成任务"""
    batch_id: UUID
    slides: List[SlideData]
    style_prompt: str
    max_workers: int
    aspect_ratio: str
    start_time: float
    results: List[BatchGenerateItem]
    status: str = "running"
    completed_count: int = 0
    success_count: int = 0
    failed_count: int = 0

    @property
    def progress(self) -> float:
        return self.completed_count / len(self.slides) if self.slides else 0.0

    @property
    def total_slides(self) -> int:
        return len(self.slides)


class BatchImageGenerator:
    """批量图片生成服务，支持多进程并发生成"""

    def __init__(
        self,
        image_generator: ImageGenerator,
        prompt_builder: PromptBuilder,
        max_concurrent_batches: int = 10,  # 增加到10个同时进行的批量任务
    ):
        self.image_generator = image_generator
        self.prompt_builder = prompt_builder
        self.max_concurrent_batches = max_concurrent_batches
        self.logger = get_logger()
        
        # 存储正在进行的批量任务
        self.active_batches: Dict[UUID, BatchTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_batches)

    def create_batch(
        self,
        slides: List[SlideData],
        style_prompt: str,
        max_workers: int = None,
        aspect_ratio: str = "16:9"
    ) -> UUID:
        """创建新的批量生成任务"""
        batch_id = uuid4()
        
        # 智能设置并发数：最小10，最大为生成页数
        if max_workers is None:
            max_workers = max(10, len(slides))
        
        # 创建批量任务
        batch_task = BatchTask(
            batch_id=batch_id,
            slides=slides.copy(),
            style_prompt=style_prompt,
            max_workers=max_workers,
            aspect_ratio=aspect_ratio,
            start_time=time.time(),
            results=[]
        )
        
        self.active_batches[batch_id] = batch_task
        
        # 开始会话记录
        session_id = self.logger.start_session(
            "batch_generate",
            batch_id=str(batch_id),
            total_slides=len(slides),
            max_workers=max_workers,
            aspect_ratio=aspect_ratio
        )
        
        # 记录批量任务开始
        self.logger.log_request(
            session_id=session_id,
            stage="batch_generate_start",
            data={
                "batch_id": str(batch_id),
                "total_slides": len(slides),
                "max_workers": max_workers,
                "aspect_ratio": aspect_ratio,
                "slides": [
                    {
                        "id": str(slide.id),
                        "page_num": slide.page_num,
                        "title": slide.title[:50],
                        "visual_desc": slide.visual_desc[:100]
                    }
                    for slide in slides
                ]
            }
        )
        
        # 异步执行批量生成
        asyncio.create_task(self._execute_batch(batch_task, session_id))
        
        return batch_id

    async def _execute_batch(self, batch_task: BatchTask, session_id: str):
        """执行批量生成任务"""
        try:
            self.logger.log_pipeline_step(
                session_id=session_id,
                step="batch_execution_start",
                details={
                    "batch_id": str(batch_task.batch_id),
                    "total_slides": len(batch_task.slides),
                    "max_workers": batch_task.max_workers,
                    "stage": "开始批量执行"
                }
            )
            
            # 使用线程池执行并发生成 - 直接使用 concurrent.futures
            with ThreadPoolExecutor(max_workers=batch_task.max_workers) as executor:
                # 提交所有任务到线程池
                future_to_slide = {}
                
                for slide in batch_task.slides:
                    future = executor.submit(
                        self._generate_single_slide,
                        slide,
                        batch_task.style_prompt,
                        batch_task.aspect_ratio,
                        session_id
                    )
                    future_to_slide[future] = slide
                
                # 等待所有任务完成
                for future in as_completed(future_to_slide):
                    slide = future_to_slide[future]
                    
                    try:
                        result = future.result()  # 直接获取结果，不需要await
                        batch_task.results.append(result)
                        batch_task.completed_count += 1
                        
                        if result.status == SlideStatus.done:
                            batch_task.success_count += 1
                        else:
                            batch_task.failed_count += 1
                        
                        # 记录单个幻灯片完成
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_completed",
                            details={
                                "batch_id": str(batch_task.batch_id),
                                "slide_id": str(slide.id),
                                "page_num": slide.page_num,
                                "status": result.status.value,
                                "completed_count": batch_task.completed_count,
                                "total_count": len(batch_task.slides),
                                "progress": batch_task.progress,
                                "stage": f"幻灯片 {slide.page_num} 生成完成"
                            }
                        )
                        
                    except Exception as e:
                        # 处理异常
                        error_result = BatchGenerateItem(
                            slide_id=slide.id,
                            page_num=slide.page_num,
                            title=slide.title,
                            status=SlideStatus.error,
                            error_message=str(e)
                        )
                        batch_task.results.append(error_result)
                        batch_task.completed_count += 1
                        batch_task.failed_count += 1
                        
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_error",
                            details={
                                "batch_id": str(batch_task.batch_id),
                                "slide_id": str(slide.id),
                                "page_num": slide.page_num,
                                "error": str(e),
                                "stage": f"幻灯片 {slide.page_num} 生成失败"
                            }
                        )
            
            # 更新任务状态
            if batch_task.failed_count == 0:
                batch_task.status = "completed"
            elif batch_task.success_count > 0:
                batch_task.status = "completed_with_errors"
            else:
                batch_task.status = "failed"
            
            total_time = time.time() - batch_task.start_time
            
            # 记录批量任务完成
            self.logger.log_response(
                session_id=session_id,
                stage="batch_generate_complete",
                data={
                    "batch_id": str(batch_task.batch_id),
                    "status": batch_task.status,
                    "total_slides": len(batch_task.slides),
                    "successful": batch_task.success_count,
                    "failed": batch_task.failed_count,
                    "total_time": total_time,
                    "success_rate": (batch_task.success_count / len(batch_task.slides)) * 100,
                    "results": [
                        {
                            "slide_id": str(result.slide_id),
                            "page_num": result.page_num,
                            "title": result.title,
                            "status": result.status.value,
                            "image_url": result.image_url,
                            "error_message": result.error_message,
                            "generation_time": result.generation_time
                        }
                        for result in batch_task.results
                    ]
                },
                success=batch_task.success_count > 0
            )
            
            self.logger.end_session(
                session_id=session_id,
                success=batch_task.success_count > 0,
                summary={
                    "endpoint": "batch_generate",
                    "batch_id": str(batch_task.batch_id),
                    "total_slides": len(batch_task.slides),
                    "successful": batch_task.success_count,
                    "failed": batch_task.failed_count,
                    "total_time": total_time,
                    "status": batch_task.status
                }
            )
            
        except Exception as e:
            batch_task.status = "failed"
            self.logger.log_response(
                session_id=session_id,
                stage="batch_generate_error",
                data={
                    "batch_id": str(batch_task.batch_id),
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                success=False
            )

    def _generate_single_slide(
        self,
        slide: SlideData,
        style_prompt: str,
        aspect_ratio: str,
        session_id: str
    ) -> BatchGenerateItem:
        """生成单个幻灯片图片"""
        start_time = time.time()
        
        try:
            # 构建最终提示词
            final_prompt = self.prompt_builder.build(
                style_prompt=style_prompt,
                visual_desc=slide.visual_desc,
                title=slide.title,
                content_text=slide.content_text,
                aspect_ratio=aspect_ratio
            )
            
            # 生成图片
            generated = self.image_generator.create_sync(
                title=slide.title,
                final_prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                page_num=slide.page_num,
                session_id=f"{session_id}_slide_{slide.page_num}"
            )
            
            generation_time = time.time() - start_time
            
            return BatchGenerateItem(
                slide_id=slide.id,
                page_num=slide.page_num,
                title=slide.title,
                image_url=generated.image_url,
                final_prompt=final_prompt,
                status=SlideStatus.done,
                generation_time=generation_time
            )
            
        except LLMClientError as e:
            generation_time = time.time() - start_time
            return BatchGenerateItem(
                slide_id=slide.id,
                page_num=slide.page_num,
                title=slide.title,
                status=SlideStatus.error,
                error_message=f"LLM API error: {str(e)}",
                generation_time=generation_time
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            return BatchGenerateItem(
                slide_id=slide.id,
                page_num=slide.page_num,
                title=slide.title,
                status=SlideStatus.error,
                error_message=str(e),
                generation_time=generation_time
            )

    def get_batch_status(self, batch_id: UUID) -> Optional[BatchStatusResponse]:
        """获取批量任务状态"""
        batch_task = self.active_batches.get(batch_id)
        if not batch_task:
            return None
        
        # 计算预计剩余时间
        estimated_remaining_time = None
        if batch_task.completed_count > 0 and batch_task.status == "running":
            avg_time_per_slide = (time.time() - batch_task.start_time) / batch_task.completed_count
            remaining_slides = len(batch_task.slides) - batch_task.completed_count
            estimated_remaining_time = avg_time_per_slide * remaining_slides
        
        return BatchStatusResponse(
            batch_id=batch_task.batch_id,
            status=batch_task.status,
            progress=batch_task.progress,
            total_slides=batch_task.total_slides,
            completed_slides=batch_task.completed_count,
            successful=batch_task.success_count,
            failed=batch_task.failed_count,
            estimated_remaining_time=estimated_remaining_time,
            results=batch_task.results.copy()
        )

    def get_batch_results(self, batch_id: UUID) -> Optional[List[BatchGenerateItem]]:
        """获取批量任务结果"""
        batch_task = self.active_batches.get(batch_id)
        if not batch_task:
            return None
        
        return batch_task.results.copy()

    def cleanup_completed_batches(self, max_age_hours: int = 24):
        """清理已完成的批量任务"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        completed_batches = [
            batch_id for batch_id, batch_task in self.active_batches.items()
            if batch_task.status in ["completed", "completed_with_errors", "failed"] and
               (current_time - batch_task.start_time) > max_age_seconds
        ]
        
        for batch_id in completed_batches:
            del self.active_batches[batch_id]
            self.logger.logger.info(f"Cleaned up batch {batch_id} (older than {max_age_hours}h)")

    def get_active_batches_count(self) -> int:
        """获取活跃的批量任务数量"""
        return len([
            batch_task for batch_task in self.active_batches.values()
            if batch_task.status == "running"
        ])


__all__ = ["BatchImageGenerator", "BatchTask"]