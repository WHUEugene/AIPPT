import React, { useState, useEffect } from 'react';
import { AspectRatioOption, CustomDimensions } from '../../services/types';

interface AspectRatioSelectorProps {
  selectedRatio: string;
  onRatioChange: (ratio: string) => void;
  onCustomDimensionsChange?: (dimensions: CustomDimensions) => void;
  className?: string;
  disabled?: boolean;
}

export const AspectRatioSelector: React.FC<AspectRatioSelectorProps> = ({
  selectedRatio,
  onRatioChange,
  onCustomDimensionsChange,
  className = '',
  disabled = false
}) => {
  const [customWidth, setCustomWidth] = useState<number>(1920);
  const [customHeight, setCustomHeight] = useState<number>(1080);
  const [showCustomInputs, setShowCustomInputs] = useState(false);

  // 预定义的比例选项
  const aspectRatioOptions: AspectRatioOption[] = [
    {
      value: "16:9",
      label: "16:9 (1920×1080) - 标准宽屏",
      description: "适用于大多数现代显示器和投影仪"
    },
    {
      value: "4:3",
      label: "4:3 (1024×768) - 传统投影",
      description: "适用于传统投影仪和老式显示器"
    },
    {
      value: "1:1",
      label: "1:1 (1080×1080) - 正方形",
      description: "适用于社交媒体和移动端显示"
    },
    {
      value: "9:16",
      label: "9:16 (1080×1920) - 手机竖屏",
      description: "适用于手机竖屏显示和短视频"
    },
    {
      value: "3:2",
      label: "3:2 (1800×1200) - 摄影比例",
      description: "适用于摄影作品展示"
    },
    {
      value: "21:9",
      label: "21:9 (2560×1080) - 超宽屏",
      description: "适用于超宽屏显示器和影院效果"
    },
    {
      value: "custom",
      label: "自定义尺寸",
      description: "输入自定义的宽高比例"
    }
  ];

  // 当选择自定义比例时，计算当前选择比例对应的尺寸
  useEffect(() => {
    if (selectedRatio === 'custom') {
      setShowCustomInputs(true);
    } else {
      setShowCustomInputs(false);
      // 根据选中的比例设置默认尺寸
      const option = aspectRatioOptions.find(opt => opt.value === selectedRatio);
      if (option) {
        const dimensions = getDimensionsForRatio(selectedRatio);
        setCustomWidth(dimensions.width);
        setCustomHeight(dimensions.height);
      }
    }
  }, [selectedRatio]);

  const getDimensionsForRatio = (ratio: string) => {
    const standardDimensions: Record<string, { width: number; height: number }> = {
      "16:9": { width: 1920, height: 1080 },
      "4:3": { width: 1024, height: 768 },
      "1:1": { width: 1080, height: 1080 },
      "9:16": { width: 1080, height: 1920 },
      "3:2": { width: 1800, height: 1200 },
      "21:9": { width: 2560, height: 1080 }
    };
    
    return standardDimensions[ratio] || { width: 1920, height: 1080 };
  };

  const handleRatioSelect = (ratio: string) => {
    onRatioChange(ratio);
  };

  const handleCustomWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value) || 1920;
    setCustomWidth(value);
    
    if (showCustomInputs && customHeight > 0) {
      const gcd = getGCD(value, customHeight);
      const aspectRatio = `${value / gcd}:${customHeight / gcd}`;
      
      if (onCustomDimensionsChange) {
        onCustomDimensionsChange({
          width: value,
          height: customHeight,
          aspectRatio
        });
      }
    }
  };

  const handleCustomHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value) || 1080;
    setCustomHeight(value);
    
    if (showCustomInputs && customWidth > 0) {
      const gcd = getGCD(customWidth, value);
      const aspectRatio = `${customWidth / gcd}:${value / gcd}`;
      
      if (onCustomDimensionsChange) {
        onCustomDimensionsChange({
          width: customWidth,
          height: value,
          aspectRatio
        });
      }
    }
  };

  // 计算最大公约数，用于简化比例
  const getGCD = (a: number, b: number): number => {
    return b === 0 ? a : getGCD(b, a % b);
  };

  const getCurrentAspectRatioDisplay = () => {
    if (showCustomInputs && customWidth > 0 && customHeight > 0) {
      const gcd = getGCD(customWidth, customHeight);
      return `${customWidth / gcd}:${customHeight / gcd}`;
    }
    return selectedRatio;
  };

  const getCurrentDescription = () => {
    if (showCustomInputs) {
      return `自定义尺寸 ${customWidth}×${customHeight} (比例 ${getCurrentAspectRatioDisplay()})`;
    }
    
    const option = aspectRatioOptions.find(opt => opt.value === selectedRatio);
    return option?.description || '';
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          幻灯片比例
        </label>
        
        <select
          value={selectedRatio}
          onChange={(e) => handleRatioSelect(e.target.value)}
          disabled={disabled}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-pku-red focus:border-pku-red disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {aspectRatioOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        
        <p className="mt-1 text-xs text-gray-500">
          {getCurrentDescription()}
        </p>
      </div>

      {/* 自定义尺寸输入 */}
      {showCustomInputs && (
        <div className="space-y-3 p-4 bg-gray-50 rounded-md border border-gray-200">
          <div className="text-sm font-medium text-gray-700">自定义尺寸</div>
          
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="block text-xs text-gray-600 mb-1">宽度 (像素)</label>
              <input
                type="number"
                min="100"
                max="4096"
                value={customWidth}
                onChange={handleCustomWidthChange}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-pku-red focus:border-pku-red disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="1920"
              />
            </div>
            
            <div className="flex items-center text-gray-500 mt-6">
              <span>×</span>
            </div>
            
            <div className="flex-1">
              <label className="block text-xs text-gray-600 mb-1">高度 (像素)</label>
              <input
                type="number"
                min="100"
                max="4096"
                value={customHeight}
                onChange={handleCustomHeightChange}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-1 focus:ring-pku-red focus:border-pku-red disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="1080"
              />
            </div>
          </div>
          
          <div className="text-xs text-gray-500">
            当前比例: {getCurrentAspectRatioDisplay()}
            <br />
            建议: 宽度1920-2560像素，高度不超过4096像素
          </div>
        </div>
      )}
    </div>
  );
};