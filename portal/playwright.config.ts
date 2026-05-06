import { defineConfig, devices } from "@playwright/test"

// Spec 216-G — ensure NEXT_PUBLIC_* fail-fast env vars (lib/env.ts) are
// present in the Playwright process AND inherited by webServer subprocess.
// Required because hero/cta/landing-nav/login all import env.ts at module
// load and SSR throws if any var is missing. webServer.env alone is not
// sufficient because Playwright spawns the dev server with a fresh env in
// some CI configurations.
process.env.NEXT_PUBLIC_SUPABASE_URL ??= "https://example.supabase.co"
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??= "dummy-key-for-e2e"
process.env.NEXT_PUBLIC_API_URL ??= "https://example.run.app"
process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ??= "Nikita_my_bot"

const PORT = 3003

export default defineConfig({
  testDir: "./e2e",
  globalSetup: require.resolve("./e2e/global-env-setup.ts"),
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
      NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: "Nikita_my_bot",
    },
  },
})
