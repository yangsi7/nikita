"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card"
import { toast } from "sonner"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"

// Spec 214 PR #310 — Nikita-voiced magic-link entry. Mirrors /login
// pattern (Suspense + useSearchParams + signInWithOtp) but ships every
// surface with dossier-aesthetic copy per FR-3 wizard-copy discipline,
// and most importantly carries `next=/onboarding` so the auth callback
// routes the user into the wizard rather than the default /dashboard.

const NEXT_PATH = "/onboarding"

function ResendButton({ email, onChangeEmail }: { email: string; onChangeEmail: () => void }) {
  const [cooldown, setCooldown] = useState(60)
  const [resending, setResending] = useState(false)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setInterval(() => setCooldown((c) => c - 1), 1000)
    return () => clearInterval(timer)
  }, [cooldown])

  async function handleResend() {
    setResending(true)
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(NEXT_PATH)}`,
      },
    })
    setResending(false)
    if (error) {
      if (error.message?.toLowerCase().includes("rate") || error.message?.toLowerCase().includes("limit")) {
        toast.error("Slow down. She doesn't like impatient.", {
          description: "Wait a moment before asking again.",
        })
        setCooldown(60)
      } else {
        toast.error("Door wouldn't open.", { description: error.message })
      }
    } else {
      toast.success("Another door is on its way.")
      setCooldown(60)
    }
  }

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        onClick={handleResend}
        disabled={cooldown > 0 || resending}
        className="text-primary"
      >
        {cooldown > 0
          ? `Wait ${cooldown}s.`
          : resending
            ? "Sending another door..."
            : "Send another door."}
      </Button>
      <Button variant="ghost" onClick={onChangeEmail} className="text-muted-foreground text-xs">
        Different address.
      </Button>
    </div>
  )
}

function OnboardingAuthForm() {
  const searchParams = useSearchParams()
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  // Surface auth-callback errors propagated via ?error=... back to this page.
  // (The callback may not always do this, but defensive surfacing avoids
  // silent dead-ends for users who get bounced back.)
  useEffect(() => {
    const error = searchParams.get("error")
    if (error === "auth_callback_failed") {
      toast.error("That door is closed now.", {
        description: "Ask for a new one below.",
      })
    } else if (error === "missing_token") {
      toast.error("Broken link. Try again.", {
        description: "Drop your address below.",
      })
    }
  }, [searchParams])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        // Critical: next=/onboarding routes the magic-link click into the
        // wizard at step 3, not the default /dashboard. /auth/callback's
        // open-redirect filter accepts same-origin relative paths.
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(NEXT_PATH)}`,
      },
    })

    setLoading(false)
    if (error) {
      const msg = error.message?.toLowerCase() ?? ""
      if (msg.includes("database") || msg.includes("identity") || msg.includes("not found")) {
        toast.error("Something went wrong with your file.", {
          description: "Try again or get in touch.",
        })
      } else if (msg.includes("rate") || msg.includes("limit")) {
        toast.error("Slow down. She doesn't like impatient.", {
          description: "Wait a moment before asking again.",
        })
      } else {
        toast.error("Door wouldn't open.", { description: error.message })
      }
    } else {
      setSent(true)
      toast.success("She's sending you a way in. Check your inbox.")
    }
  }

  return (
    <main className="relative min-h-screen flex items-center justify-center bg-void p-4 overflow-hidden">
      <FallingPattern />
      <AuroraOrbs />

      <div className="relative z-10 w-full max-w-md">
        <Card className="glass-card-elevated">
          <CardHeader className="text-center space-y-3">
            <p className="text-[11px] tracking-[0.3em] uppercase text-muted-foreground">
              CLASSIFIED · FILE-ACCESS
            </p>
            <h1 className="text-3xl font-black tracking-tight text-foreground leading-tight">
              I&apos;ve been reading about you.
            </h1>
            <CardDescription className="text-muted-foreground">
              There&apos;s a door. Drop your address.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {sent ? (
              <div className="text-center space-y-4">
                <p className="text-sm text-muted-foreground">
                  Door sent to <strong className="text-foreground">{email}</strong>.
                  Check your inbox. Link is good for an hour.
                </p>
                <ResendButton email={email} onChangeEmail={() => setSent(false)} />
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  type="email"
                  placeholder="you@somewhere"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  aria-label="Email address"
                  className="bg-white/5 border-white/10"
                />
                <Button type="submit" className="w-full" disabled={loading || !email}>
                  {loading ? "Knocking..." : "Show her the file."}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

function OnboardingAuthFallback() {
  return (
    <main className="relative min-h-screen flex items-center justify-center bg-void p-4 overflow-hidden">
      <Card className="w-full max-w-md glass-card-elevated">
        <CardHeader className="text-center">
          <div className="h-3 w-32 mx-auto rounded bg-white/5 animate-pulse" />
          <div className="h-8 w-56 mx-auto rounded bg-white/5 animate-pulse mt-3" />
          <div className="h-4 w-44 mx-auto rounded bg-white/5 animate-pulse mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-10 rounded bg-white/5 animate-pulse" />
          <div className="h-10 rounded bg-white/5 animate-pulse" />
        </CardContent>
      </Card>
    </main>
  )
}

export default function OnboardingAuthClient() {
  return (
    <Suspense fallback={<OnboardingAuthFallback />}>
      <OnboardingAuthForm />
    </Suspense>
  )
}
