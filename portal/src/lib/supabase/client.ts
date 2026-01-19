import { createBrowserClient } from '@supabase/ssr'

/**
 * Create a Supabase client for client-side operations.
 * Use this in Client Components.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

/**
 * Get the base URL for redirects.
 * Handles Vercel deployments, local development, and custom domains.
 */
export function getURL() {
  let url =
    process.env.NEXT_PUBLIC_SITE_URL ?? // Set in production (Vercel env var)
    process.env.NEXT_PUBLIC_VERCEL_URL ?? // Automatically set by Vercel
    'http://localhost:3000/'
  // Make sure to include `https://` when not localhost
  url = url.startsWith('http') ? url : `https://${url}`
  // Make sure to include a trailing `/`
  url = url.endsWith('/') ? url : `${url}/`
  return url
}

/**
 * Send a magic link to the user's email for passwordless authentication.
 *
 * @deprecated Use sendOtpCode instead for consistent OTP-based authentication
 *
 * IMPORTANT: Redirects to home page (/) instead of /auth/callback to allow
 * browser-side Supabase client to auto-detect and exchange the PKCE code.
 * The code_verifier is stored in browser cookies and must be available
 * client-side for successful PKCE exchange.
 *
 * Uses window.location.origin to ensure redirect goes back to the same domain
 * where the login was initiated. This fixes PKCE issues when the app is accessed
 * via different Vercel URLs (e.g., production domain vs deployment URL).
 */
export async function loginWithMagicLink(email: string) {
  const supabase = createClient()

  // Use current window origin to ensure redirect goes back to same domain
  // This keeps PKCE code_verifier cookies accessible on the redirect
  const redirectUrl = typeof window !== 'undefined' ? `${window.location.origin}/` : `${getURL()}`

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      // Redirect to home page on the SAME domain to let browser client handle PKCE
      emailRedirectTo: redirectUrl,
    },
  })

  return { error }
}

/**
 * Send OTP code to the user's email for passwordless authentication.
 *
 * This sends a 6-digit code to the user's email that they must enter
 * to complete authentication. This is the preferred method for portal
 * login as it's consistent with the Telegram OTP flow.
 *
 * NOTE: By NOT providing emailRedirectTo, Supabase sends an OTP code
 * instead of a magic link. The user must then call verifyOtpCode to complete.
 */
export async function sendOtpCode(email: string) {
  const supabase = createClient()

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      shouldCreateUser: true,
      // Intentionally NO emailRedirectTo - forces OTP mode instead of magic link
    },
  })

  return { error }
}

/**
 * Verify the OTP code entered by the user.
 *
 * @param email - The email address that received the OTP
 * @param code - The 6-digit code from the email
 * @returns Session data on success, error on failure
 */
export async function verifyOtpCode(email: string, code: string) {
  const supabase = createClient()

  const { data, error } = await supabase.auth.verifyOtp({
    email,
    token: code,
    type: 'email',
  })

  return { data, error }
}

/**
 * Sign out the current user.
 */
export async function logout() {
  const supabase = createClient()
  const { error } = await supabase.auth.signOut()
  return { error }
}
