import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

/**
 * Spec 216-EM3a — fail-fast env module tests.
 *
 * The module reads `process.env` at module-load time and (in non-test
 * envs) throws when required public vars are missing. We exercise the
 * three branches:
 *   1. all vars present → exported `env` object reflects them
 *   2. missing in NODE_ENV=production → throws
 *   3. missing in NODE_ENV=test → does NOT throw (test-runner exception)
 *
 * Each test uses `vi.resetModules()` + a fresh dynamic `import()` so the
 * module's top-level `readRequired()` runs against the current
 * `process.env`.
 *
 * NOTE: `NODE_ENV` is typed as a read-only union under `@types/node`'s
 * `NodeJS.ProcessEnv`, so direct assignment fails CI's TS type-check
 * with TS2540. Use `vi.stubEnv("NODE_ENV", ...)` + `vi.unstubAllEnvs()`
 * which vitest types accept and which auto-restore between tests.
 */

const REQUIRED_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME",
] as const

describe("portal/lib/env", () => {
  beforeEach(() => {
    vi.resetModules()
    // Strip required keys so each test starts from a known-clean state.
    for (const key of REQUIRED_KEYS) {
      vi.stubEnv(key, "")
      delete process.env[key]
    }
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("exports values from process.env when all required vars are set", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com")
    vi.stubEnv("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME", "Nikita_my_bot")

    const { env } = await import("@/lib/env")

    expect(env.SUPABASE_URL).toBe("https://example.supabase.co")
    expect(env.API_URL).toBe("https://api.example.com")
    expect(env.TELEGRAM_BOT_USERNAME).toBe("Nikita_my_bot")
  })

  it("throws when required vars are missing in non-test envs (production)", async () => {
    vi.stubEnv("NODE_ENV", "production")
    // Set two of three so we can assert the missing one is named in the
    // error message.
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com")
    // NEXT_PUBLIC_TELEGRAM_BOT_USERNAME intentionally unset.

    await expect(import("@/lib/env")).rejects.toThrow(
      /NEXT_PUBLIC_TELEGRAM_BOT_USERNAME/
    )
  })

  it("does NOT throw when required vars are missing in development (Spec 216-G)", async () => {
    // Spec 216-G — fail-fast scoped to NODE_ENV=production only.
    // Dev (`next dev`) and E2E now get an empty-string fallback so that
    // Next.js 16 Turbopack workers (which do not reliably inherit env vars
    // from the parent shell in CI) can boot landing-nav / hero / etc. for
    // E2E tests. The production fail-fast on Vercel deploys still triggers.
    vi.stubEnv("NODE_ENV", "development")
    // All three intentionally unset.

    const mod = await import("@/lib/env")
    expect(mod.env.SUPABASE_URL).toBe("")
    expect(mod.env.API_URL).toBe("")
    expect(mod.env.TELEGRAM_BOT_USERNAME).toBe("")
  })

  it("does NOT throw when required vars are missing under NODE_ENV=test", async () => {
    vi.stubEnv("NODE_ENV", "test")
    // All three intentionally unset.

    const mod = await import("@/lib/env")
    expect(mod.env.SUPABASE_URL).toBe("")
    expect(mod.env.API_URL).toBe("")
    expect(mod.env.TELEGRAM_BOT_USERNAME).toBe("")
  })

  it("treats empty-string values as missing", async () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co")
    vi.stubEnv("NEXT_PUBLIC_API_URL", "")
    vi.stubEnv("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME", "Nikita_my_bot")

    await expect(import("@/lib/env")).rejects.toThrow(
      /NEXT_PUBLIC_API_URL/
    )
  })
})
