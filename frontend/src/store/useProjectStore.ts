import { create } from 'zustand';
import type { SlideData, Template, ProjectSchema } from '../services/types';
import { saveProject as saveProjectApi } from '../services/api';

interface ProjectStore {
  templates: Template[];
  currentTemplate: Template | null;
  slides: SlideData[];
  currentSlideId: string | null;
  projectTitle: string;
  projectId: string | null; // 新增：记录当前项目ID
  
  setTemplates: (templates: Template[]) => void;
  addTemplate: (template: Template) => void;
  setCurrentTemplate: (template: Template | null) => void;
  setSlides: (slides: SlideData[]) => void;
  selectSlide: (id: string | null) => void;
  updateSlide: (id: string, updates: Partial<SlideData>) => void;
  setProjectTitle: (title: string) => void;
  
  // 新增方法
  loadProject: (projectData: ProjectSchema) => void;
  saveCurrentProject: () => Promise<string>;
  createNewProject: () => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  templates: [],
  currentTemplate: null,
  slides: [],
  currentSlideId: null,
  projectTitle: '新项目',
  projectId: null,
  
  setTemplates: (templates) => set({ templates }),
  addTemplate: (template) => set((state) => ({ templates: [...state.templates, template] })),
  setCurrentTemplate: (template) => set({ currentTemplate: template }),
  setSlides: (slides) => set({ slides, currentSlideId: slides[0]?.id ?? null }),
  selectSlide: (id) => set({ currentSlideId: id }),
  updateSlide: (id, updates) =>
    set((state) => ({
      slides: state.slides.map((slide) => (slide.id === id ? { ...slide, ...updates } : slide)),
    })),
  setProjectTitle: (title) => set({ projectTitle: title || '新项目' }),
  
  // 加载项目数据
  loadProject: (projectData) => {
    const fakeTemplate = {
      id: 'loaded-template',
      name: '已保存的模板',
      style_prompt: projectData.template_style_prompt,
    };
    
    set({
      projectId: projectData.id,
      slides: projectData.slides,
      currentTemplate: fakeTemplate,
      projectTitle: projectData.title,
      currentSlideId: projectData.slides[0]?.id ?? null,
    });
  },
  
  // 保存当前项目
  saveCurrentProject: async () => {
    const { projectId, slides, currentTemplate, projectTitle } = get();
    
    // 如果是新项目，生成一个 UUID
    const id = projectId || crypto.randomUUID();
    
    const payload = {
      id,
      title: projectTitle || '未命名项目',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      template_style_prompt: currentTemplate?.style_prompt || '',
      slides: slides,
      thumbnail_url: slides.length > 0 ? slides[0].image_url : undefined
    };

    try {
      await saveProjectApi(payload);
      set({ projectId: id }); // 确保保存后更新 ID
      return id;
    } catch (error) {
      console.error('保存项目失败:', error);
      throw error;
    }
  },
  
  // 创建新项目
  createNewProject: () => {
    set({
      projectId: null,
      slides: [],
      currentSlideId: null,
      projectTitle: '新项目',
      currentTemplate: null,
    });
  },
}));
