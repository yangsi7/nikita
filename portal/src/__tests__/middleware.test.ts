/**
 * Middleware tests — testing updateSession() from @/lib/supabase/middleware
 *
 * The middleware:
 * 1. Creates a Supabase server client
 * 2. Gets the current user via supabase.auth.getUser()
 * 3. Public routes (/login, /auth/*): redirect authenticated users to /dashboard or /admin
 * 4. Protected routes: redirect unauthenticated users to /login
 * 5. Admin routes (/admin*): redirect non-admin users to /dashboard
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { NextRequest } from "next/server"

// -------------------------------------------------------------------
// Helpers to build a NextRequest for a given path
// -------------------------------------------------------------------
function makeRequest(path: string): NextRequest {
  return new NextRequest(new URL(`http://localhost${path}`))
}

// -------------------------------------------------------------------
// Factory that builds a mock supabase client with a specific user
// -------------------------------------------------------------------
function mockSupabaseWithUser(user: object | null) {
  return {
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user }, error: null }),
    },
    cookies: {
      getAll: vi.fn().mockReturnValue([]),
      setAll: vi.fn(),
    },
  }
}

// -------------------------------------------------------------------
// Mock @supabase/ssr so createServerClient returns our mock
// -------------------------------------------------------------------
const mockCreateServerClient = vi.fn()

vi.mock("@supabase/ssr", () => ({
  createServerClient: (...args: unknown[]) => mockCreateServerClient(...args),
}))

// Import AFTER the mock is registered
const { updateSession } = await import("@/lib/supabase/middleware")

// -------------------------------------------------------------------
// Tests
// -------------------------------------------------------------------
describe("updateSession middleware", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ----------------------------------------------------------------
  // Unauthenticated user
  // ----------------------------------------------------------------
  describe("unauthenticated user", () => {
    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(null))
    })

    it("redirects to /login for /dashboard", async () => {
      const req = makeRequest("/dashboard")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/login")
    })

    it("redirects to /login for /admin", async () => {
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/login")
    })

    it("redirects to /login for arbitrary protected route", async () => {
      const req = makeRequest("/vices")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/login")
    })

    it("allows /login to pass through", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      // Non-redirect = either 200 (NextResponse.next()) — status 200 or no location header
      expect(res.headers.get("location")).toBeNull()
    })

    it("allows /auth/confirm to pass through (EM-1: unified callback)", async () => {
      const req = makeRequest("/auth/confirm")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("allows /auth/interstitial to pass through (Spec 215 FR-6)", async () => {
      const req = makeRequest("/auth/interstitial")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })
  })

  // ----------------------------------------------------------------
  // Player (non-admin) user
  // ----------------------------------------------------------------
  describe("authenticated player user", () => {
    const playerUser = {
      id: "player-1",
      email: "player@gmail.com",
      app_metadata: { role: "player" },
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(playerUser))
    })

    it("allows access to /dashboard", async () => {
      const req = makeRequest("/dashboard")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("redirects /admin to /dashboard for non-admin", async () => {
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("redirects /admin/users to /dashboard for non-admin", async () => {
      const req = makeRequest("/admin/users")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("redirects /login to /dashboard when already authenticated", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    // GH #524 — /auth/confirm is the PKCE verifyOtp route handler. It MUST
    // pass through regardless of session state so the route handler can mint
    // / refresh the session and issue its own redirect (typically to
    // /auth/interstitial?next=…). Middleware redirecting authed users away
    // from /auth/confirm aborts the code-exchange and drops `?next`.
    it("allows /auth/confirm to pass through when already authenticated (GH #524)", async () => {
      const req = makeRequest("/auth/confirm")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    // GH #524 — /auth/interstitial is the Spec 215 FR-6 user-gesture page
    // (Apple SFSafariViewController fix). It is rendered AFTER the session
    // is minted, so the visiting user is always authenticated. Middleware
    // MUST pass it through; otherwise the post-auth tap-to-continue page
    // would never render and `?next=/onboarding` would be dropped.
    it("allows /auth/interstitial to pass through when already authenticated (GH #524)", async () => {
      const req = makeRequest("/auth/interstitial")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("preserves ?next on /auth/interstitial when authenticated (GH #524)", async () => {
      const req = makeRequest("/auth/interstitial?next=/onboarding")
      const res = await updateSession(req)
      // Pass-through: no redirect, no Location header
      expect(res.headers.get("location")).toBeNull()
    })
  })

  // ----------------------------------------------------------------
  // Admin user via app_metadata.role (JWT claim; service-role-only)
  // ----------------------------------------------------------------
  describe("admin user (app_metadata.role)", () => {
    const adminUserMeta = {
      id: "admin-1",
      email: "someone@gmail.com",
      app_metadata: { role: "admin" },
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(adminUserMeta))
    })

    it("allows access to /admin", async () => {
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("allows access to /admin/users", async () => {
      const req = makeRequest("/admin/users")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("redirects /login to /admin when admin is authenticated", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/admin")
    })

    // GH #524 — pass-through must apply to admin users too. An admin who
    // re-clicks a magic link must still hit the PKCE handler; redirecting
    // to /admin would abort the code-exchange.
    it("allows /auth/confirm to pass through for admin user (GH #524)", async () => {
      const req = makeRequest("/auth/confirm")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    // GH #524 — admin users also land on /auth/interstitial after auth
    // (Apple SFSafariViewController fix). Middleware MUST NOT bounce them
    // to /admin; the interstitial page issues its own role-aware redirect.
    it("allows /auth/interstitial to pass through for admin user (GH #524)", async () => {
      const req = makeRequest("/auth/interstitial")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })
  })

  // ----------------------------------------------------------------
  // Security regression: @nanoleq.com email must NOT bypass role check
  // FE-003: email domain alone must never grant admin access
  // ----------------------------------------------------------------
  describe("security: @nanoleq.com email without admin role", () => {
    const nanoleqNoRole = {
      id: "attacker-1",
      email: "attacker@nanoleq.com",
      app_metadata: {},  // no role field — not a real admin
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(nanoleqNoRole))
    })

    it("denies access to /admin for @nanoleq.com user without admin role", async () => {
      // FE-003: email domain alone must not grant admin access.
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("denies access to /admin/users for @nanoleq.com user without admin role", async () => {
      const req = makeRequest("/admin/users")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("redirects /login to /dashboard (not /admin) for @nanoleq.com user without admin role", async () => {
      // A @nanoleq.com user with no role metadata is a plain player.
      // /login should send them to /dashboard, not /admin.
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
      expect(res.headers.get("location")).not.toContain("/admin")
    })
  })

  // ----------------------------------------------------------------
  // Security regression: @nanoleq.com WITH admin role must still work
  // FE-003: role=admin in metadata is the correct grant mechanism
  // ----------------------------------------------------------------
  describe("security: @nanoleq.com email WITH admin role", () => {
    const nanoleqWithRole = {
      id: "real-admin-1",
      email: "boss@nanoleq.com",
      app_metadata: { role: "admin" },
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(nanoleqWithRole))
    })

    it("allows access to /admin for @nanoleq.com user with admin role", async () => {
      // FE-003: role=admin in metadata should grant access regardless of email domain.
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("redirects /login to /admin for @nanoleq.com user with admin role", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/admin")
    })
  })

  // ----------------------------------------------------------------
  // Privesc regression: user_metadata.role === "admin" MUST NOT grant admin.
  // user_metadata is client-writable via supabase.auth.updateUser(), so any
  // authenticated user could self-escalate if we read role from there.
  // Admin is now gated on app_metadata.role (service-role-only).
  // ----------------------------------------------------------------
  describe("security: user_metadata.role=admin does NOT escalate", () => {
    const selfElevatedUser = {
      id: "attacker-2",
      email: "player@gmail.com",
      user_metadata: { role: "admin" },
      app_metadata: {},
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(selfElevatedUser))
    })

    it("denies /admin when only user_metadata.role is admin", async () => {
      const req = makeRequest("/admin")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("redirects /login to /dashboard (not /admin) when only user_metadata.role is admin", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
      expect(res.headers.get("location")).not.toContain("/admin")
    })
  })

  describe("Spec 214 T3.11 — onboarding_status='completed' skip", () => {
    const playerUser = {
      id: "player-1",
      email: "p@test.local",
      user_metadata: {},
      app_metadata: {},
    }
    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(playerUser))
    })

    it("AC-T3.11.1: completed user on /onboarding redirects to /dashboard", async () => {
      const req = new NextRequest(new URL("http://localhost/onboarding"))
      req.cookies.set("onboarding_status", "completed")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })

    it("non-completed user on /onboarding is NOT redirected (wizard paints)", async () => {
      const req = new NextRequest(new URL("http://localhost/onboarding"))
      // no onboarding_status cookie
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    // Spec 216-G removed /onboarding/auth — the test it carried (cookie
    // does not redirect that route to /dashboard) is no longer relevant.
    // Authed users hitting any /onboarding/* path with the cookie set
    // always bounce to /dashboard via the completed-skip.
  })
})
