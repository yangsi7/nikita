"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"

interface ConflictBannerProps {
  conflictState: string
  conflictTrigger?: string | null
  conflictStartedAt?: string | null
}

const conflictBadgeStyles: Record<string, { variant: "default" | "secondary" | "destructive" | "outline", className: string }> = {
  cold: { variant: "outline", className: "border-blue-400 text-blue-400 bg-blue-500/10" },
  passive_aggressive: { variant: "outline", className: "border-amber-400 text-amber-400 bg-amber-500/10" },
  vulnerable: { variant: "outline", className: "border-purple-400 text-purple-400 bg-purple-500/10" },
  explosive: { variant: "destructive", className: "bg-red-500/20" },
}

export function ConflictBanner({
  conflictState,
  conflictTrigger,
  conflictStartedAt,
}: ConflictBannerProps) {
  // Only render if in conflict
  if (conflictState === "none") {
    return null
  }

  // Calculate time since conflict started
  const getTimeSince = (timestamp: string | null): string => {
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

  const timeSince = getTimeSince(conflictStartedAt || null)
  const badgeStyle = conflictBadgeStyles[conflictState] || conflictBadgeStyles.explosive

  return (
    <GlassCard variant="danger" className="p-4">
      <div className="flex items-center gap-3">
        {/* Alert Icon */}
        <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-red-100">
              Nikita is upset
            </span>
            <Badge
              variant={badgeStyle.variant}
              className={cn("shrink-0", badgeStyle.className)}
            >
              {conflictState.replace("_", " ")}
            </Badge>
          </div>
          {conflictTrigger && (
            <p className="text-xs text-red-200/80 mt-1 truncate">
              {conflictTrigger}
            </p>
          )}
        </div>

        {/* Time */}
        <div className="text-xs text-red-200/60 shrink-0">
          {timeSince}
        </div>
      </div>
    </GlassCard>
  )
}
