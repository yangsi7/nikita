"use client"

/**
 * HandoffStep — Step 11 (final) of the wizard.
 *
 * Spec 214 FR-1 step 11 + NR-5. Renders the handoff to the live product:
 *   - Voice path (phone present + voiceCallState === "ringing"): pulsing
 *     voice ring + "Nikita is calling you now." headline + Telegram
 *     secondary CTA.
 *   - Voice fallback (voiceCallState === "unavailable"): ring hidden,
 *     fallback headline + Telegram primary CTA + aria-live announcement.
 *   - Text path (no phone): Telegram primary CTA + QR code on desktop.
 *
 * Full-viewport landing-page aesthetic per onboarding-design-brief §1, §5.
 */

import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { QRHandoff } from "@/app/onboarding/components/QRHandoff"
import { WIZARD_COPY, TELEGRAM_URL } from "@/app/onboarding/steps/copy"
import type { StepProps } from "@/app/onboarding/steps/types"

export type VoiceCallState = "idle" | "ringing" | "unavailable"

export interface HandoffStepProps extends StepProps {
  /**
   * Voice-call status surfaced by the orchestrator. `idle` = no voice call
   * dispatched (text path). `ringing` = backend confirmed a voice call is
   * in flight. `unavailable` = voice path degraded; fall back to Telegram.
   */
  voiceCallState: VoiceCallState
}

function TelegramLink({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <a
      href={TELEGRAM_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={
        "inline-flex items-center justify-center rounded-full bg-primary px-6 py-3 text-base text-primary-foreground font-semibold glow-rose-pulse transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring " +
        (className ?? "")
      }
    >
      {children}
    </a>
  )
}

export function HandoffStep({ values, voiceCallState }: HandoffStepProps) {
  const copy = WIZARD_COPY.handoff
  const isVoiceRinging = voiceCallState === "ringing" && !!values.phone
  const isVoiceUnavailable = voiceCallState === "unavailable"

  // Status message for the aria-live region. Always rendered (see AC-NR5.5)
  // so assistive tech picks up the fallback transition as an announcement.
  const statusText = isVoiceUnavailable
    ? "Voice unavailable — switching to Telegram."
    : isVoiceRinging
    ? "Voice call in progress."
    : ""

  return (
    <section
      data-testid="wizard-step-11"
      className="relative min-h-screen overflow-hidden bg-void"
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div className="w-full max-w-2xl flex flex-col items-center gap-8 text-center">
          <WizardProgress current={7} total={7} />

          {isVoiceRinging && (
            <>
              <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
                {copy.voiceHeadline}
              </h1>
              <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
                {copy.voiceSub}
              </p>
              <div
                data-testid="voice-ring-animation"
                aria-hidden="true"
                className="relative h-32 w-32"
              >
                <span className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                <span className="absolute inset-4 rounded-full bg-primary/40 animate-pulse" />
                <span className="absolute inset-8 rounded-full bg-primary" />
              </div>
            </>
          )}

          {isVoiceUnavailable && (
            <>
              <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
                {copy.fallbackHeadline}
              </h1>
              <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
                {copy.fallbackSub}
              </p>
              <div
                data-testid="voice-fallback-telegram"
                className="flex flex-col items-center gap-4"
              >
                <TelegramLink>{copy.telegramCTA}</TelegramLink>
              </div>
            </>
          )}

          {!isVoiceRinging && !isVoiceUnavailable && (
            <>
              <h1 className="text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground">
                {copy.fallbackHeadline}
              </h1>
              <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
                {copy.fallbackSub}
              </p>
            </>
          )}

          {/* Telegram CTA is always visible (AC-NR5.3). For the "unavailable"
              path it's rendered above inside the data-testid wrapper; for
              all other paths we render it here as a secondary / primary. */}
          {!isVoiceUnavailable && <TelegramLink>{copy.telegramCTA}</TelegramLink>}

          <QRHandoff telegramUrl={TELEGRAM_URL} />

          <p className="text-sm text-muted-foreground italic">{copy.finalLine}</p>

          {/* aria-live region — always mounted per AC-NR5.5. */}
          <div role="status" aria-live="polite" className="sr-only">
            {statusText}
          </div>
        </div>
      </div>
    </section>
  )
}
