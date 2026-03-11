import { defineConfig, devices } from "@playwright/test"

const PLAYER_PORT = 3003
const ADMIN_PORT = 3004

const sharedEnv = {
  E2E_AUTH_BYPASS: "true",
  NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "dummy-key-for-e2e",
  NEXT_PUBLIC_API_URL: "https://example.run.app",
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  timeout: 60_000,
  use: {
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    colorScheme: "dark",
    viewport: { width: 1280, height: 720 },
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "player",
      testMatch: /^(?!.*admin).*\.spec\.ts$/,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: `http://localhost:${PLAYER_PORT}`,
      },
    },
    {
      name: "admin",
      testMatch: /admin.*\.spec\.ts$/,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: `http://localhost:${ADMIN_PORT}`,
      },
    },
  ],
  webServer: [
    {
      command: `npm run dev -- --port ${PLAYER_PORT}`,
      url: `http://localhost:${PLAYER_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { ...sharedEnv, E2E_AUTH_ROLE: "player" },
    },
    {
      command: `npm run dev -- --port ${ADMIN_PORT}`,
      url: `http://localhost:${ADMIN_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { ...sharedEnv, E2E_AUTH_ROLE: "admin" },
    },
  ],
})
