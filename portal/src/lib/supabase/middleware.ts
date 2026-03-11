import { createServerClient } from "@supabase/ssr"
import type { User } from "@supabase/supabase-js"
import { NextResponse, type NextRequest } from "next/server"

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })
  const pathname = request.nextUrl.pathname

  // E2E auth bypass — server-side only, runtime guard
  if (process.env.E2E_AUTH_BYPASS === "true" && process.env.NODE_ENV !== "production") {
    const role = process.env.E2E_AUTH_ROLE || "player"
    const mockUser: User = role === "admin"
      ? { id: "e2e-admin-id", email: "e2e-admin@test.local", user_metadata: { role: "admin" }, aud: "authenticated", app_metadata: {}, created_at: "" }
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

// Helper: Check if user is admin (metadata role OR @nanoleq.com email)
function isAdmin(u: User): boolean {
  if (u.user_metadata?.role === "admin") return true
  if (u.email?.endsWith("@nanoleq.com")) return true
  return false
}

function handleRouting(
  user: User | null,
  pathname: string,
  request: NextRequest,
  supabaseResponse: NextResponse,
): NextResponse {
  // Public routes
  if (pathname === "/login" || pathname.startsWith("/auth/")) {
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

  return supabaseResponse
}
