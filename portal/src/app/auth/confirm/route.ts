import { NextResponse } from "next/server"
import { cookies } from "next/headers"
import { createServerClient } from "@supabase/ssr"
import type { EmailOtpType } from "@supabase/supabase-js"

/**
 * Spec 215 FR-6 — Portal `/auth/confirm` server route handler.
 *
 * Reads `?token_hash`, `?type`, `?next` from URL. Calls `verifyOtp` server-side
 * via `@supabase/ssr` `createServerClient` (cookies adapter sets the session
 * cookies on the response). On success, 302-redirects to the IS-A interstitial
 * page (separate route) with `?next=<encoded same-origin path>`. The
 * interstitial requires a user gesture before advancing — Apple
 * SFSafariViewController self-contained-session mitigation per Plan §18.3.
 *
 * Architecture deviation note: spec §FR-6 says "render IS-A always-interstitial
 * (NOT raw 302)". Next.js Route Handlers cannot return JSX, so we 302 to a
 * dedicated `/auth/interstitial` page. The user-gesture requirement is
 * preserved unchanged. Both routes are exempted in middleware.
 *
 * Testing H2: `type` is read from the URL and passed VERBATIM to verifyOtp.
 * This handler intentionally has NO hardcoded `"magiclink"` / `"signup"`
 * string literals. A vitest source-grep regression guard enforces this.
 *
 * Feature-flag gated: returns 404 unless NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true
 * (rollback safety per plan.md §18.4).
 */
export async function GET(request: Request): Promise<Response> {
  // Feature-flag gate
  if (process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP !== "true") {
    return new NextResponse("Not Found", { status: 404 })
  }

  const { searchParams, origin } = new URL(request.url)
  const tokenHash = searchParams.get("token_hash")
  const type = searchParams.get("type") as EmailOtpType | null
  const rawNext = searchParams.get("next") ?? "/dashboard"

  // NFR-Sec-1: same-origin guard. Reject protocol-relative (`//evil.com`),
  // absolute URLs (`https://evil.com`), and anything not starting with `/`.
  const next =
    rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/dashboard"

  if (!tokenHash || !type) {
    return NextResponse.redirect(
      `${origin}/login?error=missing_params`,
      { status: 302 },
    )
  }

  const cookieStore = await cookies()
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            )
          } catch {
            // Server Component context — ignore
          }
        },
      },
    },
  )

  const { error } = await supabase.auth.verifyOtp({
    token_hash: tokenHash,
    type,
  })

  if (error) {
    // Sanitize: classify into a small set of stable error codes.
    const code = classifyVerifyOtpError(error.message)
    return NextResponse.redirect(`${origin}/login?error=${code}`, {
      status: 302,
    })
  }

  const interstitialUrl = `${origin}/auth/interstitial?next=${encodeURIComponent(next)}`
  return NextResponse.redirect(interstitialUrl, { status: 302 })
}

/**
 * Map verifyOtp error messages to stable, sanitized error codes for the
 * `/login?error=` query param. We avoid leaking raw Supabase messages because
 * they may include internal request IDs or change between SDK versions.
 */
function classifyVerifyOtpError(message: string): string {
  const lower = message.toLowerCase()
  if (
    lower.includes("expired") ||
    lower.includes("invalid") ||
    lower.includes("not found")
  ) {
    return "link_expired"
  }
  return "auth_confirm_failed"
}
