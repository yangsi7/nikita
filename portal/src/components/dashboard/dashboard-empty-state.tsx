"use client"

/**
 * Dashboard empty state — shown when user has never chatted with Nikita.
 *
 * Cluster B3 (Phase-2 fix plan): the "Chat on Telegram" CTA calls
 * POST /api/v1/auth/dashboard-bridge to get a ?start=<code> deep-link
 * that atomically binds the user's telegram_id on first /start send.
 *
 * If the API call fails (network, 401, etc.) the button falls back to
 * the bare bot URL so the user is never left with a broken link.
 */

import * as React from "react"
import { GlassCard } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { MessageCircle } from "lucide-react"
import { env } from "@/lib/env"
import { api } from "@/lib/api/client"

const FALLBACK_TELEGRAM_URL = `https://t.me/${env.TELEGRAM_BOT_USERNAME}`

interface DashboardBridgeResponse {
  telegram_url: string
  expires_at: string
}

export function DashboardEmptyState() {
  const [telegramUrl, setTelegramUrl] = React.useState<string>(FALLBACK_TELEGRAM_URL)
  const [fetching, setFetching] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    async function fetchBridgeUrl() {
      try {
        const data = await api.post<DashboardBridgeResponse>(
          "/auth/dashboard-bridge",
          undefined,
          undefined,
          controller.signal
        )
        if (!cancelled && data.telegram_url) {
          setTelegramUrl(data.telegram_url)
        }
      } catch {
        // Silently fall back to the bare bot URL — user still gets a working link.
      } finally {
        if (!cancelled) setFetching(false)
      }
    }

    fetchBridgeUrl()
    return () => {
      cancelled = true
      controller.abort()
    }
  }, [])

  return (
    <GlassCard
      variant="elevated"
      className="mx-auto max-w-lg p-8 text-center"
      data-testid="dashboard-empty-state"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-rose-500/10">
          <MessageCircle className="h-7 w-7 text-rose-400" />
        </div>

        <h2 className="text-xl font-semibold text-foreground">
          Welcome to Nikita&apos;s World
        </h2>

        <p className="text-sm text-muted-foreground leading-relaxed">
          Start chatting with Nikita on Telegram to see your relationship stats
          here.
        </p>

        <Button
          asChild
          className="mt-2 bg-rose-500 hover:bg-rose-600 text-white"
        >
          <a
            href={telegramUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <MessageCircle className="h-4 w-4" />
            Chat on Telegram
          </a>
        </Button>
      </div>
    </GlassCard>
  )
}
