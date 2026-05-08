"use client"

/**
 * AgentSubspace — Spec 217-3B FR-11 sibling-DOM card rendering the
 * agent reaction OR followup question, BELOW the deterministic track
 * (never overlapping it — that was user bug 4).
 *
 * Renders one of:
 *  - reaction text (typing fades it; deterministic stays enabled)
 *  - followup question (deterministic LOCKS until resolved)
 *  - turn_failure explanation (with retry CTA)
 *  - nothing (initial / deterministic_advance / completion)
 *
 * AC-11.1, 11.2, 11.3 — `data-testid="agent-subspace"`. Parent = sibling
 * to DeterministicTrack.
 *
 * AC-12.2 — followup focuses an interactive input INSIDE this region;
 * AC-12.4 invariant requires DeterministicTrack to be disabled while a
 * followup is open.
 */

import { AnimatePresence, motion } from "framer-motion"

import type { AgentView } from "./agent-view"

export interface AgentSubspaceProps {
  view: AgentView
  /** Reduced-motion flag from the parent (centralized so AnimatePresence
   *  here can match the wizard's overall motion stance). */
  reduceMotion?: boolean
  /** Optional retry handler shown alongside `failureExplanation`. */
  onRetry?: () => void
  /** Unique identifier per turn — used as the AnimatePresence key so
   *  consecutive responses with identical text (e.g. two "got it"
   *  reactions) still trigger the exit/enter cinematic. WizardShell
   *  passes `state.lastTurnId`. Falls back to a content-derived key
   *  when null (initial paint). QA iter-1 IMPORTANT-3 fix. */
  turnId?: string | null
}

export function AgentSubspace({
  view,
  reduceMotion = false,
  onRetry,
  turnId = null,
}: AgentSubspaceProps) {
  const hasContent =
    view.reactionText !== null ||
    view.followupQuestion !== null ||
    view.failureExplanation !== null

  return (
    <section
      data-testid="agent-subspace"
      data-mode={
        view.followupQuestion
          ? "followup"
          : view.failureExplanation
            ? "failure"
            : view.reactionText
              ? "reaction"
              : "idle"
      }
      aria-live="polite"
      className="rounded-2xl border border-white/5 bg-white/[0.03] px-6 py-4 backdrop-blur-sm min-h-[1px]"
    >
      <AnimatePresence mode="wait">
        {hasContent ? (
          <motion.div
            // Prefer the per-turn UUID so consecutive identical-text
            // responses still play exit/enter; fall back to derived key
            // for first paint when turnId is still null.
            key={
              turnId ??
              (view.followupQuestion ?? "") +
                (view.reactionText ?? "") +
                (view.failureExplanation ?? "")
            }
            initial={
              reduceMotion
                ? false
                : { opacity: 0, y: 8, filter: "blur(4px)" }
            }
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={
              reduceMotion ? { opacity: 0 } : { opacity: 0, y: -8 }
            }
            transition={
              reduceMotion ? { duration: 0 } : { duration: 0.25 }
            }
          >
            {view.followupQuestion ? (
              <p
                data-testid="agent-followup"
                className="text-base text-foreground/90"
              >
                {view.followupQuestion}
              </p>
            ) : null}
            {view.reactionText && !view.followupQuestion ? (
              <p
                data-testid="agent-reaction"
                className="text-sm text-foreground/70 italic"
              >
                {view.reactionText}
              </p>
            ) : null}
            {view.failureExplanation ? (
              <div className="flex items-start justify-between gap-3">
                <p
                  data-testid="agent-failure"
                  className="text-sm text-foreground/70"
                >
                  {view.failureExplanation}
                </p>
                {onRetry ? (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="text-xs underline text-foreground/80 hover:text-foreground"
                  >
                    try again
                  </button>
                ) : null}
              </div>
            ) : null}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </section>
  )
}
