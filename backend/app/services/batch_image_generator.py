from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
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


# 多进程worker函数 - 必须在模块级别定义
def _generate_slide_worker(
    slide_data: dict,
    style_prompt: str,
    aspect_ratio: str,
    config: dict
) -> dict:
    """
    多进程worker函数，生成单个幻灯片
    slide_data: 序列化的幻灯片数据
    """
    import time
    import asyncio
    from pathlib import Path
    
    # 重新创建依赖对象（因为多进程不能共享对象）
    from ..utils.logger import get_logger
    from ..schemas.slide import SlideData, SlideStatus
    from .llm_client import OpenRouterClient
    from .prompt_builder import PromptBuilder
    from .image_generator import ImageGenerator
    
    try:
        # 重建依赖对象
        llm_client = OpenRouterClient(
            api_key=config["api_key"],
            base_url=config["base_url"]
        )
        prompt_builder = PromptBuilder(llm_client)
        image_generator = ImageGenerator(
            output_dir=Path(config["output_dir"]),
            llm_client=llm_client,
            image_model=config["image_model"]
        )
        
        # 重建SlideData对象
        slide = SlideData(
            id=slide_data["id"],
            page_num=slide_data["page_num"],
            type=slide_data["type"],
            title=slide_data["title"],
            content_text=slide_data["content_text"],
            visual_desc=slide_data["visual_desc"]
        )
        
        start_time = time.time()
        
        # 构建最终提示词
        final_prompt = prompt_builder.build(
            style_prompt=style_prompt,
            visual_desc=slide.visual_desc,
            title=slide.title,
            content_text=slide.content_text,
            aspect_ratio=aspect_ratio
        )
        
        # 生成图片（直接使用异步方法，因为在多进程中每个进程都有自己的事件循环）
        import asyncio
        
        async def generate_image():
            return await image_generator.create(
                title=slide.title,
                final_prompt=final_prompt,
                aspect_ratio=aspect_ratio,
                page_num=slide.page_num
            )
        
        # 在新的事件循环中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            generated = loop.run_until_complete(generate_image())
        finally:
            loop.close()
        
        generation_time = time.time() - start_time
        
        return {
            "success": True,
            "slide_id": slide.id,
            "page_num": slide.page_num,
            "title": slide.title,
            "image_url": generated.image_url,
            "final_prompt": final_prompt,
            "generation_time": generation_time,
            "status": "done"
        }
        
    except Exception as e:
        generation_time = time.time() - start_time if 'start_time' in locals() else 0
        return {
            "success": False,
            "slide_id": slide_data["id"],
            "page_num": slide_data["page_num"],
            "title": slide_data.get("title", ""),
            "error_message": str(e),
            "generation_time": generation_time,
            "status": "error"
        }


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
        self.executor = ProcessPoolExecutor(max_workers=max_concurrent_batches)
        
        # 多进程配置 - 从image_generator获取必要配置
        self.multiprocess_config = {
            "output_dir": str(image_generator.output_dir),
            "image_model": image_generator.image_model,
            "api_key": image_generator.llm_client.api_key,
            "base_url": str(image_generator.llm_client.base_url)
        }

    def create_batch(
        self,
        slides: List[SlideData],
        style_prompt: str,
        max_workers: int = None,
        aspect_ratio: str = "16:9"
    ) -> UUID:
        """创建新的批量生成任务"""
        batch_id = uuid4()
        
        # 智能设置并发数：1-10页使用页数个worker，10页以上使用10个worker
        if max_workers is None:
            max_workers = min(len(slides), 10)
        
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
            
            # 使用多进程执行并发生成 - 提交任务到进程池
            with ProcessPoolExecutor(max_workers=batch_task.max_workers) as executor:
                # 将所有幻灯片序列化为字典（多进程需要）
                slide_data_list = []
                for slide in batch_task.slides:
                    slide_data_list.append({
                        "id": slide.id,
                        "page_num": slide.page_num,
                        "type": slide.type,
                        "title": slide.title,
                        "content_text": slide.content_text,
                        "visual_desc": slide.visual_desc
                    })
                
                # 提交所有任务到进程池
                future_to_slide_data = {}
                for i, slide_data in enumerate(slide_data_list):
                    future = executor.submit(
                        _generate_slide_worker,
                        slide_data,
                        batch_task.style_prompt,
                        batch_task.aspect_ratio,
                        self.multiprocess_config
                    )
                    future_to_slide_data[future] = slide_data
                
                # 等待所有任务完成
                for future in as_completed(future_to_slide_data):
                    slide_data = future_to_slide_data[future]
                    
                    try:
                        worker_result = future.result()  # 获取多进程worker的结果
                        
                        # 将worker结果转换为BatchGenerateItem
                        if worker_result["success"]:
                            batch_generate_item = BatchGenerateItem(
                                slide_id=worker_result["slide_id"],
                                page_num=worker_result["page_num"],
                                title=worker_result["title"],
                                image_url=worker_result.get("image_url", ""),
                                final_prompt=worker_result.get("final_prompt", ""),
                                status=SlideStatus.done,
                                generation_time=worker_result["generation_time"]
                            )
                            batch_task.success_count += 1
                        else:
                            batch_generate_item = BatchGenerateItem(
                                slide_id=worker_result["slide_id"],
                                page_num=worker_result["page_num"],
                                title=worker_result["title"],
                                status=SlideStatus.error,
                                error_message=worker_result.get("error_message", "Unknown error"),
                                generation_time=worker_result["generation_time"]
                            )
                            batch_task.failed_count += 1
                        
                        batch_task.results.append(batch_generate_item)
                        batch_task.completed_count += 1
                        
                        # 记录单个幻灯片完成
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_completed",
                            details={
                                "batch_id": str(batch_task.batch_id),
                                "slide_id": str(worker_result["slide_id"]),
                                "page_num": worker_result["page_num"],
                                "status": worker_result["status"],
                                "completed_count": batch_task.completed_count,
                                "total_count": len(batch_task.slides),
                                "progress": batch_task.progress,
                                "success": worker_result["success"],
                                "stage": f"幻灯片 {worker_result['page_num']} 生成完成"
                            }
                        )
                        
                    except Exception as e:
                        # 处理进程池异常
                        batch_generate_item = BatchGenerateItem(
                            slide_id=slide_data["id"],
                            page_num=slide_data["page_num"],
                            title=slide_data.get("title", ""),
                            status=SlideStatus.error,
                            error_message=f"进程池错误: {str(e)}"
                        )
                        batch_task.results.append(batch_generate_item)
                        batch_task.completed_count += 1
                        batch_task.failed_count += 1
                        
                        self.logger.log_pipeline_step(
                            session_id=session_id,
                            step="slide_error",
                            details={
                                "batch_id": str(batch_task.batch_id),
                                "slide_id": str(slide_data["id"]),
                                "page_num": slide_data["page_num"],
                                "error": str(e),
                                "stage": f"幻灯片 {slide_data['page_num']} 进程池失败"
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