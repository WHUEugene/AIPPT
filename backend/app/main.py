from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .dependencies import get_settings
from .routers import export, outline, project, slide, template

settings = get_settings()

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/assets",
    StaticFiles(directory=str(settings.image_output_dir)),
    name="assets",
)

app.include_router(template.router, prefix=settings.api_prefix)
app.include_router(outline.router, prefix=settings.api_prefix)
app.include_router(slide.router, prefix=settings.api_prefix)
app.include_router(project.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.project_name,
        "message": "AI-PPT Flow backend is ready.",
    }


__all__ = ["app"]
