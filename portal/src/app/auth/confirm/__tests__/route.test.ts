/**
 * Vitest coverage for /auth/confirm route handler — Spec 216 EM-2
 * autobind-Telegram wiring.
 *
 * The route's verifyOtp call is mocked at module boundary; we assert
 * that on success it (a) POSTs to /api/v1/auth/autobind-telegram with
 * the Bearer access_token, (b) does NOT block the redirect on a 5xx,
 * and (c) does NOT block on a 409 (the wizard renders an inline
 * banner downstream — confirm route still 302s to the interstitial).
 *
 * The verifyOtp-failure path is also covered to guard against the
 * autobind helper firing on errors (which would leak a side-effect
 * for an un-authenticated session).
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"

// ---------------------------------------------------------------------------
// Mocks at module boundary. `next/server` redirects must be observable but
// not instantiate a real Next response.
// ---------------------------------------------------------------------------

const verifyOtp = vi.fn()
const cookieStoreGetAll = vi.fn(() => [])

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    auth: { verifyOtp },
  })),
}))

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    getAll: cookieStoreGetAll,
    set: vi.fn(),
  })),
}))

// Capture `NextResponse.redirect` calls without driving Next runtime.
const redirectCalls: Array<{ url: string; status?: number }> = []
vi.mock("next/server", () => ({
  NextResponse: {
    redirect: (url: string, init?: { status?: number }) => {
      redirectCalls.push({ url, status: init?.status })
      return { url, status: init?.status ?? 302 } as unknown
    },
  },
}))

// Stable env. The route reads NEXT_PUBLIC_SUPABASE_URL etc.; vitest.setup.ts
// already stubs the Telegram bot username.
process.env.NEXT_PUBLIC_SUPABASE_URL = "https://stub.supabase.co"
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "stub-anon-key"
process.env.NEXT_PUBLIC_API_URL = "https://api.stub.test"

let GET: (req: Request) => Promise<Response | unknown>

beforeEach(async () => {
  vi.resetModules()
  vi.restoreAllMocks()
  redirectCalls.length = 0
  verifyOtp.mockReset()
  // Re-import after resetModules so module-level vi.mock() bindings reapply.
  ;({ GET } = await import("../route"))
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function buildRequest(params: Record<string, string>): Request {
  const url = new URL("https://portal.test/auth/confirm")
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, v)
  }
  return new Request(url.toString())
}

describe("GET /auth/confirm — Spec 216 EM-2 autobind", () => {
  it("calls /api/v1/auth/autobind-telegram with access_token after verifyOtp success", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: "ACCESS-XYZ" } },
      error: null,
    })
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({ bound: true, already_bound: false, no_session: false }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [calledUrl, init] = fetchSpy.mock.calls[0]
    expect(String(calledUrl)).toBe(
      "https://api.stub.test/api/v1/auth/autobind-telegram",
    )
    expect(init?.method).toBe("POST")
    const headers = init?.headers as Record<string, string> | undefined
    expect(headers?.Authorization).toBe("Bearer ACCESS-XYZ")

    // Redirect to the interstitial happens regardless of bind body.
    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
  })

  it("does NOT block redirect when autobind returns 5xx (no-session-or-infra-hiccup tolerant)", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: "ACCESS-XYZ" } },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("infra hiccup", { status: 503 }),
    )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
  })

  it("does NOT block redirect on 409 conflict (cross-user telegram bind, E4/E13)", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: "ACCESS-XYZ" } },
      error: null,
    })
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "telegram_already_bound_to_other_user" }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
    // The route logs the conflict so it is observable without surfacing
    // the raw backend body to the user.
    expect(warnSpy).toHaveBeenCalled()
    warnSpy.mockRestore()
  })

  it("does NOT call autobind on verifyOtp failure (no leaked side-effect)", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: null,
      error: { message: "Token has expired or is invalid" },
    })
    const fetchSpy = vi.spyOn(globalThis, "fetch")

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(fetchSpy).not.toHaveBeenCalled()
    // Failure redirects to /onboarding/auth?error=link_expired
    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toMatch(/\/onboarding\/auth\?error=/)
  })

  it("does NOT call autobind when verifyOtp returns no session.access_token", async () => {
    // Supabase historically returns `data` without `session` for certain
    // OTP types (e.g. invite). The autobind helper must be a no-op then.
    verifyOtp.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    })
    const fetchSpy = vi.spyOn(globalThis, "fetch")

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(fetchSpy).not.toHaveBeenCalled()
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
  })
})
