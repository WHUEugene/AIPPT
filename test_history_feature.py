#!/usr/bin/env python3
"""
完整的项目历史功能测试脚本
测试后端API、数据持久化和前端集成
"""

import asyncio
import json
import requests
import time
from uuid import uuid4

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*50}")
    print(f"🧪 {title}")
    print('='*50)

def print_result(test_name, success, details=""):
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")

async def test_backend_apis():
    """测试后端API功能"""
    print_section("测试后端API接口")
    
    # 测试项目列表API
    try:
        response = requests.get(f"{BASE_URL}/api/projects")
        print_result("获取项目列表", response.status_code == 200, f"状态码: {response.status_code}")
        initial_projects = response.json()
        print(f"   初始项目数: {len(initial_projects)}")
    except Exception as e:
        print_result("获取项目列表", False, str(e))
        return
    
    # 创建测试项目数据
    test_project = {
        "id": f"test-project-{uuid4().hex[:8]}",
        "title": "AI-PPT功能测试项目",
        "created_at": "2025-12-10T09:52:00",
        "updated_at": "2025-12-10T09:52:00",
        "template_style_prompt": "现代简约科技风格，蓝色主调，专业商务",
        "slides": [
            {
                "id": str(uuid4()),
                "page_num": 1,
                "type": "cover",
                "title": "AI-PPT演示文稿",
                "content_text": "基于大语言模型的智能PPT生成系统",
                "visual_desc": "现代科技风格封面，蓝色渐变背景，简洁的AI元素",
                "status": "done",
                "image_url": "/assets/slide_cover.jpg"
            },
            {
                "id": str(uuid4()),
                "page_num": 2,
                "type": "content",
                "title": "系统架构",
                "content_text": "前端React + 后端FastAPI + AI服务",
                "visual_desc": "架构图展示，清晰的模块划分，技术栈图标",
                "status": "done",
                "image_url": "/assets/slide_architecture.jpg"
            }
        ],
        "thumbnail_url": "/assets/slide_cover.jpg"
    }
    
    # 测试项目保存
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/save",
            json=test_project,
            headers={"Content-Type": "application/json"}
        )
        success = response.status_code == 200
        print_result("保存新项目", success, f"状态码: {response.status_code}")
        if success:
            saved_project = response.json()
            print(f"   项目ID: {saved_project['id']}")
            print(f"   幻灯片数: {len(saved_project['slides'])}")
    except Exception as e:
        print_result("保存新项目", False, str(e))
        return
    
    project_id = test_project["id"]
    
    # 测试获取项目详情
    try:
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        success = response.status_code == 200
        print_result("获取项目详情", success, f"状态码: {response.status_code}")
        if success:
            project_detail = response.json()
            print(f"   项目标题: {project_detail['title']}")
            print(f"   风格提示词: {project_detail['template_style_prompt'][:30]}...")
    except Exception as e:
        print_result("获取项目详情", False, str(e))
    
    # 测试更新项目
    try:
        test_project["title"] = "更新后的测试项目"
        test_project["updated_at"] = "2025-12-10T10:00:00"
        response = requests.post(
            f"{BASE_URL}/api/projects/save",
            json=test_project,
            headers={"Content-Type": "application/json"}
        )
        success = response.status_code == 200
        print_result("更新现有项目", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("更新现有项目", False, str(e))
    
    # 测试项目列表（应该包含新项目）
    try:
        response = requests.get(f"{BASE_URL}/api/projects")
        success = response.status_code == 200
        print_result("获取更新后项目列表", success, f"状态码: {response.status_code}")
        if success:
            updated_projects = response.json()
            print(f"   项目总数: {len(updated_projects)}")
            print(f"   新增项目: {len(updated_projects) - len(initial_projects)}")
    except Exception as e:
        print_result("获取更新后项目列表", False, str(e))
    
    # 测试删除项目
    try:
        response = requests.delete(f"{BASE_URL}/api/projects/{project_id}")
        success = response.status_code == 200
        print_result("删除项目", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("删除项目", False, str(e))
    
    # 测试获取不存在项目
    try:
        response = requests.get(f"{BASE_URL}/api/projects/{project_id}")
        success = response.status_code == 404
        print_result("获取不存在项目(404)", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("获取不存在项目(404)", False, str(e))

def test_data_persistence():
    """测试数据持久化"""
    print_section("测试数据持久化")
    
    # 创建持久化测试项目
    persistent_project = {
        "id": f"persistence-test-{uuid4().hex[:8]}",
        "title": "数据持久化测试",
        "created_at": "2025-12-10T09:52:00",
        "updated_at": "2025-12-10T09:52:00",
        "template_style_prompt": "测试数据存储功能",
        "slides": [
            {
                "id": str(uuid4()),
                "page_num": 1,
                "type": "cover",
                "title": "持久化测试",
                "content_text": "验证数据是否正确保存到文件",
                "status": "done",
                "image_url": "/assets/persistence_test.jpg"
            }
        ],
        "thumbnail_url": "/assets/persistence_test.jpg"
    }
    
    # 保存项目
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/save",
            json=persistent_project,
            headers={"Content-Type": "application/json"}
        )
        success = response.status_code == 200
        print_result("保存持久化测试项目", success)
        
        if success:
            # 验证文件是否创建
            import os
            file_path = f"/Users/linyong/vscode/AIPPT/backend/data/projects/{persistent_project['id']}.json"
            file_exists = os.path.exists(file_path)
            print_result("验证项目文件存在", file_exists, f"路径: {file_path}")
            
            if file_exists:
                # 验证文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = json.load(f)
                
                content_valid = (
                    file_content['id'] == persistent_project['id'] and
                    file_content['title'] == persistent_project['title'] and
                    len(file_content['slides']) == len(persistent_project['slides'])
                )
                print_result("验证文件内容正确性", content_valid)
                
                # 清理测试文件
                os.remove(file_path)
                print_result("清理测试文件", True)
        
    except Exception as e:
        print_result("持久化测试失败", False, str(e))

def test_frontend_compatibility():
    """测试前端兼容性"""
    print_section("测试前端兼容性")
    
    # 测试前端根路径
    try:
        response = requests.get("http://localhost:5173/", timeout=5)
        success = response.status_code == 200
        print_result("前端首页访问", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("前端首页访问", False, str(e))
    
    # 测试CORS - 从前端域名调用API
    try:
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Origin": "http://localhost:5173"},
            timeout=5
        )
        success = response.status_code == 200
        print_result("CORS跨域访问", success, f"状态码: {response.status_code}")
        if success:
            cors_headers = response.headers.get('Access-Control-Allow-Origin')
            print(f"   CORS头: {cors_headers}")
    except Exception as e:
        print_result("CORS跨域访问", False, str(e))

def test_error_handling():
    """测试错误处理"""
    print_section("测试错误处理")
    
    # 测试无效JSON
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/save",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        success = response.status_code == 422
        print_result("无效JSON处理", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("无效JSON处理", False, str(e))
    
    # 测试缺少必填字段
    try:
        incomplete_project = {
            "id": "incomplete-test",
            "title": "不完整项目"
            # 缺少其他必填字段
        }
        response = requests.post(
            f"{BASE_URL}/api/projects/save",
            json=incomplete_project,
            headers={"Content-Type": "application/json"}
        )
        success = response.status_code == 422
        print_result("缺少必填字段处理", success, f"状态码: {response.status_code}")
    except Exception as e:
        print_result("缺少必填字段处理", False, str(e))

async def main():
    """主测试函数"""
    print_section("开始完整功能测试")
    print("测试时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("后端地址:", BASE_URL)
    print("前端地址:", "http://localhost:5173")
    
    # 执行各项测试
    await test_backend_apis()
    test_data_persistence()
    test_frontend_compatibility()
    test_error_handling()
    
    print_section("测试完成")
    print("🎉 所有测试已完成！")
    print("📝 如果所有测试都显示 ✅，说明历史项目功能正常工作")
    print("🌐 请访问 http://localhost:5173 体验完整的前端界面")

if __name__ == "__main__":
    asyncio.run(main())