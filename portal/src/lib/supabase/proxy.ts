/**
 * Supabase SSR session management utility for Next.js 16 proxy.
 *
 * Per Supabase SSR docs (Dec 2025): The proxy needs to properly pass refreshed
 * cookies BOTH to server components (via request.cookies.set) AND to browser
 * (via response.cookies.set).
 *
 * @see https://supabase.com/docs/guides/auth/server-side/creating-a-client
 */
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * Updates the Supabase session and refreshes auth cookies.
 *
 * IMPORTANT: This function properly handles cookie refresh by:
 * 1. Reading cookies from the incoming request
 * 2. Setting refreshed cookies on both request (for SSR) and response (for browser)
 * 3. Using getUser() instead of getSession() for server-side validation
 */
export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Set cookies on the request for server components
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          // Create a new response with updated request
          supabaseResponse = NextResponse.next({ request })
          // Set cookies on the response for the browser
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // IMPORTANT: Use getUser() not getSession() for server validation
  // getUser() validates the JWT with Supabase Auth server
  // getSession() only reads from cookies without validation
  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Redirect unauthenticated users from protected routes
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    const url = request.nextUrl.clone()
    url.pathname = '/'
    url.searchParams.set('error', 'auth_required')
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
