import json
import os
from glob import glob
from datetime import datetime
from pathlib import Path

from ..schemas.project import ProjectSchema, ProjectListItem


class ProjectService:
    def __init__(self):
        # 设置项目存储目录路径
        self.projects_dir = Path(__file__).parent.parent.parent / "data" / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def save_project(self, project_data: ProjectSchema) -> ProjectSchema:
        """保存项目数据到JSON文件"""
        file_path = self.projects_dir / f"{project_data.id}.json"
        
        # 更新修改时间
        project_data.updated_at = datetime.now()
        
        # 确保数据序列化正常
        project_dict = project_data.model_dump()
        
        # 处理datetime和UUID序列化
        project_dict["created_at"] = project_data.created_at.isoformat()
        project_dict["updated_at"] = project_data.updated_at.isoformat()
        
        # 处理slides中的UUID字段
        for slide in project_dict["slides"]:
            if "id" in slide and hasattr(slide["id"], "hex"):
                slide["id"] = slide["id"].hex
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(project_dict, f, ensure_ascii=False, indent=2)
            
        return project_data

    def get_project(self, project_id: str) -> ProjectSchema | None:
        """根据ID获取项目数据"""
        file_path = self.projects_dir / f"{project_id}.json"
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 解析datetime字段
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            
            # 解析slides中的UUID字段
            from uuid import UUID
            for slide in data["slides"]:
                if "id" in slide and isinstance(slide["id"], str):
                    try:
                        slide["id"] = UUID(slide["id"])
                    except ValueError:
                        # 如果不是有效UUID，保持原样或生成新的
                        pass
            
            return ProjectSchema(**data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error loading project {project_id}: {e}")
            return None

    def list_projects(self) -> list[ProjectListItem]:
        """获取所有项目的简要信息列表"""
        projects = []
        
        # 获取所有json文件
        files = list(self.projects_dir.glob("*.json"))
        
        # 按修改时间倒序排列
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                # 获取缩略图URL
                thumbnail_url = data.get("thumbnail_url")
                if not thumbnail_url and data.get("slides"):
                    # 如果没有设置缩略图，使用第一张幻灯片的图片
                    thumbnail_url = data["slides"][0].get("image_url")
                
                projects.append({
                    "id": data["id"],
                    "title": data["title"],
                    "updated_at": datetime.fromisoformat(data["updated_at"]),
                    "thumbnail_url": thumbnail_url
                })
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error loading project list item {file_path.name}: {e}")
                continue
                
        return projects

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        file_path = self.projects_dir / f"{project_id}.json"
        
        if file_path.exists():
            try:
                file_path.unlink()
                return True
            except OSError as e:
                print(f"Error deleting project {project_id}: {e}")
                return False
        return False