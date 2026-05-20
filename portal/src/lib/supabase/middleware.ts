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

  // /auth/confirm must pass through regardless of auth state. It is the PKCE
  // verifyOtp route handler that mints the session. Exact-match only — no
  // nested children. /auth/interstitial deleted in Spec 220 PR-A.
  if (pathname === "/auth/confirm") {
    return supabaseResponse
  }

  // Public routes
  // Spec 220 PR-A: `/login` becomes a 410 handler in PR-B. During PR-A
  // it is still a live route (safety gate ordering). `/auth/*` passes
  // through for the PKCE callback (confirm handled above) + any error paths.
  if (pathname === "/login" || pathname.startsWith("/auth/")) {
    if (user) {
      const redirect = isAdmin(user) ? "/admin" : "/dashboard"
      return NextResponse.redirect(new URL(redirect, request.url))
    }
    return supabaseResponse
  }

  // Protected routes — redirect unauthenticated users to TG bot (canonical
  // entry point per Spec 220 ADR-220-1). T-3 safety gate: this redirect MUST
  // be deployed before /login becomes a 410 handler (PR-A → PR-B ordering).
  if (!user) {
    // Build the deep-link the same way the landing CTAs do (hero-section.tsx):
    // canonical NEXT_PUBLIC_TELEGRAM_BOT_USERNAME + URL builder, so the `start`
    // payload survives regardless of trailing slashes. Avoids a second,
    // undocumented bot-URL env var drifting from the landing surface.
    const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "Nikita_my_bot"
    const tgBotUrl = new URL(`https://t.me/${botUsername}`)
    tgBotUrl.searchParams.set("start", "new")
    return NextResponse.redirect(tgBotUrl)
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
    const status = request.cookies.get("onboarding_status")?.value
    if (status === "completed") {
      return NextResponse.redirect(new URL("/dashboard", request.url))
    }
  }

  return supabaseResponse
}
