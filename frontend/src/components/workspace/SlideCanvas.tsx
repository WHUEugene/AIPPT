import React from 'react';

interface SlideCanvasProps {
  imageUrl?: string;
  isLoading?: boolean;
}

export const SlideCanvas: React.FC<SlideCanvasProps> = ({ imageUrl, isLoading }) => {
  return (
    <div className="w-full max-w-5xl aspect-video bg-white shadow-float relative group transition-transform duration-300">
      {imageUrl ? (
        <img src={imageUrl} alt="Slide Background" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-gray-50 text-gray-300">
          {isLoading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 border-4 border-pku-red border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm font-medium text-pku-gray">AI 正在绘图...</span>
            </div>
          ) : (
            <span>等待生成...</span>
          )}
        </div>
      )}

      <div className="absolute inset-0 pointer-events-none border border-black/5 rounded" />
    </div>
  );
};
