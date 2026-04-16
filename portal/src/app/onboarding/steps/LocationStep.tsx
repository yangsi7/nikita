"use client"

/**
 * LocationStep — Step 4 of the wizard.
 *
 * Spec 214 FR-1 step 4 + FR-4 (AC-4.0 inline venue preview after 800ms blur
 * debounce) + AC-6.2 (advance with `location_city` patch).
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5:
 * delegated to StepShell (bg-void + FallingPattern + AuroraOrbs +
 * EASE_OUT_QUART step-entry animation).
 */

import { useEffect, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { StepShell } from "@/app/onboarding/components/StepShell"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"
import type { StepProps } from "@/app/onboarding/steps/types"
import type { SocialScene } from "@/app/onboarding/types/contracts"

/**
 * Venue-preview blur debounce.
 *
 * Current: 800ms (spec AC-4.0)
 * Prior: —
 * Rationale: Spec mandates 800ms exact debounce on blur. Shorter would
 *   hammer the rate-limited preview endpoint (5/min shared quota);
 *   longer would feel laggy after the user has clearly stopped typing.
 */
const VENUE_PREVIEW_DEBOUNCE_MS = 800

/** Minimum city length before the CTA is enabled (matches schemas.ts). */
const MIN_CITY_LENGTH = 2

export function LocationStep({ values, onAdvance }: StepProps) {
  const api = useOnboardingAPI()
  const [city, setCity] = useState<string>(values.location_city ?? "")
  const [venues, setVenues] = useState<string[]>([])
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const copy = WIZARD_COPY.location

  useEffect(() => {
    return () => {
      if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    }
  }, [])

  const requestPreview = (rawCity: string) => {
    if (rawCity.trim().length < MIN_CITY_LENGTH) return
    api
      .previewBackstory({
        city: rawCity,
        // Step 4 fires with a minimal payload — other fields null/default
        // per AC-4.0.
        social_scene: (values.social_scene ?? "techno") as SocialScene,
        darkness_level: values.drug_tolerance ?? 3,
        life_stage: null,
        interest: null,
        age: null,
        occupation: null,
      })
      .then((resp) => {
        setVenues(resp.venues_used ?? [])
      })
      .catch(() => {
        // Silent per §Edge-Case Decisions — full submit at step 10 retries.
      })
  }

  const handleBlur = () => {
    if (debounceRef.current !== null) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      requestPreview(city)
    }, VENUE_PREVIEW_DEBOUNCE_MS)
  }

  const canAdvance = city.trim().length >= MIN_CITY_LENGTH

  return (
    <StepShell testId="wizard-step-4">
      <WizardProgress current={2} total={7} />
      <header className="space-y-3">
        <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
          {copy.headline}
        </h1>
        <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
          {copy.subline}
        </p>
      </header>

      <div className="space-y-4">
        <Input
          type="text"
          value={city}
          placeholder={copy.placeholder}
          onChange={(e) => setCity(e.target.value)}
          onBlur={handleBlur}
          aria-label={copy.placeholder}
          data-testid="location-city-input"
          className="bg-glass border-glass-border text-foreground"
        />
        {venues.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs tracking-[0.2em] uppercase text-primary">
              {copy.venuePreviewLabel}
            </p>
            <ul className="flex flex-wrap gap-2">
              {venues.map((v) => (
                <li
                  key={v}
                  className="rounded-full border border-glass-border bg-glass px-3 py-1 text-xs text-muted-foreground"
                >
                  {v}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div>
        <Button
          type="button"
          disabled={!canAdvance}
          onClick={() => onAdvance({ location_city: city.trim() })}
          className="text-primary font-black tracking-[0.2em] uppercase"
        >
          {copy.cta}
        </Button>
      </div>
    </StepShell>
  )
}
