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
 */

const REQUIRED_KEYS = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME",
] as const

describe("portal/lib/env", () => {
  const originalEnv = { ...process.env }

  beforeEach(() => {
    vi.resetModules()
    // Strip required keys so each test starts from a known-clean state.
    for (const key of REQUIRED_KEYS) {
      delete process.env[key]
    }
  })

  afterEach(() => {
    process.env = { ...originalEnv }
  })

  it("exports values from process.env when all required vars are set", async () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co"
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com"
    process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME = "Nikita_my_bot"

    const { env } = await import("@/lib/env")

    expect(env.SUPABASE_URL).toBe("https://example.supabase.co")
    expect(env.API_URL).toBe("https://api.example.com")
    expect(env.TELEGRAM_BOT_USERNAME).toBe("Nikita_my_bot")
  })

  it("throws when required vars are missing in non-test envs (production)", async () => {
    process.env.NODE_ENV = "production"
    // Set two of three so we can assert the missing one is named in the
    // error message.
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co"
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.com"
    // NEXT_PUBLIC_TELEGRAM_BOT_USERNAME intentionally unset.

    await expect(import("@/lib/env")).rejects.toThrow(
      /NEXT_PUBLIC_TELEGRAM_BOT_USERNAME/
    )
  })

  it("throws when required vars are missing in development", async () => {
    process.env.NODE_ENV = "development"
    // All three intentionally unset.

    await expect(import("@/lib/env")).rejects.toThrow(
      /Missing required public env vars/
    )
  })

  it("does NOT throw when required vars are missing under NODE_ENV=test", async () => {
    process.env.NODE_ENV = "test"
    // All three intentionally unset.

    const mod = await import("@/lib/env")
    expect(mod.env.SUPABASE_URL).toBe("")
    expect(mod.env.API_URL).toBe("")
    expect(mod.env.TELEGRAM_BOT_USERNAME).toBe("")
  })

  it("treats empty-string values as missing", async () => {
    process.env.NODE_ENV = "production"
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co"
    process.env.NEXT_PUBLIC_API_URL = ""
    process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME = "Nikita_my_bot"

    await expect(import("@/lib/env")).rejects.toThrow(
      /NEXT_PUBLIC_API_URL/
    )
  })
})
