from __future__ import annotations

from functools import lru_cache

from .config import Settings
from .services.image_generator import ImageGenerator
from .services.llm_client import OpenRouterClient
from .services.outline_generator import OutlineGenerator
from .services.prompt_builder import PromptBuilder
from .services.pptx_exporter import PPTXExporter
from .services.style_analyzer import StyleAnalyzer
from .services.template_store import TemplateStore
from .services.config_manager import get_app_config


@lru_cache
def get_settings() -> Settings:
    """保持向后兼容的设置获取方式"""
    settings = Settings()
    settings.ensure_runtime_paths()
    return settings


def get_app_config_cached():
    """获取应用配置（带缓存）"""
    return get_app_config()


@lru_cache
def get_template_store() -> TemplateStore:
    """模板存储实例"""
    config = get_app_config()
    return TemplateStore(config.template_store_path)


@lru_cache
def get_llm_client() -> OpenRouterClient:
    """LLM客户端实例"""
    config = get_app_config()
    return OpenRouterClient(
        api_key=config.llm_api_key,
        base_url=config.llm_api_base,
        timeout_seconds=config.llm_timeout_seconds,
    )


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder()


@lru_cache
def get_style_analyzer() -> StyleAnalyzer:
    """风格分析器实例"""
    config = get_app_config()
    return StyleAnalyzer(get_llm_client(), config.llm_chat_model)


@lru_cache
def get_outline_generator() -> OutlineGenerator:
    """大纲生成器实例"""
    config = get_app_config()
    return OutlineGenerator(get_llm_client(), config.llm_chat_model)


@lru_cache
def get_image_generator() -> ImageGenerator:
    """图像生成器实例"""
    config = get_app_config()
    return ImageGenerator(
        output_dir=config.image_output_dir,
        llm_client=get_llm_client(),
        image_model=config.llm_image_model,
    )


@lru_cache
def get_pptx_exporter() -> PPTXExporter:
    """PPTX导出器实例"""
    config = get_app_config()
    return PPTXExporter(config.pptx_output_dir, config.image_output_dir)


__all__ = [
    "get_image_generator",
    "get_llm_client",
    "get_outline_generator",
    "get_prompt_builder",
    "get_pptx_exporter",
    "get_settings",
    "get_style_analyzer",
    "get_template_store",
]
