import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { env } from "@/lib/env"
import { createClient } from "@/lib/supabase/server"
import { V2WizardShell } from "./V2WizardShell"

export const metadata: Metadata = {
  title: "Get Started | Nikita",
  description: "Set up your profile and meet Nikita",
}

/**
 * Spec 218 Slice 218-8 — Server Component auth guard + v2 wizard mount.
 *
 * SPEC DEVIATION (intentional, documented):
 *   AC C1.13's spec text suggests the page reads a literal `nikita-session`
 *   cookie via Next.js `cookies()`. This implementation uses
 *   `supabase.auth.getUser()` instead — it round-trips to the Supabase
 *   Auth server and validates the JWT signature + revocation state. The
 *   cookie peek that the AC text describes is spoof-vulnerable (any client
 *   can write that cookie name); `getUser()` is the only authoritative
 *   identity source per Spec 081 regression guard. The AC's stated intent
 *   ("Server Component validates session BEFORE any client component
 *   mounts and redirects unauthenticated users") is honored fully. Spec
 *   text superseded by this implementation note.
 *
 * Spec 218-8 (2026-05-13): Spec 216-C `WizardShell` + all `_components/`
 * bulldozed. `V2WizardShell` (Spec 218) is now the only wizard. The
 * Spec 214 legacy flag + Spec 216-C cinematic shell are both gone.
 *
 * Auth discipline (Spec 081 regression guard):
 *   - `supabase.auth.getUser()` is the only authoritative source for
 *     identity. Round-trips to Supabase Auth servers and validates the
 *     JWT's signature + revocation state.
 *   - The auth check runs on the SERVER before any client component
 *     mounts (C1.13). Unauthenticated → `redirect('/login')` (Spec 216-G:
 *     /login is now the TG-first surface; /onboarding/auth was removed).
 *
 * E2E auth bypass mirrors the existing middleware pattern.
 */
export default async function OnboardingPage() {
  // E2E_AUTH_BYPASS bypass — gated by NODE_ENV !== "production"
  // (parity with lib/supabase/middleware.ts:10). Next.js inlines
  // NODE_ENV at build time so this works in Server Components.
  const isE2E =
    process.env.E2E_AUTH_BYPASS === "true" &&
    process.env.NODE_ENV !== "production"

  if (!isE2E) {
    const supabase = await createClient()
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser()

    if (authError || !user) {
      redirect("/login")
    }

    // Use env.API_URL (fail-fast) instead of bare process.env per Spec 216-EM3a.
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      const token = session?.access_token ?? ""
      const res = await fetch(`${env.API_URL}/api/v1/portal/stats`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          cache: "no-store",
          signal: AbortSignal.timeout(5000),
        })

        if (res.ok) {
          const stats = await res.json()
          if (stats.onboarded_at) {
            redirect("/dashboard")
          }
        }
    } catch (err) {
      console.warn("[onboarding] portal stats fetch failed", err)
    }
  }

  return <V2WizardShell />
}
