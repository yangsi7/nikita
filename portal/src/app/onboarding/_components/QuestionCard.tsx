"use client"

import type { ReactNode } from "react"

/**
 * QuestionCard — glass-card surface containing NikitaReaction + headline +
 * WhyWeAsk + control + Continue/Back.
 *
 * Renders a `<main id="wizard">` landmark with `aria-label="onboarding wizard"`
 * (AC C1.12). Uses the Spec 208 `glass-card` utility — no new tokens.
 */
export function QuestionCard({ children }: { children: ReactNode }) {
  return (
    <main
      id="wizard"
      aria-label="onboarding wizard"
      className="relative w-full max-w-xl mx-auto p-6 sm:p-8 glass-card rounded-2xl"
    >
      {children}
    </main>
  )
}
