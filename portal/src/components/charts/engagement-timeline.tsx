"use client"

import { Area, AreaChart, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import type { ApiError } from "@/lib/api/types"

interface EngagementTimelineProps {
  days?: number
  className?: string
}

const TOOLTIP_STYLE = {
  background: "oklch(0.13 0 0)",
  border: "1px solid oklch(1 0 0 / 10%)",
  borderRadius: "8px",
  color: "oklch(0.95 0 0)",
  fontSize: 12,
}

export function EngagementTimeline({ days = 30, className }: EngagementTimelineProps) {
  const { data, isLoading } = useQuery<
    Awaited<ReturnType<typeof portalApi.getScoreHistory>>,
    ApiError
  >({
    queryKey: ["portal", "score-history", days],
    queryFn: () => portalApi.getScoreHistory(days),
    staleTime: STALE_TIMES.history,
    retry: 2,
  })

  if (isLoading) {
    return <LoadingSkeleton variant="chart" className={className} />
  }

  if (!data?.points?.length) {
    return null
  }

  const chartData = data.points.map((p) => ({
    time: format(new Date(p.recorded_at), "MMM d"),
    score: Math.round(p.score * 10) / 10,
    chapter: p.chapter,
  }))

  return (
    <GlassCardWithHeader
      title="Score Timeline"
      description={`Last ${days} days`}
      className={className}
    >
      <div className="h-[240px]" aria-label={`Score timeline for last ${days} days`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
            <defs>
              <linearGradient id="engagementScoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="time"
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value: number) => [`${value}`, "Score"]}
            />

            {/* Boss threshold */}
            <ReferenceLine
              y={75}
              stroke="rgba(6,182,212,0.4)"
              strokeDasharray="3 3"
              label={{ value: "Boss", fill: "rgba(255,255,255,0.35)", fontSize: 10, position: "right" }}
            />

            {/* Danger threshold */}
            <ReferenceLine
              y={30}
              stroke="rgba(239,68,68,0.4)"
              strokeDasharray="3 3"
              label={{ value: "Danger", fill: "rgba(255,255,255,0.35)", fontSize: 10, position: "right" }}
            />

            <Area
              type="monotone"
              dataKey="score"
              stroke="#f43f5e"
              fill="url(#engagementScoreGradient)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#f43f5e", stroke: "#fff", strokeWidth: 1 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCardWithHeader>
  )
}
