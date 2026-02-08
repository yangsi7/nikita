"use client"

import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from "recharts"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import type { UserMetrics } from "@/lib/api/types"

interface RadarMetricsProps {
  metrics: UserMetrics
  className?: string
}

export function RadarMetrics({ metrics, className }: RadarMetricsProps) {
  const data = [
    { subject: "Intimacy", value: metrics.intimacy, weight: metrics.weights.intimacy },
    { subject: "Passion", value: metrics.passion, weight: metrics.weights.passion },
    { subject: "Trust", value: metrics.trust, weight: metrics.weights.trust },
    { subject: "Secureness", value: metrics.secureness, weight: metrics.weights.secureness },
  ]

  return (
    <GlassCardWithHeader
      title="Hidden Metrics"
      description="The four dimensions of your relationship"
      className={className}
    >
      <div className="h-[300px]" aria-label={`Metrics: Intimacy ${metrics.intimacy}, Passion ${metrics.passion}, Trust ${metrics.trust}, Secureness ${metrics.secureness}`}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
            <PolarGrid stroke="rgba(255,255,255,0.1)" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 12 }}
            />
            <PolarRadiusAxis
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              name="Metrics"
              dataKey="value"
              stroke="#f43f5e"
              fill="#f43f5e"
              fillOpacity={0.15}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="grid grid-cols-4 gap-2 mt-2">
        {data.map((d) => (
          <div key={d.subject} className="text-center">
            <span className="text-xs text-muted-foreground">{d.subject}</span>
            <p className="text-sm font-medium">{Math.round(d.value)}</p>
            <p className="text-xs text-muted-foreground">{Math.round(d.weight * 100)}%</p>
          </div>
        ))}
      </div>
    </GlassCardWithHeader>
  )
}
