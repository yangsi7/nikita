"use client"

/**
 * SceneStep — Step 5 of the wizard.
 *
 * Spec 214 FR-1 step 5. Wraps the existing `SceneSelector` primitive which
 * is already a Radix RadioGroup (satisfies AC-9.4-pattern: `role="radiogroup"`
 * root with `role="radio"` child items + roving tabindex managed by Radix).
 *
 * Life-stage is NOT collected here (per NR-1a — derived from scene); only
 * `social_scene` is forwarded in the advance patch.
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 */

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { SceneSelector } from "@/app/onboarding/components/scene-selector"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"
import type { SocialScene } from "@/app/onboarding/types/contracts"

export function SceneStep({ values, onAdvance }: StepProps) {
  const [scene, setScene] = useState<SocialScene | null>(values.social_scene ?? null)
  const copy = WIZARD_COPY.scene

  return (
    <section
      data-testid="wizard-step-5"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-3xl flex flex-col gap-8">
          <WizardProgress current={3} total={7} />
          <header className="space-y-3">
            <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
              {copy.headline}
            </h1>
            <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
              {copy.subline}
            </p>
          </header>

          <SceneSelector
            value={scene}
            onChange={(next) => setScene(next as SocialScene)}
          />

          <div>
            <Button
              type="button"
              disabled={!scene}
              onClick={() => {
                if (scene) onAdvance({ social_scene: scene })
              }}
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
