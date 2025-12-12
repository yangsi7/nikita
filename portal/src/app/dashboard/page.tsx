'use client'

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { logout } from '@/lib/supabase/client'
import {
  useUserStats,
  useEngagement,
  useVices,
  useDecayStatus,
  useScoreHistory,
} from '@/hooks/use-dashboard-data'
import { ScoreCard } from '@/components/dashboard/ScoreCard'
import { ChapterCard } from '@/components/dashboard/ChapterCard'
import { EngagementCard } from '@/components/dashboard/EngagementCard'
import { MetricsGrid } from '@/components/dashboard/MetricsGrid'
import { VicesCard } from '@/components/dashboard/VicesCard'
import { DecayWarning } from '@/components/dashboard/DecayWarning'
import { Card, CardContent } from '@/components/ui/card'
import { Navigation } from '@/components/layout/Navigation'

export default function DashboardPage() {
  const router = useRouter()
  const { data: stats, isLoading: statsLoading, error: statsError } = useUserStats()
  const { data: engagement, isLoading: engagementLoading } = useEngagement()
  const { data: vices, isLoading: vicesLoading } = useVices()
  const { data: decayStatus } = useDecayStatus()
  const { data: scoreHistory } = useScoreHistory(7) // Last 7 days for previous score

  const handleLogout = async () => {
    await logout()
    router.push('/')
  }

  // Show error state
  if (statsError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="border-destructive/20 bg-destructive/10 max-w-md">
          <CardContent className="py-8 text-center space-y-4">
            <div className="text-4xl">⚠️</div>
            <div>
              <p className="text-lg font-medium text-destructive">Failed to load dashboard</p>
              <p className="text-sm text-muted-foreground mt-2">
                {statsError instanceof Error ? statsError.message : 'Unknown error'}
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push('/')}>
              Go to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show loading state
  if (statsLoading || !stats) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-4xl animate-pulse">💝</div>
          <p className="text-lg text-muted-foreground">Loading your relationship...</p>
        </div>
      </div>
    )
  }

  // Calculate decay info from API
  const hoursSinceLastInteraction = decayStatus
    ? decayStatus.grace_period_hours - decayStatus.hours_remaining
    : 0
  const nextDecayIn = decayStatus?.hours_remaining ?? 24
  const decayRate = decayStatus?.decay_rate ?? 0.5

  // Get previous score from score history (second most recent point)
  const previousScore =
    scoreHistory?.points && scoreHistory.points.length > 1
      ? scoreHistory.points[scoreHistory.points.length - 2]?.score
      : (stats?.relationship_score ?? 50)

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground via-primary to-foreground bg-clip-text text-transparent">
              Nikita
            </h1>
            <Navigation />
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Welcome Section */}
        <div>
          <h2 className="text-3xl font-bold mb-2">Welcome Back</h2>
          <p className="text-muted-foreground">Track your relationship with Nikita</p>
        </div>

        {/* Decay Warning */}
        <DecayWarning
          hoursSinceLastInteraction={hoursSinceLastInteraction}
          nextDecayIn={nextDecayIn}
          decayRate={decayRate}
          chapter={stats.chapter}
        />

        {/* Top Cards Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <ScoreCard
            score={stats.relationship_score}
            previousScore={previousScore}
            chapter={stats.chapter}
          />
          <ChapterCard
            chapter={stats.chapter}
            bossAttempts={stats.boss_attempts}
            gameStatus={stats.game_status}
            relationshipScore={stats.relationship_score}
          />
          {!engagementLoading && engagement && (
            <EngagementCard
              state={engagement.state}
              multiplier={engagement.multiplier}
              consecutiveInZone={engagement.consecutive_in_zone}
              consecutiveClingyDays={engagement.consecutive_clingy_days}
              consecutiveDistantDays={engagement.consecutive_distant_days}
            />
          )}
        </div>

        {/* Metrics Grid */}
        <MetricsGrid
          chapter={stats.chapter}
          metrics={{
            intimacy: stats.metrics.intimacy,
            passion: stats.metrics.passion,
            trust: stats.metrics.trust,
            secureness: stats.metrics.secureness,
          }}
        />

        {/* Vices Card */}
        {!vicesLoading && vices && (
          <VicesCard
            vices={vices.map((v) => ({
              category: v.category,
              intensityLevel: v.intensity_level,
              engagementScore: v.engagement_score,
            }))}
          />
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-xs text-muted-foreground/50">
          Data refreshes every 30 seconds
        </div>
      </main>
    </div>
  )
}
