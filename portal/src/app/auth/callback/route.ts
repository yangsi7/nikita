import { createClient } from '@/lib/supabase/server'
import { NextResponse, type NextRequest } from 'next/server'
import type { EmailOtpType } from '@supabase/supabase-js'

/**
 * Auth callback route handler for magic link authentication.
 *
 * Supports two flows:
 * 1. PKCE flow: Supabase redirects with ?code=XXX (from signInWithOtp)
 * 2. Token hash flow: Direct link with ?token_hash=XXX&type=email (from custom email template)
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

    // Handle PKCE flow (default for signInWithOtp)
    if (code) {
      const { error } = await supabase.auth.exchangeCodeForSession(code)

      if (error) {
        console.error('Auth callback error (PKCE):', error)
        return NextResponse.redirect(
          `${origin}/?error=auth_error&error_description=${encodeURIComponent(error.message)}`
        )
      }

      // Successful authentication
      return NextResponse.redirect(`${origin}${next}`)
    }

    // Handle token hash flow (for custom email templates)
    if (token_hash && type) {
      const { error } = await supabase.auth.verifyOtp({
        type,
        token_hash,
      })

      if (error) {
        console.error('Auth callback error (token_hash):', error)
        return NextResponse.redirect(
          `${origin}/?error=auth_error&error_description=${encodeURIComponent(error.message)}`
        )
      }

      // Successful authentication
      return NextResponse.redirect(`${origin}${next}`)
    }

    // No valid auth parameters provided
    return NextResponse.redirect(
      `${origin}/?error=missing_params&error_description=No+authentication+parameters+provided`
    )
  } catch (err) {
    console.error('Unexpected error in auth callback:', err)
    return NextResponse.redirect(
      `${origin}/?error=unexpected_error&error_description=An+unexpected+error+occurred`
    )
  }
}
