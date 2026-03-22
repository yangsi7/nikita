import { redirect } from "next/navigation"
import { createClient } from "@/lib/supabase/server"
import { OnboardingCinematic } from "./onboarding-cinematic"

export default async function OnboardingPage() {
  const supabase = await createClient()
  const { data: { user }, error: authError } = await supabase.auth.getUser()

  if (authError || !user) {
    redirect("/login")
  }

  // Check if user already completed onboarding by fetching portal stats
  try {
    const { data: { session } } = await supabase.auth.getSession()
    const token = session?.access_token ?? ""
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? ""
    const res = await fetch(`${apiUrl}/api/v1/portal/stats`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    })

    if (res.ok) {
      const stats = await res.json()
      if (stats.onboarded_at) {
        redirect("/dashboard")
      }
    }
  } catch {
    // If stats fetch fails, show onboarding anyway (better than blocking)
  }

  return <OnboardingCinematic userId={user.id} />
}
