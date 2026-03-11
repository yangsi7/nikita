"use client"

import { Clock } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DecayStatus } from "@/lib/api/types"

interface DecayCountdownProps {
  decay: DecayStatus
}

export function DecayCountdown({ decay }: DecayCountdownProps) {
  const gracePercent = decay.grace_period_hours > 0
    ? (decay.hours_remaining / decay.grace_period_hours) * 100
    : 100

  const colorClass = gracePercent > 50
    ? "text-emerald-400"
    : gracePercent > 25
      ? "text-amber-400"
      : "text-rose-400"

  const hours = Math.floor(decay.hours_remaining)
  const minutes = Math.round((decay.hours_remaining % 1) * 60)

  return (
    <div className="flex items-center gap-2 text-xs">
      <Clock className={cn("h-3.5 w-3.5", colorClass)} />
      <span className="text-muted-foreground">Grace:</span>
      <span className={colorClass}>{hours}h {minutes}m</span>
      {decay.is_decaying && (
        <span className="text-rose-400">(-{decay.decay_rate}%/hr)</span>
      )}
    </div>
  )
}
