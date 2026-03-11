import { defineConfig, devices } from "@playwright/test"

const PORT = 3003

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    colorScheme: "dark",
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "player",
      testMatch: /^(?!.*admin).*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } },
    },
    {
      name: "admin",
      testMatch: /admin.*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } },
    },
  ],
  webServer: {
    command: `npm run dev -- --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      E2E_AUTH_BYPASS: "true",
      E2E_AUTH_ROLE: "player",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "dummy-key-for-e2e",
      NEXT_PUBLIC_API_URL: "https://example.run.app",
    },
  },
})
