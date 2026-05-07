/**
 * Spec 217-2 FR-4a — Backstory archetype fallback surface.
 *
 * Renders a placeholder line for the first `timeoutMs` ms (default 4 s),
 * then morphs into a shadcn/ui `Alert` with a retry CTA when the BE
 * has not delivered `archetype_cards` in time. The retry handler is
 * wired by the parent (`WizardShell`) to re-POST the cached
 * `(user_id, turn_id)` answer; the BE idempotency cache dedupes.
 *
 * Root cause this guards (per spike `20260507-spec217-2-backstory-diagnosis.md`
 * §C5): `WizardShell.tsx` previously rendered an indefinite "preparing
 * the three of us…" placeholder when `state.lastResponse.output.archetype_cards`
 * was null, with no recovery path — the user-visible hang.
 *
 * Test scaffold uses `vi.useFakeTimers()` per `live-testing-protocol.md`
 * AC-T.1bis (NEVER real wall-clock — would multiply CI runtime).
 */

"use client"

import { useEffect, useState } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"

interface ArchetypeFallbackProps {
  /** Click handler — re-POST the cached answer for the current slot. */
  onRetry: () => void
  /** Pre-Alert grace window in ms. Default 4000 (within the 3-5 s
   * AC-4a.1 budget). */
  timeoutMs?: number
}

/**
 * Stable structured-log event names — kept out of the JSX tree so the
 * AC-4a.4 grep target is constant.
 */
const FALLBACK_EVENT = "backstory_fallback_fired"

export function ArchetypeFallback({
  onRetry,
  timeoutMs = 4000,
}: ArchetypeFallbackProps) {
  const [showAlert, setShowAlert] = useState(false)

  useEffect(() => {
    const id = window.setTimeout(() => {
      setShowAlert(true)
      // AC-4a.4: structured FE log on fallback fire. The payload shape
      // mirrors the BE `extra=` convention (no PII; UUIDs are not in
      // the FE banlist). The orchestrator's Sentry hook (if wired)
      // promotes this to a backend event.
      console.warn(FALLBACK_EVENT, { reason: "null_cards" })
    }, timeoutMs)
    return () => window.clearTimeout(id)
  }, [timeoutMs])

  if (!showAlert) {
    return (
      <p className="text-sm text-foreground/60">
        preparing the three of us…
      </p>
    )
  }

  return (
    <Alert variant="default" className="bg-void/60 border-primary/30">
      <AlertTitle>that step took a beat too long.</AlertTitle>
      <AlertDescription>
        <span>
          backstory pipeline didn&apos;t finish in time. give it another
          try, your last answer is cached.
        </span>
        <Button
          type="button"
          variant="default"
          size="sm"
          onClick={onRetry}
          className="mt-2 rounded-full glow-rose-pulse"
        >
          try again
        </Button>
      </AlertDescription>
    </Alert>
  )
}
