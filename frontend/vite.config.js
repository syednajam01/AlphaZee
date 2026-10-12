import { defineConfig } from 'vite';

export default defineConfig(({ mode }) => ({
  server: {
    port: mode === 'test' ? 3001 : 3000,
    strictPort: true,
    host: '127.0.0.1',
    open: false,
    proxy: {
      '/api': {
        target: mode === 'test' ? 'http://127.0.0.1:8001' : 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
}));
