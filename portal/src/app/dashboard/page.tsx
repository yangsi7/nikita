"use client"

import { useUserStats } from "@/hooks/use-user-stats"
import { useScoreHistory } from "@/hooks/use-score-history"
import { RelationshipHero } from "@/components/dashboard/relationship-hero"
import { HiddenMetrics } from "@/components/dashboard/hidden-metrics"
import { ScoreTimeline } from "@/components/charts/score-timeline"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useUserStats()
  const { data: history, isLoading: historyLoading } = useScoreHistory()

  if (statsLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton variant="ring" />
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="chart" />
      </div>
    )
  }

  if (statsError || !stats) {
    return <ErrorDisplay message="Failed to load dashboard" onRetry={() => refetchStats()} />
  }

  return (
    <div className="space-y-6">
      <RelationshipHero stats={stats} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {historyLoading ? (
          <LoadingSkeleton variant="chart" />
        ) : history ? (
          <ScoreTimeline data={history.points} />
        ) : null}
        <HiddenMetrics metrics={stats.metrics} />
      </div>
    </div>
  )
}
