import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ImagePlus, Loader2, Pencil, Plus } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { fetchTemplates, generateSlide, updateTemplate } from '../services/api';
import type { Template } from '../services/types';
import { useProjectStore } from '../store/useProjectStore';

const fallbackTemplates: Template[] = [
  {
    id: '22133566-d215-4d60-a883-1e3dfb9c1508',
    name: '北大典雅学术版',
    style_prompt: '北大红搭配黑白配色，强调书卷质感',
    vis_settings: { primary_color: '#8B0012' },
    cover_image: '/api/placeholder/400/300/8B0012/FFFFFF?text=北大典雅',
  },
  {
    id: '7dd2d9a8-1c94-4ecc-854c-d741a706dc21',
    name: '深空科技蓝',
    style_prompt: '深空蓝背景搭配霓虹线条',
    vis_settings: { primary_color: '#0B1021' },
    cover_image: '/api/placeholder/400/300/0B1021/00FFFF?text=深空科技',
  },
  {
    id: 'fd870c83-150e-4376-8779-ee3101c66f13',
    name: '极简商务灰',
    style_prompt: '柔和灰度与细线结构',
    vis_settings: { primary_color: '#555555' },
    cover_image: '/api/placeholder/400/300/555555/FFFFFF?text=极简商务',
  },
];

export default function TemplateSelect() {
  const navigate = useNavigate();
  const { templates, setTemplates, setCurrentTemplate, upsertTemplate, currentTemplate } = useProjectStore();
  const [loading, setLoading] = useState(false);
  const [previewLoadingId, setPreviewLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await fetchTemplates();
        if (data.length === 0) {
          setTemplates(fallbackTemplates);
        } else {
          setTemplates(data);
        }
        setError(null);
      } catch (err) {
        console.warn('Failed to fetch templates, using fallback', err);
        setTemplates(fallbackTemplates);
        setError('暂时无法连接后端，已加载示例模版。');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [setTemplates]);

  const handleSelect = (template: Template) => {
    setCurrentTemplate(template);
    navigate('/input');
  };

  const handleEdit = (event: React.MouseEvent, templateId: string) => {
    event.stopPropagation();
    navigate(`/templates/${templateId}/edit`);
  };

  const handleGeneratePreview = async (event: React.MouseEvent, template: Template) => {
    event.stopPropagation();
    if (previewLoadingId) {
      return;
    }

    setError(null);
    setPreviewLoadingId(template.id);

    try {
      const response = await generateSlide({
        style_prompt: template.style_prompt,
        visual_desc: '一张高完成度的 PPT 模板封面预览图，突出该模板的配色、排版秩序、背景材质、主标题区和视觉焦点，用于模板选择页展示。',
        aspect_ratio: '16:9',
        page_num: 1,
        title: template.name,
        content_text: '模板预览',
      });

      const updatedTemplate: Template = {
        ...template,
        cover_image: response.image_url,
      };

      try {
        await updateTemplate(template.id, {
          name: template.name,
          style_prompt: template.style_prompt,
          cover_image: response.image_url,
          vis_settings: template.vis_settings,
          aspect_ratios: template.aspect_ratios,
          default_aspect_ratio: template.default_aspect_ratio,
          custom_dimensions: template.custom_dimensions,
        });
      } catch (err) {
        console.warn('Update template preview failed, fallback to local record', err);
      }

      upsertTemplate(updatedTemplate);
      if (currentTemplate?.id === updatedTemplate.id) {
        setCurrentTemplate(updatedTemplate);
      }
    } catch (err) {
      console.error(err);
      setError('模板示例图生成失败，请确认后端绘图接口已启动');
    } finally {
      setPreviewLoadingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-pku-light p-6 md:p-12">
      <header className="flex flex-wrap items-center justify-between mb-12 gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-5 h-5 mr-2" /> 返回
          </Button>
          <h1 className="text-3xl font-serif text-pku-black">选择设计模版</h1>
        </div>
        {error && <span className="text-sm text-red-500">{error}</span>}
      </header>

      {loading ? (
        <div className="text-center text-gray-500">正在加载模版...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div
            onClick={() => navigate('/create-template')}
            className="border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center h-64 cursor-pointer hover:border-pku-red hover:bg-pku-red/5 transition-all group"
          >
            <Plus className="w-10 h-10 text-gray-400 group-hover:text-pku-red mb-4" />
            <span className="font-serif text-lg text-gray-500 group-hover:text-pku-red">提取新风格</span>
          </div>

          {templates.map((template) => (
            <Card
              key={template.id}
              className="h-64 flex flex-col overflow-hidden cursor-pointer hover:ring-2 ring-pku-red transition-all group"
              onClick={() => handleSelect(template)}
            >
              <div className="flex-1 bg-gray-200 relative overflow-hidden">
                {template.cover_image ? (
                  <img 
                    src={template.cover_image} 
                    alt={template.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div
                    className="absolute inset-0 flex flex-col items-center justify-center text-white p-5 text-center"
                    style={{
                      background: `linear-gradient(135deg, ${template.vis_settings?.primary_color || '#8B0012'} 0%, #1f2937 100%)`,
                    }}
                  >
                    <div className="text-xs uppercase tracking-[0.25em] opacity-70 mb-2">Template</div>
                    <div className="font-serif text-2xl leading-tight">{template.name}</div>
                    <div className="text-xs mt-3 opacity-80 line-clamp-3">{template.style_prompt}</div>
                  </div>
                )}
                <div className="absolute top-3 right-3 flex gap-2">
                  {!template.cover_image && (
                    <button
                      type="button"
                      className="h-8 px-3 rounded-md bg-white/90 text-gray-700 text-xs font-medium shadow-sm hover:bg-white"
                      onClick={(event) => handleGeneratePreview(event, template)}
                    >
                      {previewLoadingId === template.id ? (
                        <span className="flex items-center">
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" /> 生成中
                        </span>
                      ) : (
                        <span className="flex items-center">
                          <ImagePlus className="w-3 h-3 mr-1" /> 示例图
                        </span>
                      )}
                    </button>
                  )}
                  <button
                    type="button"
                    className="h-8 w-8 rounded-md bg-white/90 text-gray-700 flex items-center justify-center shadow-sm hover:bg-white"
                    onClick={(event) => handleEdit(event, template.id)}
                    aria-label={`编辑${template.name}`}
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                </div>
                <div
                  className="absolute bottom-0 left-0 w-full h-2"
                  style={{ backgroundColor: template.vis_settings?.primary_color || '#8B0012' }}
                />
              </div>
              <div className="p-4 bg-white">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-serif font-bold text-lg mb-1">{template.name}</h3>
                  {!template.cover_image && <span className="text-[10px] text-amber-600 whitespace-nowrap">无封面图</span>}
                </div>
                <p className="text-xs text-gray-500 line-clamp-2">{template.style_prompt}</p>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
