"use client"

/**
 * PhoneDemoTakeover — FR-010 full-screen takeover during phone-demo call (Spec 218 slice 218-7)
 *
 * Requirements (FR-010):
 * - Full-screen takeover, focus-trapped
 * - aria-live="polite" announces "Nikita is calling. Please wait."
 * - prefers-reduced-motion: static icon instead of animated waveform
 * - "End early" button visible after 5s (prevents accidental dismissal)
 * - Dismisses automatically on Supabase Realtime status update (call.ended)
 * - 30-second ceiling timeout auto-dismisses as fallback
 *
 * Stub — GREEN phase provides full implementation.
 */

export interface PhoneDemoTakeoverProps {
  userId: string
  onComplete: (status: "ended_success" | "ended_error" | "ceiling_timeout") => void
}

export function PhoneDemoTakeover({ userId, onComplete }: PhoneDemoTakeoverProps) {
  // GREEN phase: full implementation. Stub raises to surface import errors.
  throw new Error("PhoneDemoTakeover — GREEN phase not implemented")

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Phone demo active"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background"
    >
      {/* aria-live region for accessibility (FR-010) */}
      <div aria-live="polite" className="sr-only">
        Nikita is calling. Please wait.
      </div>

      {/* Animated waveform placeholder (motion:safe) / static icon (motion:reduce) */}
      <div className="motion-reduce:hidden">
        {/* Animated waveform — GREEN phase */}
      </div>
      <div className="hidden motion-reduce:flex flex-col items-center gap-4">
        <span className="text-4xl">📞</span>
        <p className="text-lg font-medium">Calling…</p>
      </div>

      {/* End early button — visible after 5s (FR-010) */}
      {/* GREEN phase handles the 5s delay */}
      <button
        type="button"
        className="mt-8 rounded-md border px-4 py-2 text-sm"
        onClick={() => onComplete("ended_error")}
      >
        End early
      </button>
    </div>
  )
}
