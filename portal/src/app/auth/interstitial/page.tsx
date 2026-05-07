import { headers } from "next/headers"
import { notFound } from "next/navigation"
import { userAgent } from "next/server"
import { Suspense } from "react"

import InterstitialClient from "./InterstitialClient"

interface InterstitialPageProps {
  searchParams: Promise<{ next?: string | string[] }>
}

/**
 * Spec 215 FR-6 + Spec 217-1 FR-2 — IS-A Always-Interstitial server shell.
 *
 * Server-side UA detection (AC-2.4): `userAgent({ headers })` from
 * `next/server` is the canonical Next.js 16 RSC pattern — the request
 * `User-Agent` header is parsed once on the server and passed to the
 * client component as a primitive `requireGesture` boolean. NEVER use
 * `window.navigator.userAgent` — that route caused a silent SSR/CSR
 * mismatch regression in the legacy InterstitialClient.
 *
 * UA classification:
 *   - iOS Safari (incl. standalone PWA) → requireGesture=true
 *   - Telegram in-app browser → requireGesture=true
 *   - Unknown / unparsable UA → requireGesture=true (default-safe)
 *   - Confirmed Chrome desktop, Firefox, Edge → requireGesture=false
 *
 * Same-origin guard: only `/`-prefixed `?next` paths reach the client
 * (defense in depth — client component re-checks).
 *
 * Feature-flag gated — returns 404 unless `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true`
 * (rollback safety per Spec 215 plan §18.4).
 */
export default async function InterstitialPage({
  searchParams,
}: InterstitialPageProps) {
  if (process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP !== "true") {
    notFound()
  }

  const ua = userAgent({ headers: await headers() })

  // Positive UA detection — only known-safe browsers auto-advance.
  // Anything else (iOS, Telegram IAB, unknown) requires a tap.
  const browserName = ua.browser.name ?? ""
  const osName = ua.os.name ?? ""
  const rawUa = ua.ua ?? ""

  const isIOS = osName === "iOS"
  const isMacOSSafari = osName === "Mac OS" && browserName === "Safari"
  const isTelegramIAB = /Telegram[/\s]/i.test(rawUa)
  const isConfirmedDesktop =
    !isIOS &&
    !isMacOSSafari &&
    !isTelegramIAB &&
    (browserName === "Chrome" ||
      browserName === "Firefox" ||
      browserName === "Edge" ||
      browserName === "Microsoft Edge")

  const requireGesture = !isConfirmedDesktop

  // Same-origin guard on `?next` (defense-in-depth: client re-validates).
  const params = await searchParams
  const rawNext = Array.isArray(params.next) ? params.next[0] : params.next
  const safeNext =
    typeof rawNext === "string" &&
    rawNext.startsWith("/") &&
    !rawNext.startsWith("//")
      ? rawNext
      : "/dashboard"

  return (
    <Suspense fallback={null}>
      <InterstitialClient requireGesture={requireGesture} next={safeNext} />
    </Suspense>
  )
}
