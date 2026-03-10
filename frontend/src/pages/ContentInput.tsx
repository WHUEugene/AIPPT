import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText,
  Sparkles,
  Wand2,
  CheckCircle,
  AlertCircle,
  ArrowRight,
  Trash2,
  Image,
  AlignLeft,
  Type,
  ListOrdered
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { generateOutlineStream, type StreamMessage } from '../services/api';
import { useProjectStore } from '../store/useProjectStore';
import type { SlideData } from '../services/types';
import { generateId } from '../utils/uuid';

export default function ContentInput() {
  const navigate = useNavigate();
  const { currentTemplate, setSlides, setProjectTitle } = useProjectStore();
  const [pageCount, setPageCount] = useState(10);
  const [text, setText] = useState('');
  const [title, setTitle] = useState('未命名项目');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamMessages, setStreamMessages] = useState<StreamMessage[]>([]);
  const [generatedSlides, setGeneratedSlides] = useState<SlideData[]>([]);
  const [revisionNotes, setRevisionNotes] = useState('');

  const handleGenerate = async () => {
    const baseContent = text.trim();
    const revisionContent = revisionNotes.trim();
    const previousSlides = generatedSlides.length
      ? [...generatedSlides].sort((a, b) => a.page_num - b.page_num)
      : [];

    const outlineContext = previousSlides.length
      ? previousSlides
          .map((slide) => {
            const typeLabel = slide.type === 'cover' ? '封面页' : slide.type === 'ending' ? '结束页' : '内容页';
            const visualText = slide.visual_desc?.trim() ? slide.visual_desc : '（暂无图像描述）';
            const contentText = slide.content_text?.trim() ? slide.content_text : '（暂无正文内容）';
            return [
              `第${slide.page_num}页（${typeLabel}）`,
              `标题：${slide.title || '未命名'}`,
              `文字要点：${contentText}`,
              `图像描述：${visualText}`
            ].join('\n');
          })
          .join('\n\n')
      : '';

    const promptSections: string[] = [];
    if (baseContent) {
      promptSections.push(`【原始文档】\n${baseContent}`);
    }
    if (outlineContext) {
      promptSections.push(`【上一版大纲】\n${outlineContext}`);
    }
    if (revisionContent) {
      promptSections.push(`【修改意见】\n${revisionContent}`);
    }

    const promptInput = promptSections.join('\n\n');

    if (!promptInput) return;

    setIsGenerating(true);
    setError(null);
    setStreamMessages([]);
    const tempSlides: SlideData[] = [];
    setGeneratedSlides([]);
    
    try {
      await generateOutlineStream(promptInput, pageCount, currentTemplate?.id, (message) => {
        setStreamMessages(prev => [...prev, message]);
        
        if (message.type === 'slide' && message.slide) {
          const newSlide: SlideData = {
            id: generateId(),
            page_num: message.slide!.page_num,
            type: message.slide!.type as any,
            title: message.slide!.title,
            content_text: message.slide!.content_text,
            visual_desc: message.slide!.visual_desc,
            status: 'pending' as any
          };
          tempSlides.push(newSlide);
          setGeneratedSlides(prev => [...prev, newSlide]);
        }
      });
      
      // Generation completed successfully
      setSlides(tempSlides);
      setProjectTitle(title);
      
    } catch (err) {
      console.error(err);
      setError('生成大纲失败，请检查网络连接或稍后重试。');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSlideFieldChange = (
    slideId: string,
    field: keyof Pick<SlideData, 'title' | 'content_text' | 'visual_desc'>,
    value: string
  ) => {
    setGeneratedSlides(prev => {
      const updated = prev.map(slide =>
        slide.id === slideId ? { ...slide, [field]: value } : slide
      );
      setSlides(updated);
      return updated;
    });
  };

  const handleDeleteSlide = (slideId: string) => {
    setGeneratedSlides(prev => {
      const filtered = prev
        .filter(slide => slide.id !== slideId)
        .map((slide, index) => ({ ...slide, page_num: index + 1 }));
      setSlides(filtered);
      return filtered;
    });
  };

  const sortedSlides = useMemo(
    () => [...generatedSlides].sort((a, b) => a.page_num - b.page_num),
    [generatedSlides]
  );

  const renderMessage = (message: StreamMessage, index: number) => {
    switch (message.type) {
      case 'start':
        return (
          <div key={index} className="flex items-center gap-2 text-blue-600 p-2 rounded">
            <Wand2 className="w-4 h-4 animate-spin" />
            <span>{message.message}</span>
          </div>
        );
      
      case 'progress':
        return (
          <div key={index} className="flex items-center gap-2 text-gray-600 p-2 rounded">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-sm">{message.message}</span>
          </div>
        );
      
      case 'slide':
        return (
          <div key={index} className="border border-green-200 bg-green-50 rounded-lg p-3 mb-2">
            <div className="flex items-center gap-2 text-green-700 mb-2">
              <CheckCircle className="w-4 h-4" />
              <span className="font-medium">第 {message.slide?.page_num} 页: {message.slide?.title}</span>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2">{message.slide?.content_text}</p>
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

  return (
    <div className="h-screen bg-white flex flex-col">
      <header className="h-16 border-b border-gray-200 flex items-center justify-between px-8">
        <div>
          <h2 className="text-xl font-serif font-bold">智能大纲生成</h2>
          <p className="text-sm text-gray-500">输入文档内容，AI流式生成结构化PPT大纲</p>
        </div>
        <div className="text-sm text-gray-500">
          {generatedSlides.length > 0 && (
            <span>已生成 {generatedSlides.length} 页大纲</span>
          )}
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧输入区 */}
        <div className="w-1/2 p-8 bg-gray-50 border-r border-gray-200 flex flex-col">
          <div className="mb-6">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">内容输入</h3>
            
            <div className="flex flex-col gap-2 mb-4">
              <label className="text-sm font-medium text-gray-700">项目名称</label>
              <input
                className="border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="输入项目名称"
              />
            </div>

            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm font-medium text-gray-700">预计页数:</span>
              <input
                type="range"
                min={1}
                max={50}
                value={pageCount}
                onChange={(e) => setPageCount(parseInt(e.target.value, 10))}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <span className="font-mono font-bold text-blue-500 text-lg w-10">{pageCount}</span>
            </div>

            {currentTemplate && (
              <div className="text-sm text-gray-600 bg-blue-50 p-2 rounded">
                使用模板: <span className="font-medium">{currentTemplate.name}</span>
              </div>
            )}
          </div>

          <div className="flex-1 flex flex-col">
            <label className="text-sm font-bold text-gray-700 flex items-center mb-2">
              <FileText className="w-4 h-4 mr-2" />
              文档内容
            </label>
            <textarea
              className="flex-1 w-full p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm leading-relaxed"
              placeholder="在此处粘贴你的论文摘要、会议记录或大纲..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={isGenerating}
            />
          </div>

          <div className="mt-4">
            <label className="text-sm font-bold text-gray-700 flex items-center mb-2">
              <ListOrdered className="w-4 h-4 mr-2" />
              修改意见（可选）
            </label>
            <textarea
              className="w-full min-h-[120px] p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm leading-relaxed"
              placeholder="针对已生成的大纲补充要求、提出修改意见或强调重点，LLM 会结合这些说明重新生成。"
              value={revisionNotes}
              onChange={(e) => setRevisionNotes(e.target.value)}
              disabled={isGenerating}
            />
            <p className="text-xs text-gray-500 mt-1">可在初稿生成后继续输入优化建议，再次点击生成即可获得更新版本。</p>
          </div>

          <div className="mt-6 flex gap-3">
            <Button 
              className="flex-1 py-3 text-lg" 
              onClick={handleGenerate} 
              disabled={(text.trim() === '' && revisionNotes.trim() === '') || isGenerating}
            >
              {isGenerating ? (
                <span className="flex items-center">
                  <Wand2 className="animate-spin mr-2" /> 正在生成大纲...
                </span>
              ) : (
                <span className="flex items-center">
                  <Sparkles className="mr-2" /> AI 生成大纲
                </span>
              )}
            </Button>
            
            <Button 
              onClick={() => {
                console.log('点击下一步，状态:', { isGenerating, generatedSlidesLength: generatedSlides.length });
                navigate('/workspace', { state: { autoGenerate: true } });
              }} 
              className={`px-6 py-3 text-lg ${
                (isGenerating || generatedSlides.length === 0)
                  ? 'bg-gray-300 cursor-not-allowed' 
                  : 'bg-green-600 hover:bg-green-700'
              }`}
              disabled={isGenerating || generatedSlides.length === 0}
            >
              {isGenerating ? (
                <span className="flex items-center">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  生成中...
                </span>
              ) : generatedSlides.length === 0 ? (
                <span className="flex items-center">
                  下一步 <ArrowRight className="ml-2 w-4 h-4" />
                </span>
              ) : (
                <span className="flex items-center">
                  下一步 <ArrowRight className="ml-2 w-4 h-4" />
                </span>
              )}
            </Button>
          </div>
          
          {error && (
            <div className="mt-2 text-sm text-red-500 bg-red-50 p-2 rounded">
              {error}
            </div>
          )}
        </div>

        {/* 右侧流式输出区 */}
        <div className="w-1/2 p-8 flex flex-col bg-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">生成结果</h3>
            {isGenerating && (
              <div className="flex items-center gap-2 text-blue-500">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-sm">生成中...</span>
              </div>
            )}
          </div>
          
          {/* 滚动区域 */}
          <div className="flex-1 overflow-y-auto space-y-6 pr-2">
            <div>
              {!isGenerating && streamMessages.length === 0 && (
                <div className="flex items-center justify-center h-48 text-gray-400 border border-dashed border-gray-200 rounded-lg">
                  <div className="text-center px-6">
                    <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>输入内容并点击"AI 生成大纲"</p>
                    <p className="text-sm mt-2">生成过程将实时显示在这里</p>
                  </div>
                </div>
              )}

              {streamMessages.length > 0 && (
                <div className="space-y-2">
                  {streamMessages.map((message, index) => renderMessage(message, index))}
                </div>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="text-base font-semibold text-gray-800 flex items-center gap-2">
                    <AlignLeft className="w-4 h-4 text-blue-500" /> 页面大纲详情
                  </h4>
                  <p className="text-xs text-gray-500">查看每一页计划输出的文字与图像描述，可直接编辑或删除。</p>
                </div>
                {generatedSlides.length > 0 && (
                  <span className="text-xs text-gray-500">共 {generatedSlides.length} 页</span>
                )}
              </div>

              {sortedSlides.length === 0 ? (
                <div className="border border-dashed border-gray-200 rounded-lg p-6 text-center text-gray-400">
                  尚未生成可编辑的大纲，生成后可在此修改每页内容。
                </div>
              ) : (
                <div className="space-y-4">
                  {sortedSlides.map((slide) => (
                    <div key={slide.id} className="border border-gray-200 rounded-xl p-4 shadow-sm">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold text-blue-500 uppercase tracking-wide">第 {slide.page_num} 页 · {slide.type === 'cover' ? '封面' : slide.type === 'ending' ? '结束' : '内容'}</p>
                          <input
                            className="w-full mt-1 text-lg font-semibold text-gray-900 bg-transparent border-b border-transparent focus:border-blue-400 focus:outline-none"
                            value={slide.title}
                            onChange={(e) => handleSlideFieldChange(slide.id, 'title', e.target.value)}
                          />
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500"
                          onClick={() => handleDeleteSlide(slide.id)}
                        >
                          <Trash2 className="w-4 h-4 mr-1" /> 删除
                        </Button>
                      </div>

                      <div className="mt-4 space-y-4">
                        <div>
                          <label className="text-xs font-semibold text-gray-500 uppercase flex items-center gap-2 mb-2">
                            <Type className="w-3.5 h-3.5" /> 文字内容
                          </label>
                          <textarea
                            className="w-full p-3 border border-gray-200 rounded-lg text-sm text-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={3}
                            value={slide.content_text}
                            onChange={(e) => handleSlideFieldChange(slide.id, 'content_text', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="text-xs font-semibold text-gray-500 uppercase flex items-center gap-2 mb-2">
                            <Image className="w-3.5 h-3.5" /> 图像描述
                          </label>
                          <textarea
                            className="w-full p-3 border border-gray-200 rounded-lg text-sm text-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={3}
                            value={slide.visual_desc}
                            onChange={(e) => handleSlideFieldChange(slide.id, 'visual_desc', e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
