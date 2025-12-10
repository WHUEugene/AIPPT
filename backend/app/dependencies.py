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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_paths()
    return settings


@lru_cache
def get_template_store() -> TemplateStore:
    settings = get_settings()
    return TemplateStore(settings.template_store_path)


@lru_cache
def get_llm_client() -> OpenRouterClient:
    settings = get_settings()
    return OpenRouterClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        timeout_seconds=settings.llm_timeout_seconds,
    )


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder()


@lru_cache
def get_style_analyzer() -> StyleAnalyzer:
    settings = get_settings()
    return StyleAnalyzer(get_llm_client(), settings.llm_chat_model)


@lru_cache
def get_outline_generator() -> OutlineGenerator:
    settings = get_settings()
    return OutlineGenerator(get_llm_client(), settings.llm_chat_model)


@lru_cache
def get_image_generator() -> ImageGenerator:
    settings = get_settings()
    return ImageGenerator(
        output_dir=settings.image_output_dir,
        llm_client=get_llm_client(),
        image_model=settings.llm_image_model,
    )


@lru_cache
def get_pptx_exporter() -> PPTXExporter:
    settings = get_settings()
    return PPTXExporter(settings.pptx_output_dir, settings.image_output_dir)


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
