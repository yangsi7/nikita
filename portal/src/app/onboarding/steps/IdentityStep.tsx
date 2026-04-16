"use client"

/**
 * IdentityStep — Step 7 of the wizard.
 *
 * Spec 214 NR-2 + FR-1 step 7. Three optional fields:
 *   - name        (text)
 *   - age         (number, min 18, max 99)
 *   - occupation  (text, maxLength 100)
 *
 * All optional — empty advance is allowed (CTA enabled by default). The
 * only blocking validation is age < 18, which surfaces the Nikita-voiced
 * "Come back when you're older." message with an `aria-describedby` link
 * from the input to the error node (AC-9.4 a11y).
 *
 * Full-viewport landing-page aesthetic via StepShell. Renders the
 * DossierReveal data-use panel ABOVE the inputs (teaching moment #1 from
 * the design brief).
 */

import { useId, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { StepShell } from "@/app/onboarding/components/StepShell"
import { DossierReveal } from "@/app/onboarding/components/DossierReveal"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

const AGE_MIN = 18
const AGE_MAX = 99
const OCCUPATION_MAX = 100

/**
 * Design-brief §"How Nikita Works" Reveal Pattern, teaching moment #1:
 * what Nikita stores about the player and why.
 */
const IDENTITY_REVEAL_ITEMS = [
  { label: "NAME", detail: "so she calls you yours" },
  { label: "AGE", detail: "so she calibrates innuendo" },
  { label: "OCCUPATION", detail: "so she remembers your Mondays" },
  { label: "READ?", detail: "consent acknowledged" },
]

export function IdentityStep({ values, onAdvance }: StepProps) {
  const nameId = useId()
  const ageId = useId()
  const ageErrorId = useId()
  const occupationId = useId()
  const copy = WIZARD_COPY.identity

  const [name, setName] = useState<string>(values.name ?? "")
  const [age, setAge] = useState<string>(values.age !== null ? String(values.age) : "")
  const [occupation, setOccupation] = useState<string>(values.occupation ?? "")
  const [ageError, setAgeError] = useState<boolean>(false)

  const ageNumber = age === "" ? null : Number(age)
  const ageInvalid = ageNumber !== null && (Number.isNaN(ageNumber) || ageNumber < AGE_MIN)
  const canAdvance = !ageInvalid
  const showAgeError = ageInvalid || ageError

  return (
    <StepShell testId="wizard-step-7">
      <WizardProgress current={5} total={7} />
      <header className="space-y-3">
        <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
          {copy.headline}
        </h1>
        <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
          {copy.subline}
        </p>
      </header>

      <DossierReveal items={IDENTITY_REVEAL_ITEMS} prompt="data handling" />

      <div className="rounded-xl border border-glass-border bg-glass p-6 space-y-5 backdrop-blur-md">
        <div className="flex flex-col gap-2">
          <label
            htmlFor={nameId}
            className="text-xs tracking-[0.2em] uppercase text-primary"
          >
            {copy.nameLabel}
          </label>
          <Input
            id={nameId}
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={copy.namePlaceholder}
          />
        </div>

        <div className="flex flex-col gap-2">
          <label
            htmlFor={ageId}
            className="text-xs tracking-[0.2em] uppercase text-primary"
          >
            {copy.ageLabel}
          </label>
          <Input
            id={ageId}
            type="number"
            value={age}
            min={AGE_MIN}
            max={AGE_MAX}
            placeholder={copy.agePlaceholder}
            aria-invalid={showAgeError}
            aria-describedby={showAgeError ? ageErrorId : undefined}
            onChange={(e) => setAge(e.target.value)}
            onBlur={() => setAgeError(ageInvalid)}
          />
          {showAgeError && (
            <p
              id={ageErrorId}
              role="alert"
              className="text-sm text-primary"
            >
              {copy.ageError}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <label
            htmlFor={occupationId}
            className="text-xs tracking-[0.2em] uppercase text-primary"
          >
            {copy.occupationLabel}
          </label>
          <Input
            id={occupationId}
            type="text"
            value={occupation}
            maxLength={OCCUPATION_MAX}
            onChange={(e) => setOccupation(e.target.value)}
            placeholder={copy.occupationPlaceholder}
          />
        </div>
      </div>

      <div>
        <Button
          type="button"
          disabled={!canAdvance}
          onClick={() =>
            onAdvance({
              name: name.trim() === "" ? null : name.trim(),
              age: ageNumber,
              occupation: occupation.trim() === "" ? null : occupation.trim(),
            })
          }
          className="text-primary-foreground font-black tracking-[0.2em] uppercase"
        >
          {copy.cta}
        </Button>
      </div>
    </StepShell>
  )
}
