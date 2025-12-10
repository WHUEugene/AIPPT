import { create } from 'zustand';
import type { SlideData, Template } from '../services/types';

interface ProjectStore {
  templates: Template[];
  currentTemplate: Template | null;
  slides: SlideData[];
  currentSlideId: string | null;
  projectTitle: string;
  setTemplates: (templates: Template[]) => void;
  addTemplate: (template: Template) => void;
  setCurrentTemplate: (template: Template | null) => void;
  setSlides: (slides: SlideData[]) => void;
  selectSlide: (id: string | null) => void;
  updateSlide: (id: string, updates: Partial<SlideData>) => void;
  setProjectTitle: (title: string) => void;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  templates: [],
  currentTemplate: null,
  slides: [],
  currentSlideId: null,
  projectTitle: '新项目',
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
}));
