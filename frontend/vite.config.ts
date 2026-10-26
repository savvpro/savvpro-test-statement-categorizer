import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const backend = 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In development the browser talks to Vite, which forwards API calls to the backend.
    // That makes them same-origin, so no CORS setup is needed.
    proxy: { '/api': backend, '/health': backend },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
