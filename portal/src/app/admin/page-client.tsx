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
        <KpiCard title="Total Users" value={stats.total_users} status="good" />
        <KpiCard title="Active Users (7d)" value={stats.active_users} status="good" />
        <KpiCard title="New Signups (7d)" value={stats.new_users_7d} status="good" />
        <KpiCard title="Total Conversations" value={stats.total_conversations} status="good" />
        <KpiCard title="Avg Score" value={Number(stats.avg_relationship_score).toFixed(1)} status={Number(stats.avg_relationship_score) >= 40 ? "good" : "warning"} />
      </div>
    </div>
  )
}
