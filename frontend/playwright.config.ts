import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

const frontendPort = process.env.PLAYWRIGHT_PORT ?? "3002";
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "8001";
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${frontendPort}`;
const apiBaseUrl = `http://127.0.0.1:${backendPort}/api`;

function loadBackendEnv(): Record<string, string> {
  const envPath = path.join(__dirname, "../backend/.env");
  try {
    const content = readFileSync(envPath, "utf8");
    const entries: Record<string, string> = {};
    for (const line of content.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) {
        continue;
      }
      const separatorIndex = trimmed.indexOf("=");
      if (separatorIndex <= 0) {
        continue;
      }
      const key = trimmed.slice(0, separatorIndex).trim();
      const value = trimmed.slice(separatorIndex + 1).trim();
      entries[key] = value;
    }
    return entries;
  } catch {
    return {};
  }
}

const backendEnv = loadBackendEnv();

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  timeout: 60_000,
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `../backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        STORAGE_DIR: "../backend/storage/e2e-live",
        CORS_ORIGINS: `["http://127.0.0.1:${frontendPort}","http://localhost:${frontendPort}"]`,
        DATABASE_USE_ALEMBIC: "false",
        OPENAI_API_KEY: process.env.OPENAI_API_KEY ?? backendEnv.OPENAI_API_KEY ?? "",
        OPENAI_MODEL: process.env.OPENAI_MODEL ?? backendEnv.OPENAI_MODEL ?? "gpt-4o-mini",
      },
    },
    {
      command: `NEXT_PUBLIC_API_URL=${apiBaseUrl} npx next dev --port ${frontendPort}`,
      url: baseURL,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
