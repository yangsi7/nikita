"use client"

import { useEffect, useState } from "react"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"

// Spec 214 PR #310 — Nikita-voiced magic-link entry. Mirrors /login
// pattern (signInWithOtp) but ships every surface with dossier-aesthetic
// copy per FR-3 wizard-copy discipline, and most importantly carries
// `next=/onboarding` so the auth callback routes the user into the
// wizard rather than the default /dashboard.
//
// No Suspense / useSearchParams here: /auth/callback redirects failures
// to /login?error=... (not back to /onboarding/auth), so reading the
// error query param on this page would be dead code. Routing failures
// back to /onboarding/auth for funnel-copy consistency is tracked
// separately as a follow-up to this PR (it requires modifying the
// shared callback route, which is out of scope for the wiring fix).

const NEXT_PATH = "/onboarding"

/** Build the magic-link emailRedirectTo URL with the wizard `next` param. */
function buildCallbackUrl() {
  return `${window.location.origin}/auth/callback?next=${encodeURIComponent(NEXT_PATH)}`
}

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
      options: { emailRedirectTo: buildCallbackUrl() },
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

export default function OnboardingAuthClient() {
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      // Critical: next=/onboarding routes the magic-link click into the
      // wizard at step 3, not the default /dashboard. /auth/callback's
      // open-redirect filter accepts same-origin relative paths.
      options: { emailRedirectTo: buildCallbackUrl() },
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
            {/* CardTitle is a styled div per shadcn; nesting an h1 inside
                preserves the visible aesthetic AND a semantic top-level
                heading for AT users. /login uses CardTitle directly with
                no h1, which is less accessible — we improve on that here. */}
            <CardTitle>
              <h1 className="text-3xl font-black tracking-tight text-foreground leading-tight">
                I&apos;ve been reading about you.
              </h1>
            </CardTitle>
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
