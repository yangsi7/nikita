"use client"

import { useState } from "react"
import { useForm, FormProvider } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { toast } from "sonner"
import { profileSchema, type ProfileFormValues } from "./schemas"
import { ScoreSection } from "./sections/score-section"
import { ChapterSection } from "./sections/chapter-section"
import { RulesSection } from "./sections/rules-section"
import { ProfileSection } from "./sections/profile-section"
import { MissionSection } from "./sections/mission-section"
import { AmbientParticles } from "./components/ambient-particles"
import { ScrollProgress } from "./components/scroll-progress"
import { apiClient } from "@/lib/api/client"

interface OnboardingCinematicProps {
  userId: string
}

export function OnboardingCinematic({ userId }: OnboardingCinematicProps) {
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      location_city: "",
      social_scene: undefined,
      drug_tolerance: 3,
    },
  })

  async function onSubmit(data: ProfileFormValues) {
    setSubmitting(true)
    setError(null)

    try {
      await apiClient<{ status: string; user_id: string }>(
        "/onboarding/profile",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      )

      setSubmitted(true)
      toast.success("Profile saved! Opening Telegram...")

      // Use https://t.me/ — works on all platforms (opens app if installed, web client if not)
      // Avoids tg:// protocol race condition where fallback fires unconditionally
      setTimeout(() => {
        window.location.href = "https://t.me/Nikita_my_bot"
      }, 1500)
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: string }).detail)
          : "Something went wrong. Please try again."
      setError(message)
      toast.error(message)
      setSubmitting(false)
    }
  }

  const onError = () => {
    document
      .querySelector('[data-testid="section-profile"]')
      ?.scrollIntoView({ behavior: "smooth" })
  }

  return (
    <FormProvider {...form}>
      <AmbientParticles />
      <form
        onSubmit={form.handleSubmit(onSubmit, onError)}
        className="h-screen snap-y snap-mandatory motion-reduce:snap-proximity overflow-y-auto scroll-smooth bg-void-ambient"
      >
        <ScoreSection />
        <ChapterSection />
        <RulesSection />
        <ProfileSection />
        <MissionSection submitting={submitting} error={error} submitted={submitted} />
      </form>
      <ScrollProgress />
    </FormProvider>
  )
}
