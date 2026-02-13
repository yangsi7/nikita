"use client"

import { useDetailedScores } from "@/hooks/use-detailed-scores"
import { useThreads } from "@/hooks/use-threads"
import { ScoreDetailChart } from "@/components/dashboard/score-detail-chart"
import { ThreadTable } from "@/components/dashboard/thread-table"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"

export default function InsightsPage() {
  const { data: scores, isLoading: scoresLoading, error: scoresError, refetch: refetchScores } = useDetailedScores()
  const { data: threads, isLoading: threadsLoading, error: threadsError, refetch: refetchThreads } = useThreads()

  if (scoresError) {
    return <ErrorDisplay message="Failed to load insights" onRetry={() => refetchScores()} />
  }

  if (threadsError) {
    return <ErrorDisplay message="Failed to load conversation threads" onRetry={() => refetchThreads()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Deep Insights</h1>
      </div>

      <GlassCardWithHeader title="Score Breakdown" description="How each interaction affects your score">
        {scoresLoading ? (
          <LoadingSkeleton variant="chart" />
        ) : scores?.points ? (
          <ScoreDetailChart points={scores.points} />
        ) : (
          <p className="text-sm text-muted-foreground">No score history available.</p>
        )}
      </GlassCardWithHeader>

      <GlassCardWithHeader
        title="Conversation Threads"
        description={threads ? `${threads.open_count} open` : undefined}
      >
        {threadsLoading ? (
          <LoadingSkeleton variant="card-grid" count={3} />
        ) : threads?.threads ? (
          <ThreadTable threads={threads.threads} openCount={threads.open_count} />
        ) : (
          <p className="text-sm text-muted-foreground">No threads yet.</p>
        )}
      </GlassCardWithHeader>
    </div>
  )
}
