"use client"

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { formatDate } from "@/lib/utils"
import type { ScorePoint } from "@/lib/api/types"

interface ScoreTimelineProps {
  data: ScorePoint[]
  className?: string
}

export function ScoreTimeline({ data, className }: ScoreTimelineProps) {
  const chartData = data.map((point) => ({
    ...point,
    date: new Date(point.recorded_at).getTime(),
    label: formatDate(point.recorded_at),
  }))

  return (
    <GlassCardWithHeader title="Score Timeline" description="Last 30 days" className={className}>
      <div className="h-[280px]" aria-label="Score trend over 30 days">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <defs>
              <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(val) => new Date(val).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              stroke="rgba(255,255,255,0.2)"
              fontSize={11}
              tickLine={false}
            />
            <YAxis domain={[0, 100]} stroke="rgba(255,255,255,0.2)" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: "rgba(0,0,0,0.8)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                fontSize: 12,
              }}
              labelFormatter={(val) => formatDate(val)}
              formatter={(value: number) => [`${Math.round(value)}`, "Score"]}
            />
            <ReferenceLine y={55} stroke="rgba(6,182,212,0.3)" strokeDasharray="3 3" />
            <ReferenceLine y={75} stroke="rgba(244,63,94,0.3)" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="score"
              stroke="#f43f5e"
              strokeWidth={2}
              fill="url(#scoreGradient)"
              dot={false}
              activeDot={{ r: 4, fill: "#f43f5e", stroke: "#fff", strokeWidth: 1 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCardWithHeader>
  )
}
