'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { ScoreHistoryPoint } from '@/lib/api/types'

interface ScoreHistoryGraphProps {
  history: ScoreHistoryPoint[]
  currentChapter: number
}

interface TooltipPayload {
  timestamp: string
  score: number
  eventType: string
  description?: string
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ payload: TooltipPayload }>
}

// Custom tooltip component (defined outside to avoid component-in-render warning)
function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <div className="bg-card border border-border rounded-md p-3 shadow-lg">
        <p className="text-sm font-medium">{data.timestamp}</p>
        <p className="text-lg font-bold text-primary">{data.score.toFixed(1)}</p>
        <p className="text-xs text-muted-foreground capitalize">{data.eventType}</p>
        {data.description && (
          <p className="text-xs text-muted-foreground mt-1">{data.description}</p>
        )}
      </div>
    )
  }
  return null
}

export function ScoreHistoryGraph({ history, currentChapter }: ScoreHistoryGraphProps) {
  // Boss thresholds by chapter
  const bossThresholds: Record<number, number> = {
    1: 55,
    2: 60,
    3: 65,
    4: 70,
    5: 75,
  }

  const currentThreshold = bossThresholds[currentChapter] || 75

  // Transform data for recharts
  const chartData = history.map((point) => ({
    timestamp: new Date(point.timestamp).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    score: point.score,
    eventType: point.event_type,
    description: point.description,
  }))

  if (history.length === 0) {
    return (
      <Card className="border-border/50 bg-card/50">
        <CardHeader>
          <CardTitle>Score History</CardTitle>
          <CardDescription>Last 30 days</CardDescription>
        </CardHeader>
        <CardContent className="py-12">
          <div className="text-center space-y-3">
            <div className="text-4xl">📊</div>
            <p className="text-sm text-muted-foreground">No score history yet</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader>
        <CardTitle>Score History</CardTitle>
        <CardDescription>Last {history.length} data points</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
            <XAxis dataKey="timestamp" stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <YAxis domain={[0, 100]} stroke="hsl(var(--muted-foreground))" fontSize={12} />
            <Tooltip content={<CustomTooltip />} />
            {/* Boss threshold line */}
            <ReferenceLine
              y={currentThreshold}
              stroke="hsl(var(--primary))"
              strokeDasharray="5 5"
              label={{
                value: 'Boss Threshold',
                position: 'insideTopRight',
                fill: 'hsl(var(--primary))',
              }}
            />
            {/* Score line */}
            <Line
              type="monotone"
              dataKey="score"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ fill: 'hsl(var(--primary))', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="mt-4 text-xs text-muted-foreground text-center">
          Current boss threshold: {currentThreshold} (Chapter {currentChapter})
        </div>
      </CardContent>
    </Card>
  )
}
