import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const root = path.resolve(__dirname, "../..");
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command:
        ".venv/bin/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8100",
      cwd: root,
      url: "http://127.0.0.1:8100/api/health",
      reuseExistingServer: false,
      env: {
        WCL_CLIENT_ID: "",
        WCL_CLIENT_SECRET: "",
        GEMINI_API_KEY: "",
        CORS_ORIGINS: '["http://127.0.0.1:3100"]',
      },
    },
    {
      command:
        "npm run build && npm run start -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 120000,
      env: { E2E: "1", NEXT_PUBLIC_API_URL: "http://127.0.0.1:8100" },
    },
  ],
});
