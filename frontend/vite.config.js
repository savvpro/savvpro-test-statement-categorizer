import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// During development the API runs on :8000 and Vite forwards /api to it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000',
    },
  },
})
