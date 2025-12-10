#!/usr/bin/env python3
"""
完整的后端API测试脚本
测试所有接口功能，包括批量生成功能
"""

import asyncio
import json
import time
import uuid
import httpx
from typing import Dict, Any, List


class APITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    async def test_api(self, method: str, endpoint: str, data: Dict = None, 
                      params: Dict = None, expected_status: int = 200, 
                      description: str = "") -> Dict[str, Any]:
        """测试单个API接口"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                end_time = time.time()
                duration = end_time - start_time
                
                result = {
                    "endpoint": endpoint,
                    "method": method,
                    "description": description,
                    "status_code": response.status_code,
                    "expected_status": expected_status,
                    "duration": duration,
                    "success": response.status_code == expected_status,
                    "response": response.text[:500]  # 只记录前500字符
                }
                
                if response.status_code == expected_status:
                    print(f"✅ {description or endpoint} - {response.status_code} ({duration:.2f}s)")
                else:
                    print(f"❌ {description or endpoint} - {response.status_code} (expected {expected_status}) ({duration:.2f}s)")
                    print(f"   Response: {response.text}")
                
                self.test_results.append(result)
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            result = {
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "status_code": 0,
                "expected_status": expected_status,
                "duration": duration,
                "success": False,
                "error": str(e),
                "response": str(e)
            }
            
            print(f"❌ {description or endpoint} - ERROR: {str(e)} ({duration:.2f}s)")
            self.test_results.append(result)
            return result

    async def test_template_apis(self):
        """测试模板相关接口"""
        print("\n🔍 测试模板接口...")
        
        # 获取模板列表
        await self.test_api(
            "GET", "/api/template",
            description="获取模板列表"
        )
        
        # 获取配置验证
        await self.test_api(
            "GET", "/api/slide/batch/config/validate",
            description="验证批量生成配置"
        )
        
        # 获取最优配置建议
        await self.test_api(
            "GET", "/api/slide/batch/config/optimal",
            params={"slides_count": 10},
            description="获取最优配置建议"
        )

    async def test_outline_apis(self):
        """测试大纲生成接口"""
        print("\n🔍 测试大纲生成接口...")
        
        outline_data = {
            "text": """
            AI-PPT Flow 项目介绍
            
            AI-PPT Flow 是一个基于人工智能的演示文稿生成系统，支持自动化风格分析、大纲生成和图片创建。
            
            核心功能：
            1. 智能风格分析
            2. 自动大纲生成  
            3. 批量图片生成
            4. 多模板支持
            
            技术架构：
            - 前端：React + TypeScript
            - 后端：Python + FastAPI
            - AI服务：OpenRouter + Gemini模型
            
            项目优势：
            - 全流程自动化
            - 支持自定义模板
            - 高并发批量处理
            - 详细日志记录
            """,
            "slide_count": 5,
            "template_id": None
        }
        
        await self.test_api(
            "POST", "/api/outline/generate",
            data=outline_data,
            description="生成演示文稿大纲"
        )

    async def test_batch_apis(self):
        """测试批量生成接口"""
        print("\n🔍 测试批量生成接口...")
        
        # 创建测试幻灯片数据
        test_slides = [
            {
                "id": str(uuid.uuid4()),
                "page_num": 1,
                "type": "cover",
                "title": "AI-PPT Flow 项目介绍",
                "content_text": "智能演示文稿生成系统\n2024年度进展报告",
                "visual_desc": "现代科技风格，深蓝色渐变背景，中央突出项目标题"
            },
            {
                "id": str(uuid.uuid4()),
                "page_num": 2,
                "type": "content", 
                "title": "核心功能",
                "content_text": "1. 智能风格分析\n2. 自动大纲生成\n3. 批量图片生成",
                "visual_desc": "左侧功能图标，右侧功能说明，蓝色主题"
            }
        ]
        
        batch_data = {
            "slides": test_slides,
            "style_prompt": "现代商务风格，专业简洁，蓝色主调",
            "max_workers": 2,  # 使用较低的并发数避免API限制
            "aspect_ratio": "16:9"
        }
        
        # 测试批量生成（可能会失败，因为需要真实的API key）
        await self.test_api(
            "POST", "/api/slide/batch/generate",
            data=batch_data,
            expected_status=500,  # 预期可能失败，因为需要API key
            description="批量生成幻灯片图片（预期可能失败）"
        )
        
        # 测试活跃任务数量
        await self.test_api(
            "GET", "/api/slide/batch/active-count",
            description="获取活跃批量任务数量"
        )

    async def test_single_slide_apis(self):
        """测试单张幻灯片生成接口"""
        print("\n🔍 测试单张幻灯片生成接口...")
        
        slide_data = {
            "style_prompt": "现代商务风格，蓝色主题",
            "visual_desc": "简洁的商务背景，左侧导航栏",
            "title": "项目概述",
            "content_text": "AI-PPT Flow 系统介绍",
            "aspect_ratio": "16:9"
        }
        
        # 测试单张幻灯片生成（预期可能失败）
        await self.test_api(
            "POST", "/api/slide/generate",
            data=slide_data,
            expected_status=500,
            description="生成单张幻灯片图片（预期可能失败）"
        )

    async def test_export_apis(self):
        """测试导出接口"""
        print("\n🔍 测试导出接口...")
        
        export_data = {
            "project": {
                "title": "测试项目",
                "template_style_prompt": "现代商务风格",
                "slides": [
                    {
                        "page_num": 1,
                        "title": "封面",
                        "content_text": "测试内容",
                        "image_url": "/assets/test.jpg",
                        "visual_desc": "封面描述"
                    }
                ]
            },
            "file_name": "test_export.pptx"
        }
        
        # 测试PPTX导出
        await self.test_api(
            "POST", "/api/export/pptx",
            data=export_data,
            description="导出PPTX文件"
        )

    async def print_summary(self):
        """打印测试总结"""
        print("\n📊 测试总结:")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"总测试数: {total_tests}")
        print(f"成功: {successful_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {successful_tests/total_tests*100:.1f}%")
        
        total_time = sum(r["duration"] for r in self.test_results)
        print(f"总耗时: {total_time:.2f}秒")
        
        if failed_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['description'] or result['endpoint']}: {result.get('error', 'HTTP ' + str(result['status_code']))}")
        
        # 保存详细结果到文件
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print("\n📁 详细结果已保存到 test_results.json")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始API测试...")
        print("基础URL:", self.base_url)
        print("=" * 50)
        
        try:
            # 首先检查服务器是否在线
            await self.test_api("GET", "/api/template", description="检查服务器连接")
            
            # 运行各类接口测试
            await self.test_template_apis()
            await self.test_outline_apis()
            await self.test_batch_apis()
            await self.test_single_slide_apis()
            await self.test_export_apis()
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {str(e)}")
        
        await self.print_summary()


async def main():
    """主函数"""
    tester = APITester("http://localhost:8000")
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())