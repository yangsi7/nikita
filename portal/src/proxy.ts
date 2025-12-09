/**
 * Next.js 16 proxy for authentication and route protection.
 *
 * Uses the shared updateSession utility from lib/supabase/proxy.ts
 * per Supabase SSR best practices (Dec 2025).
 *
 * @see https://supabase.com/docs/guides/auth/server-side/creating-a-client
 */
import { type NextRequest, NextResponse } from 'next/server'
import { updateSession } from '@/lib/supabase/proxy'
import { createServerClient } from '@supabase/ssr'

export async function proxy(request: NextRequest) {
  // First, update the session using the shared utility
  // This handles cookie refresh for both server components and browser
  const response = await updateSession(request)

  // If updateSession returned a redirect (e.g., auth_required), use it
  if (response.headers.get('location')) {
    return response
  }

  // Additional logic: redirect authenticated users from landing to dashboard
  // We need to check user again since updateSession already validated
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll() {
          // No-op for this read-only check
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // If authenticated and accessing landing page, redirect to dashboard
  if (user && request.nextUrl.pathname === '/') {
    const redirectUrl = request.nextUrl.clone()
    redirectUrl.pathname = '/dashboard'
    return NextResponse.redirect(redirectUrl)
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
