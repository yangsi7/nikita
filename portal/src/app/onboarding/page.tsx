import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { createClient } from "@/lib/supabase/server"
import { OnboardingWizard } from "./onboarding-wizard"

export const metadata: Metadata = {
  title: "Get Started | Nikita",
  description: "Set up your profile and meet Nikita",
}

/**
 * Spec 214 PR 214-C (T311) — wizard entry point.
 *
 * Auth discipline (Spec 081 regression guard):
 *   - `supabase.auth.getUser()` is the only authoritative source for identity
 *     decisions. It round-trips to Supabase Auth servers and validates the
 *     JWT's signature + revocation state.
 *   - `supabase.auth.getSession()` is permitted ONLY for JWT extraction when
 *     we already know the user is authenticated (e.g., attaching the bearer
 *     token to an outbound fetch). It reads the cookie without validation
 *     and is spoofable — never branch on it.
 *
 * Resume UX: `?resume=true` in the URL is a user-facing UX signal only (e.g.,
 * analytics, shareable return links). The wizard itself auto-hydrates from
 * localStorage on mount (spec NR-1 / AC-NR1.1), which is the authoritative
 * mechanism regardless of the query param. The param is neither read nor
 * required server-side.
 */

export default async function OnboardingPage() {
  // E2E auth bypass — mirrors middleware.ts pattern (server-side only, never in production).
  const isE2E = process.env.E2E_AUTH_BYPASS === "true" && process.env.NODE_ENV !== "production"
  let userId: string

  if (isE2E) {
    userId = "e2e-player-id"
  } else {
    const supabase = await createClient()
    // Spec 081: use getUser() — validates the JWT server-side. Do NOT use
    // getSession() here; a spoofed cookie would bypass auth entirely.
    const { data: { user }, error: authError } = await supabase.auth.getUser()

    if (authError || !user) {
      redirect("/login")
    }
    userId = user.id
  }

  // Already-onboarded short-circuit. Fetch portal stats with an explicit
  // Bearer token extracted via getSession(). This is a non-auth branch —
  // getUser() above already established identity.
  if (!isE2E) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (apiUrl) {
      try {
        const supabase = await createClient()
        // Spec 081: getSession() ONLY for JWT extraction — we already validated
        // the user via getUser() above. Never branch on this for identity.
        const { data: { session } } = await supabase.auth.getSession()
        const token = session?.access_token ?? ""
        const res = await fetch(`${apiUrl}/api/v1/portal/stats`, {
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
        // Stats fetch failed — show onboarding anyway (better than blocking).
        // Logged (not silent) so Cloud Run / Vercel log sweeps can spot a
        // persistent backend outage degrading the onboarding funnel.
        console.warn("[onboarding] portal stats fetch failed", err)
      }
    }
  }

  return <OnboardingWizard userId={userId} />
}
