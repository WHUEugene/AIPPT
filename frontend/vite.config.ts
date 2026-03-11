import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const frontendPort = Number(process.env.AIPPT_FRONTEND_PORT || 15173);
const backendPort = Number(process.env.AIPPT_BACKEND_PORT || 18000);

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: frontendPort,
    allowedHosts: ['.ngrok-free.dev', '.ngrok.io'],
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
      '/assets': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
});
