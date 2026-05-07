"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"

import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { Button } from "@/components/ui/button"

interface InterstitialClientProps {
  /**
   * Spec 217-1 FR-2 / AC-2.4 — server-rendered UA detection result.
   * `true` when UA is iOS WebKit, Telegram in-app browser, or unknown
   * (default-safe fallback). The brand veil + tap surface ALWAYS render;
   * this prop only gates whether a programmatic auto-advance fires.
   */
  requireGesture: boolean
  /** Validated `?next` redirect target. Server passes the same-origin path. */
  next: string
}

const AUTO_ADVANCE_MS = 100

/**
 * Spec 215 FR-6 / FR-6a + Spec 217-1 FR-2 — IS-A Always-Interstitial
 * with brand-veil reskin.
 *
 * Renders unconditionally after `/auth/confirm` mints the session. Brand
 * veil (bg-void + AuroraOrbs + Geist Sans heading) is always visible.
 *
 * Auto-advance gating (AC-2.3): a programmatic `router.push(next)` fires
 * after a short brand-veil flash ONLY when the server has confirmed the UA
 * is non-iOS-WebKit AND non-Telegram-IAB (positive detection of Chrome
 * desktop / Firefox / Edge). For iOS standalone, Telegram IAB, and any
 * unknown UA, the user must tap the surface to advance — this preserves
 * Apple's SFSafariViewController self-contained-session cookie commit
 * (Spec 215 FR-6 invariant).
 *
 * Tap surface (AC-2.1bis): native `<button>` (via shadcn `Button`) with
 * keyboard activation (Enter/Space handled natively). Inner button is at
 * least 44x44px (WCAG 2.1 AA touch target) and the surrounding wrapper is
 * full-viewport for tap-anywhere ergonomics.
 *
 * Same-origin guard on `?next`: protocol-relative (`//evil.com`) and
 * absolute URLs (`https://evil.com`) are rejected; falls back to /dashboard.
 *
 * NO em-dashes in user-facing copy (project rule).
 */
export default function InterstitialClient({
  requireGesture,
  next,
}: InterstitialClientProps) {
  const router = useRouter()

  // Same-origin guard, repeated client-side as defense-in-depth even though
  // the server already validates `next` before passing it down.
  const safeNext =
    typeof next === "string" &&
    next.startsWith("/") &&
    !next.startsWith("//")
      ? next
      : "/dashboard"

  // Prefetch (AC-2.5) — instant transition once the user taps.
  useEffect(() => {
    router.prefetch(safeNext)
  }, [router, safeNext])

  // Auto-advance gating (AC-2.3) — only fires for confirmed-safe UAs.
  // Use a ref to ensure the timer is cleared on unmount even under fake
  // timers in tests.
  const advancedRef = useRef(false)
  useEffect(() => {
    if (requireGesture) return
    if (advancedRef.current) return
    const t = setTimeout(() => {
      advancedRef.current = true
      router.push(safeNext)
    }, AUTO_ADVANCE_MS)
    return () => clearTimeout(t)
  }, [requireGesture, router, safeNext])

  function handleAdvance() {
    if (advancedRef.current) return
    advancedRef.current = true
    router.push(safeNext)
  }

  return (
    <main
      role="main"
      data-require-gesture={requireGesture ? "true" : "false"}
      className="relative min-h-screen w-full overflow-hidden bg-void"
    >
      <AuroraOrbs />
      <div className="relative z-10 flex min-h-screen w-full flex-col items-center justify-center px-6">
        <div className="flex w-full max-w-sm flex-col items-center gap-6 text-center">
          <p
            className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground"
            id="interstitial-eyebrow"
          >
            cleared
          </p>
          <h1
            id="interstitial-title"
            className="font-display text-[clamp(2rem,5vw,3rem)] font-black leading-none tracking-tighter text-foreground"
          >
            tap to enter
          </h1>
          <Button
            type="button"
            variant="default"
            size="lg"
            aria-label="tap to enter"
            aria-describedby="interstitial-eyebrow"
            data-testid="interstitial-tap-cta"
            onClick={handleAdvance}
            className="min-h-[44px] w-full max-w-[320px]"
          >
            tap to enter
          </Button>
        </div>
      </div>
    </main>
  )
}
