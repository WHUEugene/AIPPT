import { create } from 'zustand';
import type { SlideData, Template, ProjectSchema } from '../services/types';
import { saveProject as saveProjectApi } from '../services/api';
import { generateId } from '../utils/uuid';

interface ProjectStore {
  templates: Template[];
  currentTemplate: Template | null;
  slides: SlideData[];
  currentSlideId: string | null;
  projectTitle: string;
  projectId: string | null; // 新增：记录当前项目ID
  
  setTemplates: (templates: Template[]) => void;
  addTemplate: (template: Template) => void;
  upsertTemplate: (template: Template) => void;
  setCurrentTemplate: (template: Template | null) => void;
  setSlides: (slides: SlideData[]) => void;
  selectSlide: (id: string | null) => void;
  updateSlide: (id: string, updates: Partial<SlideData>) => void;
  insertSlideAt: (index: number, slide: SlideData) => void;
  removeSlide: (id: string) => void;
  setProjectTitle: (title: string) => void;
  
  // 新增方法
  loadProject: (projectData: ProjectSchema) => void;
  saveCurrentProject: () => Promise<string>;
  createNewProject: () => void;
}

const resequenceSlides = (slides: SlideData[]): SlideData[] =>
  slides.map((slide, index) => ({
    ...slide,
    page_num: index + 1,
  }));

export const useProjectStore = create<ProjectStore>((set, get) => ({
  templates: [],
  currentTemplate: null,
  slides: [],
  currentSlideId: null,
  projectTitle: '新项目',
  projectId: null,
  
  setTemplates: (templates) => set({ templates }),
  addTemplate: (template) => set((state) => ({ templates: [...state.templates, template] })),
  upsertTemplate: (template) =>
    set((state) => {
      const exists = state.templates.some((item) => item.id === template.id);
      return {
        templates: exists
          ? state.templates.map((item) => (item.id === template.id ? template : item))
          : [...state.templates, template],
        currentTemplate: state.currentTemplate?.id === template.id ? template : state.currentTemplate,
      };
    }),
  setCurrentTemplate: (template) => set({ currentTemplate: template }),
  setSlides: (slides) => {
    const normalizedSlides = resequenceSlides(slides);
    set({ slides: normalizedSlides, currentSlideId: normalizedSlides[0]?.id ?? null });
  },
  selectSlide: (id) => set({ currentSlideId: id }),
  updateSlide: (id, updates) =>
    set((state) => ({
      slides: state.slides.map((slide) => (slide.id === id ? { ...slide, ...updates } : slide)),
    })),
  insertSlideAt: (index, slide) =>
    set((state) => {
      const nextSlides = [...state.slides];
      nextSlides.splice(index, 0, slide);
      const normalizedSlides = resequenceSlides(nextSlides);
      const insertedSlide = normalizedSlides[index];
      return {
        slides: normalizedSlides,
        currentSlideId: insertedSlide?.id ?? state.currentSlideId,
      };
    }),
  removeSlide: (id) =>
    set((state) => {
      if (state.slides.length <= 1) {
        return state;
      }

      const removeIndex = state.slides.findIndex((slide) => slide.id === id);
      if (removeIndex === -1) {
        return state;
      }

      const nextSlides = state.slides.filter((slide) => slide.id !== id);
      const normalizedSlides = resequenceSlides(nextSlides);
      const nextSelectedSlide =
        normalizedSlides[Math.min(removeIndex, normalizedSlides.length - 1)] ?? normalizedSlides[0] ?? null;

      return {
        slides: normalizedSlides,
        currentSlideId: nextSelectedSlide?.id ?? null,
      };
    }),
  setProjectTitle: (title) => set({ projectTitle: title || '新项目' }),
  
  // 加载项目数据
  loadProject: (projectData) => {
    const normalizedSlides = resequenceSlides(projectData.slides);
    const fakeTemplate = {
      id: 'loaded-template',
      name: '已保存的模板',
      style_prompt: projectData.template_style_prompt,
    };
    
    set({
      projectId: projectData.id,
      slides: normalizedSlides,
      currentTemplate: fakeTemplate,
      projectTitle: projectData.title,
      currentSlideId: normalizedSlides[0]?.id ?? null,
    });
  },
  
  // 保存当前项目
  saveCurrentProject: async () => {
    const { projectId, slides, currentTemplate, projectTitle } = get();
    
    // 如果是新项目，生成一个 UUID
    const id = projectId || generateId();
    
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
