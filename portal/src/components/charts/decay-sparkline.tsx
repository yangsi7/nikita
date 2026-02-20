"use client"

import { useQuery } from "@tanstack/react-query"
import { TrendingDown, Shield } from "lucide-react"
import { portalApi } from "@/lib/api/portal"
import { cn } from "@/lib/utils"
import type { ApiError } from "@/lib/api/types"

interface DecaySparklineProps {
  className?: string
}

export function DecaySparkline({ className }: DecaySparklineProps) {
  const { data } = useQuery<
    Awaited<ReturnType<typeof portalApi.getDecayStatus>>,
    ApiError
  >({
    queryKey: ["portal", "decay"],
    queryFn: portalApi.getDecayStatus,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 2,
  })

  if (!data) return null

  const isGrace = !data.is_decaying && data.hours_remaining > 0
  const urgency =
    data.hours_remaining < 6 ? "high" : data.hours_remaining < 12 ? "medium" : "low"

  const gracePercent = isGrace
    ? Math.min(100, (data.hours_remaining / data.grace_period_hours) * 100)
    : 0

  return (
    <div className={cn("glass-card p-3 flex items-center gap-3", className)}>
      {isGrace ? (
        <Shield className="h-5 w-5 text-cyan-400 shrink-0" aria-hidden />
      ) : (
        <TrendingDown className="h-5 w-5 text-red-400 shrink-0" aria-hidden />
      )}

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {isGrace ? "Grace Period" : "Decaying"}
          </span>
          <span
            className={cn(
              "text-xs font-medium tabular-nums",
              data.is_decaying
                ? "text-red-400"
                : urgency === "high"
                  ? "text-amber-400"
                  : "text-cyan-400"
            )}
          >
            {data.is_decaying
              ? `-${data.decay_rate.toFixed(1)}/hr`
              : `${data.hours_remaining.toFixed(1)}h left`}
          </span>
        </div>

        {/* Progress bar */}
        <div
          className="mt-1.5 h-1 rounded-full bg-white/5 overflow-hidden"
          role="progressbar"
          aria-valuenow={Math.round(gracePercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Grace period remaining"
        >
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              data.is_decaying
                ? "bg-red-400"
                : urgency === "high"
                  ? "bg-amber-400"
                  : "bg-cyan-400"
            )}
            style={{ width: `${gracePercent}%` }}
          />
        </div>
      </div>
    </div>
  )
}
