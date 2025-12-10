import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, History } from 'lucide-react';
import { Card } from '../components/ui/Card';

export default function Welcome() {
  const navigate = useNavigate();

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-pku-light relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-2 bg-pku-red" />

      <div className="z-10 text-center mb-12">
            <h1 className="text-6xl font-serif font-bold text-pku-black mb-4 tracking-tight">AI-PPT Flow</h1>
            <p className="text-xl text-pku-gray font-light tracking-wide">从文档到演示，仅需片刻雕琢</p>
      </div>

      <div className="flex flex-wrap gap-8 z-10">
        <Card
          className="w-64 h-72 flex flex-col items-center justify-center cursor-pointer hover:-translate-y-2 transition-transform duration-300 group"
          onClick={() => navigate('/templates')}
        >
          <div className="w-16 h-16 rounded-full bg-pku-red/10 flex items-center justify-center mb-6 group-hover:bg-pku-red transition-colors">
            <PlusCircle className="w-8 h-8 text-pku-red group-hover:text-white" />
          </div>
          <h3 className="text-xl font-serif mb-2">开始新项目</h3>
          <p className="text-sm text-gray-500 text-center px-4">选择模版，导入文档，<br />一键生成 PPT</p>
        </Card>

        <Card className="w-64 h-72 flex flex-col items-center justify-center opacity-60">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-6">
            <History className="w-8 h-8 text-gray-600" />
          </div>
          <h3 className="text-xl font-serif mb-2">历史记录</h3>
          <p className="text-sm text-gray-500 text-center px-4">下一步将同步接入<br /> 本地历史项目</p>
        </Card>
      </div>

      <div className="absolute bottom-8 text-xs text-gray-400 font-mono">v1.0.0 | Powered by LLM & VLM</div>
    </div>
  );
}
