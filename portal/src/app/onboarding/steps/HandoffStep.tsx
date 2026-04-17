"use client"

/**
 * HandoffStep — Step 11 (final) of the wizard.
 *
 * Spec 214 FR-1 step 11 + NR-5 + FR-11b (GH #321). Renders the handoff
 * to the live product:
 *   - Voice path (phone present + voiceCallState === "ringing"): pulsing
 *     voice ring + "Nikita is calling you now." headline + Telegram
 *     secondary CTA.
 *   - Voice fallback (voiceCallState === "unavailable"): ring hidden,
 *     fallback headline + Telegram primary CTA + aria-live announcement.
 *   - Text path (no phone): Telegram primary CTA + QR code on desktop.
 *
 * GH #321 REQ-1: on mount, calls `useOnboardingAPI().linkTelegram()` to
 * mint a 6-char deep-link token. The Telegram CTA's href becomes
 * `https://t.me/Nikita_my_bot?start=<code>` so the bot's `_handle_start`
 * can atomically bind `users.telegram_id` on first message. On failure
 * we do NOT render a bare-URL fallback (brief Q-3): bare-URL fallback
 * reproduces the orphan-row bug this work exists to eliminate.
 *
 * Full-viewport landing-page aesthetic via StepShell.
 */

import { useEffect, useState } from "react"

import { StepShell } from "@/app/onboarding/components/StepShell"
import { WizardProgress } from "@/app/onboarding/components/WizardProgress"
import { QRHandoff } from "@/app/onboarding/components/QRHandoff"
import { useOnboardingAPI } from "@/app/onboarding/hooks/use-onboarding-api"
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
  href,
  className,
  children,
}: {
  href: string
  className?: string
  children: React.ReactNode
}) {
  return (
    <a
      href={href}
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

/**
 * Composes the Telegram CTA deep-link. Requires a valid 6-char code minted
 * by `POST /portal/link-telegram`. Bare-URL fallback on error is NOT
 * permitted (brief Q-3).
 */
function buildTelegramHref(code: string): string {
  return `${TELEGRAM_URL}?start=${code}`
}

export function HandoffStep({ values, voiceCallState }: HandoffStepProps) {
  const copy = WIZARD_COPY.handoff
  const isVoiceRinging = voiceCallState === "ringing" && !!values.phone
  const isVoiceUnavailable = voiceCallState === "unavailable"

  // GH #321 REQ-1: mint a single-use binding code on mount. Exposed state:
  // - bindingCode: string | null     (null until resolved / error / retrying)
  // - bindingStatus: idle|loading|ready|error
  // - `retryBinding()`              invoked by the error-path Retry button
  // Code mint is orthogonal to voice/text branching, so the effect depends
  // only on `api` (memoized stable identity) and a `retryCount` state used
  // to re-fire. StrictMode's double-invoke is acceptable: each mint creates
  // a fresh row and invalidates the previous (single-row-per-user in
  // telegram_link_codes), so the final render uses the latest code.
  const api = useOnboardingAPI()
  const [bindingCode, setBindingCode] = useState<string | null>(null)
  const [bindingStatus, setBindingStatus] = useState<
    "loading" | "ready" | "error"
  >("loading")
  const [retryCount, setRetryCount] = useState<number>(0)

  useEffect(() => {
    let cancelled = false
    setBindingStatus("loading")
    api
      .linkTelegram()
      .then((response) => {
        if (!cancelled) {
          setBindingCode(response.code)
          setBindingStatus("ready")
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBindingCode(null)
          setBindingStatus("error")
        }
      })
    return () => {
      cancelled = true
    }
  }, [api, retryCount])

  const retryBinding = (): void => {
    setRetryCount((n) => n + 1)
  }

  // CTA href: armed with ?start=<code> once we have one; empty string (and
  // disabled-looking rendering) otherwise. Bare-URL fallback is forbidden.
  const telegramHref = bindingCode !== null ? buildTelegramHref(bindingCode) : ""

  // Status message for the aria-live region. Always rendered (see AC-NR5.5)
  // so assistive tech picks up the fallback transition as an announcement.
  const statusText = isVoiceUnavailable
    ? "Voice unavailable — switching to Telegram."
    : isVoiceRinging
      ? "Voice call in progress."
      : ""

  return (
    <StepShell testId="wizard-step-11">
      <div className="flex flex-col items-center gap-8 text-center">
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
              {bindingStatus === "ready" && bindingCode !== null && (
                <TelegramLink href={telegramHref}>{copy.telegramCTA}</TelegramLink>
              )}
              {bindingStatus === "loading" && (
                <span
                  data-testid="telegram-cta-loading-fallback"
                  aria-busy="true"
                  className="inline-flex items-center justify-center rounded-full bg-muted px-6 py-3 text-base text-muted-foreground font-semibold"
                >
                  {copy.telegramCTALoading}
                </span>
              )}
              {bindingStatus === "error" && (
                <button
                  type="button"
                  data-testid="telegram-cta-retry-fallback"
                  onClick={retryBinding}
                  className="inline-flex items-center justify-center rounded-full border border-destructive bg-background px-6 py-3 text-base text-destructive font-semibold transition-colors hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {copy.telegramCTARetry}
                </button>
              )}
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

        {/* Telegram CTA is always visible (AC-NR5.3) EXCEPT when the binding
            code hasn't arrived yet or failed. Bare-URL fallback is forbidden
            per brief Q-3 (GH #321). For the "unavailable" path the link is
            rendered above inside the data-testid wrapper; for all other
            paths we render it here as a secondary / primary.

            While linkTelegram() is pending, a disabled stand-in indicates
            to the user that the handoff is being prepared (no silent gap).
            On error, a retry button re-fires linkTelegram() inline without
            losing wizard state (no full-page refresh). */}
        {!isVoiceUnavailable && bindingStatus === "ready" && bindingCode !== null && (
          <TelegramLink href={telegramHref}>{copy.telegramCTA}</TelegramLink>
        )}
        {!isVoiceUnavailable && bindingStatus === "loading" && (
          <span
            data-testid="telegram-cta-loading"
            aria-busy="true"
            className="inline-flex items-center justify-center rounded-full bg-muted px-6 py-3 text-base text-muted-foreground font-semibold"
          >
            {copy.telegramCTALoading}
          </span>
        )}
        {!isVoiceUnavailable && bindingStatus === "error" && (
          <button
            type="button"
            data-testid="telegram-cta-retry"
            onClick={retryBinding}
            className="inline-flex items-center justify-center rounded-full border border-destructive bg-background px-6 py-3 text-base text-destructive font-semibold transition-colors hover:bg-destructive/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {copy.telegramCTARetry}
          </button>
        )}

        {/* GH #321: the QR must carry the deep-link too so desktop→phone
            handoff also gets the token. When the code isn't ready, we omit
            the QR rather than link to a bare URL. */}
        {bindingCode !== null && (
          <QRHandoff telegramUrl={telegramHref} />
        )}

        {bindingStatus === "error" && (
          <p className="text-sm text-destructive" role="alert">
            {copy.bindingError}
          </p>
        )}

        <p className="text-sm text-muted-foreground italic">{copy.finalLine}</p>

        {/* aria-live region — always mounted per AC-NR5.5. */}
        <div role="status" aria-live="polite" className="sr-only">
          {statusText}
        </div>
      </div>
    </StepShell>
  )
}
