import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev mode proxies /api to the FastAPI backend on :8000.
// Production mode builds to dist/ and FastAPI serves it directly.
export default defineConfig({
  plugins: [react()],
  // Plain-CSS project: skip PostCSS config discovery so a stray
  // postcss.config.* in a parent directory can never break the build.
  css: { postcss: {} },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
