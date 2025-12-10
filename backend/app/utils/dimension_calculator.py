"""
尺寸和比例计算工具模块
用于处理幻灯片的各种比例和尺寸需求
"""

from typing import Dict, Tuple


class DimensionCalculator:
    """尺寸计算器"""
    
    # 预定义的标准比例配置
    STANDARD_ASPECT_RATIOS = {
        "16:9": {
            "width": 1920,
            "height": 1080,
            "name": "16:9 (1920×1080)",
            "description": "标准宽屏"
        },
        "4:3": {
            "width": 1024,
            "height": 768,
            "name": "4:3 (1024×768)",
            "description": "传统投影仪"
        },
        "1:1": {
            "width": 1080,
            "height": 1080,
            "name": "1:1 (1080×1080)",
            "description": "正方形"
        },
        "9:16": {
            "width": 1080,
            "height": 1920,
            "name": "9:16 (1080×1920)",
            "description": "手机竖屏"
        },
        "3:2": {
            "width": 1800,
            "height": 1200,
            "name": "3:2 (1800×1200)",
            "description": "摄影比例"
        },
        "21:9": {
            "width": 2560,
            "height": 1080,
            "name": "21:9 (2560×1080)",
            "description": "超宽屏"
        }
    }
    
    @classmethod
    def calculate_dimensions(cls, aspect_ratio: str, base_width: int = 1920) -> Tuple[int, int]:
        """
        根据比例计算实际尺寸
        
        Args:
            aspect_ratio: 比例字符串，如 "16:9"
            base_width: 基础宽度，默认1920
            
        Returns:
            (width, height): 计算得到的尺寸
        """
        # 如果是标准比例，直接返回预定义尺寸
        if aspect_ratio in cls.STANDARD_ASPECT_RATIOS:
            config = cls.STANDARD_ASPECT_RATIOS[aspect_ratio]
            return config["width"], config["height"]
        
        # 如果是自定义比例，进行计算
        try:
            width_str, height_str = aspect_ratio.split(":")
            width_ratio = int(width_str)
            height_ratio = int(height_str)
            
            # 计算实际高度
            actual_height = int(base_width * height_ratio / width_ratio)
            
            return base_width, actual_height
            
        except (ValueError, ZeroDivisionError):
            # 如果解析失败，返回默认16:9比例
            return 1920, 1080
    
    @classmethod
    def get_aspect_ratio_info(cls, aspect_ratio: str) -> Dict:
        """
        获取比例的详细信息
        
        Args:
            aspect_ratio: 比例字符串
            
        Returns:
            包含比例信息的字典
        """
        if aspect_ratio in cls.STANDARD_ASPECT_RATIOS:
            return cls.STANDARD_ASPECT_RATIOS[aspect_ratio].copy()
        
        # 自定义比例
        try:
            width_str, height_str = aspect_ratio.split(":")
            width_ratio = int(width_str)
            height_ratio = int(height_str)
            
            width, height = cls.calculate_dimensions(aspect_ratio)
            
            return {
                "width": width,
                "height": height,
                "name": f"自定义 ({aspect_ratio})",
                "description": f"自定义比例 {width_ratio}:{height_ratio}"
            }
        except (ValueError, ZeroDivisionError):
            # 错误情况返回默认配置
            return cls.STANDARD_ASPECT_RATIOS["16:9"].copy()
    
    @classmethod
    def get_available_ratios(cls) -> Dict[str, Dict]:
        """
        获取所有可用的比例选项
        
        Returns:
            包含所有比例选项的字典
        """
        return cls.STANDARD_ASPECT_RATIOS.copy()
    
    @classmethod
    def validate_aspect_ratio(cls, aspect_ratio: str) -> bool:
        """
        验证比例格式是否正确
        
        Args:
            aspect_ratio: 比例字符串
            
        Returns:
            是否为有效比例
        """
        if aspect_ratio in cls.STANDARD_ASPECT_RATIOS:
            return True
        
        try:
            parts = aspect_ratio.split(":")
            if len(parts) != 2:
                return False
            
            width_ratio = int(parts[0])
            height_ratio = int(parts[1])
            
            # 比例值必须为正数
            return width_ratio > 0 and height_ratio > 0
            
        except (ValueError, IndexError):
            return False
    
    @classmethod
    def get_optimal_base_width(cls, aspect_ratio: str) -> int:
        """
        根据比例选择最优的基础宽度
        
        Args:
            aspect_ratio: 比例字符串
            
        Returns:
            推荐的基础宽度
        """
        if aspect_ratio in cls.STANDARD_ASPECT_RATIOS:
            return cls.STANDARD_ASPECT_RATIOS[aspect_ratio]["width"]
        
        # 对于自定义比例，根据长宽比选择合适的基准宽度
        try:
            width_str, height_str = aspect_ratio.split(":")
            width_ratio = int(width_str)
            height_ratio = int(height_str)
            
            ratio_value = width_ratio / height_ratio
            
            if ratio_value >= 2.0:  # 超宽屏
                return 2560
            elif ratio_value >= 1.5:  # 宽屏
                return 1920
            elif ratio_value >= 1.0:  # 接近正方形
                return 1080
            else:  # 竖屏
                return 1080
                
        except (ValueError, ZeroDivisionError):
            return 1920


def calculate_dimensions(aspect_ratio: str, base_width: int = 1920) -> Tuple[int, int]:
    """
    便捷函数：根据比例计算尺寸
    
    Args:
        aspect_ratio: 比例字符串，如 "16:9"
        base_width: 基础宽度，默认1920
        
    Returns:
        (width, height): 计算得到的尺寸
    """
    return DimensionCalculator.calculate_dimensions(aspect_ratio, base_width)


def get_aspect_ratio_info(aspect_ratio: str) -> Dict:
    """
    便捷函数：获取比例的详细信息
    
    Args:
        aspect_ratio: 比例字符串
        
    Returns:
        包含比例信息的字典
    """
    return DimensionCalculator.get_aspect_ratio_info(aspect_ratio)


def validate_aspect_ratio(aspect_ratio: str) -> bool:
    """
    便捷函数：验证比例格式是否正确
    
    Args:
        aspect_ratio: 比例字符串
        
    Returns:
        是否为有效比例
    """
    return DimensionCalculator.validate_aspect_ratio(aspect_ratio)


# 预定义的比例选项列表，用于前端下拉选择
ASPECT_RATIO_OPTIONS = [
    {"value": "16:9", "label": "16:9 (1920×1080) - 标准宽屏", "description": "适用于大多数现代显示器和投影仪"},
    {"value": "4:3", "label": "4:3 (1024×768) - 传统投影", "description": "适用于传统投影仪和老式显示器"},
    {"value": "1:1", "label": "1:1 (1080×1080) - 正方形", "description": "适用于社交媒体和移动端显示"},
    {"value": "9:16", "label": "9:16 (1080×1920) - 手机竖屏", "description": "适用于手机竖屏显示和短视频"},
    {"value": "3:2", "label": "3:2 (1800×1200) - 摄影比例", "description": "适用于摄影作品展示"},
    {"value": "21:9", "label": "21:9 (2560×1080) - 超宽屏", "description": "适用于超宽屏显示器和影院效果"},
    {"value": "custom", "label": "自定义尺寸", "description": "输入自定义的宽高比例"}
]


__all__ = [
    "DimensionCalculator",
    "calculate_dimensions",
    "get_aspect_ratio_info", 
    "validate_aspect_ratio",
    "ASPECT_RATIO_OPTIONS"
]