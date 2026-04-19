import { createServerClient } from "@supabase/ssr"
import type { User } from "@supabase/supabase-js"
import { NextResponse, type NextRequest } from "next/server"

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })
  const pathname = request.nextUrl.pathname

  // E2E auth bypass — server-side only, runtime guard
  if (process.env.E2E_AUTH_BYPASS === "true" && process.env.NODE_ENV !== "production") {
    const role = request.cookies.get("e2e-role")?.value || process.env.E2E_AUTH_ROLE || "player"
    const mockUser: User = role === "admin"
      ? { id: "e2e-admin-id", email: "e2e-admin@test.local", user_metadata: {}, aud: "authenticated", app_metadata: { role: "admin" }, created_at: "" }
      : { id: "e2e-player-id", email: "e2e-player@test.local", user_metadata: {}, aud: "authenticated", app_metadata: {}, created_at: "" }

    return handleRouting(mockUser, pathname, request, supabaseResponse)
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  return handleRouting(user, pathname, request, supabaseResponse)
}

// Helper: Check if user is admin.
//
// Admin is gated on the `app_metadata.role` JWT claim — a service-role-only
// Supabase surface. `user_metadata` is DELIBERATELY NOT consulted here
// because it is client-writable via `supabase.auth.updateUser()` and would
// allow any authenticated user to self-elevate.
function isAdmin(u: User): boolean {
  return u.app_metadata?.role === "admin"
}

function handleRouting(
  user: User | null,
  pathname: string,
  request: NextRequest,
  supabaseResponse: NextResponse,
): NextResponse {
  // Landing page — always public, all users (authenticated or not, including admins)
  if (pathname === "/") {
    return supabaseResponse
  }

  // Public routes
  // Spec 214 PR 214-C (T312): `/onboarding/auth` is the Nikita-voiced magic-
  // link landing page (step 2 of the 11-step wizard). It must be reachable
  // unauthenticated so users can request the magic link. Authenticated users
  // hitting it are bounced to their role-appropriate home.
  if (
    pathname === "/login" ||
    pathname.startsWith("/auth/") ||
    pathname.startsWith("/onboarding/auth")
  ) {
    if (user) {
      const redirect = isAdmin(user) ? "/admin" : "/dashboard"
      return NextResponse.redirect(new URL(redirect, request.url))
    }
    return supabaseResponse
  }

  // Protected routes — redirect to login if no user
  if (!user) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  // Admin routes — check role
  if (pathname.startsWith("/admin")) {
    if (!isAdmin(user)) {
      return NextResponse.redirect(new URL("/dashboard", request.url))
    }
  }

  // Spec 214 T3.11: users with onboarding_status='completed' cookie should
  // skip the onboarding flow entirely. The cookie is set by the app_router
  // backend after successful onboarding commit. Cheaper than refetching
  // `/portal/stats` in middleware on every request. The onboarding `page.tsx`
  // also has a server-side belt-and-suspenders redirect, but the middleware
  // redirect prevents the wizard paint for a split second.
  if (pathname === "/onboarding" || pathname.startsWith("/onboarding/")) {
    // Do not apply the completed-skip on `/onboarding/auth` (magic-link
    // landing). Already gated above for authenticated users.
    if (!pathname.startsWith("/onboarding/auth")) {
      const status = request.cookies.get("onboarding_status")?.value
      if (status === "completed") {
        return NextResponse.redirect(new URL("/dashboard", request.url))
      }
    }
  }

  return supabaseResponse
}
