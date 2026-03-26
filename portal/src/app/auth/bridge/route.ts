import { NextResponse } from "next/server"
import { createClient } from "@/lib/supabase/server"

const apiUrl = process.env.NEXT_PUBLIC_API_URL

/**
 * Auth bridge route for Telegram→Portal zero-click authentication.
 *
 * Receives a short-lived bridge token from the Telegram "Enter Nikita's World" button,
 * exchanges it with the backend for a Supabase hashed_token, then calls verifyOtp()
 * to establish a session WITHOUT PKCE (bypassing the code_verifier mismatch).
 *
 * Flow: Telegram button → /auth/bridge?token=XXX → backend exchange → verifyOtp → /onboarding
 *
 * GH #187: Fixes PKCE mismatch where admin.generate_link() creates magic links server-side
 * but exchangeCodeForSession() requires a code_verifier that only exists in the initiating browser.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const token = searchParams.get("token")

  if (!token) {
    return NextResponse.redirect(`${origin}/login?error=missing_token`)
  }

  try {
    // 1. Exchange bridge token with backend
    const res = await fetch(`${apiUrl}/api/v1/auth/exchange-bridge-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })

    if (!res.ok) {
      console.error("[auth/bridge] Token exchange failed:", res.status)
      return NextResponse.redirect(`${origin}/login?error=auth_bridge_failed`)
    }

    const { hashed_token, redirect_path } = await res.json()

    // 2. Create Supabase session via verifyOtp (bypasses PKCE)
    // This is Supabase's documented pattern for server-side email confirmation.
    // verifyOtp with token_hash establishes session + sets cookies via setAll().
    // See: @supabase/auth-js VerifyTokenHashParams { token_hash: string; type: EmailOtpType }
    const supabase = await createClient()
    const { error } = await supabase.auth.verifyOtp({
      token_hash: hashed_token,
      type: "magiclink",
    })

    if (error) {
      console.error("[auth/bridge] verifyOtp failed:", error.message)
      return NextResponse.redirect(`${origin}/login?error=auth_bridge_failed`)
    }

    // 3. Redirect to target (sanitize against open redirects — FE-010 pattern)
    const next =
      redirect_path?.startsWith("/") && !redirect_path.startsWith("//")
        ? redirect_path
        : "/dashboard"

    return NextResponse.redirect(`${origin}${next}`)
  } catch (err) {
    console.error("[auth/bridge] Unexpected error:", err)
    return NextResponse.redirect(`${origin}/login?error=auth_bridge_failed`)
  }
}
