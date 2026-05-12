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
 */

import { useEffect, useRef, useState } from "react"

import { createClient } from "@/lib/supabase/client"

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
      .channel("phone_demo_calls")
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
      await fetch("/api/v1/converse/onboarding/phone-demo/end-call", {
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

      {/* Animated waveform (motion:safe) */}
      <div
        aria-hidden="true"
        className="motion-reduce:hidden mb-6 flex gap-1 items-end h-16"
      >
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="w-2 rounded-full bg-foreground animate-bounce"
            style={{
              height: `${24 + i * 8}px`,
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>

      {/* Static icon for prefers-reduced-motion (FR-010) */}
      <div
        aria-hidden="true"
        className="hidden motion-reduce:flex flex-col items-center gap-4 mb-6"
      >
        <span className="text-5xl">📞</span>
        <p className="text-lg font-medium">Calling…</p>
      </div>

      <p className="text-xl font-semibold mb-2">Nikita&apos;s calling…</p>
      <p className="text-sm text-muted-foreground mb-8">Answer when your phone rings</p>

      {/* End early button — visible only after 5s delay (FR-010) */}
      {showEndEarly && (
        <button
          type="button"
          className="rounded-md border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          onClick={() => void handleEndEarly()}
        >
          End early
        </button>
      )}
    </div>
  )
}
