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
 * Testing H2: `type` is read from the URL and validated against an
 * authoritative runtime allow-list (VALID_OTP_TYPES) before being passed
 * VERBATIM to verifyOtp. This handler intentionally has NO hardcoded default
 * `"magiclink"` / `"signup"` selection, but DOES validate input. A vitest
 * source-grep regression guard enforces both properties.
 *
 * EM-1 (plan §EM-1): the legacy `/auth/callback` route was unified out;
 * `/auth/confirm` is the single auth-completion handler. Always live —
 * the prior `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP` 404 gate was removed.
 *
 * Failure redirects target `/onboarding/auth?error=...` (not `/login`)
 * for funnel-copy consistency: users who entered via the wizard land
 * back in the wizard funnel, not the legacy admin-login surface.
 */

/**
 * Authoritative allow-list of EmailOtpType values per Supabase JS docs:
 * https://supabase.com/docs/reference/javascript/auth-verifyotp
 *
 * I-1 fix: prior implementation cast `searchParams.get("type")` directly to
 * `EmailOtpType`, allowing arbitrary URL-supplied strings to flow into
 * `verifyOtp`. This list is the runtime gate that prevents that.
 */
const VALID_OTP_TYPES = [
  "signup",
  "magiclink",
  "recovery",
  "invite",
  "email_change",
  "email",
] as const

export async function GET(request: Request): Promise<Response> {
  const { searchParams, origin } = new URL(request.url)
  const tokenHash = searchParams.get("token_hash")
  const rawType = searchParams.get("type")
  const type: EmailOtpType | null =
    rawType !== null &&
    (VALID_OTP_TYPES as ReadonlyArray<string>).includes(rawType)
      ? (rawType as EmailOtpType)
      : null
  const rawNext = searchParams.get("next") ?? "/dashboard"

  // NFR-Sec-1: same-origin guard. Reject protocol-relative (`//evil.com`),
  // absolute URLs (`https://evil.com`), and anything not starting with `/`.
  const next =
    rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/dashboard"

  // I-1 fix: distinguish "type was supplied but invalid" from "type missing".
  // A non-null rawType that failed the allow-list check is invalid_type;
  // anything else (including missing tokenHash) is missing_params.
  if (rawType !== null && type === null) {
    return NextResponse.redirect(
      `${origin}/onboarding/auth?error=invalid_type`,
      { status: 302 },
    )
  }

  if (!tokenHash || !type) {
    return NextResponse.redirect(
      `${origin}/onboarding/auth?error=missing_params`,
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

  const { data: verified, error } = await supabase.auth.verifyOtp({
    token_hash: tokenHash,
    type,
  })

  if (error) {
    // Sanitize: classify into a small set of stable error codes.
    const code = classifyVerifyOtpError(error.message)
    return NextResponse.redirect(`${origin}/onboarding/auth?error=${code}`, {
      status: 302,
    })
  }

  // Spec 216 EM-2 — auto-bind Telegram. After verifyOtp succeeds (cookies
  // set on `cookieStore`), call backend POST /auth/autobind-telegram with
  // the just-issued access token.
  //
  // Outcome handling:
  //  - "ok" / "no_session" / "infra_error"  → continue to interstitial.
  //    Portal-first signups (no in-flight TG session) and 5xx infra
  //    hiccups must still let the user reach /onboarding. The wizard
  //    renders an inline "link your Telegram" banner per EM-2 plan
  //    edge case E14 (downstream of this route).
  //  - "conflict"  → redirect to /onboarding/auth?error=telegram_conflict.
  //    The user-facing toast (mapped in page-client.tsx ERROR_TOASTS)
  //    surfaces E4 / E13: this Telegram identity is already bound to
  //    another email. Without this surface the wizard sits silently
  //    waiting for a bind that will never complete (QA finding 2).
  const autobind = await tryAutobindTelegram({
    accessToken: verified?.session?.access_token,
    origin,
  })

  if (autobind === "conflict") {
    return NextResponse.redirect(
      `${origin}/onboarding/auth?error=telegram_conflict`,
      { status: 302 },
    )
  }

  const interstitialUrl = `${origin}/auth/interstitial?next=${encodeURIComponent(next)}`
  return NextResponse.redirect(interstitialUrl, { status: 302 })
}

type AutobindOutcome = "ok" | "no_session" | "conflict" | "infra_error" | "skipped"

/**
 * Best-effort POST to backend /auth/autobind-telegram. The endpoint is
 * idempotent on the no-session and already-bound branches — re-entry
 * (user clicks the magic link twice) returns 200 with no_session=true.
 *
 * Returns a discriminated outcome so the caller can route 409 conflicts
 * to /onboarding/auth?error=telegram_conflict (QA finding 2). 5xx and
 * network errors return "infra_error" and the caller continues to the
 * interstitial — the wizard fallback banner is the user-facing surface
 * for those (per EM-2 plan E14).
 */
async function tryAutobindTelegram(args: {
  accessToken: string | undefined
  origin: string
}): Promise<AutobindOutcome> {
  if (!args.accessToken) {
    return "skipped"
  }
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl) {
    return "skipped"
  }
  try {
    const res = await fetch(`${apiUrl}/api/v1/auth/autobind-telegram`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${args.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    })
    if (res.status === 409) {
      // Cross-user telegram_id conflict (E4/E13). Caller surfaces a
      // toast on /onboarding/auth.
      console.warn("[auth/confirm] autobind-telegram conflict (409)")
      return "conflict"
    }
    if (!res.ok) {
      // Non-409 failures are non-fatal; the wizard renders a
      // link-your-Telegram banner per the EM-2 fallback flow.
      console.warn(
        "[auth/confirm] autobind-telegram non-OK:",
        res.status,
      )
      return "infra_error"
    }
    // 2xx — body has shape { bound, already_bound, no_session } but
    // the caller only needs the conflict-vs-not distinction; treat
    // every 2xx the same.
    try {
      const body = (await res.json()) as { no_session?: boolean }
      return body.no_session ? "no_session" : "ok"
    } catch {
      return "ok"
    }
  } catch (err) {
    console.warn("[auth/confirm] autobind-telegram request failed:", err)
    return "infra_error"
  }
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
