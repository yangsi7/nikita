import type { Metadata } from "next"
import { redirect } from "next/navigation"
import { createClient } from "@/lib/supabase/server"
import { OnboardingWizard } from "./onboarding-wizard"
import { WizardShell } from "./_components/WizardShell"

export const metadata: Metadata = {
  title: "Get Started | Nikita",
  description: "Set up your profile and meet Nikita",
}

/**
 * Spec 216-C — Server Component auth guard (AC C1.13).
 *
 * Spec 216-C ships a new cinematic 15-screen wizard rendered by
 * `WizardShell`. The legacy 11-step form wizard remains accessible
 * behind the `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` env flag so we can
 * dark-launch + revert quickly. Default: new wizard.
 *
 * Auth discipline (Spec 081 regression guard):
 *   - `supabase.auth.getUser()` is the only authoritative source for
 *     identity. Round-trips to Supabase Auth servers and validates the
 *     JWT's signature + revocation state.
 *   - The auth check runs on the SERVER before any client component
 *     mounts (C1.13). Unauthenticated → `redirect('/onboarding/auth')`.
 *
 * E2E auth bypass mirrors the existing middleware pattern.
 */
export default async function OnboardingPage() {
  const isE2E =
    process.env.E2E_AUTH_BYPASS === "true" &&
    process.env.NODE_ENV !== "production"
  const useLegacy = process.env.NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD === "true"

  let userId: string

  if (isE2E) {
    userId = "e2e-player-id"
  } else {
    const supabase = await createClient()
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser()

    if (authError || !user) {
      redirect("/onboarding/auth")
    }
    userId = user.id
  }

  if (!isE2E) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL
    if (apiUrl) {
      try {
        const supabase = await createClient()
        const {
          data: { session },
        } = await supabase.auth.getSession()
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
        console.warn("[onboarding] portal stats fetch failed", err)
      }
    }
  }

  if (useLegacy) {
    return <OnboardingWizard userId={userId} />
  }
  return <WizardShell />
}
