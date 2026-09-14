import { defineConfig, devices } from "@playwright/test";

const channel = process.env.PLAYWRIGHT_CHANNEL || (process.platform === "win32" ? "chrome" : undefined);

export default defineConfig({
  testDir: "./e2e",
  timeout: 45000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 }, channel } },
    { name: "mobile", use: { ...devices["iPhone 13"], defaultBrowserType: "chromium", channel } },
  ],
  webServer: [
    { command: process.platform === "win32" ? "..\\.venv\\Scripts\\python.exe -m uvicorn tests.demo_api:app --app-dir .. --host 127.0.0.1 --port 8000" : "python -m uvicorn tests.demo_api:app --app-dir .. --host 127.0.0.1 --port 8000", url: "http://127.0.0.1:8000", reuseExistingServer: false, timeout: 30000 },
    { command: "npm run start -- --hostname 127.0.0.1", url: "http://127.0.0.1:3000", reuseExistingServer: false, timeout: 30000 },
  ],
});
