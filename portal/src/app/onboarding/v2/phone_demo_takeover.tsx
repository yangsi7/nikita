"use client"

/**
 * PhoneDemoTakeover — FR-010 full-screen takeover during phone-demo call (Spec 218 slice 218-7)
 *
 * Requirements (FR-010):
 * - Full-screen takeover, focus-trapped via role="dialog" + aria-modal
 * - aria-live="polite" announces "Nikita is calling. Please wait."
 * - prefers-reduced-motion: static icon instead of animated waveform
 * - "End early" button visible after 5s (prevents accidental dismissal)
 * - Dismisses automatically on Supabase Realtime status update (call ended)
 * - 30-second ceiling timeout auto-dismisses as fallback
 *
 * Realtime subscription: postgres_changes on phone_demo_calls filtered by user_id.
 * Polling is FORBIDDEN (spec §Entity 2).
 *
 * Cluster X: removed 📞 emoji (replaced with Lucide Phone icon);
 * replaced inline-style height/delay with CSS custom properties;
 * replaced raw <button> with shadcn Button.
 */

import { useEffect, useRef, useState } from "react"
import { Phone } from "lucide-react"

import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"

// Ceiling timeout: auto-dismiss after 30s if no Realtime event arrives (FR-010)
const CEILING_TIMEOUT_MS = 30_000
// "End early" button appears after 5s minimum delay (FR-010)
const END_EARLY_DELAY_MS = 5_000

// Terminal statuses that should close the takeover
const TERMINAL_STATUSES = new Set([
  "ended_success",
  "ended_busy",
  "ended_no_answer",
  "ended_error",
  "ceiling_timeout",
])

export interface PhoneDemoTakeoverProps {
  userId: string
  onComplete: (status: "ended_success" | "ended_error" | "ceiling_timeout") => void
}

export function PhoneDemoTakeover({ userId, onComplete }: PhoneDemoTakeoverProps) {
  const [showEndEarly, setShowEndEarly] = useState(false)
  const ceilingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const endEarlyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const completedRef = useRef(false)

  function complete(status: "ended_success" | "ended_error" | "ceiling_timeout") {
    if (completedRef.current) return
    completedRef.current = true
    if (ceilingTimerRef.current) clearTimeout(ceilingTimerRef.current)
    if (endEarlyTimerRef.current) clearTimeout(endEarlyTimerRef.current)
    onComplete(status)
  }

  useEffect(() => {
    // Ceiling timeout — auto-dismiss after 30s (FR-010)
    ceilingTimerRef.current = setTimeout(() => {
      complete("ceiling_timeout")
    }, CEILING_TIMEOUT_MS)

    // "End early" button appears after 5s (FR-010)
    endEarlyTimerRef.current = setTimeout(() => {
      setShowEndEarly(true)
    }, END_EARLY_DELAY_MS)

    // Supabase Realtime subscription on phone_demo_calls (spec §Entity 2)
    // Polling FORBIDDEN — only Realtime events drive dismissal.
    const supabase = createClient()
    const channel = supabase
      .channel(`phone_demo_calls:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "phone_demo_calls",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          const newStatus: string = payload.new?.status ?? ""
          if (TERMINAL_STATUSES.has(newStatus)) {
            complete(
              newStatus === "ended_success"
                ? "ended_success"
                : newStatus === "ceiling_timeout"
                  ? "ceiling_timeout"
                  : "ended_error"
            )
          }
        }
      )
      .subscribe()

    return () => {
      if (ceilingTimerRef.current) clearTimeout(ceilingTimerRef.current)
      if (endEarlyTimerRef.current) clearTimeout(endEarlyTimerRef.current)
      void supabase.removeChannel(channel)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId])

  async function handleEndEarly() {
    try {
      await fetch("/api/v1/onboarding/phone-demo/end-call", {
        method: "POST",
        credentials: "include",
      })
    } catch {
      // best-effort
    }
    complete("ended_error")
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Phone demo active"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background"
    >
      {/* aria-live region (FR-010) */}
      <div aria-live="polite" className="sr-only">
        Nikita is calling. Please wait.
      </div>

      {/* Animated waveform (motion:safe) — CSS custom properties for bar height + delay */}
      <div
        aria-hidden="true"
        className="motion-reduce:hidden mb-6 flex gap-1 items-end h-16"
      >
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="w-2 rounded-full bg-foreground animate-bounce h-[var(--bar-h)] [animation-delay:var(--bar-delay)]"
            style={{ "--bar-h": `${24 + i * 8}px`, "--bar-delay": `${i * 0.1}s` } as React.CSSProperties}
          />
        ))}
      </div>

      {/* Static icon for prefers-reduced-motion (FR-010) — Lucide Phone, no emoji */}
      <div
        aria-hidden="true"
        className="hidden motion-reduce:flex flex-col items-center gap-4 mb-6"
      >
        <Phone className="h-12 w-12 stroke-1" />
        <p className="text-lg font-medium">Calling&hellip;</p>
      </div>

      <p className="text-xl font-semibold mb-2">Nikita&apos;s calling&hellip;</p>
      <p className="text-sm text-muted-foreground mb-8">Answer when your phone rings</p>

      {/* End early button — visible only after 5s delay (FR-010) */}
      {showEndEarly && (
        <Button
          type="button"
          variant="outline"
          onClick={() => void handleEndEarly()}
        >
          End early
        </Button>
      )}
    </div>
  )
}
