import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The browser only talks to Vite; Vite forwards /api to the Python backend.
// This avoids CORS problems and works inside Codespaces.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: true, // dev server only (Codespaces uses a forwarded hostname)
    proxy: { "/api": "http://localhost:8000" },
  },
});
