"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { cn } from "@/lib/utils"

interface WarmthMeterProps {
  /** Warmth value from 0.0 to 1.0 (derived from intimacy) */
  value: number
}

function getWarmthLabel(value: number): string {
  if (value < 0.2) return "Cold"
  if (value < 0.4) return "Cool"
  if (value < 0.6) return "Neutral"
  if (value < 0.8) return "Warm"
  return "Hot"
}

function getWarmthColor(value: number): string {
  if (value < 0.3) return "from-blue-500 to-blue-400"
  if (value < 0.6) return "from-amber-500 to-amber-400"
  return "from-rose-500 to-rose-400"
}

function getWarmthTextColor(value: number): string {
  if (value < 0.3) return "text-blue-400"
  if (value < 0.6) return "text-amber-400"
  return "text-rose-400"
}

export function WarmthMeter({ value }: WarmthMeterProps) {
  const percentage = Math.round(value * 100)
  const label = getWarmthLabel(value)
  const gradientClass = getWarmthColor(value)
  const textColorClass = getWarmthTextColor(value)

  return (
    <GlassCard className="p-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-foreground">Warmth</h4>
          <span className={cn("text-xs font-medium", textColorClass)}>
            {label}
          </span>
        </div>

        {/* Horizontal gauge */}
        <div className="relative h-3 w-full rounded-full bg-white/10 overflow-hidden">
          <div
            className={cn(
              "absolute inset-y-0 left-0 rounded-full bg-gradient-to-r transition-all duration-700 ease-out",
              gradientClass
            )}
            style={{ width: `${percentage}%` }}
            role="progressbar"
            aria-valuenow={percentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Warmth: ${percentage}% (${label})`}
          />
        </div>

        {/* Percentage */}
        <div className="text-center">
          <span className={cn("text-2xl font-mono font-bold", textColorClass)}>
            {percentage}%
          </span>
        </div>
      </div>
    </GlassCard>
  )
}
