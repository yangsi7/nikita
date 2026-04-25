/**
 * WizardProgress — step progress label.
 *
 * Spec 214 FR-2 + Shared Chrome in `docs/content/wizard-copy.md`.
 * Renders the canonical "step n of 7" label in the
 * `text-xs tracking-[0.2em] uppercase text-muted-foreground`
 * cadence used throughout the wizard.
 */

import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import { cn } from "@/lib/utils"

export interface WizardProgressProps {
  current: number
  total: number
  className?: string
}

export function WizardProgress({
  current,
  total,
  className,
}: WizardProgressProps) {
  const label =
    total === 7
      ? WIZARD_COPY.progress.label(current)
      : `step ${current} of ${total}`
  return (
    <p
      className={cn(
        "text-xs tracking-[0.2em] uppercase text-muted-foreground",
        className
      )}
      data-testid="wizard-progress"
    >
      {label}
    </p>
  )
}
