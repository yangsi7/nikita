"use client"

/**
 * DarknessStep — Step 6 of the wizard.
 *
 * Spec 214 FR-1 step 6 + Edginess slider with live Nikita quote. The
 * slider primitive owns its own level-label mapping (see
 * `components/edginess-slider.tsx`); this step renders the Nikita framing
 * around it and advances with `drug_tolerance` on CTA click.
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 * Renders the DossierReveal consequence ladder above the slider (teaching
 * moment #2 from the design brief).
 */

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { EdginessSlider } from "@/app/onboarding/components/edginess-slider"
import { DossierReveal } from "@/app/onboarding/components/DossierReveal"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

/**
 * Design-brief §"How Nikita Works" Reveal Pattern, teaching moment #2:
 * consequence ladder for the darkness/edginess slider positions.
 */
const DARKNESS_REVEAL_ITEMS = [
  { label: "0.2", detail: "soft chaos, no scars" },
  { label: "0.4", detail: "real fights, real grace" },
  { label: "0.6", detail: "vice surfaces in week 2" },
  { label: "0.8", detail: "she fights you for it" },
  { label: "1.0", detail: "she will not save you" },
]

export function DarknessStep({ values, onAdvance }: StepProps) {
  const [level, setLevel] = useState<number>(values.drug_tolerance ?? 3)
  const copy = WIZARD_COPY.darkness

  return (
    <section
      data-testid="wizard-step-6"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-2xl flex flex-col gap-8">
          <WizardProgress current={4} total={7} />
          <header className="space-y-3">
            <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
              {copy.headline}
            </h1>
            <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
              {copy.subline}
            </p>
          </header>

          <DossierReveal items={DARKNESS_REVEAL_ITEMS} prompt="consequence ladder" />

          <div className="rounded-xl border border-glass-border bg-glass p-8 backdrop-blur-md">
            <EdginessSlider value={level} onChange={setLevel} />
          </div>

          <div>
            <Button
              type="button"
              onClick={() => onAdvance({ drug_tolerance: level })}
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
