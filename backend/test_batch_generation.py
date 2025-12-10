#!/usr/bin/env python3
"""
批量图片生成测试脚本
用于验证批量生成接口的功能
"""

import asyncio
import json
import time
from uuid import uuid4
import httpx
from pathlib import Path


def create_test_slides():
    """创建测试用的幻灯片数据"""
    return [
        {
            "id": str(uuid4()),
            "page_num": 1,
            "type": "cover",
            "title": "AI-PPT Flow 项目汇报",
            "content_text": "智能化演示文稿生成系统\n2024年度进展报告",
            "visual_desc": "现代科技风格，深蓝色渐变背景，中央突出项目标题，底部有简洁的装饰线条，整体简洁专业"
        },
        {
            "id": str(uuid4()),
            "page_num": 2,
            "type": "content",
            "title": "项目概述",
            "content_text": "AI-PPT Flow 是基于大语言模型的智能PPT生成系统，支持自动化风格分析、大纲生成和图片创建。",
            "visual_desc": "左侧展示系统架构图，右侧列出核心功能特点，使用蓝色和白色为主色调，保持简洁商务风格"
        },
        {
            "id": str(uuid4()),
            "page_num": 3,
            "type": "content",
            "title": "核心功能",
            "content_text": "1. 智能风格分析\n2. 自动大纲生成\n3. 批量图片生成\n4. 多模板支持",
            "visual_desc": "使用图标和简洁文字展示四大核心功能，每个功能配有相应的图标，布局清晰有序"
        },
        {
            "id": str(uuid4()),
            "page_num": 4,
            "type": "content",
            "title": "技术架构",
            "content_text": "采用微服务架构，支持高并发处理，集成最新的AI模型技术。",
            "visual_desc": "展示技术架构图，包含前端、后端、AI服务层，使用流程图形式展示数据处理流程"
        },
        {
            "id": str(uuid4()),
            "page_num": 5,
            "type": "ending",
            "title": "谢谢观看",
            "content_text": "AI-PPT Flow 项目组\n让PPT制作更智能、更高效",
            "visual_desc": "简洁的感谢页面，深色背景配以白色文字，底部显示项目信息，整体庄重得体"
        }
    ]


async def test_batch_generation():
    """测试批量生成接口"""
    base_url = "http://localhost:8000"
    
    # 测试数据
    test_slides = create_test_slides()
    style_prompt = """
基于现代商务演示的设计理念，采用专业简约的风格。
### 视觉风格提示词 (Style Prompt)

**1. 配色与材质 (Color & Material)**
*   **色彩基调**：专业商务风格，以深蓝色(#1e3a8a)为主色调，搭配浅灰色(#f3f4f6)作为辅助色。
*   **点缀色彩**：使用深红色(#dc2626)作为重点强调色，保持整体商务感。
*   **光影质感**：均匀的柔和光照，避免强烈阴影，营造专业稳重的氛围。
*   **材质表现**：平滑细腻的质感，现代感强，避免过多纹理。

**2. 构图与层次 (Composition & Layers)**
*   **画幅比例**：标准16:9宽屏比例，适合投影展示。
*   **空间布局**：清晰的层次结构，主次分明，留有适当的留白。
*   **层次关系**：背景简洁，前景内容突出，保持良好的可读性。

**3. 画面细节 (Screen Details)**
*   **视觉风格**：现代商务简约风格，专业设计感。
*   **清晰度**：高分辨率，文字清晰可读，图像细节丰富。

**4. 作图注意事项 (Precautions)**
*   **避免元素**：过于花哨的装饰、复杂纹理、低饱和度色彩。
*   **重点控制**：保持整体风格的统一性，确保文字可读性。
"""
    
    print("🚀 开始测试批量图片生成接口...")
    print(f"📊 测试幻灯片数量: {len(test_slides)}")
    print(f"🎨 风格提示词长度: {len(style_prompt)} 字符")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # 1. 批量生成
            print("\n1️⃣ 发送批量生成请求...")
            start_time = time.time()
            
            # 测试不同的并发数
            test_configs = [
                {"max_workers": 2, "name": "低并发测试"},
                {"max_workers": 5, "name": "中等并发测试"},
                {"max_workers": 10, "name": "高并发测试"},
            ]
            
            results = []
            
            for config in test_configs:
                print(f"\n🔄 {config['name']} (max_workers={config['max_workers']})...")
                batch_request = {
                    "slides": test_slides,
                    "style_prompt": style_prompt,
                    "max_workers": config['max_workers'],
                    "aspect_ratio": "16:9"
                }
                
                start_time = time.time()
                response = await client.post(
                    f"{base_url}/api/slide/batch/generate",
                    json=batch_request
                )
                
                if response.status_code != 200:
                    print(f"❌ {config['name']} 失败: {response.status_code}")
                    continue
                
                result = response.json()
                generation_time = time.time() - start_time
                
                print(f"✅ {config['name']} 完成!")
                print(f"   成功: {result['successful']}, 失败: {result['failed']}")
                print(f"   耗时: {generation_time:.2f}秒")
                print(f"   平均每张: {generation_time/len(test_slides):.2f}秒")
                
                results.append({
                    "config": config,
                    "result": result,
                    "generation_time": generation_time
                })
                
                # 短暂休息避免API限制
                await asyncio.sleep(2)
            
            # 2. 分析测试结果
            if not results:
                print("❌ 所有配置测试都失败了")
                return False
                
            print("\n📊 测试结果分析:")
            fastest = min(results, key=lambda x: x["generation_time"])
            slowest = max(results, key=lambda x: x["generation_time"])
            
            for result_item in results:
                config = result_item["config"]
                result_data = result_item["result"]
                generation_time = result_item["generation_time"]
                
                avg_time = generation_time / len(test_slides)
                success_rate = result_data["successful"] / result_data["total_slides"] * 100
                
                status = "🥇" if result_item == fastest else "🥉" if result_item == slowest else "🥈"
                print(f"{status} {config['name']}: {generation_time:.1f}秒, 平均每张 {avg_time:.1f}秒, 成功率 {success_rate:.1f}%")
            
            # 使用最快的测试结果进行后续验证
            best_result = fastest["result"]
            generation_time = fastest["generation_time"]
            
            # 3. 检查结果详情
            print("\n3️⃣ 检查生成结果...")
            success_count = 0
            for i, slide_result in enumerate(best_result['results']):
                status_emoji = "✅" if slide_result['status'] == 'done' else "❌"
                print(f"{status_emoji} 幻灯片 {slide_result['page_num']}: {slide_result['title']}")
                print(f"   状态: {slide_result['status']}")
                print(f"   生成时间: {slide_result.get('generation_time', 0):.2f}秒")
                if slide_result['image_url']:
                    print(f"   图片URL: {slide_result['image_url']}")
                if slide_result['error_message']:
                    print(f"   错误信息: {slide_result['error_message']}")
                print()
                
                if slide_result['status'] == 'done':
                    success_count += 1
            
            # 4. 测试状态查询接口
            print("4️⃣ 测试状态查询接口...")
            status_request = {"batch_id": best_result['batch_id']}
            status_response = await client.post(
                f"{base_url}/api/slide/batch/status",
                json=status_request
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"✅ 状态查询成功:")
                print(f"   批量状态: {status['status']}")
                print(f"   进度: {status['progress']:.1%}")
                print(f"   已完成: {status['completed_slides']}/{status['total_slides']}")
            else:
                print(f"❌ 状态查询失败: {status_response.status_code}")
            
            # 5. 测试活跃任务查询
            print("5️⃣ 测试活跃任务查询...")
            active_response = await client.get(f"{base_url}/api/slide/batch/active-count")
            if active_response.status_code == 200:
                active_count = active_response.json()
                print(f"✅ 当前活跃批量任务数: {active_count['active_batches']}")
            else:
                print(f"❌ 活跃任务查询失败: {active_response.status_code}")
            
            # 6. 验证生成的图片文件
            print("6️⃣ 验证生成的图片文件...")
            generated_files = []
            for slide_result in best_result['results']:
                if slide_result['image_url']:
                    filename = slide_result['image_url'].split('/')[-1]
                    generated_files.append(filename)
            
            if generated_files:
                print(f"✅ 成功生成 {len(generated_files)} 个图片文件:")
                for filename in generated_files:
                    print(f"   📁 {filename}")
            else:
                print("❌ 没有生成任何图片文件")
            
            # 7. 测试配置验证接口
            print("\n7️⃣ 测试配置验证接口...")
            config_response = await client.get(f"{base_url}/api/slide/batch/config/validate")
            if config_response.status_code == 200:
                config_info = config_response.json()
                print(f"✅ 配置验证完成:")
                print(f"   配置有效: {config_info['valid']}")
                if config_info['issues']:
                    print(f"   配置问题: {config_info['issues']}")
                if config_info['recommendations']:
                    print(f"   建议: {config_info['recommendations']}")
            else:
                print(f"❌ 配置验证失败: {config_response.status_code}")
            
            # 8. 测试最优配置接口
            print("\n8️⃣ 测试最优配置接口...")
            optimal_response = await client.post(
                f"{base_url}/api/slide/batch/config/optimal",
                json={"slides_count": 10}
            )
            if optimal_response.status_code == 200:
                optimal_info = optimal_response.json()
                print(f"✅ 最优配置建议:")
                print(f"   幻灯片数量: {optimal_info['slides_count']}")
                print(f"   建议并发数: {optimal_info['recommended_workers']}")
                print(f"   预估时间: {optimal_info['estimated_time_formatted']}")
            else:
                print(f"❌ 最优配置查询失败: {optimal_response.status_code}")
            
            # 9. 总结
            print("\n🎉 测试完成!")
            print(f"📊 测试总结:")
            print(f"   总幻灯片: {best_result['total_slides']}")
            print(f"   成功生成: {success_count}")
            print(f"   失败数量: {best_result['failed']}")
            print(f"   最佳耗时: {generation_time:.2f}秒")
            print(f"   平均每张: {generation_time/len(test_slides):.2f}秒")
            
            if success_count == len(test_slides):
                print("🎊 所有幻灯片生成成功!")
                return True
            else:
                print("⚠️ 部分幻灯片生成失败")
                return False
            
        except httpx.ConnectError:
            print("❌ 无法连接到后端服务，请确保后端正在运行")
            return False
        except httpx.TimeoutException:
            print("❌ 请求超时")
            return False
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {str(e)}")
            return False


async def main():
    """主函数"""
    print("🔧 AI-PPT Flow 批量图片生成测试")
    print("=" * 50)
    
    success = await test_batch_generation()
    
    if success:
        print("\n🎊 测试通过! 批量生成功能工作正常")
        exit(0)
    else:
        print("\n❌ 测试失败! 请检查后端日志")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())