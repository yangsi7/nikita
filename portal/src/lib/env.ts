/**
 * Spec 216-EM3a — fail-fast env module.
 *
 * NOTE: `env.TELEGRAM_BOT_USERNAME` has no consumer on master until
 * EM-2 (Telegram auto-bind PR); the export exists now to unblock that
 * PR. Do NOT delete during drift audits.
 *
 * Centralizes the public env vars the portal cannot run without and
 * throws at module-load time when any required var is missing. This
 * surfaces misconfiguration immediately on app boot instead of letting
 * a `process.env.X!` non-null assertion silently propagate `undefined`
 * into Supabase / fetch / deep-link string interpolation, which then
 * fails further downstream with confusing errors (e.g. "Invalid URL").
 *
 * Required public vars:
 *   - NEXT_PUBLIC_SUPABASE_URL       — Supabase project URL (auth + data)
 *   - NEXT_PUBLIC_API_URL            — FastAPI backend base URL
 *   - NEXT_PUBLIC_TELEGRAM_BOT_USERNAME — Telegram bot username for deep
 *                                        links (consumed by EM-2; this
 *                                        module makes the value available
 *                                        before EM-2 lands so callers can
 *                                        migrate without another shim).
 *
 * Test-env exception: vitest tests run with `process.env.NODE_ENV ===
 * "test"` and frequently do not set NEXT_PUBLIC_* vars. Skipping the
 * throw in that mode keeps the test surface unchanged. Production /
 * development boots still fail fast.
 */

type RequiredKey =
  | "NEXT_PUBLIC_SUPABASE_URL"
  | "NEXT_PUBLIC_API_URL"
  | "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME"

const REQUIRED_VARS: readonly RequiredKey[] = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_API_URL",
  "NEXT_PUBLIC_TELEGRAM_BOT_USERNAME",
] as const

function readRequired(): Record<RequiredKey, string> {
  const out: Partial<Record<RequiredKey, string>> = {}
  const missing: RequiredKey[] = []

  for (const key of REQUIRED_VARS) {
    const value = process.env[key]
    if (!value || value.length === 0) {
      missing.push(key)
    } else {
      out[key] = value
    }
  }

  // Fail-fast ONLY in production (`next build` / `next start` on Vercel).
  // Dev (`next dev`) and test (vitest, playwright E2E) get an empty-string
  // fallback so module-load does not throw when env vars are missing.
  // Rationale: Spec 216-G found that Next.js 16 Turbopack workers in CI
  // do not reliably inherit env vars set by the parent shell, webServer.env,
  // inline shell env-prefix, or .env.local writes (see PR #537 commit
  // history — 7 attempts failed). Production fail-fast is the only place
  // we actually need this guard; dev / E2E can tolerate empty strings
  // because:
  //   - Vercel builds set the vars via dashboard config (production gate).
  //   - Vitest sets NODE_ENV=test and skips heavy SSR.
  //   - Playwright E2E uses E2E_AUTH_BYPASS=true and dummy backends.
  if (missing.length > 0 && process.env.NODE_ENV === "production") {
    throw new Error(
      `[portal/lib/env] Missing required public env vars: ${missing.join(
        ", "
      )}. Set them in Vercel project settings (or .env.local for dev).`
    )
  }

  // Fill missing with empty strings so the typed shape is satisfied in
  // test mode. Callers should not read these in tests; if they do, the
  // empty string surfaces as a fast failure at use-site rather than a
  // module-load throw.
  for (const key of REQUIRED_VARS) {
    if (out[key] === undefined) {
      out[key] = ""
    }
  }

  return out as Record<RequiredKey, string>
}

const required = readRequired()

export const env = {
  SUPABASE_URL: required.NEXT_PUBLIC_SUPABASE_URL,
  API_URL: required.NEXT_PUBLIC_API_URL,
  TELEGRAM_BOT_USERNAME: required.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME,
} as const

export type PortalEnv = typeof env
