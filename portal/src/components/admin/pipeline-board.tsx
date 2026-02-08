"use client"

import { GlassCard, GlassCardWithHeader } from "@/components/glass/glass-card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn, formatDuration, formatDateTime } from "@/lib/utils"
import type { PipelineHealth, PipelineStageHealth } from "@/lib/api/types"

interface PipelineBoardProps {
  health: PipelineHealth
}

function stageColor(rate: number): string {
  if (rate >= 95) return "text-emerald-400 border-emerald-400/30 bg-emerald-500/10"
  if (rate >= 80) return "text-amber-400 border-amber-400/30 bg-amber-500/10"
  return "text-red-400 border-red-400/30 bg-red-500/10"
}

export function PipelineBoard({ health }: PipelineBoardProps) {
  return (
    <div className="space-y-6">
      {/* Stage Grid */}
      <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2">
        {health.stages.map((stage) => (
          <GlassCard key={stage.name} className={cn("p-3 text-center border", stageColor(stage.success_rate))}>
            <p className="text-[10px] font-medium truncate">{stage.name.replace("_", " ")}</p>
            <p className="text-lg font-bold">{stage.success_rate.toFixed(0)}%</p>
            <p className="text-[10px] text-muted-foreground">{formatDuration(stage.avg_duration_ms)}</p>
            {stage.error_count > 0 && (
              <p className="text-[10px] text-red-400">{stage.error_count} errors</p>
            )}
          </GlassCard>
        ))}
      </div>

      {/* Recent Failures */}
      {health.recent_failures.length > 0 && (
        <GlassCardWithHeader title="Recent Failures" description={`${health.recent_failures.length} failures`}>
          <div className="glass-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-white/5">
                  <TableHead>Conversation</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Error</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {health.recent_failures.slice(0, 10).map((f, i) => (
                  <TableRow key={i} className="border-white/5">
                    <TableCell className="text-xs font-mono">{f.conversation_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-xs">{f.stage}</TableCell>
                    <TableCell className="text-xs text-red-400 max-w-[200px] truncate">{f.error}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDateTime(f.timestamp)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </GlassCardWithHeader>
      )}
    </div>
  )
}
