"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"

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
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    })
    setResending(false)
    if (error) {
      if (error.message?.toLowerCase().includes("rate") || error.message?.toLowerCase().includes("limit")) {
        toast.error("Please wait before requesting another link", {
          description: "For security, there's a short cooldown between requests.",
        })
        setCooldown(60)
      } else {
        toast.error("Failed to resend", { description: error.message })
      }
    } else {
      toast.success("New link sent! Check your inbox.")
      setCooldown(60)
    }
  }

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        onClick={handleResend}
        disabled={cooldown > 0 || resending}
        className="text-rose-400"
      >
        {cooldown > 0
          ? `Resend in ${cooldown}s`
          : resending
            ? "Sending..."
            : "Resend magic link"}
      </Button>
      <Button variant="ghost" onClick={onChangeEmail} className="text-muted-foreground text-xs">
        Try another email
      </Button>
    </div>
  )
}

function LoginForm() {
  const searchParams = useSearchParams()
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  // Handle auth callback errors (e.g. expired/invalid magic link, bridge failures)
  useEffect(() => {
    const error = searchParams.get("error")
    if (error === "auth_callback_failed") {
      toast.error("Login link expired or invalid", {
        description: "Please request a new login link.",
      })
    } else if (error === "auth_bridge_failed") {
      toast.error("Automatic sign-in failed", {
        description: "Please sign in with your email below.",
      })
    } else if (error === "missing_token") {
      toast.error("Invalid link", {
        description: "Please sign in with your email below.",
      })
    }
  }, [searchParams])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    setLoading(false)
    if (error) {
      // Classify error for better UX
      const msg = error.message?.toLowerCase() ?? ""
      if (msg.includes("database") || msg.includes("identity") || msg.includes("not found")) {
        toast.error("Account issue detected", {
          description: "There was a problem with your account. Please try again or contact support.",
        })
      } else if (msg.includes("rate") || msg.includes("limit")) {
        toast.error("Too many attempts", {
          description: "Please wait a moment before trying again.",
        })
      } else {
        toast.error("Failed to send login link", { description: error.message })
      }
    } else {
      setSent(true)
      toast.success("Check your email for a login link")
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-void p-4">
      <Card className="w-full max-w-md glass-card-elevated">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-rose-400">Nikita</CardTitle>
          <CardDescription className="text-muted-foreground">
            Sign in to your dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-muted-foreground">
                We sent a magic link to <strong className="text-foreground">{email}</strong>.
                Check your inbox — the link is valid for up to 1 hour.
              </p>
              <ResendButton email={email} onChangeEmail={() => setSent(false)} />
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <Input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                className="bg-white/5 border-white/10"
              />
              <Button type="submit" className="w-full" disabled={loading || !email}>
                {loading ? "Sending..." : "Send Magic Link"}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
