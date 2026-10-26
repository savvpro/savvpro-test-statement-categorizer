import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const apiUrl = env.VITE_API_URL || "/api";
  const apiProxyTarget = apiUrl.startsWith("/")
    ? "http://127.0.0.1:8000"
    : undefined;

  return {
    plugins: [react()],
    server: {
      proxy: apiProxyTarget
        ? {
            [apiUrl]: {
              target: apiProxyTarget,
              changeOrigin: true,
              rewrite: (path) => path.slice(apiUrl.length),
            },
          }
        : undefined,
    },
  };
});
