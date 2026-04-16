import { NextResponse } from "next/server"
import { createClient } from "@/lib/supabase/server"

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get("code")
  // FE-010: Reject open-redirect attempts (e.g. next=//evil.com or next=https://evil.com).
  // Only allow same-origin relative paths starting with a single slash.
  const rawNext = searchParams.get("next") ?? "/dashboard"
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/dashboard"

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      const { data: { user } } = await supabase.auth.getUser()
      // Gate admin on app_metadata.role (service-role-only; not client-writable).
      // user_metadata is NEVER consulted — it is writable from the browser via
      // supabase.auth.updateUser() and would enable self-escalation.
      const role = user?.app_metadata?.role
      const redirectTo = role === "admin" ? "/admin" : next
      return NextResponse.redirect(`${origin}${redirectTo}`)
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`)
}
