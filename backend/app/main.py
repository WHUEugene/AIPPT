from __future__ import annotations

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .dependencies import get_settings
from .routers import export, outline, project, slide, template, config
from .services.config_manager import get_app_config

# 获取配置（使用动态配置管理器）
app_config = get_app_config()

# 创建应用
app = FastAPI(title=app_config.project_name)

# CORS中间件 - 使用动态配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件挂载 - 使用动态配置
try:
    # 确保目录存在
    import os
    image_dir = str(app_config.image_output_dir)
    os.makedirs(image_dir, exist_ok=True)
    app.mount(
        "/assets",
        StaticFiles(directory=image_dir),
        name="assets",
    )
    print(f"✅ 成功挂载静态文件目录: {image_dir}")
except Exception as e:
    print(f"⚠️  静态文件目录挂载失败，将继续运行: {e}")

# 路由注册 - 使用动态配置
app.include_router(config.router, prefix=app_config.api_prefix)
app.include_router(template.router, prefix=app_config.api_prefix)
app.include_router(outline.router, prefix=app_config.api_prefix)
app.include_router(slide.router, prefix=app_config.api_prefix)
app.include_router(project.router, prefix=app_config.api_prefix)
app.include_router(export.router, prefix=app_config.api_prefix)

# 异常处理器 - 详细记录422错误
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    logging.error(f"Validation error at {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.json() if hasattr(exc, 'json') else str(exc)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error at {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": app_config.project_name,
        "message": "AI-PPT Flow backend is ready.",
    }


__all__ = ["app"]
