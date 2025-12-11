import { HashRouter, Route, Routes, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import Welcome from './pages/Welcome';
import TemplateSelect from './pages/TemplateSelect';
import TemplateCreate from './pages/TemplateCreate';
import ContentInput from './pages/ContentInput';
import Workspace from './pages/Workspace';
import History from './pages/History';
import Settings from './pages/Settings';

function BackendStarter() {
  const [backendReady, setBackendReady] = useState(false);
  const [backendStarting, setBackendStarting] = useState(true);

  useEffect(() => {
    const startBackend = async () => {
      try {
        // 只在桌面环境中启动后端
        if (window.__TAURI__) {
          console.log('检测到桌面环境，准备启动后端...');
          const { Command } = await import('@tauri-apps/plugin-shell');
          
          // 启动 Python 后端
          const command = Command.sidecar('backend-api');
          
          // 增强前端报错
          command.on('close', data => {
            console.log(`Sidecar closed with code ${data.code} and signal ${data.signal}`);
          });
          command.on('error', error => console.error(`Sidecar error: ${error}`));
          command.stdout.on('data', line => console.log(`[PY]: ${line}`));
          command.stderr.on('data', line => console.error(`[PY ERR]: ${line}`));
          
          command.spawn().then((child) => {
            console.log('Python 后端已启动，PID:', child.pid);
          }).catch((e) => {
            console.error('致命错误：无法启动 Sidecar', e);
          });
          
          // 健康检查：等待后端真正启动
          let attempts = 0;
          const maxAttempts = 30; // 最多等待30秒
          
          const checkBackend = async () => {
            try {
              const response = await fetch('http://localhost:8000/');
              if (response.ok) {
                console.log('后端健康检查通过！');
                setBackendReady(true);
                setBackendStarting(false);
                return;
              }
            } catch (error) {
              attempts++;
              if (attempts < maxAttempts) {
                console.log(`等待后端启动... (${attempts}/${maxAttempts})`);
                setTimeout(checkBackend, 1000);
              } else {
                console.error('后端启动超时');
                setBackendStarting(false);
              }
            }
          };
          
          // 等待3秒后开始健康检查
          setTimeout(() => {
            checkBackend();
          }, 3000);
        } else {
          // Web环境，直接设置为已就绪
          setBackendReady(true);
          setBackendStarting(false);
        }
      } catch (error) {
        console.error('启动后端失败:', error);
        setBackendStarting(false);
      }
    };

    startBackend();
  }, []);

  if (backendStarting || !backendReady) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            {backendStarting ? '正在启动后端服务...' : '后端服务启动失败'}
          </p>
          <p className="text-gray-400 text-sm mt-2">AI-PPT Flow</p>
        </div>
      </div>
    );
  }

  return null;
}

function KeyboardNavigation() {
  const navigate = useNavigate();
  const location = useLocation();
  
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Alt + Left Arrow 或 Backspace 返回上一页
      if ((e.altKey && e.key === 'ArrowLeft') || (e.key === 'Backspace' && e.target instanceof HTMLElement && !e.target.matches('input, textarea'))) {
        // 在首页不执行返回操作
        if (location.pathname !== '/' && location.pathname !== '/templates') {
          e.preventDefault();
          navigate(-1);
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [navigate, location.pathname]);

  return null;
}

function AppContent() {
  return (
    <>
      <KeyboardNavigation />
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/templates" element={<TemplateSelect />} />
        <Route path="/create-template" element={<TemplateCreate />} />
        <Route path="/input" element={<ContentInput />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <>
      <BackendStarter />
      <HashRouter>
        <AppContent />
      </HashRouter>
    </>
  );
}
