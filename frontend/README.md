# AI-PPT Flow – Frontend Skeleton

React + Vite + Tailwind CSS workspace that implements the "北大典雅学术版"视觉系统以及完整的页流程（欢迎 -> 模版 -> 内容输入 -> 工作台）。

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

When the dev server starts, open `http://localhost:5173` to see the workspace layout. Tailwind automatically picks up files from `src/**/*` and `index.html`.

## Design System Files

- `tailwind.config.js` – extends theme with PKU brand palette, serif/sans stacks, academic shadows.
- `src/index.css` – global body/heading styles, scrollbar treatment, disables page scrolling for desktop-app feel.
- `src/components/ui/Button.tsx` – variants (`primary`, `outline`, `ghost`) and sizes (`sm`, `md`, `lg`).
- `src/components/ui/Card.tsx` – minimal card shell for template thumbnails。
- `src/layouts/WorkspaceLayout.tsx` – PPT 三栏布局骨架。
- `src/components/workspace/SlideCanvas.tsx` – 16:9 画布，支持加载态与文字覆盖。
- `src/pages/*` – Welcome、TemplateSelect、TemplateCreate、ContentInput、Workspace 五个页面。
- `src/store/useProjectStore.ts` – Zustand 状态管理（模版&幻灯片）。
- `src/services/api.ts` / `types.ts` – 同后端对齐的数据模型与 fetch 封装。
- `src/App.tsx` – `HashRouter` 路由配置。

## Tailwind / PostCSS setup

The usual Tailwind toolchain is already configured:

- `postcss.config.js` loads `tailwindcss` + `autoprefixer`.
- `tailwind.config.js` scans `index.html` and `src/**/*.{js,ts,jsx,tsx}`.
- `src/main.tsx` imports `./index.css` so all base layers are active.

If you add new directories, be sure to include them in the `content` array.

## Backend Proxy / API

`vite.config.ts` proxies `/api/*` to `http://localhost:8000`，与 FastAPI 后端保持一致。页面中所有 AI 调用（风格分析、大纲生成、重绘、导出）都通过 `src/services/api.ts` 访问该前缀。

若后端暂不可用，`TemplateSelect` 会降级加载示例模版以便演示 UI。其它 API 调用会提示错误信息。
