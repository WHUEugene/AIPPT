"""
配置管理服务
负责应用程序配置的读取、保存和验证
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from pydantic import ValidationError

from ..schemas.config import AppConfig
from ..utils.logger import get_logger


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    兼容开发环境和 PyInstaller 打包后的环境
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为 backend/data/config.json
        """
        self.logger = get_logger()
        
        # 确定配置文件路径
        if config_file:
            self.config_file = Path(config_file)
        else:
            # 默认配置文件位置：使用 get_resource_path 处理
            self.config_file = Path(get_resource_path("data/config.json"))
        
        # 确保配置目录存在
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 默认配置
        self._default_config = AppConfig(
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_api_base=os.getenv("LLM_API_BASE", "https://openrouter.ai/api/v1"),
            llm_chat_model=os.getenv("LLM_CHAT_MODEL", "google/gemini-3-pro-preview"),
            llm_image_model=os.getenv("LLM_IMAGE_MODEL", "google/gemini-3-pro-image-preview"),
            llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
            
            image_output_dir=os.getenv("IMAGE_OUTPUT_DIR", "backend/generated/images"),
            pptx_output_dir=os.getenv("PPTX_OUTPUT_DIR", "backend/generated/pptx"),
            template_store_path=os.getenv("TEMPLATE_STORE_PATH", "backend/data/templates.json"),
            
            allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,https://your-domain.com").split(","),
            
            project_name=os.getenv("PROJECT_NAME", "AI-PPT Flow Backend"),
            api_prefix=os.getenv("API_PREFIX", "/api")
        )
        
        self._config: Optional[AppConfig] = None
        self._last_loaded: Optional[float] = None
    
    def _load_from_file(self) -> Optional[AppConfig]:
        """
        从文件加载配置
        
        Returns:
            加载的配置对象，如果文件不存在则返回None
        """
        if not self.config_file.exists():
            self.logger.logger.info(f"配置文件不存在: {self.config_file}")
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 验证配置格式
            config = AppConfig(**config_data)
            self.logger.logger.info(f"成功加载配置文件: {self.config_file}")
            return config
            
        except json.JSONDecodeError as e:
            self.logger.logger.error(f"配置文件JSON格式错误: {e}")
            return None
        except ValidationError as e:
            self.logger.logger.error(f"配置文件验证失败: {e}")
            return None
        except Exception as e:
            self.logger.logger.error(f"加载配置文件失败: {e}")
            return None
    
    def _save_to_file(self, config: AppConfig) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置对象
            
        Returns:
            是否保存成功
        """
        try:
            # 创建配置目录
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 备份现有配置文件
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.json.backup')
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    self.logger.logger.info(f"已创建配置文件备份: {backup_file}")
                except Exception as e:
                    self.logger.logger.warning(f"创建配置文件备份失败: {e}")
            
            # 保存新配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.logger.info(f"成功保存配置文件: {self.config_file}")
            return True
            
        except Exception as e:
            self.logger.logger.error(f"保存配置文件失败: {e}")
            return False
    
    def get_config(self, force_reload: bool = False) -> AppConfig:
        """
        获取配置
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            配置对象
        """
        current_time = time.time()
        
        # 检查是否需要重新加载
        if (force_reload or 
            self._config is None or 
            self._last_loaded is None or 
            current_time - self._last_loaded > 60):  # 60秒缓存
            
            # 尝试从文件加载
            file_config = self._load_from_file()
            
            if file_config:
                self._config = file_config
            else:
                # 使用默认配置并保存到文件
                self._config = self._default_config
                self._save_to_file(self._config)
                self.logger.logger.info("使用默认配置并保存到文件")
            
            self._last_loaded = current_time
        
        return self._config
    
    def update_config(self, updates: Dict) -> bool:
        """
        更新配置
        
        Args:
            updates: 要更新的配置字段
            
        Returns:
            是否更新成功
        """
        try:
            # 获取当前配置
            current_config = self.get_config()
            
            # 创建新的配置对象
            current_data = current_config.dict()
            current_data.update(updates)
            
            # 验证新配置
            new_config = AppConfig(**current_data)
            
            # 保存到文件
            if self._save_to_file(new_config):
                self._config = new_config
                self._last_loaded = time.time()
                self.logger.logger.info("配置更新成功")
                return True
            else:
                return False
                
        except ValidationError as e:
            self.logger.logger.error(f"配置验证失败: {e}")
            return False
        except Exception as e:
            self.logger.logger.error(f"更新配置失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """
        重置为默认配置
        
        Returns:
            是否重置成功
        """
        if self._save_to_file(self._default_config):
            self._config = self._default_config
            self._last_loaded = time.time()
            self.logger.logger.info("已重置为默认配置")
            return True
        else:
            return False
    
    def is_configured(self) -> bool:
        """
        检查是否已配置基本参数
        
        Returns:
            是否已配置
        """
        config = self.get_config()
        return bool(config.llm_api_key.strip())
    
    def validate_config(self, config: AppConfig) -> list[str]:
        """
        验证配置的有效性
        
        Args:
            config: 要验证的配置
            
        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []
        
        # 检查API密钥
        if not config.llm_api_key.strip():
            errors.append("API密钥不能为空")
        
        # 检查API基础地址
        if not config.llm_api_base.strip():
            errors.append("API基础地址不能为空")
        elif not (config.llm_api_base.startswith('http://') or 
                 config.llm_api_base.startswith('https://')):
            errors.append("API基础地址必须以http://或https://开头")
        
        # 检查超时时间
        if config.llm_timeout_seconds < 30 or config.llm_timeout_seconds > 300:
            errors.append("超时时间必须在30-300秒之间")
        
        # 检查目录路径
        for field_name, field_value in [
            ("图像输出目录", config.image_output_dir),
            ("PPTX输出目录", config.pptx_output_dir),
            ("模板存储路径", config.template_store_path)
        ]:
            if not field_value.strip():
                errors.append(f"{field_name}不能为空")
        
        # 检查允许的跨域源
        if not config.allowed_origins:
            errors.append("必须指定至少一个允许的跨域源")
        
        return errors


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_app_config() -> AppConfig:
    """
    获取应用程序配置
    
    Returns:
        应用程序配置对象
    """
    return get_config_manager().get_config()


__all__ = [
    "ConfigManager",
    "get_config_manager", 
    "get_app_config"
]