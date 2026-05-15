"use client"

/**
 * Dashboard empty state — shown when user has never chatted with Nikita.
 *
 * Cluster B3 (Phase-2 fix plan): the "Chat on Telegram" CTA calls
 * POST /api/v1/auth/dashboard-bridge to get a ?start=<code> deep-link
 * that atomically binds the user's telegram_id on first /start send.
 *
 * QA iter-1 Fix #2: loading state disables the button while the fetch
 * is in-flight. On error, a "Retry connection" affordance is shown.
 *
 * QA iter-2: useRef to store the AbortController across fetchBridgeUrl calls.
 * Previous in-flight controller is aborted before starting a new one, so a
 * stale slow mount result cannot overwrite a faster retry result.
 */

import * as React from "react"
import { GlassCard } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { MessageCircle, RefreshCw } from "lucide-react"
import { api } from "@/lib/api/client"

interface DashboardBridgeResponse {
  telegram_url: string
  expires_at: string
}

type FetchState =
  | { status: "loading" }
  | { status: "success"; telegram_url: string }
  | { status: "error" }

export function DashboardEmptyState() {
  const [fetchState, setFetchState] = React.useState<FetchState>({ status: "loading" })
  // QA iter-2: store controller in a ref so fetchBridgeUrl can abort the prior
  // in-flight request before creating a new one, regardless of how the second
  // call is triggered (retry click, re-render, or future polling).
  const controllerRef = React.useRef<AbortController | null>(null)

  const fetchBridgeUrl = React.useCallback(() => {
    // Abort any previous in-flight request before starting a new one.
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setFetchState({ status: "loading" })

    api.post<DashboardBridgeResponse>(
      "/auth/dashboard-bridge",
      undefined,
      undefined,
      controller.signal
    )
      .then((data) => {
        if (data.telegram_url) {
          setFetchState({ status: "success", telegram_url: data.telegram_url })
        } else {
          setFetchState({ status: "error" })
        }
      })
      .catch((err: unknown) => {
        // Ignore AbortError — a newer request has taken over.
        if (err instanceof DOMException && err.name === "AbortError") return
        setFetchState({ status: "error" })
      })
  }, [])

  React.useEffect(() => {
    fetchBridgeUrl()
    // Cleanup: abort the current in-flight request on unmount.
    return () => controllerRef.current?.abort()
  }, [fetchBridgeUrl])

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

        {fetchState.status === "success" ? (
          <Button asChild className="mt-2 bg-rose-500 hover:bg-rose-600 text-white">
            <a
              href={fetchState.telegram_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <MessageCircle className="h-4 w-4" />
              Chat on Telegram
            </a>
          </Button>
        ) : fetchState.status === "loading" ? (
          <Button
            className="mt-2 bg-rose-500 hover:bg-rose-600 text-white"
            disabled
          >
            <MessageCircle className="h-4 w-4" />
            Chat on Telegram
          </Button>
        ) : (
          <div className="flex flex-col items-center gap-2 mt-2">
            <p className="text-xs text-muted-foreground">
              Couldn&apos;t set up the connection.
            </p>
            <Button
              variant="outline"
              className="text-rose-400 border-rose-400/30"
              onClick={fetchBridgeUrl}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              Retry connection
            </Button>
          </div>
        )}
      </div>
    </GlassCard>
  )
}
