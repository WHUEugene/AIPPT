export interface TemplateVisSettings {
  font?: string;
  primary_color?: string;
}

export interface Template {
  id: string;
  name: string;
  style_prompt: string;
  cover_image?: string;
  vis_settings?: TemplateVisSettings;
}

export type SlideType = 'cover' | 'content' | 'ending';
export type SlideStatus = 'pending' | 'generating' | 'done' | 'error';

export interface SlideData {
  id: string;
  page_num: number;
  type: SlideType;
  title: string;
  content_text: string;
  visual_desc: string;
  final_prompt?: string;
  image_url?: string;
  status: SlideStatus;
}

export interface OutlineResponse {
  slides: SlideData[];
}

export interface SlideGenerateResponse {
  image_url: string;
  final_prompt: string;
  revised_prompt: string;
  status: SlideStatus;
}

export interface TemplateListResponse {
  templates: Template[];
}

export interface TemplateAnalyzeResponse {
  style_prompt: string;
}

export interface ProjectState {
  template_id?: string;
  template_style_prompt?: string;
  title?: string;
  slides: SlideData[];
}
