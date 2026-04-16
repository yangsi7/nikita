"use client"

/**
 * DossierHeader — Step 3 of the wizard.
 *
 * Spec 214 FR-1 step 3 + FR-2 + AC-1.4 (metrics default to 50%, never the
 * legacy 75/100). Full-viewport landing-page aesthetic per
 * `docs/content/onboarding-design-brief.md` — StepShell wraps the background
 * atmosphere + framer-motion step-entry animation; this step owns the
 * hero-scale headline + classified-file metric rail.
 */

import type { CSSProperties } from "react"

import { Button } from "@/components/ui/button"
import { StepShell } from "@/app/onboarding/components/StepShell"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

export interface DossierMetrics {
  nikita: number
  trust: number
  tension: number
  memory: number
}

const DEFAULT_METRICS: DossierMetrics = {
  nikita: 50,
  trust: 50,
  tension: 50,
  memory: 50,
}

export interface DossierHeaderProps extends StepProps {
  /** Real UserMetrics; falls back to 50/50/50/50 per AC-1.4. */
  metrics?: DossierMetrics
}

export function DossierHeader({ onAdvance, metrics }: DossierHeaderProps) {
  const m = metrics ?? DEFAULT_METRICS
  const copy = WIZARD_COPY.dossierHeader
  const values: Array<[string, number]> = [
    [copy.metricLabels[0], m.nikita],
    [copy.metricLabels[1], m.trust],
    [copy.metricLabels[2], m.tension],
    [copy.metricLabels[3], m.memory],
  ]

  return (
    <StepShell testId="wizard-step-3">
      <WizardProgress current={1} total={7} />
      <header className="space-y-3">
        <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
          {copy.headline}
        </h1>
        <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
          {copy.subline}
        </p>
      </header>

      <div className="rounded-xl border border-glass-border bg-glass p-6 backdrop-blur-md">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {values.map(([label, value]) => (
            <div key={label} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs tracking-[0.2em] uppercase text-muted-foreground">
                  {label}
                </span>
                <span className="text-xs font-black tabular-nums text-primary">
                  {`${value}%`}
                </span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-glass-border">
                {/*
                  Dynamic width routed through a CSS custom property so the
                  geometry is declared via Tailwind (w-[var(--bar-width)])
                  rather than inline `style={{ width: ... }}` — spec
                  AC-2.3 forbids inline geometry literals.
                */}
                <div
                  className="h-full rounded-full bg-primary/80 w-[var(--bar-width)]"
                  style={{ "--bar-width": `${value}%` } as CSSProperties}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <Button
          type="button"
          onClick={() => onAdvance({})}
          className="text-primary font-black tracking-[0.2em] uppercase"
        >
          {copy.cta}
        </Button>
      </div>
    </StepShell>
  )
}
