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
 * Full-viewport landing-page aesthetic via StepShell (bg-void +
 * FallingPattern + AuroraOrbs + EASE_OUT_QUART step-entry animation).
 */

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { StepShell } from "@/app/onboarding/components/StepShell"
import { SceneSelector } from "@/app/onboarding/components/scene-selector"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"
import type { SocialScene } from "@/app/onboarding/types/contracts"

export function SceneStep({ values, onAdvance }: StepProps) {
  const [scene, setScene] = useState<SocialScene | null>(values.social_scene ?? null)
  const copy = WIZARD_COPY.scene

  return (
    <StepShell testId="wizard-step-5" contentMaxWidthClass="max-w-3xl">
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
    </StepShell>
  )
}
