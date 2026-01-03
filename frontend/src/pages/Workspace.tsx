import React, { useMemo, useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Download, RefreshCcw, Play, Save, Clock } from 'lucide-react';
import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { SlideCanvas } from '../components/workspace/SlideCanvas';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { AspectRatioSelector } from '../components/ui/AspectRatioSelector';
import { generateSlide, exportPptx, batchGenerateSlides, getBatchStatus } from '../services/api';
import type { SlideData, BatchGenerateResult, SlideStatus, CustomDimensions } from '../services/types';
import { useProjectStore } from '../store/useProjectStore';

export default function Workspace() {
  const navigate = useNavigate();
  const location = useLocation<{ autoGenerate?: boolean }>();
  const {
    slides,
    currentSlideId,
    selectSlide,
    updateSlide,
    currentTemplate,
    projectTitle,
    projectId,
    saveCurrentProject,
  } = useProjectStore();
  const [regenerating, setRegenerating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [batchGenerating, setBatchGenerating] = useState(false);
  const [batchProgress, setBatchProgress] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [lastEditTime, setLastEditTime] = useState<number>(Date.now());
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const autoBatchTriggeredRef = useRef(false);
  // 新增比例相关状态
  const [selectedAspectRatio, setSelectedAspectRatio] = useState<string>('16:9');
  const [customDimensions, setCustomDimensions] = useState<CustomDimensions>({
    width: 1920,
    height: 1080,
    aspectRatio: '16:9'
  });

  const currentSlide = useMemo(() => {
    return slides.find((slide) => slide.id === currentSlideId) || slides[0] || null;
  }, [slides, currentSlideId]);

  // 批量生成所有图片
  const handleBatchGenerate = async () => {
    if (batchGenerating) {
      return;
    }

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

      // 使用选中的比例，如果是自定义则使用计算出的比例
      const aspectRatioToUse = selectedAspectRatio === 'custom' 
        ? customDimensions.aspectRatio 
        : selectedAspectRatio;
        
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
        // 不传max_workers，让后端使用智能逻辑：最少10个，最多等于幻灯片数量
        aspect_ratio: aspectRatioToUse
      });

      setBatchProgress(`批量生成完成！成功: ${result.successful}/${result.total_slides}`);

      // 更新幻灯片状态和图片URL
      result.results.forEach(slideResult => {
        const slide = slides.find(s => s.id === slideResult.slide_id);
        if (slide) {
          updateSlide(slide.id, {
            image_url: slideResult.image_url,
            status: slideResult.status as SlideStatus,
            final_prompt: slideResult.final_prompt
          });
        }
      });

      // 批量生成完成后自动保存项目
      try {
        await saveCurrentProject();
        setBatchProgress(prev => prev + ' (项目已自动保存)');
      } catch (err) {
        console.error('自动保存失败:', err);
        setBatchProgress(prev => prev + ' (自动保存失败，请手动保存)');
      }

      // 图片生成完毕后，等待3秒再隐藏进度提示，让用户看到完整结果
      setTimeout(() => setBatchProgress(''), 5000);

    } catch (err) {
      console.error(err);
      setError('批量生成失败，请确认后端批量生成接口已启动');
      
      // 重置所有幻灯片状态
      slides.forEach(slide => {
        updateSlide(slide.id, { status: 'pending' });
      });
    } finally {
      setBatchGenerating(false);
      // 进度提示的隐藏逻辑已在上面处理（图片生成完毕后3秒）
    }
  };

  // 跳转自大纲页时自动批量生成（仅触发一次）
  useEffect(() => {
    const shouldAutoGenerate = location.state?.autoGenerate;
    if (!shouldAutoGenerate || autoBatchTriggeredRef.current) {
      return;
    }

    const hasNoImages = slides.length > 0 && slides.every(slide => !slide.image_url);
    const hasTemplate = !!currentTemplate;

    if (!hasNoImages || !hasTemplate || batchGenerating) {
      return;
    }

    autoBatchTriggeredRef.current = true;
    const timer = setTimeout(() => {
      handleBatchGenerate();
    }, 1000);

    return () => clearTimeout(timer);
  }, [location.state, slides, currentTemplate, batchGenerating]);

  // 自动保存功能：编辑后5分钟自动保存
  useEffect(() => {
    const setupAutoSave = () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }

      autoSaveTimerRef.current = setTimeout(async () => {
        try {
          await saveCurrentProject();
          console.log('项目已自动保存');
        } catch (err) {
          console.error('自动保存失败:', err);
        }
      }, 5 * 60 * 1000); // 5分钟
    };

    // 监听编辑操作
    const handleEdit = () => {
      setLastEditTime(Date.now());
      setupAutoSave();
    };

    // 监听幻灯片内容变化
    if (slides.length > 0) {
      setupAutoSave();
    }

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [slides, currentTemplate, saveCurrentProject]);

  // 页面关闭前提醒保存
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      const timeSinceLastEdit = Date.now() - lastEditTime;
      const hasUnsavedChanges = timeSinceLastEdit < 5 * 60 * 1000; // 5分钟内有编辑

      if (hasUnsavedChanges && slides.length > 0) {
        e.preventDefault();
        e.returnValue = '您有未保存的更改，确定要离开吗？';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [lastEditTime, slides]);

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
      // 使用选中的比例，如果是自定义则使用计算出的比例
      const aspectRatioToUse = selectedAspectRatio === 'custom' 
        ? customDimensions.aspectRatio 
        : selectedAspectRatio;
        
      const resp = await generateSlide({
        style_prompt: currentTemplate.style_prompt,
        visual_desc: currentSlide.visual_desc,
        aspect_ratio: aspectRatioToUse,
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
      const projectData = {
        template_id: currentTemplate?.id,
        template_style_prompt: currentTemplate?.style_prompt,
        title: projectTitle,
        slides,
      };
      
      const blob = await exportPptx(projectData, `${projectTitle || 'AI_PPT_Flow'}.pptx`);
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

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage('');
    setError(null);
    
    try {
      await saveCurrentProject();
      setSaveMessage('项目已保存');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error(err);
      setError('保存失败，请检查网络连接');
    } finally {
      setSaving(false);
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
      
      {/* 提示信息 */}
      <div className="flex flex-col gap-2">
        {saveMessage && (
          <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-700">{saveMessage}</p>
          </div>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    </div>
  );

  const panel = (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-2">模版设定（只读）</h3>
        <textarea
          className="w-full h-28 p-3 text-xs border border-gray-200 rounded bg-gray-50"
          value={currentTemplate?.style_prompt || '未选择模版'}
          readOnly
        />
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-3">大纲内容（可编辑）</h3>
        <div className="space-y-3">
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">幻灯片标题</div>
            <input
              className="w-full p-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-pku-red"
              value={currentSlide.title}
              onChange={(e) => {
                updateSlide(currentSlide.id, { title: e.target.value });
                setLastEditTime(Date.now());
              }}
              placeholder="例如：项目亮点 / 行业趋势"
            />
          </div>
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">正文内容</div>
            <textarea
              className="w-full h-32 p-3 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-pku-red"
              value={currentSlide.content_text}
              onChange={(e) => {
                updateSlide(currentSlide.id, { content_text: e.target.value });
                setLastEditTime(Date.now());
              }}
              placeholder="写下该页需要呈现的要点、数据或文案..."
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          ✏️ 这些文本会被用于提示词的标题与内嵌正文部分，修改后记得重新生成图片。
        </p>
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-2">画面描述（可编辑）</h3>
        <textarea
          className="w-full h-40 p-3 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-pku-red"
          value={currentSlide.visual_desc}
          onChange={(e) => {
            updateSlide(currentSlide.id, { visual_desc: e.target.value });
            setLastEditTime(Date.now()); // 标记为已编辑
          }}
          placeholder="描述这一页幻灯片应该包含什么样的视觉内容和布局..."
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 提示：修改描述后点击"更新并重绘"按钮可以重新生成当前页图片
        </p>
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-700 mb-2">生成提示词（参考）</h3>
        <textarea
          className="w-full h-40 p-3 text-xs border border-gray-200 rounded bg-gray-50"
          value={currentSlide.final_prompt || ''}
          readOnly
          placeholder="完成单页重绘或批量生成后，这里会展示完整提示词，方便对照检查"
        />
        <p className="text-xs text-gray-500 mt-2">
          🔍 提示词由模版风格、画面描述、标题/正文以及尺寸约束共同组成，用于驱动 VLM 绘制最终图片。
        </p>
      </section>

      <section>
        <AspectRatioSelector
          selectedRatio={selectedAspectRatio}
          onRatioChange={setSelectedAspectRatio}
          onCustomDimensionsChange={setCustomDimensions}
          disabled={batchGenerating || regenerating}
        />
        <p className="text-xs text-gray-500 mt-2">
          💡 提示：选择合适的比例会影响图片生成的最终尺寸和布局
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
          <div className="flex items-center gap-8">
            <div>
              <span className="font-serif text-xl font-bold text-pku-red">{projectTitle}</span>
            </div>
            
            <div className="flex items-center gap-6 text-sm">
              <div className="text-xs text-gray-500">
                模版：{currentTemplate?.name || '未选择'}
              </div>
              
              {projectId && (
                <>
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    已保存
                  </div>
                  
                  <div className="text-xs text-gray-400">
                    项目ID: {projectId.slice(0, 8)}...
                  </div>
                </>
              )}
            </div>
          </div>
          
          <div className="flex gap-3">
            <Button 
              variant="outline" 
              onClick={handleSave} 
              disabled={saving || batchGenerating}
            >
              <Save className="w-4 h-4 mr-2" /> 
              {saving ? '保存中...' : '保存项目'}
            </Button>
            
            <Button 
              variant="outline" 
              onClick={() => navigate('/history')}
              className="text-gray-600 hover:text-pku-red"
            >
              <Clock className="w-4 h-4 mr-2" /> 
              我的项目
            </Button>
            
            <Button variant="outline" onClick={handleExport} disabled={exporting}>
              <Download className="w-4 h-4 mr-2" /> {exporting ? '导出中...' : '导出 PPTX'}
            </Button>
          </div>
        </div>
      }
      sidebar={sidebar}
      canvas={canvas}
      panel={panel}
    />
  );
}
