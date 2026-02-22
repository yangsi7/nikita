"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { cn, formatDuration } from "@/lib/utils"
import type { PipelineHealth } from "@/lib/api/types"

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
      {/* Summary */}
      <div className="flex flex-wrap gap-4 text-sm">
        <Badge variant="outline" className={cn(
          health.status === "healthy" ? "text-emerald-400 border-emerald-400/30" : "text-red-400 border-red-400/30"
        )}>
          {health.status}
        </Badge>
        <span className="text-muted-foreground">v{health.pipeline_version}</span>
        <span className="text-muted-foreground">{health.total_runs_24h} runs (24h)</span>
        <span className="text-muted-foreground">{health.overall_success_rate.toFixed(1)}% success</span>
        <span className="text-muted-foreground">{formatDuration(health.avg_pipeline_duration_ms)} avg</span>
      </div>

      {/* Stage Grid */}
      <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2">
        {health.stages.map((stage) => (
          <GlassCard key={stage.name} className={cn("p-3 text-center border", stageColor(stage.success_rate))}>
            <p className="text-[10px] font-medium truncate">{stage.name.replace("_", " ")}</p>
            <p className="text-lg font-bold">{stage.success_rate.toFixed(0)}%</p>
            <p className="text-[10px] text-muted-foreground">{formatDuration(stage.avg_duration_ms)}</p>
            {stage.failures_24h > 0 && (
              <p className="text-[10px] text-red-400">{stage.failures_24h} failures</p>
            )}
            {stage.is_critical && (
              <Badge variant="outline" className="text-[8px] mt-1 border-red-400/30 text-red-400">critical</Badge>
            )}
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
