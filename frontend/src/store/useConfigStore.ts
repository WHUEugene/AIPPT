import { create } from 'zustand';

export interface AppConfig {
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

interface ConfigStore {
  config: AppConfig;
  loading: boolean;
  error: string | null;
  
  // Actions
  loadConfig: () => Promise<void>;
  saveConfig: (config: Partial<AppConfig>) => Promise<boolean>;
  updateConfig: (updates: Partial<AppConfig>) => void;
  resetConfig: () => void;
  testConnection: () => Promise<{ success: boolean; message: string }>;
  
  // Computed
  isConfigured: boolean;
  hasApiKey: boolean;
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  config: defaultConfig,
  loading: false,
  error: null,
  
  isConfigured: false,
  hasApiKey: false,
  
  loadConfig: async () => {
    set({ loading: true, error: null });
    
    try {
      const response = await fetch('/api/config');
      if (response.ok) {
        const config = await response.json();
        set({ 
          config, 
          loading: false,
          isConfigured: true,
          hasApiKey: Boolean(config.llm_api_key?.trim())
        });
      } else {
        const error = await response.text();
        set({ error, loading: false });
      }
    } catch (error) {
      console.error('加载配置失败:', error);
      set({ 
        error: '加载配置失败，请检查网络连接', 
        loading: false 
      });
    }
  },
  
  saveConfig: async (updates) => {
    const currentConfig = { ...get().config, ...updates };
    
    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentConfig),
      });
      
      if (response.ok) {
        const savedConfig = await response.json();
        set({ 
          config: savedConfig,
          isConfigured: true,
          hasApiKey: Boolean(savedConfig.llm_api_key?.trim())
        });
        return true;
      } else {
        const error = await response.text();
        set({ error });
        return false;
      }
    } catch (error) {
      console.error('保存配置失败:', error);
      set({ error: '保存配置失败，请检查网络连接' });
      return false;
    }
  },
  
  updateConfig: (updates) => {
    const newConfig = { ...get().config, ...updates };
    set({ 
      config: newConfig,
      hasApiKey: Boolean(newConfig.llm_api_key?.trim())
    });
  },
  
  resetConfig: () => {
    set({ 
      config: defaultConfig,
      error: null,
      isConfigured: false,
      hasApiKey: false
    });
  },
  
  testConnection: async () => {
    const config = get().config;
    
    if (!config.llm_api_key?.trim()) {
      return {
        success: false,
        message: '请先配置API密钥'
      };
    }
    
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
        return {
          success: true,
          message: data.message || '连接测试成功'
        };
      } else {
        const error = await response.text();
        return {
          success: false,
          message: error || '连接测试失败'
        };
      }
    } catch (error) {
      return {
        success: false,
        message: '网络连接失败'
      };
    }
  }
}));