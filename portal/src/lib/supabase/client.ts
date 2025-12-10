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
 * IMPORTANT: Redirects to home page (/) instead of /auth/callback to allow
 * browser-side Supabase client to auto-detect and exchange the PKCE code.
 * The code_verifier is stored in browser cookies and must be available
 * client-side for successful PKCE exchange.
 */
export async function loginWithMagicLink(email: string) {
  const supabase = createClient()

  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      // Redirect to home page to let browser client handle PKCE code exchange
      emailRedirectTo: `${getURL()}`,
    },
  })

  return { error }
}

/**
 * Sign out the current user.
 */
export async function logout() {
  const supabase = createClient()
  const { error } = await supabase.auth.signOut()
  return { error }
}
