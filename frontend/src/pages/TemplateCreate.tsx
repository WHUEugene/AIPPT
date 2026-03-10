import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowRight,
  ImagePlus,
  Loader2,
  Pencil,
  Upload,
  Wand2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import {
  analyzeTemplateStream,
  fetchTemplates,
  generateSlide,
  saveTemplate,
  updateTemplate,
  type TemplateStreamMessage,
} from '../services/api';
import type { Template } from '../services/types';
import { useProjectStore } from '../store/useProjectStore';
import { generateId } from '../utils/uuid';

const TEMPLATE_PREVIEW_VISUAL_DESC = '一张高完成度的演示文稿封面图。画面中心有清晰的标题区、几何化的信息版式、强烈的风格化背景、精致的留白与装饰细节，整体用于展示模板的配色、材质、版式和氛围。';
const TEMPLATE_PREVIEW_TITLE = '模板风格示例';
const TEMPLATE_PREVIEW_TEXT = '用于模板封面展示';

export default function TemplateCreate() {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const isEditMode = !!templateId;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [coverImageUrl, setCoverImageUrl] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [isLoadingTemplate, setIsLoadingTemplate] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [name, setName] = useState('未命名模版');
  const [error, setError] = useState<string | null>(null);
  const [streamMessages, setStreamMessages] = useState<TemplateStreamMessage[]>([]);
  const { templates, addTemplate, upsertTemplate, setCurrentTemplate, currentTemplate } = useProjectStore();

  useEffect(() => {
    let cancelled = false;

    async function loadTemplateForEdit() {
      if (!isEditMode || !templateId) {
        return;
      }

      setIsLoadingTemplate(true);
      setError(null);

      try {
        let matched = templates.find((template) => template.id === templateId);
        if (!matched) {
          const remoteTemplates = await fetchTemplates();
          matched = remoteTemplates.find((template) => template.id === templateId);
        }

        if (!matched) {
          if (!cancelled) {
            setError('未找到要编辑的模版');
          }
          return;
        }

        if (cancelled) {
          return;
        }

        setName(matched.name);
        setPrompt(matched.style_prompt);
        setCoverImageUrl(matched.cover_image || '');
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setError('加载模版失败');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingTemplate(false);
        }
      }
    }

    loadTemplateForEdit();

    return () => {
      cancelled = true;
    };
  }, [isEditMode, templateId, templates]);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    const fileListArray = Array.from(fileList);
    setFiles(fileListArray);

    if (fileListArray.length > 0) {
      const firstFile = fileListArray[0];
      const url = URL.createObjectURL(firstFile);
      setCoverImageUrl(url);
    }
  };

  const handleAnalyze = async () => {
    if (files.length === 0) {
      setError('请先上传至少一张参考图片');
      return;
    }

    setError(null);
    setIsAnalyzing(true);
    setPrompt('');
    setStreamMessages([]);

    try {
      await analyzeTemplateStream(files, (message) => {
        setStreamMessages((prev) => [...prev, message]);

        if (message.type === 'chunk' && message.content) {
          setPrompt((prev) => prev + message.content + '\n');
        }

        if (message.type === 'complete' && message.style_prompt) {
          setPrompt(message.style_prompt);
        }
      });
    } catch (err) {
      console.error(err);
      setError('风格分析失败，请检查网络连接或稍后重试');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGeneratePreview = async () => {
    if (!prompt.trim()) {
      setError('请先填写或分析出模板提示词');
      return;
    }

    setError(null);
    setIsGeneratingPreview(true);
    try {
      const response = await generateSlide({
        style_prompt: prompt,
        visual_desc: TEMPLATE_PREVIEW_VISUAL_DESC,
        aspect_ratio: '16:9',
        page_num: 1,
        title: name || TEMPLATE_PREVIEW_TITLE,
        content_text: TEMPLATE_PREVIEW_TEXT,
      });
      setCoverImageUrl(response.image_url);
    } catch (err) {
      console.error(err);
      setError('示例图生成失败，请确认后端绘图接口已启动');
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  const renderStreamMessage = (message: TemplateStreamMessage, index: number) => {
    switch (message.type) {
      case 'start':
        return (
          <div key={index} className="flex items-center gap-2 text-blue-600 p-2 rounded">
            <Wand2 className="w-4 h-4 animate-spin" />
            <span>{message.message}</span>
            {message.file_count && <span className="text-sm">({message.file_count} 个文件)</span>}
          </div>
        );

      case 'progress':
        return (
          <div key={index} className="flex items-center gap-2 text-gray-600 p-2 rounded">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">{message.message}</span>
          </div>
        );

      case 'chunk_start':
        return (
          <div key={index} className="flex items-center gap-2 text-green-600 p-2 rounded">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">{message.message}</span>
          </div>
        );

      case 'complete':
        return (
          <div key={index} className="flex items-center gap-2 text-green-600 p-3 rounded bg-green-100 border border-green-200">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">{message.message}</span>
          </div>
        );

      case 'error':
        return (
          <div key={index} className="flex items-center gap-2 text-red-600 p-3 rounded bg-red-100 border border-red-200">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">{message.message}</span>
          </div>
        );

      default:
        return null;
    }
  };

  const resolveCoverImageForSave = async () => {
    if (!coverImageUrl) {
      return undefined;
    }

    if (coverImageUrl.startsWith('blob:')) {
      const response = await fetch(coverImageUrl);
      const blob = await response.blob();
      return await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });
    }

    return coverImageUrl;
  };

  const handleSave = async () => {
    if (!prompt.trim()) {
      setError('请先分析图片生成风格提示词');
      return;
    }

    setError(null);

    const payload = {
      name,
      style_prompt: prompt,
      cover_image: await resolveCoverImageForSave(),
      vis_settings: {
        primary_color: '#8B0012',
      },
      aspect_ratios: ['16:9', '4:3', '1:1'],
      default_aspect_ratio: '16:9',
    };

    try {
      let saved: Template;

      if (isEditMode && templateId) {
        try {
          saved = await updateTemplate(templateId, payload);
        } catch (err) {
          console.warn('Update template failed, fallback to local record', err);
          saved = { id: templateId, ...payload };
        }
        upsertTemplate(saved);
        if (currentTemplate?.id === saved.id) {
          setCurrentTemplate(saved);
        }
        navigate('/templates');
        return;
      }

      try {
        saved = await saveTemplate(payload);
      } catch (err) {
        console.warn('Save template failed, fallback to local record', err);
        saved = { id: generateId(), ...payload };
      }
      addTemplate(saved);
      setCurrentTemplate(saved);
      navigate('/input');
    } catch (err) {
      console.error(err);
      setError(isEditMode ? '保存模版修改失败' : '保存模版失败');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      <header className="h-16 border-b border-gray-200 flex items-center justify-between px-8">
        <div>
          <h2 className="text-xl font-serif font-bold">
            {isEditMode ? '编辑风格模版' : '新建风格模版 (Style Extraction)'}
          </h2>
          <p className="text-sm text-gray-500">
            {isEditMode ? '修改模版名称、风格提示词和封面图' : '上传 PPT 参考图，调用 VLM 提炼 Style Prompt'}
          </p>
        </div>
        <Button variant="ghost" onClick={() => navigate('/templates')}>
          取消
        </Button>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/2 p-8 bg-gray-50 border-r border-gray-200 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">
              {isEditMode ? 'Template Cover' : 'Reference Image'}
            </h3>
            <input
              type="text"
              className="border border-gray-300 rounded px-2 py-1 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="模版名称"
            />
          </div>

          <div className="flex-1 flex gap-4">
            <div
              className="flex-1 border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center bg-white hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                accept="image/*"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
              />
              <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mb-4">
                <Upload className="w-8 h-8 text-blue-500" />
              </div>
              <p className="text-gray-600 font-medium">
                {isEditMode ? '上传新的模板参考图或封面图' : '拖拽或点击上传 PPT 截图'}
              </p>
              <p className="text-xs text-gray-400 mt-2">
                {isEditMode ? '支持重新分析风格，也可仅替换封面图' : '支持 JPG, PNG (建议上传封面页)'}
              </p>
              {files.length > 0 && (
                <p className="text-xs text-pku-red mt-4">已选择 {files.length} 张图片</p>
              )}
            </div>

            {coverImageUrl && (
              <div className="w-1/2 border-2 border-gray-200 rounded-lg overflow-hidden bg-white">
                <div className="text-xs text-gray-500 text-center py-1 bg-gray-100">封面预览</div>
                <img
                  src={coverImageUrl}
                  alt="封面预览"
                  className="w-full h-full object-cover"
                />
              </div>
            )}
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
            <Button onClick={handleAnalyze} disabled={isAnalyzing || files.length === 0 || isLoadingTemplate}>
              {isAnalyzing ? (
                <span className="flex items-center">
                  <Wand2 className="animate-spin mr-2" /> 正在分析视觉风格...
                </span>
              ) : (
                <span className="flex items-center">
                  <Wand2 className="mr-2" /> {isEditMode ? '重新分析风格' : '开始 AI 分析'}
                </span>
              )}
            </Button>

            <Button
              variant="outline"
              onClick={handleGeneratePreview}
              disabled={isGeneratingPreview || isAnalyzing || !prompt.trim() || isLoadingTemplate}
            >
              {isGeneratingPreview ? (
                <span className="flex items-center">
                  <Loader2 className="animate-spin mr-2 w-4 h-4" /> 正在生成示例图...
                </span>
              ) : (
                <span className="flex items-center">
                  <ImagePlus className="mr-2 w-4 h-4" /> 生成模板示例图
                </span>
              )}
            </Button>
          </div>

          <p className="text-xs text-gray-500 mt-3">
            没有封面图时，建议直接生成一张模板示例图，模板列表会更好辨认。
          </p>

          {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
        </div>

        <div className="w-1/2 p-8 flex flex-col bg-gray-50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">
              {isEditMode ? '模版内容编辑' : '分析进度'}
            </h3>
            {(isAnalyzing || isGeneratingPreview || isLoadingTemplate) && (
              <div className="flex items-center gap-2 text-blue-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">
                  {isLoadingTemplate ? '加载中...' : isGeneratingPreview ? '正在生成示例图...' : '分析中...'}
                </span>
              </div>
            )}
          </div>

          <div className="h-48 overflow-y-auto mb-4 border border-gray-200 rounded-lg bg-white p-4">
            {!isAnalyzing && streamMessages.length === 0 && (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  {isEditMode ? <Pencil className="w-8 h-8 mx-auto mb-2 opacity-50" /> : <Upload className="w-8 h-8 mx-auto mb-2 opacity-50" />}
                  <p className="text-sm">{isEditMode ? '可以直接修改模版名称和提示词' : '上传图片并点击分析'}</p>
                  <p className="text-xs mt-1">
                    {isEditMode ? '如果重新上传参考图，也可以再跑一次风格分析' : '分析过程将实时显示在这里'}
                  </p>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {streamMessages.map((message, index) => renderStreamMessage(message, index))}
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Style Prompt (可编辑)</h3>
              {prompt && (
                <span className="text-xs text-green-600">✓ 可直接保存</span>
              )}
            </div>

            <div className="flex-1 relative">
              <textarea
                className="w-full h-full p-6 bg-gray-900 text-green-400 font-mono text-sm rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="// 等待分析结果... 这里将显示 AI 提取的风格描述指令"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={isAnalyzing || isLoadingTemplate}
              />
              {!prompt && !isAnalyzing && !isLoadingTemplate && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <span className="text-gray-500">请先上传图片并点击分析</span>
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <Button onClick={handleSave} disabled={!prompt.trim() || isAnalyzing || isGeneratingPreview || isLoadingTemplate}>
              {isEditMode ? '保存模版修改' : '保存并使用此模版'} <ArrowRight className="ml-2 w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
