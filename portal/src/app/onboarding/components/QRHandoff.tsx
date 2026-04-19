"use client"

/**
 * QRHandoff — desktop-only QR code that deep-links to Nikita's Telegram bot.
 *
 * Spec 214 NR-4 + AC-NR4.1..4.4. Renders nothing on mobile viewports
 * (<768px); on desktop, a <figure> wraps a qrcode.react artifact with
 * a <figcaption> carrying the canonical Nikita caption per FR-3.
 *
 * SSR strategy: the first client render seeds from `window.innerWidth`
 * where available (reduces the desktop QR flash-in) and falls back to
 * mobile on the server. A listener keeps the state live across viewport
 * changes.
 *
 * Foreground colour is read from the `--foreground` CSS custom property
 * at runtime (spec AC-2.3 forbids inline `oklch(...)` literals); a hex
 * fallback matches the token for the single SSR frame before the effect
 * runs.
 */

import { useEffect, useState } from "react"
import { QRCodeSVG } from "qrcode.react"

import { WIZARD_COPY } from "@/app/onboarding/steps/copy"

export interface QRHandoffProps {
  telegramUrl: string
  label?: string
}

/** SSR-safe fallback that visually matches `--foreground` (oklch(0.95 0 0)). */
const FOREGROUND_FALLBACK_HEX = "#f2f2f2"

function readInitialIsDesktop(): boolean {
  // SSR optimisation: if we're on the client at module evaluation time,
  // seed from innerWidth so desktop users see the QR on first paint
  // instead of a single-frame mobile render.
  if (typeof window === "undefined") return false
  return typeof window.innerWidth === "number" && window.innerWidth >= 768
}

function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState<boolean>(readInitialIsDesktop)
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return
    }
    const mql = window.matchMedia("(min-width: 768px)")
    if (!mql) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- subscribe to viewport breakpoint on mount
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

function useForegroundColor(): string {
  const [fgColor, setFgColor] = useState<string>(FOREGROUND_FALLBACK_HEX)
  useEffect(() => {
    if (typeof window === "undefined" || typeof document === "undefined") return
    const fg = getComputedStyle(document.documentElement)
      .getPropertyValue("--foreground")
      .trim()
    // --foreground is stored as a full `oklch(...)` string in globals.css
    // (lines 64 + 113), so it can be assigned directly without wrapping.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot read of theme token on mount
    if (fg) setFgColor(fg)
  }, [])
  return fgColor
}

export function QRHandoff({ telegramUrl, label }: QRHandoffProps) {
  const isDesktop = useIsDesktop()
  const fgColor = useForegroundColor()
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
        fgColor={fgColor}
        level="M"
      />
      <figcaption className="text-xs tracking-widest uppercase text-muted-foreground text-center max-w-[20ch]">
        {caption}
      </figcaption>
    </figure>
  )
}
