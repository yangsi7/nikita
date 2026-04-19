"use client"

/**
 * ClearanceGrantedCeremony — Spec 214 T3.9 stub (PR 4 FR-11e fills in the
 * full ceremony: stamp animation, scene backdrop, QR code on desktop).
 *
 * T3.9 scope: render a minimal "FILE CLOSED" + CTA to the t.me deep link so
 * the wizard-complete → ceremony handoff is testable end-to-end. The code
 * is read from `useConversationState`'s `linkCode` (minted in the reducer
 * BEFORE this component paints — AC-T3.9.4).
 */

import { DossierStamp } from "@/app/onboarding/components/DossierStamp"

export interface ClearanceGrantedCeremonyProps {
  linkCode: string | null
}

export function ClearanceGrantedCeremony({
  linkCode,
}: ClearanceGrantedCeremonyProps) {
  const href = linkCode
    ? `https://t.me/Nikita_my_bot?start=${encodeURIComponent(linkCode)}`
    : undefined

  return (
    <div
      data-testid="clearance-granted-ceremony"
      className="flex min-h-[100dvh] w-full flex-col items-center justify-center gap-6 bg-background px-6 py-10 text-center"
    >
      <DossierStamp />
      <p className="max-w-md text-sm text-muted-foreground">
        your file is closed. tap below to continue in Telegram.
      </p>
      {href ? (
        <a
          data-testid="ceremony-cta"
          href={href}
          className="inline-flex h-12 items-center justify-center rounded-xl bg-primary px-6 text-sm font-medium text-primary-foreground"
        >
          continue in Telegram
        </a>
      ) : (
        <p className="text-xs text-destructive">link token missing</p>
      )}
    </div>
  )
}
