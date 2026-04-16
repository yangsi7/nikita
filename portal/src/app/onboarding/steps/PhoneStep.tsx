"use client"

/**
 * PhoneStep — Step 9 of the wizard.
 *
 * Spec 214 FR-1 step 9 + NR-3 (country pre-flight). Binary choice:
 *   - Voice path: tel input + libphonenumber-js country detection against
 *     `SUPPORTED_PHONE_COUNTRIES`. Unsupported country → inline Nikita
 *     error and auto-switch to Telegram path.
 *   - Text path: advance with phone=null.
 *
 * Validation order (AC-NR3.2): E.164 format check FIRST, then country
 * support check. Both are purely client-side (AC-NR3.4).
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 */

import { useState } from "react"
import { parsePhoneNumberFromString } from "libphonenumber-js"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { E164_PHONE_REGEX } from "@/app/onboarding/schemas"
import {
  isSupportedPhoneCountry,
  SUPPORTED_PHONE_COUNTRIES,
} from "@/app/onboarding/constants/supported-phone-countries"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

type Path = "voice" | "text" | null
type PhoneError = "invalid_format" | "unsupported_country" | null

// Referencing the list keeps the import intentional — the constant list is
// the source of truth for NR-3.
void SUPPORTED_PHONE_COUNTRIES

export function PhoneStep({ values, onAdvance }: StepProps) {
  const [path, setPath] = useState<Path>(null)
  const [phone, setPhone] = useState<string>(values.phone ?? "")
  const [error, setError] = useState<PhoneError>(null)
  const copy = WIZARD_COPY.phone

  const validatePhone = (raw: string): PhoneError => {
    if (raw.trim() === "") return null
    // AC-NR3.2: E.164 first
    if (!E164_PHONE_REGEX.test(raw)) return "invalid_format"
    // AC-NR3.1 + NR-3.4: purely client-side country check
    const parsed = parsePhoneNumberFromString(raw)
    if (!parsed) return "invalid_format"
    if (!isSupportedPhoneCountry(parsed.country ?? null)) {
      return "unsupported_country"
    }
    return null
  }

  const handleBlur = () => {
    const next = validatePhone(phone)
    setError(next)
    if (next === "unsupported_country") {
      // AC-US4.2: auto-route to the text path
      setPath("text")
    }
  }

  const voiceReady = path === "voice" && error === null && phone.trim() !== ""
  const textSelected = path === "text"

  return (
    <section
      data-testid="wizard-step-9"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-2xl flex flex-col gap-8">
          <WizardProgress current={7} total={7} />
          <header className="space-y-3">
            <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
              {copy.headline}
            </h1>
            <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
              {copy.subline}
            </p>
          </header>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Button
              type="button"
              variant={path === "voice" ? "default" : "outline"}
              onClick={() => {
                setPath("voice")
                setError(null)
              }}
              className="tracking-[0.1em]"
            >
              {copy.voiceOption}
            </Button>
            <Button
              type="button"
              variant={path === "text" ? "default" : "outline"}
              onClick={() => {
                setPath("text")
                setError(null)
              }}
              className="tracking-[0.1em]"
            >
              {copy.textOption}
            </Button>
          </div>

          {path === "voice" && (
            <div className="rounded-xl border border-glass-border bg-glass p-6 space-y-3 backdrop-blur-md">
              <Input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                onBlur={handleBlur}
                placeholder={copy.phonePlaceholder}
                aria-invalid={error !== null}
                aria-label={copy.voiceOption}
              />
              {error === "invalid_format" && (
                <p className="text-sm text-primary">{copy.invalidFormatError}</p>
              )}
            </div>
          )}

          {/* AC-NR3.1/3.3: unsupported-country error is rendered OUTSIDE
              the voice-path gate because an unsupported number auto-routes
              path to "text" — the error must still be visible so the user
              understands WHY the Telegram path is selected. */}
          {error === "unsupported_country" && (
            <p
              className="text-sm text-primary"
              data-testid="phone-country-error"
            >
              {copy.unsupportedCountryError}
            </p>
          )}

          <div>
            {textSelected ? (
              <Button
                type="button"
                onClick={() => onAdvance({ phone: null })}
                className="text-primary font-black tracking-[0.2em] uppercase"
              >
                {copy.ctaText}
              </Button>
            ) : (
              <Button
                type="button"
                disabled={!voiceReady}
                onClick={() => onAdvance({ phone: phone.trim() })}
                className="text-primary font-black tracking-[0.2em] uppercase"
              >
                {copy.ctaVoice}
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
