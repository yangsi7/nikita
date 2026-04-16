"use client"

/**
 * DossierReveal — staggered ✓ teaching reveal (Spec 214 design-brief §"How
 * Nikita Works" Reveal Pattern, see docs/content/onboarding-design-brief.md).
 *
 * 1:1 visual sibling of `portal/src/components/landing/system-terminal.tsx`
 * but tuned for the wizard:
 *   - rose-glow ✓ marker (matches dossier theme — NOT terminal green)
 *   - label/foreground on the left, detail/muted on the right
 *   - 50ms stagger between rows by default (matches system-terminal cadence)
 *   - reduced-motion path via matchMedia: render full state on first paint
 *   - controllable: when `revealedCount` is supplied (PipelineGate), this
 *     overrides the auto stagger so the orchestrator can drive the reveal
 *     from external state (pipeline stage completion).
 *
 * The component does NOT pull `useReducedMotion` from framer-motion because
 * the global vitest mock in `portal/vitest.setup.ts` does not export it for
 * the bulk of step tests. The matchMedia + useEffect pattern is the same one
 * used by `system-terminal.tsx` and is the project-wide source of truth.
 */

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

export interface DossierRevealItem {
  label: string
  detail: string
}

export interface DossierRevealProps {
  items: DossierRevealItem[]
  /** Stagger between rows in ms. Default 50ms (matches system-terminal). */
  intervalMs?: number
  /** Override accent — defaults to rose. cyan is reserved for system-info beats. */
  accent?: "rose" | "cyan"
  /**
   * If supplied, externally controls how many rows are revealed (used by
   * PipelineGate to map pipeline-stage completion to ✓ rows). When undefined,
   * the component runs its own stagger timer.
   */
  revealedCount?: number
  className?: string
  /** Optional terminal-prompt eyebrow line shown above the rows. */
  prompt?: string
}

const DEFAULT_INTERVAL_MS = 50

const ACCENT_CLASS: Record<NonNullable<DossierRevealProps["accent"]>, string> = {
  rose: "text-primary",
  cyan: "text-cyan-glow",
}

export function DossierReveal({
  items,
  intervalMs = DEFAULT_INTERVAL_MS,
  accent = "rose",
  revealedCount,
  className,
  prompt,
}: DossierRevealProps) {
  const isControlled = typeof revealedCount === "number"
  const reducedMotionRef = useRef(false)
  const [internalCount, setInternalCount] = useState(0)

  useEffect(() => {
    // Detect reduced-motion via matchMedia (mirrors system-terminal.tsx) so
    // we don't depend on framer-motion's hook (not exported in test mocks).
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      reducedMotionRef.current = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches
    }

    if (isControlled) return

    if (reducedMotionRef.current) {
      setInternalCount(items.length)
      return
    }

    setInternalCount(0)
    let count = 0
    const id = setInterval(() => {
      count += 1
      setInternalCount(count)
      if (count >= items.length) clearInterval(id)
    }, intervalMs)
    return () => clearInterval(id)
  }, [items.length, intervalMs, isControlled])

  const visible = isControlled
    ? Math.max(0, Math.min(revealedCount ?? 0, items.length))
    : internalCount
  const accentClass = ACCENT_CLASS[accent]

  return (
    <div
      className={cn(
        "font-mono text-sm bg-glass rounded-lg border border-glass-border p-4 space-y-1",
        className
      )}
      data-testid="dossier-reveal"
    >
      {prompt ? (
        <p className="text-muted-foreground text-xs mb-3">
          <span className={accentClass}>$</span> {prompt}
        </p>
      ) : null}
      {items.map((item, i) => (
        <div
          key={`${item.label}-${i}`}
          className={cn(
            "flex items-start gap-3 transition-opacity duration-200",
            i < visible ? "opacity-100" : "opacity-0"
          )}
        >
          <span className={cn("shrink-0", accentClass)}>✓</span>
          <span className="text-foreground">{item.label}</span>
          <span className="text-muted-foreground ml-auto text-xs text-right">
            {item.detail}
          </span>
        </div>
      ))}
    </div>
  )
}
