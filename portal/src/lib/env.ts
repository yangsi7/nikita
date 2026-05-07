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

// CRITICAL — Spec 216-H PR-F hotfix (2026-05-07):
//
// MUST use STATIC `process.env.X` member access for `NEXT_PUBLIC_*` vars.
// Next.js (and Turbopack / Webpack) only inline `process.env.X` into the
// CLIENT bundle when the access is a STATIC literal property reference.
// Dynamic indexing — `process.env[key]`, `process.env[REQUIRED_VARS[i]]`,
// destructuring via a variable — is NOT replaced; it remains a runtime
// `process.env` read, and `process.env` is `{}` in the browser.
//
// Prior implementation used `for (const key of REQUIRED_VARS) ...
// process.env[key]`, which compiled to runtime `process.env[key]`. Result:
// every browser page load on prod crashed with "Missing required public
// env vars" (post-PR-E #538 incident, 2026-05-07).
//
// Reference: https://nextjs.org/docs/app/api-reference/config/next-config-js/env
//   "Note: To inline an environment variable, you must use the syntax
//   process.env.[NAME]. Other syntax (such as destructuring) will not
//   work."
//
// Test-env exception: vitest sets NODE_ENV=test; the production fail-fast
// is gated on `process.env.NODE_ENV === "production"` so test runs get
// empty-string fallbacks.

const RAW_SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL
const RAW_TELEGRAM_BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME

function readRequired(): {
  SUPABASE_URL: string
  API_URL: string
  TELEGRAM_BOT_USERNAME: string
} {
  const missing: string[] = []
  if (!RAW_SUPABASE_URL) missing.push("NEXT_PUBLIC_SUPABASE_URL")
  if (!RAW_API_URL) missing.push("NEXT_PUBLIC_API_URL")
  if (!RAW_TELEGRAM_BOT_USERNAME) missing.push("NEXT_PUBLIC_TELEGRAM_BOT_USERNAME")

  // Fail-fast ONLY in production (`next build` / `next start` on Vercel).
  // Dev (`next dev`) and test (vitest, playwright E2E) get an empty-string
  // fallback so module-load does not throw when env vars are missing.
  // Rationale: Spec 216-G found that Next.js 16 Turbopack workers in CI
  // do not reliably inherit env vars set by the parent shell, webServer.env,
  // inline shell env-prefix, or .env.local writes (see PR #537 commit
  // history — 7 attempts failed). Production fail-fast is the only place
  // we actually need this guard; dev / E2E can tolerate empty strings.
  if (missing.length > 0 && process.env.NODE_ENV === "production") {
    throw new Error(
      `[portal/lib/env] Missing required public env vars: ${missing.join(
        ", "
      )}. Set them in Vercel project settings (or .env.local for dev).`
    )
  }

  return {
    SUPABASE_URL: RAW_SUPABASE_URL ?? "",
    API_URL: RAW_API_URL ?? "",
    TELEGRAM_BOT_USERNAME: RAW_TELEGRAM_BOT_USERNAME ?? "",
  }
}

const required = readRequired()

export const env = {
  SUPABASE_URL: required.SUPABASE_URL,
  API_URL: required.API_URL,
  TELEGRAM_BOT_USERNAME: required.TELEGRAM_BOT_USERNAME,
} as const

export type PortalEnv = typeof env
