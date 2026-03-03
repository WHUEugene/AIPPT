from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID


class PipelineLogger:
    """专门用于记录AI-PPT Flow各个阶段详细日志的工具类"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path("logs")
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建logger实例
        self.logger = logging.getLogger("pipeline_logger")
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 控制台handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 文件handler - 详细日志
            file_handler = logging.FileHandler(
                self.log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d')}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 格式化器
            detailed_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(detailed_formatter)
            file_handler.setFormatter(detailed_formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
        
        # 生成日志文件目录
        self.session_logs = self.log_dir / "sessions"
        self.session_logs.mkdir(parents=True, exist_ok=True)
    
    def start_session(self, endpoint: str, **kwargs) -> str:
        """开始一个新的请求会话"""
        session_id = str(uuid.uuid4())
        
        # 处理不可JSON序列化的对象
        def safe_serialize(obj):
            if isinstance(obj, UUID):
                return str(obj)
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        safe_kwargs = {k: safe_serialize(v) for k, v in kwargs.items()}
        
        session_data = {
            "session_id": session_id,
            "endpoint": endpoint,
            "start_time": datetime.now().isoformat(),
            "timestamp": time.time(),
            "metadata": safe_kwargs
        }
        
        self._write_session_file(session_id, "start", session_data)
        self.logger.info(f"[{session_id}] 🚀 START {endpoint} | {json.dumps(safe_kwargs, ensure_ascii=False)}")
        
        return session_id
    
    def safe_serialize_data(self, data: Any) -> Any:
        """安全序列化数据，处理UUID等不可序列化对象"""
        if isinstance(data, UUID):
            return str(data)
        elif isinstance(data, dict):
            return {k: self.safe_serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.safe_serialize_data(item) for item in data]
        elif hasattr(data, '__dict__'):
            return str(data)
        else:
            return data

    def log_request(self, session_id: str, stage: str, data: Dict[str, Any]):
        """记录请求输入数据"""
        timestamp = datetime.now().isoformat()
        safe_data = self.safe_serialize_data(data)
        
        log_data = {
            "session_id": session_id,
            "stage": stage,
            "type": "request",
            "timestamp": timestamp,
            "data": safe_data
        }
        
        self._write_session_file(session_id, f"request_{stage}", log_data)
        self.logger.info(f"[{session_id}] 📥 REQUEST {stage} | {json.dumps(safe_data, ensure_ascii=False)}")
    
    def log_response(self, session_id: str, stage: str, data: Dict[str, Any], success: bool = True):
        """记录响应输出数据"""
        timestamp = datetime.now().isoformat()
        safe_data = self.safe_serialize_data(data)
        
        log_data = {
            "session_id": session_id,
            "stage": stage,
            "type": "response",
            "timestamp": timestamp,
            "success": success,
            "data": safe_data
        }
        
        self._write_session_file(session_id, f"response_{stage}", log_data)
        status = "✅" if success else "❌"
        self.logger.info(f"[{session_id}] {status} RESPONSE {stage} | {json.dumps(safe_data, ensure_ascii=False)}")
    
    def log_llm_call(self, session_id: str, stage: str, model: str, messages: list, 
                    temperature: float = None, max_tokens: int = None, response: str = None, 
                    error: str = None):
        """记录LLM调用的详细信息"""
        timestamp = datetime.now().isoformat()
        safe_messages = self.safe_serialize_data(messages)
        
        llm_data = {
            "session_id": session_id,
            "stage": stage,
            "type": "llm_call",
            "timestamp": timestamp,
            "model": model,
            "messages": safe_messages,
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        if response:
            llm_data["response"] = response
            self.logger.info(f"[{session_id}] 🤖 LLM {stage} | Model: {model} | Response: {response[:200]}...")
        
        if error:
            llm_data["error"] = error
            self.logger.error(f"[{session_id}] ❌ LLM {stage} | Model: {model} | Error: {error}")
        
        self._write_session_file(session_id, f"llm_{stage}", llm_data)
    
    def log_image_generation(self, session_id: str, prompt: str, model: str, 
                           width: int, height: int, image_path: str = None, error: str = None):
        """记录图片生成的详细信息"""
        timestamp = datetime.now().isoformat()
        
        img_data = {
            "session_id": session_id,
            "type": "image_generation",
            "timestamp": timestamp,
            "prompt": prompt,
            "model": model,
            "dimensions": f"{width}x{height}"
        }
        
        if image_path:
            img_data["image_path"] = image_path
            self.logger.info(f"[{session_id}] 🎨 IMAGE | Model: {model} | Size: {width}x{height} | Path: {image_path}")
        
        if error:
            img_data["error"] = error
            self.logger.error(f"[{session_id}] ❌ IMAGE | Model: {model} | Error: {error}")
        
        self._write_session_file(session_id, "image_generation", img_data)
    
    def log_pipeline_step(self, session_id: str, step: str, details: Dict[str, Any]):
        """记录pipeline中的各个步骤"""
        timestamp = datetime.now().isoformat()
        safe_details = self.safe_serialize_data(details)
        
        step_data = {
            "session_id": session_id,
            "step": step,
            "type": "pipeline_step",
            "timestamp": timestamp,
            "details": safe_details
        }
        
        self._write_session_file(session_id, f"step_{step}", step_data)
        self.logger.info(f"[{session_id}] ⚙️  STEP {step} | {json.dumps(safe_details, ensure_ascii=False)}")
    
    def end_session(self, session_id: str, success: bool = True, summary: Dict[str, Any] = None):
        """结束请求会话"""
        timestamp = datetime.now().isoformat()
        safe_summary = self.safe_serialize_data(summary or {})
        
        session_data = {
            "session_id": session_id,
            "end_time": timestamp,
            "success": success,
            "summary": safe_summary
        }
        
        self._write_session_file(session_id, "end", session_data)
        status = "✅" if success else "❌"
        self.logger.info(f"[{session_id}] {status} END | {json.dumps(safe_summary, ensure_ascii=False)}")
    
    def _write_session_file(self, session_id: str, action: str, data: Dict[str, Any]):
        """写入会话日志文件"""
        filename = f"{session_id}_{action}.json"
        filepath = self.session_logs / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to write session log: {e}")

    # Compatibility passthroughs for callers that use standard logging API.
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


# 全局logger实例
pipeline_logger = PipelineLogger()


def get_logger() -> PipelineLogger:
    """获取pipeline logger实例"""
    return pipeline_logger


__all__ = ["PipelineLogger", "get_logger"]
