"use client"

import { useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { isTelegramIAB } from "@/lib/auth/ua"

/**
 * Spec 215 FR-6 / FR-6a — IS-A Always-Interstitial.
 *
 * Renders unconditionally after `/auth/confirm` mints the session. The user
 * must tap "Continue to Nikita" to advance — gates against Apple's
 * SFSafariViewController self-contained-session behaviour where cookies
 * minted in an in-app webview are not visible to subsequent navigations.
 *
 * "Open in Safari" Universal Link is rendered only when the UA matches the
 * Telegram in-app browser (centralized helper per GH #420).
 *
 * Same-origin guard on `?next`: protocol-relative (`//evil.com`) and absolute
 * URLs (`https://evil.com`) are rejected; falls back to `/dashboard`.
 *
 * NO em-dashes in user-facing copy (project rule).
 */
export default function InterstitialClient() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isIAB, setIsIAB] = useState(false)

  useEffect(() => {
    if (typeof navigator !== "undefined") {
      setIsIAB(isTelegramIAB(navigator.userAgent))
    }
  }, [])

  const rawNext = searchParams.get("next") ?? "/dashboard"
  const next =
    rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/dashboard"

  // Universal Link points at the canonical apex domain. The interstitial is
  // always served from the same origin, so this is the post-redirect URL the
  // user already sees in the browser bar.
  const universalLink =
    typeof window !== "undefined"
      ? `${window.location.origin}/auth/interstitial?next=${encodeURIComponent(next)}`
      : "#"

  function handleContinue() {
    router.push(next)
  }

  return (
    <main
      role="main"
      className="mx-auto flex min-h-screen max-w-md items-center justify-center p-8"
    >
      <Card
        aria-labelledby="interstitial-title"
        className="w-full rounded-2xl shadow-lg"
      >
        <CardContent className="space-y-6 p-8">
          <h1
            id="interstitial-title"
            className="font-display text-2xl text-foreground"
          >
            You&apos;re cleared. Enter the portal.
          </h1>
          <p
            id="interstitial-subtitle"
            className="text-muted-foreground text-sm"
          >
            Tap to enter your portal.
          </p>
          <div className="space-y-3">
            <Button
              variant="default"
              size="lg"
              className="w-full"
              aria-describedby="interstitial-subtitle"
              onClick={handleContinue}
            >
              Continue to Nikita
            </Button>
            {isIAB && (
              <Button
                asChild
                variant="link"
                className="w-full"
              >
                <a
                  href={universalLink}
                  aria-label="Open this page in Safari"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open in Safari
                </a>
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
