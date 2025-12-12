import { createClient } from '@/lib/supabase/server'
import { NextResponse, type NextRequest } from 'next/server'
import type { EmailOtpType } from '@supabase/supabase-js'

/**
 * Auth callback route handler for magic link authentication.
 *
 * IMPORTANT: As of Dec 2025, this route is now a FALLBACK handler only.
 * The primary PKCE code exchange happens client-side via browser Supabase client
 * auto-detection (emailRedirectTo points to / instead of /auth/callback).
 *
 * This route handles:
 * 1. Token hash flow: Direct link with ?token_hash=XXX&type=email (custom email templates)
 * 2. Fallback PKCE: If someone manually navigates here with ?code=XXX
 * 3. Error cases
 *
 * Uses server-side Supabase client to properly set session cookies.
 */
export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const origin = requestUrl.origin

  // Check for PKCE flow (code parameter)
  const code = requestUrl.searchParams.get('code')

  // Check for token hash flow (token_hash + type parameters)
  const token_hash = requestUrl.searchParams.get('token_hash')
  const type = requestUrl.searchParams.get('type') as EmailOtpType | null

  // Determine redirect destination (default to dashboard)
  const next = requestUrl.searchParams.get('next') ?? '/dashboard'

  try {
    const supabase = await createClient()

    // Handle PKCE flow (fallback - normally happens client-side)
    if (code) {
      const { error } = await supabase.auth.exchangeCodeForSession(code)

      if (error) {
        console.error('[Auth Callback] PKCE code exchange failed:', error.message)
        console.error('[Auth Callback] This likely means the code_verifier is missing.')
        console.error('[Auth Callback] User may have clicked link in different browser/device.')
        return NextResponse.redirect(
          `${origin}/?error=auth_error&error_description=${encodeURIComponent(error.message)}`
        )
      }

      // Successful authentication
      console.log('[Auth Callback] PKCE code exchange succeeded (fallback path)')
      return NextResponse.redirect(`${origin}${next}`)
    }

    // Handle token hash flow (for custom email templates)
    if (token_hash && type) {
      const { error } = await supabase.auth.verifyOtp({
        type,
        token_hash,
      })

      if (error) {
        console.error('[Auth Callback] Token hash verification failed:', error.message)
        return NextResponse.redirect(
          `${origin}/?error=auth_error&error_description=${encodeURIComponent(error.message)}`
        )
      }

      // Successful authentication
      console.log('[Auth Callback] Token hash verification succeeded')
      return NextResponse.redirect(`${origin}${next}`)
    }

    // No valid auth parameters provided
    console.warn('[Auth Callback] No valid auth parameters (code or token_hash)')
    return NextResponse.redirect(
      `${origin}/?error=missing_params&error_description=No+authentication+parameters+provided`
    )
  } catch (err) {
    console.error('[Auth Callback] Unexpected error:', err)
    return NextResponse.redirect(
      `${origin}/?error=unexpected_error&error_description=An+unexpected+error+occurred`
    )
  }
}
