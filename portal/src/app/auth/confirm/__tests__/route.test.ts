/**
 * Vitest coverage for /auth/confirm route handler — Spec 216 EM-2
 * autobind-Telegram wiring + W1 session hygiene + W3 pending-user redirect.
 *
 * The route's verifyOtp call is mocked at module boundary; we assert
 * that on success it (a) POSTs to /api/v1/auth/autobind-telegram with
 * the Bearer access_token, (b) does NOT block the redirect on a 5xx
 * (continues to interstitial), and (c) DOES redirect to
 * /login?error=telegram_conflict on 409 (cross-user telegram_id conflict
 * surfaces a user-facing toast via the existing ERROR_TOASTS registry on
 * /login — Spec 216-G removed the legacy /onboarding/auth surface).
 *
 * The verifyOtp-failure path is also covered to guard against the
 * autobind helper firing on errors (which would leak a side-effect
 * for an un-authenticated session).
 *
 * W1 (CRITICAL): signOut({scope:'local'}) is called BEFORE verifyOtp to
 * prevent cross-user session leakage when User-B clicks a magic link in a
 * browser that already has User-A's session active.
 *
 * W3 (HIGH): after autobind, the route checks users.onboarding_status and
 * redirects pending users to /onboarding (or the safe next= param) rather
 * than always falling through to /dashboard.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"

// ---------------------------------------------------------------------------
// Mocks at module boundary. `next/server` redirects must be observable but
// not instantiate a real Next response.
// ---------------------------------------------------------------------------

const verifyOtp = vi.fn()
const signOut = vi.fn()
const cookieStoreGetAll = vi.fn(() => [])

// fromSelect mock — returns a chainable builder so route can call
// supabase.from("users").select("onboarding_status").eq("id", uid).single()
const mockSingle = vi.fn()
const mockEq = vi.fn(() => ({ single: mockSingle }))
const mockSelect = vi.fn(() => ({ eq: mockEq }))
const mockFrom = vi.fn(() => ({ select: mockSelect }))

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    auth: { verifyOtp, signOut },
    from: mockFrom,
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
  signOut.mockReset()
  signOut.mockResolvedValue({ error: null })
  mockSingle.mockReset()
  mockEq.mockReturnValue({ single: mockSingle })
  mockSelect.mockReturnValue({ eq: mockEq })
  mockFrom.mockReturnValue({ select: mockSelect })
  // Default: user is completed (no change to existing redirect behaviour).
  mockSingle.mockResolvedValue({
    data: { onboarding_status: "completed" },
    error: null,
  })
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

  it("redirects to /login?error=telegram_conflict on 409 (cross-user bind, E4/E13)", async () => {
    // 409 must surface a user-facing toast via the ERROR_TOASTS registry
    // on /login (Spec 216-G), not be silently swallowed into the
    // interstitial.
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
    expect(redirectCalls[0].url).toContain(
      "/login?error=telegram_conflict",
    )
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
    // Failure redirects to /login?error=link_expired (Spec 216-G)
    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toMatch(/\/login\?error=/)
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

  // GH #570 — `?next=` honour regression guard.
  // Walk B4 (2026-05-08) reported `/auth/confirm?next=/onboarding` landing
  // on `/dashboard`. Code review showed the route preserves `next` correctly;
  // these tests lock the contract so any future regression surfaces immediately.
  describe("next= param honour (GH #570)", () => {
    it("forwards next=/onboarding to interstitial URL on autobind ok", async () => {
      verifyOtp.mockResolvedValueOnce({
        data: { session: { access_token: "ACCESS-XYZ" } },
        error: null,
      })
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({ bound: true, already_bound: false, no_session: false }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )

      await GET(
        buildRequest({
          token_hash: "T",
          type: "magiclink",
          next: "/onboarding",
        }),
      )

      expect(redirectCalls).toHaveLength(1)
      expect(redirectCalls[0].url).toBe(
        "https://portal.test/auth/interstitial?next=%2Fonboarding",
      )
    })

    it("falls back to /dashboard when next is missing", async () => {
      verifyOtp.mockResolvedValueOnce({
        data: { session: { access_token: "ACCESS-XYZ" } },
        error: null,
      })
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({ bound: true, already_bound: false, no_session: false }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )

      await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

      expect(redirectCalls).toHaveLength(1)
      expect(redirectCalls[0].url).toContain("next=%2Fdashboard")
    })

    it("rejects protocol-relative next (//evil.com), falls back to /dashboard", async () => {
      verifyOtp.mockResolvedValueOnce({
        data: { session: { access_token: "ACCESS-XYZ" } },
        error: null,
      })
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response(
          JSON.stringify({ bound: true, already_bound: false, no_session: false }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )

      await GET(
        buildRequest({
          token_hash: "T",
          type: "magiclink",
          next: "//evil.com/pwn",
        }),
      )

      expect(redirectCalls).toHaveLength(1)
      // Same-origin guard rejects // and falls back to /dashboard.
      expect(redirectCalls[0].url).toContain("next=%2Fdashboard")
      expect(redirectCalls[0].url).not.toContain("evil.com")
    })

    it("forwards next=/onboarding even when autobind returns infra_error (5xx)", async () => {
      verifyOtp.mockResolvedValueOnce({
        data: { session: { access_token: "ACCESS-XYZ" } },
        error: null,
      })
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response("infra hiccup", { status: 503 }),
      )

      await GET(
        buildRequest({
          token_hash: "T",
          type: "magiclink",
          next: "/onboarding",
        }),
      )

      expect(redirectCalls).toHaveLength(1)
      expect(redirectCalls[0].url).toBe(
        "https://portal.test/auth/interstitial?next=%2Fonboarding",
      )
    })
  })
})

// ---------------------------------------------------------------------------
// W1 — Cross-user session leakage fix (CRITICAL)
// signOut({scope:'local'}) must be called BEFORE verifyOtp so any
// pre-existing session is cleared before a new magic-link is processed.
// ---------------------------------------------------------------------------
describe("W1 — signOut called before verifyOtp (cross-user session hygiene)", () => {
  it("test_signOut_called_before_verifyOtp: signOut fires before verifyOtp on every successful request", async () => {
    const callOrder: string[] = []
    signOut.mockImplementation(async () => {
      callOrder.push("signOut")
      return { error: null }
    })
    verifyOtp.mockImplementation(async () => {
      callOrder.push("verifyOtp")
      return {
        data: { session: { access_token: "ACCESS-XYZ" } },
        error: null,
      }
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ bound: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(callOrder).toEqual(["signOut", "verifyOtp"])
    expect(signOut).toHaveBeenCalledWith({ scope: "local" })
  })

  it("continues to verifyOtp even when signOut returns an error (no existing session is fine)", async () => {
    // signOut on a session-less browser returns an error; must not abort the flow.
    signOut.mockResolvedValueOnce({ error: { message: "no session" } })
    verifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: "ACCESS-XYZ" } },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ bound: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    // Still reaches interstitial — signOut error is non-fatal
    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
    expect(verifyOtp).toHaveBeenCalledTimes(1)
  })

  it("signOut throwing (rejected promise) does not halt verifyOtp flow", async () => {
    // Tests the try/catch at route.ts:124. The previous test only covers the
    // case where signOut resolves with {error}; this one covers a thrown/rejected
    // promise (e.g., network failure mid-request), which is the other branch of
    // the try/catch that was untested.
    signOut.mockRejectedValueOnce(new Error("network error"))
    verifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: "ACCESS-XYZ" } },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ bound: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )

    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    // catch block absorbed the throw — verifyOtp and redirect still run
    expect(verifyOtp).toHaveBeenCalledTimes(1)
    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain("/auth/interstitial")
  })
})

// ---------------------------------------------------------------------------
// W3 — pending users redirected to /onboarding (HIGH)
// After autobind, the route must check users.onboarding_status and send
// pending users to /onboarding, not /dashboard.
// ---------------------------------------------------------------------------
describe("W3 — onboarding_status check controls redirect destination", () => {
  function autobindOkResponse() {
    return new Response(
      JSON.stringify({ bound: true, already_bound: false, no_session: false }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    )
  }

  it("test_pending_user_with_next_onboarding_redirects_to_onboarding: pending user + next=/onboarding → interstitial wrapping /onboarding (documentation test)", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: {
        session: { access_token: "ACCESS-XYZ" },
        user: { id: "uid-pending" },
      },
      error: null,
    })
    mockSingle.mockResolvedValueOnce({
      data: { onboarding_status: "pending" },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(autobindOkResponse())

    await GET(
      buildRequest({ token_hash: "T", type: "magiclink", next: "/onboarding" }),
    )

    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain(
      "/auth/interstitial?next=%2Fonboarding",
    )
    // onboarding_status was queried
    expect(mockFrom).toHaveBeenCalledWith("users")
  })

  it("test_pending_user_W3_override: pending user with next=/dashboard → W3 overrides to /onboarding (not /dashboard)", async () => {
    // This test FALSIFIES W3: if the W3 branch were deleted, next=/dashboard would
    // pass through unchanged and the assertion would fail. next=/onboarding in the
    // previous test is indistinguishable from a fallthrough, so this test supplies
    // a different next= value to prove the override is active.
    verifyOtp.mockResolvedValueOnce({
      data: {
        session: { access_token: "ACCESS-XYZ" },
        user: { id: "uid-pending" },
      },
      error: null,
    })
    mockSingle.mockResolvedValueOnce({
      data: { onboarding_status: "pending" },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(autobindOkResponse())

    await GET(
      buildRequest({ token_hash: "T", type: "magiclink", next: "/dashboard" }),
    )

    expect(redirectCalls).toHaveLength(1)
    // W3 must redirect to /onboarding, NOT pass through /dashboard
    expect(redirectCalls[0].url).toContain(
      "/auth/interstitial?next=%2Fonboarding",
    )
    expect(redirectCalls[0].url).not.toContain("%2Fdashboard")
  })

  it("test_pending_user_no_next_redirects_to_onboarding: pending user with no next= still lands on /onboarding", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: {
        session: { access_token: "ACCESS-XYZ" },
        user: { id: "uid-pending" },
      },
      error: null,
    })
    mockSingle.mockResolvedValueOnce({
      data: { onboarding_status: "pending" },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(autobindOkResponse())

    // No next= param — the old default /dashboard must NOT win for pending users
    await GET(buildRequest({ token_hash: "T", type: "magiclink" }))

    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain(
      "/auth/interstitial?next=%2Fonboarding",
    )
  })

  it("test_completed_user_redirects_to_dashboard_or_safe_next: completed user with next=/dashboard stays on /dashboard", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: {
        session: { access_token: "ACCESS-XYZ" },
        user: { id: "uid-completed" },
      },
      error: null,
    })
    // Default mockSingle returns completed; explicit for clarity.
    mockSingle.mockResolvedValueOnce({
      data: { onboarding_status: "completed" },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(autobindOkResponse())

    await GET(
      buildRequest({ token_hash: "T", type: "magiclink", next: "/dashboard" }),
    )

    expect(redirectCalls).toHaveLength(1)
    expect(redirectCalls[0].url).toContain(
      "/auth/interstitial?next=%2Fdashboard",
    )
  })

  it("test_completed_user_with_unsafe_next_falls_back_to_dashboard: open-redirect guard still active for completed users", async () => {
    verifyOtp.mockResolvedValueOnce({
      data: {
        session: { access_token: "ACCESS-XYZ" },
        user: { id: "uid-completed" },
      },
      error: null,
    })
    mockSingle.mockResolvedValueOnce({
      data: { onboarding_status: "completed" },
      error: null,
    })
    vi.spyOn(globalThis, "fetch").mockResolvedValue(autobindOkResponse())

    // protocol-relative URL must be rejected
    await GET(
      buildRequest({
        token_hash: "T",
        type: "magiclink",
        next: "//evil.com/pwn",
      }),
    )

    expect(redirectCalls).toHaveLength(1)
    // Must fall back to /dashboard, not evil.com
    expect(redirectCalls[0].url).toContain("next=%2Fdashboard")
    expect(redirectCalls[0].url).not.toContain("evil.com")
  })
})
