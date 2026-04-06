"use client"

import { useState, useEffect } from "react"
import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { CloudRain } from "lucide-react"
import { cn } from "@/lib/utils"

interface ConflictBannerProps {
  conflictState: string
  conflictTrigger?: string | null
  conflictStartedAt?: string | null
}

const narrativeText: Record<string, string> = {
  cold: "Nikita went cold",
  passive_aggressive: "Nikita is being passive-aggressive",
  vulnerable: "Nikita is feeling vulnerable",
  explosive: "Nikita is furious",
}

const conflictBadgeStyles: Record<string, { variant: "default" | "secondary" | "destructive" | "outline", className: string }> = {
  cold: { variant: "outline", className: "border-blue-400 text-blue-400 bg-blue-500/10" },
  passive_aggressive: { variant: "outline", className: "border-amber-400 text-amber-400 bg-amber-500/10" },
  vulnerable: { variant: "outline", className: "border-purple-400 text-purple-400 bg-purple-500/10" },
  explosive: { variant: "destructive", className: "bg-red-500/20" },
}

// Calculate time since conflict started
function getTimeSince(timestamp: string | null): string {
  if (!timestamp) return "Unknown"

  const now = new Date()
  const started = new Date(timestamp)
  const diffMs = now.getTime() - started.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`
  if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`
  if (diffMins > 0) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`
  return "Just now"
}

export function ConflictBanner({
  conflictState,
  conflictTrigger,
  conflictStartedAt,
}: ConflictBannerProps) {
  // Compute time since on client only to avoid SSR hydration mismatch (React #418)
  const [timeSince, setTimeSince] = useState("")
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeSince(getTimeSince(conflictStartedAt || null)) // hydration-safe: compute on client only
  }, [conflictStartedAt])

  // Only render if in conflict — hooks must be above this early return
  if (conflictState === "none") {
    return null
  }

  const badgeStyle = conflictBadgeStyles[conflictState] || conflictBadgeStyles.explosive

  return (
    <GlassCard variant="default" className="p-4" role="alert" aria-live="polite">
      <div className="flex items-center gap-3">
        {/* Alert Icon */}
        <CloudRain className="h-5 w-5 text-muted-foreground shrink-0" aria-hidden="true" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-foreground/80">
              {narrativeText[conflictState] ?? "Nikita is upset"}
            </span>
            <Badge
              variant={badgeStyle.variant}
              className={cn("shrink-0", badgeStyle.className)}
            >
              {conflictState.replace(/_/g, " ")}
            </Badge>
          </div>
          {conflictTrigger && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {conflictTrigger}
            </p>
          )}
        </div>

        {/* Time */}
        <div className="text-xs text-muted-foreground/60 shrink-0">
          {timeSince}
        </div>
      </div>
    </GlassCard>
  )
}
