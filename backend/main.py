#!/usr/bin/env python3
"""
Main entry point for the backend application when packaged as an executable.
"""

import sys
import os

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    兼容开发环境和 PyInstaller 打包后的环境
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.main import app
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    
    # Default host and port
    host = "0.0.0.0"
    port = 8000
    
    # Check if command line arguments are provided
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number, using default 8000")
    
    print(f"Starting AI-PPT backend on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)