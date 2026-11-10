import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: mode === 'test' ? 3001 : 3000,
    strictPort: true,
    host: process.env.VITE_HOST || '127.0.0.1',
    open: false,
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true', interval: 250 },
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || (mode === 'test' ? 'http://127.0.0.1:8001' : 'http://localhost:8000'),
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 4173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:18000',
        changeOrigin: true,
      },
    },
  },
}));
