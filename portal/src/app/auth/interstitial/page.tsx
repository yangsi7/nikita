import { notFound } from "next/navigation"
import { Suspense } from "react"

import InterstitialClient from "./InterstitialClient"

/**
 * Spec 215 FR-6 — IS-A Always-Interstitial page.
 *
 * Thin server-component wrapper around `InterstitialClient`. Feature-flag
 * gated — returns 404 unless `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true`
 * (rollback safety per plan.md §18.4).
 */
export default function InterstitialPage() {
  if (process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP !== "true") {
    notFound()
  }
  return (
    <Suspense fallback={null}>
      <InterstitialClient />
    </Suspense>
  )
}
