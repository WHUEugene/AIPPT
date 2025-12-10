import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { generateOutline } from '../services/api';
import { useProjectStore } from '../store/useProjectStore';

export default function ContentInput() {
  const navigate = useNavigate();
  const { currentTemplate, setSlides, setProjectTitle } = useProjectStore();
  const [pageCount, setPageCount] = useState(8);
  const [text, setText] = useState('');
  const [title, setTitle] = useState('未命名项目');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!text) return;
    setLoading(true);
    setError(null);
    try {
      const response = await generateOutline(text, pageCount, currentTemplate?.id);
      setSlides(response.slides);
      setProjectTitle(title);
      navigate('/workspace');
    } catch (err) {
      console.error(err);
      setError('生成大纲失败，请检查后端是否已启动。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pku-light flex items-center justify-center p-4 md:p-8">
      <div className="w-full max-w-5xl bg-white rounded-xl shadow-xl overflow-hidden flex flex-col h-[85vh]">
        <div className="h-16 bg-pku-red px-8 flex items-center justify-between shrink-0">
          <h2 className="text-white font-serif text-xl">导入内容</h2>
          <span className="text-white/80 text-sm">Step 2 / 4</span>
        </div>

        <div className="flex-1 flex flex-col p-8 gap-4 overflow-hidden">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">项目名称</label>
            <input
              className="border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-pku-red focus:border-transparent"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <label className="text-sm font-bold text-gray-700 flex items-center">
            <FileText className="w-4 h-4 mr-2" /> 粘贴文档内容 / Markdown
          </label>
          <textarea
            className="flex-1 w-full p-4 border border-gray-200 rounded-lg resize-none focus:ring-2 focus:ring-pku-red focus:border-transparent outline-none text-base leading-relaxed"
            placeholder="在此处粘贴你的论文摘要、会议记录或大纲..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="mt-2 flex flex-col md:flex-row items-start md:items-center justify-between border-t border-gray-100 pt-4 gap-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-700">预计页数:</span>
              <input
                type="range"
                min={5}
                max={20}
                value={pageCount}
                onChange={(e) => setPageCount(parseInt(e.target.value, 10))}
                className="w-48 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-pku-red"
              />
              <span className="font-mono font-bold text-pku-red text-lg w-10">{pageCount}</span>
            </div>

            <Button size="lg" onClick={handleGenerate} disabled={!text || loading}>
              <Sparkles className="w-5 h-5 mr-2" />
              {loading ? 'LLM 正在思考...' : 'AI 生成大纲'}
            </Button>
          </div>
          {error && <span className="text-sm text-red-500">{error}</span>}
        </div>
      </div>
    </div>
  );
}
