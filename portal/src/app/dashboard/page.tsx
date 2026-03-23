"use client"

import { useUserStats } from "@/hooks/use-user-stats"
import { useScoreHistory } from "@/hooks/use-score-history"
import { useEmotionalState } from "@/hooks/use-emotional-state"
import { useThoughts } from "@/hooks/use-thoughts"
import { useDecay } from "@/hooks/use-decay"
import { usePsycheTips } from "@/hooks/use-psyche-tips"
import { DashboardEmptyState } from "@/components/dashboard/dashboard-empty-state"
import { RelationshipHero } from "@/components/dashboard/relationship-hero"
import { HiddenMetrics } from "@/components/dashboard/hidden-metrics"
import { ScoreTimeline } from "@/components/charts/score-timeline"
import { MoodOrbMini } from "@/components/dashboard/mood-orb-mini"
import { ConflictBanner } from "@/components/dashboard/conflict-banner"
import { ThoughtBubble } from "@/components/dashboard/thought-bubble"
import { DecayCountdown } from "@/components/dashboard/decay-countdown"
import { PsycheSummary } from "@/components/dashboard/psyche-summary"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCard } from "@/components/glass/glass-card"

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading, error: statsError, refetch: refetchStats } = useUserStats()
  const { data: history, isLoading: historyLoading } = useScoreHistory()
  const { data: emotionalState, isLoading: emotionalLoading } = useEmotionalState()
  const { data: thoughts } = useThoughts({ limit: 1 })
  const { data: decay, isLoading: decayLoading } = useDecay()
  const { data: psyche } = usePsycheTips()

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

  if (!stats.last_interaction_at) {
    return <DashboardEmptyState />
  }

  return (
    <div className="space-y-6">
      {emotionalLoading ? (
        <LoadingSkeleton variant="card" />
      ) : emotionalState && emotionalState.conflict_state !== "none" ? (
        <ConflictBanner
          conflictState={emotionalState.conflict_state}
          conflictTrigger={emotionalState.conflict_trigger}
          conflictStartedAt={emotionalState.conflict_started_at}
        />
      ) : null}

      <RelationshipHero stats={stats} />

      {emotionalLoading ? (
        <LoadingSkeleton variant="card" />
      ) : emotionalState ? (
        <GlassCard className="p-4">
          <div className="flex items-center justify-between">
            <MoodOrbMini state={emotionalState} />
            {thoughts?.thoughts?.[0] && (
              <div className="flex-1 ml-4 max-w-md">
                <ThoughtBubble thought={thoughts.thoughts[0]} />
              </div>
            )}
          </div>
          {decayLoading ? (
            <div className="mt-3 border-t border-white/5 pt-3">
              <LoadingSkeleton variant="card" />
            </div>
          ) : decay ? (
            <div className="mt-3 border-t border-white/5 pt-3">
              <DecayCountdown decay={decay} />
            </div>
          ) : null}
        </GlassCard>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {historyLoading ? (
          <LoadingSkeleton variant="chart" />
        ) : history ? (
          <ScoreTimeline data={history.points} />
        ) : null}
        <HiddenMetrics metrics={stats.metrics} />
        {psyche && <PsycheSummary psyche={psyche} />}
      </div>
    </div>
  )
}
