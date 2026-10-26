import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "..");
const python = resolve(
  root,
  process.platform === "win32"
    ? ".venv/Scripts/python.exe"
    : ".venv/bin/python",
);
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1536, height: 1024 },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001`,
      cwd: root,
      url: "http://127.0.0.1:8001/api/health",
      env: { SORTEDHISAB_DB: ".local/e2e.sqlite3" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      env: { API_TARGET: "http://127.0.0.1:8001" },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
