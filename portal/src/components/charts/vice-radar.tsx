"use client"

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { useQuery } from "@tanstack/react-query"
import { portalApi } from "@/lib/api/portal"
import { STALE_TIMES } from "@/lib/constants"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import type { ApiError } from "@/lib/api/types"

const TOOLTIP_STYLE = {
  background: "oklch(0.13 0 0)",
  border: "1px solid oklch(1 0 0 / 10%)",
  borderRadius: "8px",
  color: "oklch(0.95 0 0)",
  fontSize: 12,
}

interface ViceRadarProps {
  className?: string
}

export function ViceRadar({ className }: ViceRadarProps) {
  const { data, isLoading } = useQuery<
    Awaited<ReturnType<typeof portalApi.getVices>>,
    ApiError
  >({
    queryKey: ["portal", "vices"],
    queryFn: portalApi.getVices,
    staleTime: STALE_TIMES.history,
    retry: 2,
  })

  if (isLoading) {
    return <LoadingSkeleton variant="chart" className={className} />
  }

  if (!data?.length) {
    return null
  }

  const chartData = data.map((v) => ({
    category: v.category.replace(/_/g, " "),
    intensity: v.intensity_level,
    engagement: v.engagement_score,
  }))

  return (
    <GlassCardWithHeader
      title="Vice Profile"
      description="Personalization dimensions"
      className={className}
    >
      <div className="h-[280px]" aria-label="Vice intensity radar chart">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} cx="50%" cy="50%" outerRadius="75%">
            <PolarGrid stroke="rgba(255,255,255,0.1)" />
            <PolarAngleAxis
              dataKey="category"
              tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 5]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Intensity"
              dataKey="intensity"
              stroke="#f43f5e"
              fill="#f43f5e"
              fillOpacity={0.2}
              strokeWidth={2}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value: number, name: string) => [value.toFixed(1), name]}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </GlassCardWithHeader>
  )
}
