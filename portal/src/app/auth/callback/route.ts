import { createClient } from '@/lib/supabase'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * Auth callback route handler for magic link authentication.
 *
 * Handles the redirect from Supabase magic link emails:
 * 1. Exchanges the auth code for a session
 * 2. Sets the session cookie
 * 3. Redirects to dashboard on success
 * 4. Redirects to login with error on failure
 */
export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const origin = requestUrl.origin

  // If no code, redirect to login with error
  if (!code) {
    return NextResponse.redirect(
      `${origin}/?error=missing_code&error_description=No+authentication+code+provided`
    )
  }

  try {
    const supabase = createClient()

    // Exchange the code for a session
    const { error } = await supabase.auth.exchangeCodeForSession(code)

    if (error) {
      console.error('Auth callback error:', error)
      return NextResponse.redirect(
        `${origin}/?error=auth_error&error_description=${encodeURIComponent(error.message)}`
      )
    }

    // Successful authentication - redirect to dashboard
    return NextResponse.redirect(`${origin}/dashboard`)
  } catch (err) {
    console.error('Unexpected error in auth callback:', err)
    return NextResponse.redirect(
      `${origin}/?error=unexpected_error&error_description=An+unexpected+error+occurred`
    )
  }
}
