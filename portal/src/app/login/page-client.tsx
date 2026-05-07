"use client"

import { Suspense, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { toast } from "sonner"
import { env } from "@/lib/env"

/**
 * Spec 216-G — TG-first canonical login surface.
 *
 * Replaced the legacy magic-link email form. The single canonical
 * authentication path is now: tap CTA → open Telegram → bot handles
 * email + magic-link via signup_handler FSM (telegram.py:644-685) →
 * `/auth/confirm` autobinds `users.telegram_id` → portal session.
 *
 * `/login` exists for two surfaces:
 *   1. Sign-out destination (sidebar.tsx:55) — returning users land here.
 *   2. `/auth/confirm` failure redirect target (link expired, conflict, etc.).
 *
 * Both render the same TG-first CTA. No portal-side email form exists.
 */

// Spec 217-1 FR-1 / AC-1.3: append `?start=welcome` so Telegram renders
// a START button on cold-start (this CTA is shown to unauthenticated users
// after sign-out or /auth/confirm failure — both cases are pre-bot-conversation
// flows where the START button must surface).
const TELEGRAM_URL = (() => {
  const url = new URL(`https://t.me/${env.TELEGRAM_BOT_USERNAME}`)
  url.searchParams.set("start", "welcome")
  return url.toString()
})()

const ERROR_TOASTS: Record<string, { title: string; description: string }> = {
  link_expired: {
    title: "That link expired",
    description: "Open Telegram and tap /start again to get a new one.",
  },
  invalid_type: {
    title: "Invalid link",
    description: "Open Telegram and tap /start again.",
  },
  missing_params: {
    title: "Invalid link",
    description: "Open Telegram and tap /start again.",
  },
  auth_confirm_failed: {
    title: "Sign-in failed",
    description: "Open Telegram and tap /start again.",
  },
  telegram_conflict: {
    title: "This Telegram account is already linked to another email",
    description: "Reach out to support if this is unexpected.",
  },
  telegram_bind_failed: {
    title: "Couldn't link your Telegram",
    description: "Open Telegram and tap /start again. If it keeps happening, reach out to support.",
  },
}

function LoginInner() {
  const searchParams = useSearchParams()

  useEffect(() => {
    const error = searchParams.get("error")
    if (!error) return
    const t = ERROR_TOASTS[error]
    if (t) {
      toast.error(t.title, { description: t.description })
    } else {
      toast.error("Sign-in failed", {
        description: "Open Telegram and tap /start to begin.",
      })
    }
  }, [searchParams])

  return (
    <div className="flex min-h-screen items-center justify-center bg-void p-4">
      <Card className="w-full max-w-md glass-card-elevated">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold text-rose-400">
            Nikita
          </CardTitle>
          <CardDescription className="text-muted-foreground">
            She lives in Telegram. Tap to begin.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button asChild className="w-full" size="lg">
            <a
              href={TELEGRAM_URL}
              data-testid="login-telegram-cta"
              rel="noopener noreferrer"
            >
              Open Telegram
            </a>
          </Button>
          <p className="text-xs text-muted-foreground text-center">
            Already chatting with her? Tap /start in your conversation.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

function LoginFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-void p-4">
      <Card className="w-full max-w-md glass-card-elevated">
        <CardHeader className="text-center">
          <div className="h-8 w-24 mx-auto rounded bg-white/5 animate-pulse" />
          <div className="h-4 w-48 mx-auto rounded bg-white/5 animate-pulse mt-2" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-10 rounded bg-white/5 animate-pulse" />
          <div className="h-10 rounded bg-white/5 animate-pulse" />
        </CardContent>
      </Card>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginInner />
    </Suspense>
  )
}
