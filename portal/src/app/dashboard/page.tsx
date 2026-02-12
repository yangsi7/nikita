"use client"

import { useUserStats } from "@/hooks/use-user-stats"
import { useScoreHistory } from "@/hooks/use-score-history"
import { useEmotionalState } from "@/hooks/use-emotional-state"
import { useThoughts } from "@/hooks/use-thoughts"
import { RelationshipHero } from "@/components/dashboard/relationship-hero"
import { HiddenMetrics } from "@/components/dashboard/hidden-metrics"
import { ScoreTimeline } from "@/components/charts/score-timeline"
import { MoodOrbMini } from "@/components/dashboard/mood-orb-mini"
import { ConflictBanner } from "@/components/dashboard/conflict-banner"
import { ThoughtBubble } from "@/components/dashboard/thought-bubble"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCard } from "@/components/glass/glass-card"

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useUserStats()
  const { data: history, isLoading: historyLoading } = useScoreHistory()
  const { data: emotionalState } = useEmotionalState()
  const { data: thoughts } = useThoughts({ limit: 1 })

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
      {emotionalState && emotionalState.conflict_state !== "none" && (
        <ConflictBanner
          conflictState={emotionalState.conflict_state}
          conflictTrigger={emotionalState.conflict_trigger}
          conflictStartedAt={emotionalState.conflict_started_at}
        />
      )}

      <RelationshipHero stats={stats} />

      {emotionalState && (
        <GlassCard className="p-4">
          <div className="flex items-center justify-between">
            <MoodOrbMini state={emotionalState} />
            {thoughts?.thoughts?.[0] && (
              <div className="flex-1 ml-4 max-w-md">
                <ThoughtBubble thought={thoughts.thoughts[0]} />
              </div>
            )}
          </div>
        </GlassCard>
      )}

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
