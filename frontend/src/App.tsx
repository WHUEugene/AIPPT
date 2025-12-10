import { HashRouter, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Welcome from './pages/Welcome';
import TemplateSelect from './pages/TemplateSelect';
import TemplateCreate from './pages/TemplateCreate';
import ContentInput from './pages/ContentInput';
import Workspace from './pages/Workspace';
import History from './pages/History';
import Settings from './pages/Settings';

function BackendStarter() {
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    const startBackend = async () => {
      try {
        // 只在桌面环境中启动后端
        if (window.__TAURI__) {
          const { Command } = await import('@tauri-apps/plugin-shell');
          
          // 启动 Python 后端
          const command = Command.sidecar('binaries/backend-api');
          
          command.spawn().then((child) => {
            console.log('Python 后端已启动，PID:', child.pid);
          });

          // 监听后端输出（可选，用于调试）
          command.on('close', data => {
            console.log(`后端退出了，代码: ${data.code}`);
          });
          
          command.on('error', error => console.error(`后端报错: ${error}`));
        }
      } catch (error) {
        console.error('启动后端失败:', error);
      }
      
      // 等待一下让后端启动
      setTimeout(() => setBackendReady(true), 3000);
    };

    startBackend();
  }, []);

  if (!backendReady) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在启动后端服务...</p>
          <p className="text-gray-400 text-sm mt-2">AI-PPT Flow</p>
        </div>
      </div>
    );
  }

  return null;
}

export default function App() {
  return (
    <>
      <BackendStarter />
      <HashRouter>
        <Routes>
          <Route path="/" element={<Welcome />} />
          <Route path="/templates" element={<TemplateSelect />} />
          <Route path="/create-template" element={<TemplateCreate />} />
          <Route path="/input" element={<ContentInput />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </HashRouter>
    </>
  );
}
