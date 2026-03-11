"use client"

import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { ENGAGEMENT_STATES } from "@/lib/constants"
import { cn } from "@/lib/utils"
import type { EngagementData } from "@/lib/api/types"

interface EngagementPulseProps {
  data: EngagementData
}

const stateColors: Record<string, string> = {
  calibrating: "border-blue-400 text-blue-400",
  in_zone: "border-emerald-400 text-emerald-400",
  drifting: "border-amber-400 text-amber-400",
  clingy: "border-orange-400 text-orange-400",
  distant: "border-sky-400 text-sky-400",
  out_of_zone: "border-red-400 text-red-400",
}

const MULTIPLIER_MESSAGES: Record<string, string> = {
  calibrating: "Getting to know your rhythm. Just be yourself.",
  in_zone: "Perfect balance. Every conversation counts at full value.",
  drifting: "Your engagement is fading. A thoughtful message could help.",
  clingy: "Frequent messaging is dampening your score gains. Give her space.",
  distant: "She misses you. Reconnect to restore your full impact.",
  out_of_zone: "Your interaction pattern needs a reset. Find your rhythm.",
}

export function EngagementPulse({ data }: EngagementPulseProps) {
  const multiplierColor =
    data.multiplier >= 1.0 ? "text-emerald-400 border-emerald-400/30 bg-emerald-500/10" :
    data.multiplier >= 0.7 ? "text-amber-400 border-amber-400/30 bg-amber-500/10" :
    "text-red-400 border-red-400/30 bg-red-500/10"

  return (
    <GlassCardWithHeader
      data-testid="card-engagement-chart"
      title="Engagement Pulse"
      description="Contact frequency affects your score multiplier"
      action={
        <Badge variant="outline" className={multiplierColor}>
          {data.multiplier.toFixed(1)}x
        </Badge>
      }
    >
      <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
        {ENGAGEMENT_STATES.map((state) => {
          const isActive = data.state?.toLowerCase() === state
          return (
            <div
              key={state}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all",
                isActive
                  ? cn(stateColors[state], "border-current shadow-lg", "animate-pulse")
                  : "border-white/5 text-muted-foreground/50"
              )}
            >
              <div className={cn(
                "h-3 w-3 rounded-full",
                isActive ? "bg-current" : "bg-white/10"
              )} />
              <span className="text-[10px] font-medium leading-tight text-center">
                {state.replace(/_/g, " ")}
              </span>
            </div>
          )
        })}
      </div>
      {MULTIPLIER_MESSAGES[data.state] && (
        <p className={cn("text-xs mt-3",
          data.multiplier >= 1.0 ? "text-emerald-400/80" :
          data.multiplier >= 0.7 ? "text-amber-400/80" : "text-rose-400/80"
        )}>
          {MULTIPLIER_MESSAGES[data.state]}
        </p>
      )}
      {data.recent_transitions.length > 0 && (
        <div className="mt-4 space-y-1">
          <p className="text-xs text-muted-foreground font-medium">Recent Changes</p>
          {data.recent_transitions.slice(0, 3).map((t, i) => (
            <p key={i} className="text-xs text-muted-foreground">
              {(t.from_state ?? "").replace(/_/g, " ")} → {t.to_state.replace(/_/g, " ")} · {t.reason}
            </p>
          ))}
        </div>
      )}
    </GlassCardWithHeader>
  )
}
