/**
 * useOptimisticTypewriter — Spec 214 T3.5.
 *
 * Reveals the given `text` character-by-character at ~40 chars/sec, capped
 * at `MAX_DURATION_MS` (1500 ms). Returns the partial-revealed string for
 * `aria-hidden` rendering plus a `done` flag. Respects
 * `prefers-reduced-motion`: when set, returns the full text on first render
 * and never schedules an interval.
 *
 * Design: one `setTimeout` tree per text; cleared on unmount or text change.
 * Cap enforcement: effective step = max(ceil(text.length / MAX_STEPS), 1).
 */

import { useEffect, useState } from "react"

export const TYPEWRITER_CHARS_PER_SECOND = 40
export const TYPEWRITER_MAX_DURATION_MS = 1500

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

export function useOptimisticTypewriter(text: string): {
  visible: string
  done: boolean
} {
  const [visible, setVisible] = useState<string>(() =>
    prefersReducedMotion() ? text : ""
  )

  useEffect(() => {
    if (prefersReducedMotion()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot reveal sync for reduced-motion
      setVisible(text)
      return
    }
    if (text.length === 0) {
      setVisible("")
      return
    }
    const perCharMs = 1000 / TYPEWRITER_CHARS_PER_SECOND
    const uncappedMs = perCharMs * text.length
    const totalMs = Math.min(uncappedMs, TYPEWRITER_MAX_DURATION_MS)
    const step = totalMs / text.length
    let i = 0
    setVisible("")
    const id = setInterval(() => {
      i += 1
      setVisible(text.slice(0, i))
      if (i >= text.length) clearInterval(id)
    }, step)
    return () => clearInterval(id)
  }, [text])

  return { visible, done: visible === text }
}
