import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Sparkles, Wand2, CheckCircle, AlertCircle, ArrowRight } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { generateOutline, generateOutlineStream, type StreamMessage } from '../services/api';
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

  const handleGenerate = async () => {
    if (!text) return;
    
    setIsGenerating(true);
    setError(null);
    setStreamMessages([]);
    const tempSlides: SlideData[] = [];
    setGeneratedSlides([]);
    
    try {
      await generateOutlineStream(text, pageCount, currentTemplate?.id, (message) => {
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

          <div className="mt-6 flex gap-3">
            <Button 
              className="flex-1 py-3 text-lg" 
              onClick={handleGenerate} 
              disabled={!text || isGenerating}
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
                navigate('/workspace');
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
          <div className="flex-1 overflow-y-auto">
            {!isGenerating && streamMessages.length === 0 && (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>输入内容并点击"AI 生成大纲"</p>
                  <p className="text-sm mt-2">生成过程将实时显示在这里</p>
                </div>
              </div>
            )}

            {streamMessages.map((message, index) => renderMessage(message, index))}
          </div>

          </div>
      </div>
    </div>
  );
}
