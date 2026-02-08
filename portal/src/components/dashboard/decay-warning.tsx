"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Timer, MessageSquare } from "lucide-react"
import type { DecayStatus } from "@/lib/api/types"

interface DecayWarningProps {
  data: DecayStatus
}

export function DecayWarning({ data }: DecayWarningProps) {
  const gracePercent = (data.hours_remaining / data.grace_period_hours) * 100
  const isUrgent = gracePercent < 25
  const hours = Math.floor(data.hours_remaining)
  const minutes = Math.round((data.hours_remaining - hours) * 60)

  const progressColor = gracePercent > 50 ? "text-emerald-400" : gracePercent > 25 ? "text-amber-400" : "text-red-400"

  if (!data.is_decaying && gracePercent > 50) return null

  return (
    <GlassCard variant={isUrgent ? "danger" : "default"} className="p-6">
      <div className="flex items-center gap-4">
        <div className="relative flex items-center justify-center">
          <svg className="h-20 w-20 -rotate-90">
            <circle cx="40" cy="40" r="36" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/10" />
            <circle
              cx="40" cy="40" r="36" fill="none" stroke="currentColor" strokeWidth="4"
              className={progressColor}
              strokeDasharray={`${(gracePercent / 100) * 226} 226`}
              strokeLinecap="round"
            />
          </svg>
          <Timer className={cn("absolute h-6 w-6", progressColor)} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium">
            {data.is_decaying ? "Score is decaying!" : "Grace period running"}
          </p>
          <p className={cn("text-2xl font-bold", progressColor)}>
            {hours}h {minutes}m
          </p>
          <p className="text-xs text-muted-foreground">
            Rate: -{data.decay_rate}/hr · Projected: {Math.round(data.projected_score)}
          </p>
        </div>
        {isUrgent && (
          <Button size="sm" className="bg-rose-500 hover:bg-rose-600 animate-pulse">
            <MessageSquare className="mr-1 h-3 w-3" />
            Talk to Nikita
          </Button>
        )}
      </div>
    </GlassCard>
  )
}
