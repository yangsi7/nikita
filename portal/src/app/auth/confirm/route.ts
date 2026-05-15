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
 * Spec 216-G: failure redirects target `/login?error=...`. The
 * portal-first `/onboarding/auth` route was removed; `/login` is the
 * single TG-first surface for both fresh and returning users (any
 * sign-out lands here too).
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
      `${origin}/login?error=invalid_type`,
      { status: 302 },
    )
  }

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

  // W1 (CRITICAL): clear any pre-existing session before processing the new
  // magic-link token. Without this, User-A's session cookies remain active
  // when User-B clicks a magic link in the same browser, causing the new
  // verifyOtp call to inherit User-A's session context and potentially leaking
  // User-A's identity into User-B's wizard flow.
  //
  // scope:'local' clears only this device's session cookies; it does NOT
  // revoke the refresh token server-side, which is the correct behaviour —
  // we are discarding the stale local session, not revoking the previous user.
  //
  // Non-fatal: if there is no existing session, signOut returns { error }.
  // We discard both the return value and any thrown exception — proceed to
  // verifyOtp regardless.
  try {
    await supabase.auth.signOut({ scope: "local" })
  } catch {
    // Best-effort — no existing session is the common case; failures are fine.
  }

  const { data: verified, error } = await supabase.auth.verifyOtp({
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

  // Spec 216 EM-2 + PR-E (216-H repair) — auto-bind Telegram. After
  // verifyOtp succeeds (cookies set on `cookieStore`), call backend
  // POST /auth/autobind-telegram with the just-issued access token.
  //
  // Outcome handling:
  //  - "ok" / "infra_error" / "skipped"  → continue to interstitial.
  //    5xx infra hiccups must still let the user reach /onboarding.
  //  - "conflict"  → redirect to /login?error=telegram_conflict.
  //    Surfaces E4/E13 (this Telegram identity is bound to another
  //    email).
  //  - "bind_failed"  → redirect to /login?error=telegram_bind_failed
  //    (PR-E). Surfaces the post-216-G fatal case where the canonical
  //    TG-first flow somehow landed here without an FSM row AND
  //    users.telegram_id IS NULL. Pre-PR-E this silently mounted the
  //    wizard with a NULL bind, leaving every downstream Nikita
  //    system (decay, scheduled events, voice, push) silently no-op.
  //
  // Synchronous await is intentional — needed for outcome-based
  // routing on 409. ~50ms backend call per /auth/confirm.
  const autobind = await tryAutobindTelegram({
    accessToken: verified?.session?.access_token,
    origin,
  })

  if (autobind === "conflict") {
    return NextResponse.redirect(
      `${origin}/login?error=telegram_conflict`,
      { status: 302 },
    )
  }

  if (autobind === "bind_failed") {
    return NextResponse.redirect(
      `${origin}/login?error=telegram_bind_failed`,
      { status: 302 },
    )
  }

  // W3 (HIGH): for pending users, honour next=/onboarding (or default to it).
  // Users who have not completed onboarding must land on /onboarding, not on
  // /dashboard. The users table is queried with the just-verified session so
  // RLS applies — no service-role key needed.
  //
  // Failure modes:
  //  - DB error / user row missing: fall through to the original `next` param.
  //    Non-fatal; the onboarding page itself has a server-side idempotency
  //    check that will redirect completed users to /dashboard.
  //  - onboarding_status == "completed" (or any other value): preserve the
  //    caller-supplied `next` with the existing same-origin guard already
  //    applied at the top of this handler.
  const userId = verified?.user?.id
  if (userId) {
    const { data: userRow, error: userErr } = await supabase
      .from("users")
      .select("onboarding_status")
      .eq("id", userId)
      .single()

    if (!userErr && userRow?.onboarding_status === "pending") {
      const pendingNext = "/onboarding"
      const pendingInterstitialUrl = `${origin}/auth/interstitial?next=${encodeURIComponent(pendingNext)}`
      return NextResponse.redirect(pendingInterstitialUrl, { status: 302 })
    }
  }

  const interstitialUrl = `${origin}/auth/interstitial?next=${encodeURIComponent(next)}`
  return NextResponse.redirect(interstitialUrl, { status: 302 })
}

type AutobindOutcome =
  | "ok"
  | "no_session"
  | "conflict"
  | "bind_failed"
  | "infra_error"
  | "skipped"

/**
 * Best-effort POST to backend /auth/autobind-telegram. Returns a
 * discriminated outcome so the caller can route on 409 conflicts.
 *
 * 409 detail mapping (PR-E):
 *  - "telegram_already_bound_to_other_user" → "conflict"
 *  - "telegram_bind_failed_fsm_missing" → "bind_failed"
 *  - "telegram_bind_failed_user_row_missing" → "bind_failed"
 *  - any other 409 detail → "conflict" (conservative default)
 *
 * 5xx and network errors return "infra_error"; the caller continues
 * to the interstitial.
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
      // PR-E: differentiate cross-user-conflict from bind-failed.
      // Default to "conflict" if body parse fails.
      try {
        const body = (await res.json()) as { detail?: string }
        const detail = body?.detail ?? ""
        if (
          detail === "telegram_bind_failed_fsm_missing" ||
          detail === "telegram_bind_failed_user_row_missing"
        ) {
          console.warn(
            "[auth/confirm] autobind-telegram bind_failed:",
            detail,
          )
          return "bind_failed"
        }
        console.warn(
          "[auth/confirm] autobind-telegram conflict:",
          detail || "(no detail)",
        )
        return "conflict"
      } catch {
        console.warn("[auth/confirm] autobind-telegram 409 (no body)")
        return "conflict"
      }
    }
    if (!res.ok) {
      // Non-409 failures are non-fatal; user proceeds to interstitial.
      console.warn(
        "[auth/confirm] autobind-telegram non-OK:",
        res.status,
      )
      return "infra_error"
    }
    // 2xx — body has shape { bound, already_bound, no_session }.
    // The caller treats every 2xx the same (continue to interstitial).
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
