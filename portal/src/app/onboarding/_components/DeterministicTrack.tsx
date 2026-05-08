"use client"

/**
 * DeterministicTrack — Spec 217-3B FR-11 sibling-DOM card holding the
 * deterministic question + control + Continue affordance. Sits as the
 * first sibling under WizardShell's main flex-column container; the
 * AgentSubspace renders below it (NOT inside it — overlay was bug 4).
 *
 * AC-11.1, 11.2, 11.3 — `data-testid="deterministic-card"`. Parent is the
 * same DOM node as AgentSubspace's parent (asserted in vitest).
 *
 * AC-12.1 — when `disabled` is true (followup in flight), all interactive
 * descendants are non-focusable via `aria-hidden` + `pointer-events-none`.
 * Reaction-only does NOT set `disabled` — typing fades the reaction.
 */

import type { ReactNode } from "react"

export interface DeterministicTrackProps {
  /** Deterministic question card body — control + Continue button.
   *  Composed by WizardShell so the per-slot control switch stays out of
   *  this component. */
  children: ReactNode
  /** When true, the deterministic chrome locks (followup-in-flight or
   *  pending POST). Maps to AC-12.1 / AC-12.4 — at most ONE input
   *  focusable across both regions. */
  disabled?: boolean
  /** Optional headline rendered above children. */
  headline?: string | null
}

export function DeterministicTrack({
  children,
  disabled = false,
  headline,
}: DeterministicTrackProps) {
  return (
    <section
      data-testid="deterministic-card"
      data-disabled={disabled ? "true" : "false"}
      aria-busy={disabled ? "true" : "false"}
      className={[
        "rounded-2xl border border-white/10 bg-white/5 px-6 py-6 backdrop-blur-md",
        "shadow-[0_2px_24px_rgba(0,0,0,0.25)]",
        disabled ? "pointer-events-none opacity-60" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      // When disabled, hide the whole region from a11y tree so focus moves
      // to the agent subspace instead. Spec AC-12.4 invariant.
      aria-hidden={disabled ? "true" : "false"}
    >
      {headline ? (
        <h1 className="text-2xl sm:text-3xl font-semibold text-foreground">
          {headline}
        </h1>
      ) : null}
      <div className={headline ? "mt-6" : ""}>{children}</div>
    </section>
  )
}
