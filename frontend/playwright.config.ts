import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8001",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command:
      process.platform === "win32"
        ? "..\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8001"
        : "../.venv/bin/python -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8001",
    url: "http://127.0.0.1:8001/api/health",
    reuseExistingServer: false,
    env: { LEDGERLY_DB: `../data/e2e-${Date.now()}.db` },
  },
});
