"use client"

import { useEffect, useState } from "react"
import { formatDate, formatRelativeTime } from "@/lib/utils"

interface RelativeTimeProps {
  date: string | Date
  className?: string
}

/**
 * Hydration-safe relative time display.
 *
 * Renders the absolute date during SSR (deterministic), then switches
 * to relative time ("5m ago") after client mount. Updates every 60s.
 */
export function RelativeTime({ date, className }: RelativeTimeProps) {
  const [display, setDisplay] = useState(() => formatDate(date))

  useEffect(() => {
    // Intentional: switch from SSR absolute date to relative time on client mount.
    // The synchronous setState here is safe — it batches with the effect commit.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDisplay(formatRelativeTime(date))

    const interval = setInterval(() => {
      setDisplay(formatRelativeTime(date))
    }, 60_000)

    return () => clearInterval(interval)
  }, [date])

  return <span className={className}>{display}</span>
}
