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

    it("allows /auth/callback to pass through", async () => {
      const req = makeRequest("/auth/callback")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("allows /auth/confirm to pass through", async () => {
      const req = makeRequest("/auth/confirm")
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
      user_metadata: { role: "player" },
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

    it("redirects /auth/callback to /dashboard when already authenticated", async () => {
      const req = makeRequest("/auth/callback")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/dashboard")
    })
  })

  // ----------------------------------------------------------------
  // Admin user via role metadata
  // ----------------------------------------------------------------
  describe("admin user (role metadata)", () => {
    const adminUserMeta = {
      id: "admin-1",
      email: "someone@gmail.com",
      user_metadata: { role: "admin" },
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
  })

  // ----------------------------------------------------------------
  // Admin user via @nanoleq.com email
  // ----------------------------------------------------------------
  describe("admin user (nanoleq.com email)", () => {
    const adminUserEmail = {
      id: "admin-2",
      email: "boss@nanoleq.com",
      user_metadata: {},
    }

    beforeEach(() => {
      mockCreateServerClient.mockReturnValue(mockSupabaseWithUser(adminUserEmail))
    })

    it("allows access to /admin routes via nanoleq.com email", async () => {
      const req = makeRequest("/admin/pipeline")
      const res = await updateSession(req)
      expect(res.headers.get("location")).toBeNull()
    })

    it("redirects /login to /admin for nanoleq.com user", async () => {
      const req = makeRequest("/login")
      const res = await updateSession(req)
      expect(res.status).toBe(307)
      expect(res.headers.get("location")).toContain("/admin")
    })
  })
})
