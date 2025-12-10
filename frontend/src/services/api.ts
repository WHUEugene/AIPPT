import type {
  OutlineResponse,
  ProjectState,
  SlideGenerateResponse,
  Template,
  TemplateAnalyzeResponse,
  TemplateListResponse,
} from './types';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }
  return (await res.blob()) as unknown as T;
}

export async function fetchTemplates(): Promise<Template[]> {
  const res = await fetch(`${API_BASE}/template`);
  const data = await handleResponse<TemplateListResponse>(res);
  return data.templates;
}

export async function analyzeTemplate(formData: FormData): Promise<TemplateAnalyzeResponse> {
  const res = await fetch(`${API_BASE}/template/analyze`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<TemplateAnalyzeResponse>(res);
}

export async function saveTemplate(payload: Omit<Template, 'id'>): Promise<Template> {
  const res = await fetch(`${API_BASE}/template/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await handleResponse<{ template: Template }>(res);
  return data.template;
}

export async function generateOutline(text: string, slideCount: number, templateId?: string): Promise<OutlineResponse> {
  const res = await fetch(`${API_BASE}/outline/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, slide_count: slideCount, template_id: templateId }),
  });
  return handleResponse<OutlineResponse>(res);
}

export async function generateSlide(payload: {
  style_prompt: string;
  visual_desc: string;
  aspect_ratio?: string;
  page_num?: number;
  title?: string;
  content_text?: string;
}): Promise<SlideGenerateResponse> {
  const res = await fetch(`${API_BASE}/slide/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ aspect_ratio: '16:9', ...payload }),
  });
  return handleResponse<SlideGenerateResponse>(res);
}

export async function exportPptx(project: ProjectState, fileName?: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/pptx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project, file_name: fileName }),
  });
  return handleResponse<Blob>(res);
}

export interface BatchGenerateRequest {
  slides: Array<{
    id: string;
    page_num: number;
    type: string;
    title: string;
    content_text: string;
    visual_desc: string;
  }>;
  style_prompt: string;
  max_workers?: number;
  aspect_ratio?: string;
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

export async function batchGenerateSlides(request: BatchGenerateRequest): Promise<BatchGenerateResult> {
  const res = await fetch(`${API_BASE}/slide/batch/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...request,
      max_workers: request.max_workers || 3,
      aspect_ratio: request.aspect_ratio || '16:9'
    }),
  });
  return handleResponse<BatchGenerateResult>(res);
}

export interface BatchStatusRequest {
  batch_id: string;
}

export interface BatchStatusResult {
  batch_id: string;
  status: string;
  progress: number;
  total_slides: number;
  completed_slides: number;
  successful: number;
  failed: number;
  estimated_remaining_time: number | null;
  results: BatchGenerateResult['results'];
}

export async function getBatchStatus(request: BatchStatusRequest): Promise<BatchStatusResult> {
  const res = await fetch(`${API_BASE}/slide/batch/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return handleResponse<BatchStatusResult>(res);
}
