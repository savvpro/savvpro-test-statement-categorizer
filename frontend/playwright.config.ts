import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// Every run gets a new database; browser tests never touch the developer's workspace.
const directory = mkdtempSync(join(tmpdir(), "ledgerly-e2e-"));
const python =
  process.env.E2E_PYTHON ??
  (process.platform === "win32"
    ? "../.venv/Scripts/python.exe"
    : "../.venv/bin/python");
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
      ? {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
          args: ["--no-sandbox"],
        }
      : undefined,
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn statement_categorizer.main:app --app-dir ../backend --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      env: { LEDGER_DB_PATH: join(directory, "test.sqlite3") },
      timeout: 20000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: "http://127.0.0.1:8001" },
      timeout: 20000,
    },
  ],
});
