"use client"

/**
 * ClearanceGrantedCeremony — Spec 214 T4.1 (FR-11e).
 *
 * The full-viewport closeout that paints when `useConversationState`
 * reports `conversation_complete=true`. Mounts after the wizard's last
 * agent turn, after `POST /portal/link-telegram` has succeeded (the
 * reducer mints `linkCode` BEFORE this component is rendered so the
 * CTA can carry the deep-link payload).
 *
 * Replaces the T3.9 stub.
 *
 * Composition:
 *   - DossierStamp(state="cleared") — the "you're in" stamp
 *     plus a complementary ready line. DossierStamp
 *     already respects `prefers-reduced-motion` via
 *     `useReducedMotionCompat`, so the stamp half of AC-T4.1.2 is
 *     satisfied "for free" by composition.
 *   - Final Nikita line — short, em-dash free per project convention.
 *   - "Meet her on Telegram" CTA → t.me deep link.
 *   - Desktop-only QR code (≥768px) via the shared QRHandoff component.
 *
 * AC contracts:
 *   - AC-T4.1.1: full viewport, stamp + Nikita line + CTA + QR(desktop).
 *   - AC-T4.1.2: prefers-reduced-motion respected (DossierStamp +
 *     `prefers-reduced-motion: reduce` media query gate on the
 *     fade-in transition).
 *   - AC-T4.1.3: throws if `linkCode` is null — the link MUST be
 *     minted by the reducer BEFORE mount; rendering with a null code
 *     would produce a CTA pointing at `/start=` which Telegram would
 *     happily accept and silently strand.
 */

import { DossierStamp } from "@/app/onboarding/components/DossierStamp"
import { QRHandoff } from "@/app/onboarding/components/QRHandoff"

export interface ClearanceGrantedCeremonyProps {
  linkCode: string | null
}

const TELEGRAM_BOT_USERNAME = "Nikita_my_bot"
// Final Nikita line. Plain ASCII punctuation only; em-dashes are
// banned in user-visible UI strings per the project Output Style rule.
const FINAL_NIKITA_LINE =
  "got everything i need. see you on Telegram in a second."
const CTA_LABEL = "Meet her on Telegram"

export function ClearanceGrantedCeremony({
  linkCode,
}: ClearanceGrantedCeremonyProps) {
  // AC-T4.1.3: hard fail rather than render a broken CTA. The
  // reducer mints `linkCode` synchronously when the conversation
  // completes; a null here is a programming bug at the parent.
  if (!linkCode) {
    throw new Error(
      "ClearanceGrantedCeremony rendered without linkCode; " +
        "the reducer must mint the bridge token BEFORE mount " +
        "(Spec 214 AC-T4.1.3)."
    )
  }

  const telegramUrl = `https://t.me/${TELEGRAM_BOT_USERNAME}?start=${encodeURIComponent(
    linkCode
  )}`

  return (
    <div
      data-testid="clearance-granted-ceremony"
      // `motion-safe:` and `motion-reduce:` Tailwind variants honour
      // the user's `prefers-reduced-motion` setting at the CSS layer
      // (no JS branch). Pair with DossierStamp's reduced-motion-aware
      // typewriter so AC-T4.1.2 holds end-to-end.
      className={[
        "flex min-h-[100dvh] w-full flex-col items-center justify-center",
        "gap-8 bg-background px-6 py-12 text-center",
        "motion-safe:animate-in motion-safe:fade-in motion-safe:duration-500",
      ].join(" ")}
    >
      <div className="flex flex-col items-center gap-3">
        <p className="text-sm tracking-[0.4em] uppercase text-muted-foreground">
          you&apos;re in.
        </p>
        <DossierStamp state="cleared" className="text-3xl sm:text-4xl" />
        <p
          data-testid="ceremony-clearance-granted"
          className="text-sm tracking-[0.4em] uppercase text-primary/80"
        >
          ready.
        </p>
      </div>

      <p
        data-testid="ceremony-nikita-line"
        className="max-w-md text-base text-foreground/90"
      >
        {FINAL_NIKITA_LINE}
      </p>

      <a
        data-testid="ceremony-cta"
        href={telegramUrl}
        // External target so the user lands in the Telegram app (or web)
        // without losing the portal tab (lets them recover if their
        // browser blocks the deep-link handler).
        target="_blank"
        rel="noopener noreferrer"
        className={[
          "inline-flex h-12 items-center justify-center rounded-xl",
          "bg-primary px-8 text-sm font-medium text-primary-foreground",
          "shadow-lg transition-shadow hover:shadow-xl",
          "motion-safe:transition-transform motion-safe:hover:scale-[1.02]",
        ].join(" ")}
      >
        {CTA_LABEL}
      </a>

      <QRHandoff telegramUrl={telegramUrl} />
    </div>
  )
}
