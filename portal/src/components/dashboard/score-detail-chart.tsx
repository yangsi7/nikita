"use client"

import { Badge } from "@/components/ui/badge"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { DetailedScorePoint } from "@/lib/api/types"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { ArrowUp, ArrowDown, Minus } from "lucide-react"

interface ScoreDetailChartProps {
  points: DetailedScorePoint[]
}

const METRIC_INFO = {
  intimacy: { label: "I", color: "rose", title: "Intimacy" },
  passion: { label: "P", color: "amber", title: "Passion" },
  trust: { label: "T", color: "blue", title: "Trust" },
  secureness: { label: "S", color: "emerald", title: "Secureness" },
} as const

export function ScoreDetailChart({ points }: ScoreDetailChartProps) {
  if (points.length === 0) {
    return (
      <GlassCardWithHeader title="Score Breakdown">
        <div className="text-center py-8 text-muted-foreground">
          No score history available.
        </div>
      </GlassCardWithHeader>
    )
  }

  // Sort by recorded_at desc (most recent first)
  const sortedPoints = [...points].sort(
    (a, b) =>
      new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
  )

  return (
    <GlassCardWithHeader title="Score Breakdown">
      <div className="rounded-lg border border-white/10 overflow-hidden">
        <Table aria-label="Score history breakdown">
          <TableHeader>
            <TableRow className="border-white/10 hover:bg-white/5">
              <TableHead className="text-muted-foreground">Time</TableHead>
              <TableHead className="text-muted-foreground text-right">
                Score
              </TableHead>
              <TableHead className="text-muted-foreground text-right">
                Delta
              </TableHead>
              <TableHead className="text-muted-foreground text-center">
                Metrics
              </TableHead>
              <TableHead className="text-muted-foreground">Event</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedPoints.map((point) => {
              const scoreDelta = point.score_delta ?? 0
              const deltaColor =
                scoreDelta > 0
                  ? "text-emerald-400"
                  : scoreDelta < 0
                    ? "text-red-400"
                    : "text-slate-400"

              return (
                <TableRow
                  key={point.id}
                  className="border-white/10 hover:bg-white/5"
                >
                  <TableCell className="text-sm text-foreground">
                    {format(new Date(point.recorded_at), "MMM d, h:mm a")}
                  </TableCell>
                  <TableCell className="text-sm text-foreground font-medium text-right">
                    {point.score.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className={cn("flex items-center justify-end gap-1", deltaColor)}>
                      {scoreDelta > 0 ? (
                        <ArrowUp className="w-3 h-3" />
                      ) : scoreDelta < 0 ? (
                        <ArrowDown className="w-3 h-3" />
                      ) : (
                        <Minus className="w-3 h-3" />
                      )}
                      <span className="text-sm font-medium">
                        {scoreDelta > 0 && "+"}
                        {scoreDelta.toFixed(2)}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-center gap-1">
                      {Object.entries(METRIC_INFO).map(
                        ([metric, { label, title }]) => {
                          const delta =
                            point[
                              `${metric}_delta` as keyof DetailedScorePoint
                            ] as number | null
                          if (!delta || delta === 0) return null

                          return (
                            <Badge
                              key={metric}
                              variant="outline"
                              className={cn(
                                "text-xs px-1.5 py-0.5",
                                // Direct color classes to avoid Tailwind purge issues
                                metric === "intimacy" &&
                                  delta > 0 &&
                                  "bg-rose-500/20 text-rose-300 border-rose-500/30",
                                metric === "intimacy" &&
                                  delta < 0 &&
                                  "bg-rose-500/10 text-rose-400/50 border-rose-500/20",
                                metric === "passion" &&
                                  delta > 0 &&
                                  "bg-amber-500/20 text-amber-300 border-amber-500/30",
                                metric === "passion" &&
                                  delta < 0 &&
                                  "bg-amber-500/10 text-amber-400/50 border-amber-500/20",
                                metric === "trust" &&
                                  delta > 0 &&
                                  "bg-blue-500/20 text-blue-300 border-blue-500/30",
                                metric === "trust" &&
                                  delta < 0 &&
                                  "bg-blue-500/10 text-blue-400/50 border-blue-500/20",
                                metric === "secureness" &&
                                  delta > 0 &&
                                  "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
                                metric === "secureness" &&
                                  delta < 0 &&
                                  "bg-emerald-500/10 text-emerald-400/50 border-emerald-500/20"
                              )}
                              title={`${title}: ${delta > 0 ? "+" : ""}${delta.toFixed(2)}`}
                            >
                              {label}
                              {delta > 0 && "+"}
                            </Badge>
                          )
                        }
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {point.event_type && (
                      <Badge
                        variant="outline"
                        className="text-xs bg-white/5 text-foreground/70"
                      >
                        {point.event_type}
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </GlassCardWithHeader>
  )
}
