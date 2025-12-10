import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Save, Eye, EyeOff, ArrowLeft, Key, Server, Globe, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import BackButton from '../components/ui/BackButton';

interface AppConfig {
  // AI服务配置
  llm_api_key: string;
  llm_api_base: string;
  llm_chat_model: string;
  llm_image_model: string;
  llm_timeout_seconds: number;
  
  // 文件存储配置
  image_output_dir: string;
  pptx_output_dir: string;
  template_store_path: string;
  
  // CORS配置
  allowed_origins: string[];
  
  // 服务配置
  project_name: string;
  api_prefix: string;
}

const defaultConfig: AppConfig = {
  llm_api_key: '',
  llm_api_base: 'https://openrouter.ai/api/v1',
  llm_chat_model: 'google/gemini-3-pro-preview',
  llm_image_model: 'google/gemini-3-pro-image-preview',
  llm_timeout_seconds: 120,
  
  image_output_dir: 'backend/generated/images',
  pptx_output_dir: 'backend/generated/pptx',
  template_store_path: 'backend/data/templates.json',
  
  allowed_origins: ['http://localhost:5173', 'https://your-domain.com'],
  
  project_name: 'AI-PPT Flow Backend',
  api_prefix: '/api'
};

export default function Settings() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<AppConfig>(defaultConfig);
  const [originalConfig, setOriginalConfig] = useState<AppConfig>(defaultConfig);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string>('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await fetch('/api/config');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        setOriginalConfig(data);
      }
    } catch (error) {
      console.error('加载配置失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    setSaveMessage('');
    setTestResult(null);
    
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
        setOriginalConfig(data);
        setSaveMessage('配置已保存');
        setTimeout(() => setSaveMessage(''), 3000);
      } else {
        const error = await response.text();
        setSaveMessage(`保存失败: ${error}`);
      }
    } catch (error) {
      console.error('保存配置失败:', error);
      setSaveMessage('保存失败，请检查网络连接');
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTestResult(null);
    
    try {
      const response = await fetch('/api/config/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: config.llm_api_key,
          api_base: config.llm_api_base,
          model: config.llm_chat_model
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setTestResult({
          success: true,
          message: data.message || '连接测试成功'
        });
      } else {
        const error = await response.text();
        setTestResult({
          success: false,
          message: error || '连接测试失败'
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: '网络连接失败'
      });
    }
  };

  const handleInputChange = (field: keyof AppConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const hasChanges = JSON.stringify(config) !== JSON.stringify(originalConfig);
  const canSave = config.llm_api_key.trim() !== '';

  return (
    <div className="min-h-screen bg-pku-light overflow-y-auto">
      {/* 顶部导航 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                onClick={() => navigate('/')}
                className="flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                返回首页
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-pku-black">系统设置</h1>
                <p className="text-sm text-gray-500">配置API密钥和项目参数</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              {hasChanges && (
                <span className="text-sm text-orange-600">有未保存的更改</span>
              )}
              <Button
                onClick={saveConfig}
                disabled={!canSave || !hasChanges || saving}
                className="flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? '保存中...' : '保存配置'}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 配置内容 */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="space-y-8">
          {/* AI服务配置 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Key className="w-5 h-5 text-pku-red" />
              <h2 className="text-xl font-bold text-pku-black">AI服务配置</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API 密钥 <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? "text" : "password"}
                    value={config.llm_api_key}
                    onChange={(e) => handleInputChange('llm_api_key', e.target.value)}
                    placeholder="sk-or-v1-..."
                    className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600"
                  >
                    {showApiKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  OpenRouter API密钥，用于访问AI模型
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    API 基础地址
                  </label>
                  <input
                    type="url"
                    value={config.llm_api_base}
                    onChange={(e) => handleInputChange('llm_api_base', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    超时时间 (秒)
                  </label>
                  <input
                    type="number"
                    min="30"
                    max="300"
                    value={config.llm_timeout_seconds}
                    onChange={(e) => handleInputChange('llm_timeout_seconds', parseInt(e.target.value) || 120)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    文本模型
                  </label>
                  <input
                    type="text"
                    value={config.llm_chat_model}
                    onChange={(e) => handleInputChange('llm_chat_model', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    图像模型
                  </label>
                  <input
                    type="text"
                    value={config.llm_image_model}
                    onChange={(e) => handleInputChange('llm_image_model', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
              </div>

              {/* 连接测试 */}
              <div className="pt-4 border-t border-gray-200">
                <Button
                  variant="outline"
                  onClick={testConnection}
                  disabled={!config.llm_api_key.trim()}
                  className="flex items-center gap-2"
                >
                  <Globe className="w-4 h-4" />
                  测试AI服务连接
                </Button>
                
                {testResult && (
                  <div className={`mt-3 flex items-center gap-2 p-3 rounded-lg ${
                    testResult.success 
                      ? 'bg-green-50 text-green-700 border border-green-200' 
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}>
                    {testResult.success ? (
                      <CheckCircle className="w-4 h-4" />
                    ) : (
                      <AlertCircle className="w-4 h-4" />
                    )}
                    <span className="text-sm">{testResult.message}</span>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* 文件存储配置 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Server className="w-5 h-5 text-pku-red" />
              <h2 className="text-xl font-bold text-pku-black">文件存储配置</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  图像输出目录
                </label>
                <input
                  type="text"
                  value={config.image_output_dir}
                  onChange={(e) => handleInputChange('image_output_dir', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  PPTX输出目录
                </label>
                <input
                  type="text"
                  value={config.pptx_output_dir}
                  onChange={(e) => handleInputChange('pptx_output_dir', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  模板存储路径
                </label>
                <input
                  type="text"
                  value={config.template_store_path}
                  onChange={(e) => handleInputChange('template_store_path', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                />
              </div>
            </div>
          </Card>

          {/* 服务配置 */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <Server className="w-5 h-5 text-pku-red" />
              <h2 className="text-xl font-bold text-pku-black">服务配置</h2>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    项目名称
                  </label>
                  <input
                    type="text"
                    value={config.project_name}
                    onChange={(e) => handleInputChange('project_name', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    API 前缀
                  </label>
                  <input
                    type="text"
                    value={config.api_prefix}
                    onChange={(e) => handleInputChange('api_prefix', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  允许的跨域源 (每行一个)
                </label>
                <textarea
                  value={config.allowed_origins.join('\n')}
                  onChange={(e) => handleInputChange('allowed_origins', e.target.value.split('\n').filter(Boolean))}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pku-red focus:border-pku-red"
                  placeholder="http://localhost:5173&#10;https://your-domain.com"
                />
              </div>
            </div>
          </Card>
        </div>

        {/* 底部消息 */}
        {saveMessage && (
          <div className={`mt-6 p-4 rounded-lg border ${
            saveMessage.includes('失败') 
              ? 'bg-red-50 text-red-700 border-red-200' 
              : 'bg-green-50 text-green-700 border-green-200'
          }`}>
            {saveMessage}
          </div>
        )}
      </div>
    </div>
  );
}