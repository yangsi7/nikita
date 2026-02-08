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
  CALIBRATING: "border-blue-400 text-blue-400",
  IN_ZONE: "border-emerald-400 text-emerald-400",
  DRIFTING: "border-amber-400 text-amber-400",
  CLINGY: "border-orange-400 text-orange-400",
  DISTANT: "border-sky-400 text-sky-400",
  OUT_OF_ZONE: "border-red-400 text-red-400",
}

export function EngagementPulse({ data }: EngagementPulseProps) {
  const multiplierColor =
    data.multiplier >= 1.0 ? "text-emerald-400 border-emerald-400/30 bg-emerald-500/10" :
    data.multiplier >= 0.7 ? "text-amber-400 border-amber-400/30 bg-amber-500/10" :
    "text-red-400 border-red-400/30 bg-red-500/10"

  return (
    <GlassCardWithHeader
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
          const isActive = data.state === state
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
                {state.replace("_", " ")}
              </span>
            </div>
          )
        })}
      </div>
      {data.recent_transitions.length > 0 && (
        <div className="mt-4 space-y-1">
          <p className="text-xs text-muted-foreground font-medium">Recent Changes</p>
          {data.recent_transitions.slice(0, 3).map((t, i) => (
            <p key={i} className="text-xs text-muted-foreground">
              {t.from_state} → {t.to_state} · {t.reason}
            </p>
          ))}
        </div>
      )}
    </GlassCardWithHeader>
  )
}
