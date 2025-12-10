import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface BackButtonProps {
  className?: string;
  showText?: boolean;
}

export default function BackButton({ className = "", showText = true }: BackButtonProps) {
  const navigate = useNavigate();

  const handleGoBack = () => {
    navigate(-1);
  };

  return (
    <button
      onClick={handleGoBack}
      className={`flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors ${className}`}
      title="返回上一页"
    >
      <ArrowLeft size={20} />
      {showText && <span>返回</span>}
    </button>
  );
}