from fastapi import APIRouter, HTTPException
from typing import List

from ..schemas.project import ProjectSchema, ProjectListItem
from ..services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
service = ProjectService()


@router.get("", response_model=List[ProjectListItem])
async def list_projects():
    """获取所有项目的简要列表"""
    try:
        return service.list_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectSchema)
async def get_project(project_id: str):
    """根据ID获取完整的项目数据"""
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/save", response_model=ProjectSchema)
async def save_project(project: ProjectSchema):
    """保存或更新项目数据"""
    try:
        return service.save_project(project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    success = service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}