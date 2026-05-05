/**
 * Spec 215 PR-F2a / Tasks T021 — `/auth/confirm` server route handler tests.
 *
 * Behavior under test (FR-6):
 * - GET reads `?token_hash`, `?type`, `?next` from URL.
 * - Calls `supabase.auth.verifyOtp({token_hash, type})` server-side via
 *   `createServerClient` from `@supabase/ssr` (sets cookies on response).
 * - On success → 302 redirect to `/auth/interstitial?next=<encoded same-origin path>`.
 * - On error or missing params → 302 redirect to
 *   `/onboarding/auth?error=<sanitized_code>` (EM-1: funnel-copy
 *   consistency — failures land back in the wizard funnel, not /login).
 * - `type` from query is passed VERBATIM to verifyOtp (no hardcoded literal).
 *   Testing H2 regression: a static-source grep gate asserts no
 *   `'magiclink'` or `'signup'` literal exists in the handler source.
 * - EM-1: route is always live (no NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP gate).
 *
 * Mapped: AC-6.1, AC-6.2, AC-6.3, AC-6.7, AC-6.8, FR-6, Testing H2, EM-1.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

// ---------------------------------------------------------------------------
// Mock @supabase/ssr — control verifyOtp behavior per test
// ---------------------------------------------------------------------------
const mockVerifyOtp = vi.fn()
const mockCreateServerClient = vi.fn(() => ({
  auth: { verifyOtp: mockVerifyOtp },
}))

vi.mock("@supabase/ssr", () => ({
  createServerClient: (...args: unknown[]) =>
    (mockCreateServerClient as (...a: unknown[]) => unknown)(...args),
}))

// next/headers cookies() shim — route handler calls it for the cookie adapter
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    getAll: () => [],
    set: vi.fn(),
  })),
}))

const ORIGINAL_FLAG = process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP
const ORIGINAL_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const ORIGINAL_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

beforeEach(() => {
  vi.clearAllMocks()
  process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP = "true"
  process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co"
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "test-anon-key"
})

afterEach(() => {
  process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP = ORIGINAL_FLAG
  process.env.NEXT_PUBLIC_SUPABASE_URL = ORIGINAL_URL
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = ORIGINAL_KEY
})

async function loadHandler() {
  // Re-import per test so flag changes take effect
  vi.resetModules()
  return await import("@/app/auth/confirm/route")
}

function makeRequest(qs: string): Request {
  return new Request(`https://nikita-mygirl.com/auth/confirm${qs}`)
}

// ---------------------------------------------------------------------------
// Happy path
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — happy path (AC-6.1, AC-6.7)", () => {
  it("verifyOtp success → 302 to /auth/interstitial?next=...", async () => {
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=/dashboard"))
    expect(res.status).toBe(302)
    const loc = res.headers.get("location") ?? ""
    expect(loc).toContain("/auth/interstitial")
    expect(loc).toContain("next=%2Fdashboard")
  })

  it("calls verifyOtp with token_hash and type from URL (verbatim)", async () => {
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    await GET(makeRequest("?token_hash=hash123&type=signup&next=/dashboard"))
    expect(mockVerifyOtp).toHaveBeenCalledWith({
      token_hash: "hash123",
      type: "signup",
    })
  })
})

// ---------------------------------------------------------------------------
// Missing params (AC-6.2)
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — missing params (AC-6.2)", () => {
  it("missing token_hash → 302 /onboarding/auth?error=missing_params", async () => {
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?type=magiclink&next=/dashboard"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/onboarding/auth?error=missing_params")
    expect(mockVerifyOtp).not.toHaveBeenCalled()
  })

  it("missing type → 302 /onboarding/auth?error=missing_params", async () => {
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&next=/dashboard"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/onboarding/auth?error=missing_params")
    expect(mockVerifyOtp).not.toHaveBeenCalled()
  })

  it("missing next falls back to /dashboard (default safe target)", async () => {
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/auth/interstitial")
    expect(res.headers.get("location")).toContain("next=%2Fdashboard")
  })
})

// ---------------------------------------------------------------------------
// verifyOtp errors (AC-6.3, AC-6.8)
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — verifyOtp errors (AC-6.3, AC-6.8)", () => {
  it("expired-token error → 302 /login?error=link_expired", async () => {
    mockVerifyOtp.mockResolvedValue({
      data: { user: null },
      error: { message: "Token has expired or is invalid", status: 401 },
    })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=/dashboard"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/onboarding/auth?error=link_expired")
  })

  it("generic verifyOtp error → 302 /login?error=auth_confirm_failed", async () => {
    mockVerifyOtp.mockResolvedValue({
      data: { user: null },
      error: { message: "something went wrong", status: 500 },
    })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=/dashboard"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/onboarding/auth?error=auth_confirm_failed")
  })
})

// ---------------------------------------------------------------------------
// Open-redirect protection (NFR-Sec-1)
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — same-origin next sanitization", () => {
  it("rejects next=//evil.com — falls back to /dashboard", async () => {
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=//evil.com"))
    expect(res.headers.get("location")).toContain("next=%2Fdashboard")
    expect(res.headers.get("location")).not.toContain("evil.com")
  })

  it("rejects next=https://evil.com — falls back to /dashboard", async () => {
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=https://evil.com"))
    expect(res.headers.get("location")).toContain("next=%2Fdashboard")
    expect(res.headers.get("location")).not.toContain("evil.com")
  })
})

// ---------------------------------------------------------------------------
// EM-1: route is always live (no NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP gate)
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — always live (EM-1)", () => {
  it("does NOT return 404 when NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP is unset", async () => {
    delete process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP
    const { GET } = await loadHandler()
    const res = await GET(makeRequest(""))
    // Missing token_hash + type → 302 to /onboarding/auth?error=missing_params,
    // NOT a 404 (the legacy feature-flag gate was removed in EM-1).
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain(
      "/onboarding/auth?error=missing_params",
    )
  })

  it("does NOT return 404 when NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP='false'", async () => {
    process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP = "false"
    mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?token_hash=abc&type=magiclink&next=/onboarding"))
    // Verifies the route reaches verifyOtp and 302s to interstitial regardless
    // of the legacy flag value.
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/auth/interstitial")
    expect(mockVerifyOtp).toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// I-1 fix — runtime allow-list validation of `?type=` URL parameter
// ---------------------------------------------------------------------------
describe("GET /auth/confirm — runtime type allow-list (I-1)", () => {
  it("rejects bogus type with invalid_type error", async () => {
    const { GET } = await loadHandler()
    const res = await GET(makeRequest("?type=arbitrary&token_hash=abc&next=/foo"))
    expect(res.status).toBe(302)
    expect(res.headers.get("location")).toContain("/onboarding/auth?error=invalid_type")
    expect(mockVerifyOtp).not.toHaveBeenCalled()
  })

  const validTypes: ReadonlyArray<string> = [
    "signup",
    "magiclink",
    "recovery",
    "invite",
    "email_change",
    "email",
  ]
  for (const t of validTypes) {
    it(`accepts valid type '${t}' and forwards verbatim to verifyOtp`, async () => {
      mockVerifyOtp.mockResolvedValue({ data: { user: { id: "u1" } }, error: null })
      const { GET } = await loadHandler()
      await GET(makeRequest(`?token_hash=hash123&type=${t}&next=/dashboard`))
      expect(mockVerifyOtp).toHaveBeenCalledWith({
        token_hash: "hash123",
        type: t,
      })
    })
  }
})

// ---------------------------------------------------------------------------
// Testing H2 regression — no hardcoded verification_type literal in handler
// (tightened per I-2: also asserts a runtime allow-list exists)
// ---------------------------------------------------------------------------
describe("Testing H2 — handler source has no hardcoded 'magiclink'/'signup' literal", () => {
  it("route.ts contains no Constant 'magiclink' or 'signup' outside Literal[...] type narrowing AND has VALID_OTP_TYPES allow-list", () => {
    const handlerPath = resolve(__dirname, "../../../../src/app/auth/confirm/route.ts")
    const source = readFileSync(handlerPath, "utf-8")

    // I-2 tightening: the handler MUST declare a runtime allow-list constant.
    // This makes the gate impossible to bypass via a silent `as EmailOtpType`
    // cast over an arbitrary string from the URL.
    expect(source).toContain("VALID_OTP_TYPES")

    // Strip TS type-narrowing literal unions like `"magiclink" | "signup"` and
    // `as "magiclink"` style annotations, including any `EmailOtpType` casts.
    // Also strip the VALID_OTP_TYPES allow-list declaration (its values are
    // validated INPUT, not coerced output — they cannot reach verifyOtp unless
    // the URL-supplied value matches one of them).
    const stripped = source
      // Strip line comments
      .replace(/\/\/.*$/gm, "")
      // Strip block comments
      .replace(/\/\*[\s\S]*?\*\//g, "")
      // Strip the VALID_OTP_TYPES allow-list array literal (declaration line)
      .replace(/const\s+VALID_OTP_TYPES[\s\S]*?\]\s*as\s+const/g, "const VALID_OTP_TYPES = []")
      .replace(/const\s+VALID_OTP_TYPES[^=]*=\s*\[[^\]]*\]/g, "const VALID_OTP_TYPES = []")
      // Strip TS-only type union members: "magiclink" | "signup" etc.
      .replace(/:\s*("magiclink"|"signup")(\s*\|\s*"[a-z_]+")*/g, ":TYPE")
      .replace(/(\s*\|\s*("magiclink"|"signup"))/g, "")
      // Strip `as "magiclink"` / `as "signup"` casts
      .replace(/\bas\s+("magiclink"|"signup")/g, "as TYPE")

    expect(stripped).not.toContain('"magiclink"')
    expect(stripped).not.toContain('"signup"')
    expect(stripped).not.toContain("'magiclink'")
    expect(stripped).not.toContain("'signup'")
  })
})
