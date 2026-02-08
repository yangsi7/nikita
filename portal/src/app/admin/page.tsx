"use client"

import { useAdminStats } from "@/hooks/use-admin-stats"
import { KpiCard } from "@/components/admin/kpi-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function AdminOverviewPage() {
  const { data: stats, isLoading, error, refetch } = useAdminStats()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={6} />
  if (error || !stats) return <ErrorDisplay message="Failed to load admin stats" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">System Overview</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <KpiCard title="Active Users (24h)" value={stats.active_users_24h} status="good" />
        <KpiCard title="New Signups (7d)" value={stats.new_signups_7d} status="good" />
        <KpiCard title="Pipeline Success" value={`${stats.pipeline_success_rate.toFixed(1)}`} suffix="%" status={stats.pipeline_success_rate >= 95 ? "good" : stats.pipeline_success_rate >= 80 ? "warning" : "bad"} />
        <KpiCard title="Avg Processing" value={`${(stats.avg_processing_time_ms / 1000).toFixed(1)}`} suffix="s" status={stats.avg_processing_time_ms < 5000 ? "good" : "warning"} />
        <KpiCard title="Error Rate (24h)" value={`${stats.error_rate_24h.toFixed(1)}`} suffix="%" status={stats.error_rate_24h < 5 ? "good" : stats.error_rate_24h < 15 ? "warning" : "bad"} />
        <KpiCard title="Active Voice Calls" value={stats.active_voice_calls} status="good" />
      </div>
    </div>
  )
}
