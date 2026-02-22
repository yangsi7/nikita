"use client"

import { useMemo, useCallback, useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import type { PortalNotification } from "@/lib/api/types"

const STORAGE_KEY = "nikita-read-notifications"

function getReadIds(): Set<string> {
  if (typeof window === "undefined") return new Set()
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return new Set(stored ? (JSON.parse(stored) as string[]) : [])
  } catch {
    return new Set()
  }
}

function saveReadIds(ids: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]))
  } catch {
    // localStorage unavailable — silently ignore
  }
}

export function useNotifications() {
  const [readIds, setReadIds] = useState<Set<string>>(new Set())

  // Hydrate from localStorage after mount to avoid SSR mismatch
  /* eslint-disable react-hooks/set-state-in-effect -- localStorage hydration must happen in effect */
  useEffect(() => {
    setReadIds(getReadIds())
  }, [])
  /* eslint-enable react-hooks/set-state-in-effect */

  const { data: scoreHistory } = useQuery({
    queryKey: ["portal", "score-history", 7],
    queryFn: () => portalApi.getScoreHistory(7),
    staleTime: STALE_TIMES.history,
    retry: 2,
  })

  const { data: engagement } = useQuery({
    queryKey: ["portal", "engagement"],
    queryFn: portalApi.getEngagement,
    staleTime: STALE_TIMES.stats,
    retry: 2,
  })

  const { data: decay } = useQuery({
    queryKey: ["portal", "decay"],
    queryFn: portalApi.getDecayStatus,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 2,
  })

  const notifications = useMemo<PortalNotification[]>(() => {
    const notifs: PortalNotification[] = []

    // Generate notifications from score history events
    if (scoreHistory?.points) {
      const recent = scoreHistory.points.slice(-10)
      for (const point of recent) {
        if (point.event_type === "chapter_advance") {
          const id = `chapter-${point.recorded_at}`
          notifs.push({
            id,
            type: "chapter_advance",
            title: "Chapter Advanced!",
            message: `You've reached Chapter ${point.chapter}`,
            timestamp: point.recorded_at,
            read: readIds.has(id),
            actionHref: "/dashboard",
          })
        }
        if (point.event_type === "boss_encounter") {
          const id = `boss-${point.recorded_at}`
          notifs.push({
            id,
            type: "boss_encounter",
            title: "Boss Encounter",
            message: `Score: ${point.score.toFixed(1)}`,
            timestamp: point.recorded_at,
            read: readIds.has(id),
            actionHref: "/dashboard",
          })
        }
      }
    }

    // Generate notifications from engagement transitions
    if (engagement?.recent_transitions) {
      for (const t of engagement.recent_transitions.slice(0, 5)) {
        const id = `engage-${t.created_at}`
        notifs.push({
          id,
          type: "engagement_shift",
          title: "Engagement Changed",
          message: `${t.from_state ?? "unknown"} → ${t.to_state}${t.reason ? `: ${t.reason}` : ""}`,
          timestamp: t.created_at,
          read: readIds.has(id),
          actionHref: "/dashboard/engagement",
        })
      }
    }

    // Generate decay warning notification
    if (decay?.is_decaying) {
      const id = "decay-warning"
      notifs.push({
        id,
        type: "decay_warning",
        title: "Score Decaying!",
        message: `Your score is dropping. Current: ${decay.current_score.toFixed(1)} → Projected: ${decay.projected_score.toFixed(1)}`,
        timestamp: new Date().toISOString(),
        read: readIds.has(id),
        actionHref: "/dashboard",
      })
    }

    // Sort newest first
    return notifs.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
  }, [scoreHistory, engagement, decay, readIds])

  const unreadCount = notifications.filter((n) => !n.read).length

  const markAsRead = useCallback((id: string) => {
    setReadIds((prev) => {
      const next = new Set(prev)
      next.add(id)
      saveReadIds(next)
      return next
    })
  }, [])

  const markAllAsRead = useCallback(() => {
    setReadIds((prev) => {
      const next = new Set(prev)
      for (const n of notifications) next.add(n.id)
      saveReadIds(next)
      return next
    })
  }, [notifications])

  return { notifications, unreadCount, markAsRead, markAllAsRead }
}
