"use client"

import Link from "next/link"
import { useEmotionalState } from "@/hooks/use-emotional-state"
import { useLifeEvents } from "@/hooks/use-life-events"
import { useThoughts } from "@/hooks/use-thoughts"
import { MoodOrb } from "@/components/dashboard/mood-orb"
import { ConflictBanner } from "@/components/dashboard/conflict-banner"
import { LifeEventTimeline } from "@/components/dashboard/life-event-timeline"
import { ThoughtFeed } from "@/components/dashboard/thought-feed"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { ChevronRight } from "lucide-react"

export default function NikitaHubPage() {
  const { data: emotionalState, isLoading: moodLoading, error: moodError, refetch } = useEmotionalState()
  const { data: lifeEvents, isLoading: eventsLoading } = useLifeEvents()
  const { data: thoughts, isLoading: thoughtsLoading } = useThoughts()

  if (moodLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton variant="card" />
        <LoadingSkeleton variant="card-grid" count={2} />
      </div>
    )
  }

  if (moodError) {
    return <ErrorDisplay message="Failed to load Nikita's world" onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Nikita&apos;s World</h1>
      </div>

      {emotionalState && emotionalState.conflict_state !== "none" && (
        <ConflictBanner
          conflictState={emotionalState.conflict_state}
          conflictTrigger={emotionalState.conflict_trigger}
          conflictStartedAt={emotionalState.conflict_started_at}
        />
      )}

      {emotionalState && <MoodOrb state={emotionalState} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GlassCardWithHeader
          title="Today's Events"
          action={
            <Link href="/dashboard/nikita/day" className="text-xs text-muted-foreground hover:text-rose-400 flex items-center gap-1">
              View all <ChevronRight className="h-3 w-3" />
            </Link>
          }
        >
          {eventsLoading ? (
            <LoadingSkeleton variant="card" />
          ) : lifeEvents?.events ? (
            <LifeEventTimeline events={lifeEvents.events.slice(0, 5)} />
          ) : (
            <p className="text-sm text-muted-foreground">No events today yet.</p>
          )}
        </GlassCardWithHeader>

        <GlassCardWithHeader
          title="What's on Her Mind"
          action={
            <Link href="/dashboard/nikita/mind" className="text-xs text-muted-foreground hover:text-rose-400 flex items-center gap-1">
              View all <ChevronRight className="h-3 w-3" />
            </Link>
          }
        >
          {thoughtsLoading ? (
            <LoadingSkeleton variant="card" />
          ) : thoughts?.thoughts ? (
            <ThoughtFeed thoughts={thoughts.thoughts.slice(0, 3)} />
          ) : (
            <p className="text-sm text-muted-foreground">No thoughts yet.</p>
          )}
        </GlassCardWithHeader>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link href="/dashboard/nikita/stories" className="glass-card p-4 hover:bg-white/10 transition-colors">
          <h3 className="text-sm font-medium text-foreground">Storylines</h3>
          <p className="text-xs text-muted-foreground mt-1">Active narrative arcs</p>
        </Link>
        <Link href="/dashboard/nikita/circle" className="glass-card p-4 hover:bg-white/10 transition-colors">
          <h3 className="text-sm font-medium text-foreground">Social Circle</h3>
          <p className="text-xs text-muted-foreground mt-1">Nikita&apos;s friends</p>
        </Link>
      </div>
    </div>
  )
}
