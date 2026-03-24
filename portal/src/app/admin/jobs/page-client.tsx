"use client"

import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { GlassCard } from "@/components/glass/glass-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { STALE_TIMES } from "@/lib/constants"
import { CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react"

export default function JobsPage() {
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: adminApi.getProcessingStats,
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={5} />
  if (error) return <ErrorDisplay message="Failed to load processing stats" onRetry={() => refetch()} />
  if (!stats) return null

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Processing Stats</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <GlassCard className="p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-400" />
            <p className="text-sm font-medium">Success Rate</p>
          </div>
          <p className="text-2xl font-bold mt-2">{stats.success_rate.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground mt-1">
            {stats.success_count} succeeded / {stats.total_processed} total
          </p>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            <p className="text-sm font-medium">Avg Duration</p>
          </div>
          <p className="text-2xl font-bold mt-2">{(stats.avg_duration_ms / 1000).toFixed(1)}s</p>
          <p className="text-xs text-muted-foreground mt-1">{stats.avg_duration_ms.toLocaleString()}ms</p>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-400" />
            <p className="text-sm font-medium">Failed</p>
          </div>
          <p className="text-2xl font-bold mt-2 text-red-400">{stats.failed_count}</p>
          <p className="text-xs text-muted-foreground mt-1">out of {stats.total_processed} processed</p>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-amber-400" />
            <p className="text-sm font-medium">Pending</p>
          </div>
          <p className="text-2xl font-bold mt-2 text-amber-400">{stats.pending_count}</p>
          <p className="text-xs text-muted-foreground mt-1">waiting to be processed</p>
        </GlassCard>

        <GlassCard className="p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            <p className="text-sm font-medium">Stuck</p>
          </div>
          <p className="text-2xl font-bold mt-2 text-orange-400">{stats.stuck_count}</p>
          <p className="text-xs text-muted-foreground mt-1">may need attention</p>
        </GlassCard>
      </div>
    </div>
  )
}
