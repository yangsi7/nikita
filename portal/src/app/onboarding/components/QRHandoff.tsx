"use client"

/**
 * QRHandoff — desktop-only QR code that deep-links to Nikita's Telegram bot.
 *
 * Spec 214 NR-4 + AC-NR4.1..4.4. Renders nothing on mobile viewports
 * (<768px); on desktop, a <figure> wraps a qrcode.react artifact with
 * a <figcaption> carrying the canonical Nikita caption per FR-3.
 *
 * SSR strategy: the first client render uses `matches: false` (mobile)
 * to avoid hydration mismatch, then upgrades to the desktop render on
 * the first client tick if the viewport qualifies. This accepts a
 * single-frame QR flash-in on desktop as the cost of SSR safety
 * (spec §NR-4 explicit).
 */

import { useEffect, useState } from "react"
import { QRCodeSVG } from "qrcode.react"

import { WIZARD_COPY } from "@/app/onboarding/steps/copy"

export interface QRHandoffProps {
  telegramUrl: string
  label?: string
}

function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false)
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return
    }
    const mql = window.matchMedia("(min-width: 768px)")
    setIsDesktop(mql.matches)
    const listener = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    // Prefer addEventListener; fall back to addListener for older jsdom
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", listener)
      return () => mql.removeEventListener("change", listener)
    }
    mql.addListener(listener)
    return () => mql.removeListener(listener)
  }, [])
  return isDesktop
}

export function QRHandoff({ telegramUrl, label }: QRHandoffProps) {
  const isDesktop = useIsDesktop()
  if (!isDesktop) return null

  const caption = label ?? WIZARD_COPY.handoff.qrCaption
  return (
    <figure
      className="mx-auto flex flex-col items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-6"
      data-testid="qr-handoff"
    >
      <QRCodeSVG
        value={telegramUrl}
        size={160}
        bgColor="transparent"
        fgColor="oklch(0.98 0 0)"
        level="M"
      />
      <figcaption className="text-xs tracking-widest uppercase text-muted-foreground text-center max-w-[20ch]">
        {caption}
      </figcaption>
    </figure>
  )
}
