import React, { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, RefreshCcw, Play } from 'lucide-react';
import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { SlideCanvas } from '../components/workspace/SlideCanvas';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { generateSlide, exportPptx, batchGenerateSlides } from '../services/api';
import type { SlideData, BatchGenerateResult } from '../services/types';
import { useProjectStore } from '../store/useProjectStore';

export default function Workspace() {
  const navigate = useNavigate();
  const {
    slides,
    currentSlideId,
    selectSlide,
    updateSlide,
    currentTemplate,
    projectTitle,
  } = useProjectStore();
  const [regenerating, setRegenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const currentSlide = useMemo(() => {
    return slides.find((slide) => slide.id === currentSlideId) || slides[0] || null;
  }, [slides, currentSlideId]);

  // 批量生成所有图片
  const handleBatchGenerate = async () => {
    if (!currentTemplate || slides.length === 0) {
      setError('请先选择模版并生成大纲');
      return;
    }

    setBatchGenerating(true);
    setBatchProgress('准备批量生成...');
    setError(null);

    try {
      // 将所有幻灯片状态设置为生成中
      slides.forEach(slide => {
        updateSlide(slide.id, { status: 'generating' });
      });

      setBatchProgress('正在批量生成图片...');

      const result = await batchGenerateSlides({
        slides: slides.map(slide => ({
          id: slide.id,
          page_num: slide.page_num,
          type: slide.type,
          title: slide.title,
          content_text: slide.content_text,
          visual_desc: slide.visual_desc,
        })),
        style_prompt: currentTemplate.style_prompt,
        max_workers: 3,
        aspect_ratio: '16:9'
      });

      setBatchProgress(`批量生成完成！成功: ${result.successful}/${result.total_slides}`);

      // 更新幻灯片状态和图片URL
      result.results.forEach(slideResult => {
        const slide = slides.find(s => s.id === slideResult.slide_id);
        if (slide) {
          updateSlide(slide.id, {
            image_url: slideResult.image_url,
            status: slideResult.status,
            final_prompt: slideResult.final_prompt
          });
        }
      });

    } catch (err) {
      console.error(err);
      setError('批量生成失败，请确认后端批量生成接口已启动');
      
      // 重置所有幻灯片状态
      slides.forEach(slide => {
        updateSlide(slide.id, { status: 'pending' });
      });
    } finally {
      setBatchGenerating(false);
      setTimeout(() => setBatchProgress(''), 3000);
    }
  };

  // 进入页面后自动批量生成（如果没有图片的话）
  useEffect(() => {
    const hasNoImages = slides.length > 0 && slides.every(slide => !slide.image_url);
    const hasTemplate = !!currentTemplate;
    
    if (hasNoImages && hasTemplate && !batchGenerating) {
      // 延迟1秒后开始批量生成，让用户看到页面
      const timer = setTimeout(() => {
        handleBatchGenerate();
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [slides, currentTemplate]);

  if (!currentSlide) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-pku-light gap-4">
        <p className="text-gray-500">还没有生成大纲，请先返回导入文档。</p>
        <Button onClick={() => navigate('/input')}>去导入内容</Button>
      </div>
    );
  }

  const handleRegenerate = async () => {
    if (!currentTemplate) {
      setError('请先选择模版');
      return;
    }
    setRegenerating(true);
    setError(null);
    try {
      const resp = await generateSlide({
        style_prompt: currentTemplate.style_prompt,
        visual_desc: currentSlide.visual_desc,
        page_num: currentSlide.page_num,
        title: currentSlide.title,
        content_text: currentSlide.content_text,
      });
      updateSlide(currentSlide.id, {
        image_url: resp.image_url,
        final_prompt: resp.final_prompt,
        status: resp.status,
      });
    } catch (err) {
      console.error(err);
      setError('重绘失败，请确认后端绘图接口已启动');
    } finally {
      setRegenerating(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setError(null);
    try {
      const blob = await exportPptx({
        template_id: currentTemplate?.id,
        template_style_prompt: currentTemplate?.style_prompt,
        title: projectTitle,
        slides,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projectTitle || 'AI_PPT_Flow'}.pptx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError('导出失败，请检查后端导出接口。');
    } finally {
      setExporting(false);
    }
  };

  const sidebar = (
    <div className="space-y-4">
      {slides.map((slide) => (
        <Card
          key={slide.id}
          className={`p-2 cursor-pointer transition-all ${slide.id === currentSlide.id ? 'ring-2 ring-pku-red' : 'hover:ring-1 ring-gray-200'}`}
          onClick={() => selectSlide(slide.id)}
        >
          <div className="aspect-video bg-gray-100 rounded overflow-hidden relative">
            {slide.image_url ? (
              <img 
                src={slide.image_url} 
                alt={`第${slide.page_num}页`}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-gray-400">
                {slide.status === 'generating' ? (
                  <div className="flex flex-col items-center gap-1">
                    <div className="w-4 h-4 border-2 border-pku-red border-t-transparent rounded-full animate-spin"></div>
                    <span>生成中</span>
                  </div>
                ) : (
                  <span>待生成</span>
                )}
              </div>
            )}
          </div>
          <div className="mt-2 text-xs text-center font-medium text-gray-600">
            第 {slide.page_num} 页
          </div>
        </Card>
      ))}
    </div>
  );

  const canvas = (
    <div className="w-full flex flex-col items-center gap-6">
      {batchProgress && (
        <div className="w-full max-w-2xl p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm text-blue-700 font-medium">{batchProgress}</span>
          </div>
        </div>
      )}
      
      <SlideCanvas
        imageUrl={currentSlide.image_url}
        isLoading={regenerating && !currentSlide.image_url}
      />
      
      <div className="flex gap-4">
        <Button onClick={handleRegenerate} disabled={regenerating || batchGenerating}>
          <RefreshCcw className="w-4 h-4 mr-2" /> {regenerating ? '正在重绘...' : '重新生成图片'}
        </Button>
        
        <Button 
          onClick={handleBatchGenerate} 
          disabled={batchGenerating || regenerating || !currentTemplate}
          variant="outline"
        >
          <Play className="w-4 h-4 mr-2" /> 
          {batchGenerating ? '批量生成中...' : '批量生成所有图片'}
        </Button>
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );

  const panel = (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-2">风格设定（只读）</h3>
        <textarea
          className="w-full h-28 p-3 text-xs border border-gray-200 rounded bg-gray-50"
          value={currentTemplate?.style_prompt || '未选择模版'}
          readOnly
        />
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-2">画面描述（可编辑）</h3>
        <textarea
          className="w-full h-56 p-3 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-pku-red"
          value={currentSlide.visual_desc}
          onChange={(e) => updateSlide(currentSlide.id, { visual_desc: e.target.value })}
          placeholder="描述这一页幻灯片应该包含什么样的视觉内容和布局..."
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 提示：修改描述后点击"更新并重绘"按钮可以重新生成当前页图片
        </p>
      </section>

      <Button className="w-full" onClick={handleRegenerate} disabled={regenerating}>
        <RefreshCcw className="w-4 h-4 mr-2" /> 更新并重绘
      </Button>
    </div>
  );

  return (
    <WorkspaceLayout
      header={
        <div className="flex justify-between w-full items-center">
          <div>
            <span className="font-serif text-xl font-bold text-pku-red">{projectTitle}</span>
            <p className="text-xs text-gray-500">模版：{currentTemplate?.name || '未选择'}</p>
          </div>
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            <Download className="w-4 h-4 mr-2" /> {exporting ? '导出中...' : '导出 PPTX'}
          </Button>
        </div>
      }
      sidebar={sidebar}
      canvas={canvas}
      panel={panel}
    />
  );
}
