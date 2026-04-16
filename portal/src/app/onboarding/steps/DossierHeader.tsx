"use client"

/**
 * DossierHeader — Step 3 of the wizard.
 *
 * Spec 214 FR-1 step 3 + FR-2 + AC-1.4 (metrics default to 50%, never the
 * legacy 75/100). Full-viewport landing-page aesthetic per
 * `docs/content/onboarding-design-brief.md` — FallingPattern + AuroraOrbs +
 * `bg-void` wrapper with a hero-scale headline and the classified-file
 * metric rail.
 */

import { Button } from "@/components/ui/button"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
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
    <section
      data-testid="wizard-step-3"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-2xl flex flex-col gap-8">
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
                    <div
                      className="h-full rounded-full bg-primary/80"
                      style={{ width: `${value}%` }}
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
        </div>
      </div>
    </section>
  )
}
