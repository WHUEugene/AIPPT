from __future__ import annotations

import time
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_llm_client
from ..schemas.config import (
    AppConfig,
    ConfigUpdateRequest,
    ConnectionTestRequest,
    ConnectionTestResponse
)
from ..services.config_manager import get_config_manager
from ..services.llm_client import LLMClientError
from ..utils.logger import get_logger

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=AppConfig)
async def get_config():
    """
    获取当前应用程序配置
    
    Returns:
        AppConfig: 当前配置对象
    """
    logger = get_logger()
    
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        logger.logger.info("配置读取成功")
        return config
        
    except Exception as e:
        logger.logger.error(f"读取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")


@router.post("/", response_model=AppConfig)
async def update_config(request: ConfigUpdateRequest):
    """
    更新应用程序配置
    
    Args:
        request: 配置更新请求
        
    Returns:
        AppConfig: 更新后的配置对象
    """
    logger = get_logger()
    
    try:
        config_manager = get_config_manager()
        
        # 获取当前配置
        current_config = config_manager.get_config()
        current_data = current_config.dict()
        
        # 应用更新（只更新非None字段）
        updates = {}
        for field, value in request.dict(exclude_unset=True).items():
            updates[field] = value
        
        if not updates:
            # 没有需要更新的字段
            logger.logger.info("配置更新请求为空，返回当前配置")
            return current_config
        
        # 更新配置
        if config_manager.update_config(updates):
            new_config = config_manager.get_config(force_reload=True)
            
            # 记录配置更新
            logger.log_request(
                session_id=None,
                stage="config_update",
                data={
                    "updated_fields": list(updates.keys()),
                    "config_size": len(str(new_config.dict()))
                }
            )
            
            logger.logger.info(f"配置更新成功，更新字段: {list(updates.keys())}")
            return new_config
        else:
            logger.logger.error("配置更新失败")
            raise HTTPException(status_code=500, detail="配置保存失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/reset", response_model=AppConfig)
async def reset_config():
    """
    重置为默认配置
    
    Returns:
        AppConfig: 重置后的配置对象
    """
    logger = get_logger()
    
    try:
        config_manager = get_config_manager()
        
        if config_manager.reset_to_default():
            new_config = config_manager.get_config(force_reload=True)
            logger.logger.info("配置已重置为默认值")
            return new_config
        else:
            logger.logger.error("配置重置失败")
            raise HTTPException(status_code=500, detail="配置重置失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.logger.error(f"重置配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(
    request: ConnectionTestRequest,
    llm_client=Depends(get_llm_client)
):
    """
    测试AI服务连接
    
    Args:
        request: 连接测试请求
        llm_client: LLM客户端
        
    Returns:
        ConnectionTestResponse: 连接测试结果
    """
    logger = get_logger()
    
    try:
        logger.logger.info(f"开始测试AI服务连接: {request.api_base}")
        
        start_time = time.time()
        
        # 创建临时LLM客户端进行测试
        test_client = llm_client.__class__(
            api_key=request.api_key,
            base_url=request.api_base
        )
        
        # 发送测试请求
        test_messages = [
            {"role": "user", "content": "Hello, this is a connection test. Please respond with 'Connection successful'."}
        ]
        test_response = await test_client.chat(
            messages=test_messages,
            model=request.model
        )
        
        response_time = time.time() - start_time
        
        # 检查响应
        if test_response and len(test_response.strip()) > 0:
            logger.logger.info(f"AI服务连接测试成功，响应时间: {response_time:.2f}秒")
            
            return ConnectionTestResponse(
                success=True,
                message=f"连接成功，响应时间: {response_time:.2f}秒",
                model=request.model,
                response_time=response_time
            )
        else:
            logger.logger.error("AI服务连接测试失败：响应为空")
            return ConnectionTestResponse(
                success=False,
                message="连接失败：响应为空",
                model=request.model,
                response_time=response_time
            )
            
    except LLMClientError as e:
        logger.logger.error(f"AI服务连接测试失败 (LLM客户端错误): {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"连接失败: {str(e)}",
            model=request.model
        )
    except Exception as e:
        logger.logger.error(f"AI服务连接测试失败 (未知错误): {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"连接测试失败: {str(e)}",
            model=request.model
        )


@router.get("/status")
async def get_config_status():
    """
    获取配置状态信息
    
    Returns:
        dict: 配置状态信息
    """
    logger = get_logger()
    
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        
        # 验证配置
        validation_errors = config_manager.validate_config(config)
        
        status = {
            "is_configured": config_manager.is_configured(),
            "has_api_key": bool(config.llm_api_key.strip()),
            "config_file_exists": config_manager.config_file.exists(),
            "config_file_path": str(config_manager.config_file),
            "validation_errors": validation_errors,
            "is_valid": len(validation_errors) == 0
        }
        
        logger.logger.info(f"配置状态检查完成: configured={status['is_configured']}, valid={status['is_valid']}")
        
        return status
        
    except Exception as e:
        logger.logger.error(f"获取配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置状态失败: {str(e)}")


@router.post("/validate")
async def validate_config_data(config_data: Dict):
    """
    验证配置数据的有效性
    
    Args:
        config_data: 要验证的配置数据
        
    Returns:
        dict: 验证结果
    """
    logger = get_logger()
    
    try:
        # 尝试创建配置对象
        config = AppConfig(**config_data)
        
        # 使用配置管理器进行额外验证
        config_manager = get_config_manager()
        validation_errors = config_manager.validate_config(config)
        
        result = {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors
        }
        
        if result["valid"]:
            logger.logger.info("配置验证通过")
        else:
            logger.logger.warning(f"配置验证失败，错误: {validation_errors}")
        
        return result
        
    except Exception as e:
        logger.logger.error(f"配置验证异常: {e}")
        return {
            "valid": False,
            "errors": [f"配置格式错误: {str(e)}"]
        }