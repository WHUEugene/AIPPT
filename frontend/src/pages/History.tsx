import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, Trash2, FolderOpen } from 'lucide-react';
import { fetchProjects, fetchProjectDetail, deleteProject } from '../services/api';
import { useProjectStore } from '../store/useProjectStore';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import BackButton from '../components/ui/BackButton';
import type { ProjectListItem } from '../services/types';

export default function HistoryPage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const loadProject = useProjectStore((state) => state.loadProject);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await fetchProjects();
      setProjects(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError('加载项目列表失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenProject = async (id: string) => {
    try {
      const projectData = await fetchProjectDetail(id);
      loadProject(projectData);
      navigate('/workspace');
    } catch (err) {
      console.error('Failed to load project:', err);
      setError('打开项目失败，请重试');
    }
  };

  const handleDeleteProject = async (id: string, title: string) => {
    if (!window.confirm(`确定要删除项目"${title}"吗？此操作不可撤销。`)) {
      return;
    }

    try {
      await deleteProject(id);
      setProjects(projects.filter(p => p.id !== id));
    } catch (err) {
      console.error('Failed to delete project:', err);
      setError('删除项目失败，请重试');
    }
  };

  const handleCreateNew = () => {
    const createNewProject = useProjectStore.getState().createNewProject;
    createNewProject();
    navigate('/templates');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-pku-light flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-pku-red border-t-transparent rounded-full animate-spin"></div>
          <span className="text-pku-gray">加载项目列表中...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-pku-light p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <BackButton />
        </div>
        {/* 页面头部 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">我的项目</h1>
            <p className="text-gray-600">查看和继续编辑您的AI生成PPT项目</p>
          </div>
          <Button onClick={handleCreateNew}>
            + 新建项目
          </Button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
            <button 
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-600 hover:text-red-800"
            >
              关闭
            </button>
          </div>
        )}

        {/* 项目列表 */}
        {projects.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
              <FolderOpen className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-xl font-medium text-gray-900 mb-2">还没有项目</h3>
            <p className="text-gray-600 mb-6">创建您的第一个AI生成PPT项目</p>
            <Button onClick={handleCreateNew} size="lg">
              开始创建
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Card key={project.id} className="group hover:shadow-lg transition-all duration-200">
                <div className="relative">
                  {/* 缩略图 */}
                  <div className="h-48 bg-gray-100 rounded-t-lg overflow-hidden">
                    {project.thumbnail_url ? (
                      <img 
                        src={project.thumbnail_url} 
                        alt={project.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                          <FolderOpen className="w-6 h-6 text-gray-400" />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* 操作按钮 */}
                  <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteProject(project.id, project.title);
                      }}
                      className="bg-white/90 hover:bg-red-50 border-red-200 text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                
                {/* 项目信息 */}
                <div 
                  className="p-4 cursor-pointer"
                  onClick={() => handleOpenProject(project.id)}
                >
                  <h3 className="font-semibold text-gray-900 mb-2 truncate">{project.title}</h3>
                  <div className="flex items-center text-sm text-gray-500">
                    <Clock className="w-4 h-4 mr-1" />
                    {new Date(project.updated_at).toLocaleString('zh-CN', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}