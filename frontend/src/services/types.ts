export interface TemplateVisSettings {
  font?: string;
  primary_color?: string;
}

export interface TemplateCustomDimensions {
  width?: number;
  height?: number;
}

export interface Template {
  id: string;
  name: string;
  style_prompt: string;
  cover_image?: string;
  vis_settings?: TemplateVisSettings;
  // 新增比例和尺寸相关字段
  aspect_ratios?: string[];
  default_aspect_ratio?: string;
  custom_dimensions?: TemplateCustomDimensions;
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

export interface ProjectSchema {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  template_style_prompt: string;
  slides: SlideData[];
  thumbnail_url?: string;
}

export interface ProjectListItem {
  id: string;
  title: string;
  updated_at: string;
  thumbnail_url?: string;
}

export interface BatchGenerateResult {
  batch_id: string;
  total_slides: number;
  successful: number;
  failed: number;
  total_time: number;
  results: Array<{
    slide_id: string;
    page_num: number;
    title: string;
    image_url: string;
    final_prompt: string;
    status: string;
    error_message: string | null;
    generation_time: number;
  }>;
}

// 比例选项接口
export interface AspectRatioOption {
  value: string;
  label: string;
  description: string;
}

// 自定义尺寸接口
export interface CustomDimensions {
  width: number;
  height: number;
  aspectRatio: string;
}

export interface BatchStatusResult {
  batch_id: string;
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
  pending: number;
  progress: number;
  status: string;
  results?: Array<{
    slide_id: string;
    page_num: number;
    title: string;
    image_url: string;
    final_prompt: string;
    status: string;
    error_message: string | null;
    generation_time: number;
  }>;
}
