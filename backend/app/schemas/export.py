from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .project import ProjectState


class ExportRequest(BaseModel):
    project: ProjectState
    file_name: Optional[str] = None


__all__ = ["ExportRequest"]
