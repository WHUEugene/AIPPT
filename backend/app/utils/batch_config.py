from __future__ import annotations

from typing import Dict, Any
from ..config import Settings


def validate_batch_config(settings: Settings) -> Dict[str, Any]:
    """验证批量生成配置的合理性"""
    issues = []
    recommendations = []
    
    # 检查并发数配置
    if settings.batch_default_workers > settings.batch_max_workers:
        issues.append(
            f"默认并发数 ({settings.batch_default_workers}) 不能大于最大并发数 ({settings.batch_max_workers})"
        )
    
    if settings.batch_max_workers > 100:
        recommendations.append(
            "最大并发数设置较高 (>100)，请注意API限制和服务器资源消耗"
        )
    
    if settings.batch_max_concurrent > 50:
        recommendations.append(
            "同时进行的批量任务数设置较高 (>50)，请注意内存使用情况"
        )
    
    # 检查API限制考虑
    if settings.batch_max_workers > 50:
        recommendations.append(
            "建议联系OpenRouter确认API并发限制，避免触发速率限制"
        )
    
    # 性能建议
    if settings.batch_default_workers < 3:
        recommendations.append(
            "默认并发数较低 (<3)，建议增加到5-10以获得更好的性能"
        )
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "recommendations": recommendations,
        "current_config": {
            "batch_default_workers": settings.batch_default_workers,
            "batch_max_workers": settings.batch_max_workers,
            "batch_max_concurrent": settings.batch_max_concurrent,
            "batch_cleanup_hours": settings.batch_cleanup_hours,
        }
    }


def get_optimal_config(slides_count: int, settings: Settings) -> Dict[str, Any]:
    """根据幻灯片数量获取最优的批量生成配置建议"""
    
    # 基础并发数建议
    if slides_count <= 3:
        optimal_workers = min(slides_count, 3)
    elif slides_count <= 10:
        optimal_workers = 5
    elif slides_count <= 20:
        optimal_workers = 10
    elif slides_count <= 50:
        optimal_workers = 15
    else:
        optimal_workers = min(20, settings.batch_max_workers)
    
    # 确保不超过配置的最大值
    optimal_workers = min(optimal_workers, settings.batch_max_workers)
    
    # 预估时间（基于经验值：单张图片平均15-30秒）
    avg_time_per_slide = 20  # 秒
    estimated_time = (slides_count / optimal_workers) * avg_time_per_slide
    
    return {
        "slides_count": slides_count,
        "recommended_workers": optimal_workers,
        "estimated_time_seconds": estimated_time,
        "estimated_time_formatted": format_time(estimated_time),
        "max_possible_workers": settings.batch_max_workers,
        "performance_notes": get_performance_notes(slides_count, optimal_workers)
    }


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def get_performance_notes(slides_count: int, workers: int) -> list[str]:
    """获取性能优化建议"""
    notes = []
    
    if slides_count > 20 and workers < 10:
        notes.append("幻灯片数量较多，建议增加并发数以提升效率")
    
    if workers > 15:
        notes.append("高并发数可能触发API速率限制，请监控错误率")
    
    if slides_count < 5 and workers > 5:
        notes.append("幻灯片数量较少，高并发数可能不会显著提升效率")
    
    if slides_count > 50:
        notes.append("大量幻灯片建议分批处理，避免单次请求时间过长")
    
    return notes


__all__ = ["validate_batch_config", "get_optimal_config"]