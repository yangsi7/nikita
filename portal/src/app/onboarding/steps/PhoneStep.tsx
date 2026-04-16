"use client"

/**
 * PhoneStep — Step 9 of the wizard.
 *
 * Spec 214 FR-1 step 9 + NR-3 (country pre-flight). Binary choice:
 *   - Voice path: tel input + libphonenumber-js country detection against
 *     `isSupportedPhoneCountry()`. Unsupported country → inline Nikita
 *     error and auto-switch to Telegram path.
 *   - Text path: advance with phone=null.
 *
 * Validation order (AC-NR3.2): E.164 format check FIRST, then country
 * support check. Both are purely client-side (AC-NR3.4).
 *
 * Inputs wire errors to the field via `aria-describedby` (AC-9.4 a11y).
 *
 * Full-viewport landing-page aesthetic via StepShell.
 */

import { useId, useState } from "react"
import { parsePhoneNumberFromString } from "libphonenumber-js"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { StepShell } from "@/app/onboarding/components/StepShell"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { E164_PHONE_REGEX } from "@/app/onboarding/schemas"
import { isSupportedPhoneCountry } from "@/app/onboarding/constants/supported-phone-countries"
import { WIZARD_COPY } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

type Path = "voice" | "text" | null
type PhoneError = "invalid_format" | "unsupported_country" | null

export function PhoneStep({ values, onAdvance }: StepProps) {
  const phoneInputId = useId()
  const phoneFormatErrorId = useId()
  const phoneCountryErrorId = useId()
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

  const describedBy =
    error === "invalid_format"
      ? phoneFormatErrorId
      : error === "unsupported_country"
        ? phoneCountryErrorId
        : undefined

  return (
    <StepShell testId="wizard-step-9">
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
            id={phoneInputId}
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            onBlur={handleBlur}
            placeholder={copy.phonePlaceholder}
            aria-invalid={error !== null}
            aria-describedby={describedBy}
            aria-label={copy.voiceOption}
            data-testid="phone-input"
          />
          {error === "invalid_format" && (
            <p
              id={phoneFormatErrorId}
              role="alert"
              className="text-sm text-primary"
            >
              {copy.invalidFormatError}
            </p>
          )}
        </div>
      )}

      {/* AC-NR3.1/3.3: unsupported-country error is rendered OUTSIDE
          the voice-path gate because an unsupported number auto-routes
          path to "text" — the error must still be visible so the user
          understands WHY the Telegram path is selected. */}
      {error === "unsupported_country" && (
        <p
          id={phoneCountryErrorId}
          role="alert"
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
            className="text-primary-foreground font-black tracking-[0.2em] uppercase"
          >
            {copy.ctaText}
          </Button>
        ) : (
          <Button
            type="button"
            disabled={!voiceReady}
            onClick={() => onAdvance({ phone: phone.trim() })}
            className="text-primary-foreground font-black tracking-[0.2em] uppercase"
          >
            {copy.ctaVoice}
          </Button>
        )}
      </div>
    </StepShell>
  )
}
