from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """应用程序配置模型"""
    # AI服务配置
    llm_api_key: str = Field(..., description="LLM API密钥")
    llm_api_base: str = Field(default="https://openrouter.ai/api/v1", description="LLM API基础地址")
    llm_chat_model: str = Field(default="google/gemini-3-pro-preview", description="文本生成模型")
    llm_image_model: str = Field(default="google/gemini-3-pro-image-preview", description="图像生成模型")
    llm_timeout_seconds: int = Field(default=120, ge=30, le=300, description="API请求超时时间(秒)")
    
    # 文件存储配置
    image_output_dir: str = Field(default="backend/generated/images", description="图像输出目录")
    pptx_output_dir: str = Field(default="backend/generated/pptx", description="PPTX输出目录")
    template_store_path: str = Field(default="backend/data/templates.json", description="模板存储路径")
    
    # CORS配置
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173", "https://your-domain.com"],
        description="允许的跨域源列表"
    )
    
    # 服务配置
    project_name: str = Field(default="AI-PPT Flow Backend", description="项目名称")
    api_prefix: str = Field(default="/api", description="API路由前缀")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    llm_api_key: Optional[str] = Field(None, description="LLM API密钥")
    llm_api_base: Optional[str] = Field(None, description="LLM API基础地址")
    llm_chat_model: Optional[str] = Field(None, description="文本生成模型")
    llm_image_model: Optional[str] = Field(None, description="图像生成模型")
    llm_timeout_seconds: Optional[int] = Field(None, ge=30, le=300, description="API请求超时时间(秒)")
    
    # 文件存储配置
    image_output_dir: Optional[str] = Field(None, description="图像输出目录")
    pptx_output_dir: Optional[str] = Field(None, description="PPTX输出目录")
    template_store_path: Optional[str] = Field(None, description="模板存储路径")
    
    # CORS配置
    allowed_origins: Optional[List[str]] = Field(None, description="允许的跨域源列表")
    
    # 服务配置
    project_name: Optional[str] = Field(None, description="项目名称")
    api_prefix: Optional[str] = Field(None, description="API路由前缀")


class ConnectionTestRequest(BaseModel):
    """连接测试请求模型"""
    api_key: str = Field(..., description="API密钥")
    api_base: str = Field(..., description="API基础地址")
    model: str = Field(..., description="测试模型")


class ConnectionTestResponse(BaseModel):
    """连接测试响应模型"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试结果消息")
    model: Optional[str] = Field(None, description="测试的模型名称")
    response_time: Optional[float] = Field(None, description="响应时间(秒)")


__all__ = [
    "AppConfig",
    "ConfigUpdateRequest", 
    "ConnectionTestRequest",
    "ConnectionTestResponse"
]