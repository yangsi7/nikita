"use client"

import { useState } from "react"
import { useLifeEvents } from "@/hooks/use-life-events"
import { useEmotionalState } from "@/hooks/use-emotional-state"
import { useSocialCircle } from "@/hooks/use-social-circle"
import { usePsycheTips } from "@/hooks/use-psyche-tips"
import { LifeEventTimeline } from "@/components/dashboard/life-event-timeline"
import { MoodOrb } from "@/components/dashboard/mood-orb"
import { WarmthMeter } from "@/components/dashboard/warmth-meter"
import { SocialCircleGallery } from "@/components/dashboard/social-circle-gallery"
import { PsycheTips, PsycheTipsEmpty } from "@/components/dashboard/psyche-tips"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0]
}

function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr + "T12:00:00")
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

export default function NikitaDayPage() {
  const [dateStr, setDateStr] = useState(() => formatDate(new Date()))
  const lifeEvents = useLifeEvents(dateStr)
  const emotionalState = useEmotionalState()
  const socialCircle = useSocialCircle()
  const psycheTips = usePsycheTips()

  const isToday = dateStr === formatDate(new Date())

  function goBack() {
    const d = new Date(dateStr + "T12:00:00")
    d.setDate(d.getDate() - 1)
    setDateStr(formatDate(d))
  }

  function goForward() {
    const d = new Date(dateStr + "T12:00:00")
    d.setDate(d.getDate() + 1)
    setDateStr(formatDate(d))
  }

  return (
    <div className="space-y-6">
      {/* Header with date navigation */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Nikita&apos;s Day</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={goBack} className="h-8 w-8">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground min-w-[180px] text-center">
            {formatDisplayDate(dateStr)}
          </span>
          <Button variant="ghost" size="icon" onClick={goForward} disabled={isToday} className="h-8 w-8">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 2-column layout: main (2/3) + sidebar (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Daily Timeline */}
          <GlassCardWithHeader
            title={isToday ? "Today's Events" : `Events for ${dateStr}`}
            description={
              lifeEvents.data
                ? `${lifeEvents.data.total_count} event${lifeEvents.data.total_count !== 1 ? "s" : ""}`
                : undefined
            }
          >
            {lifeEvents.isLoading ? (
              <LoadingSkeleton variant="card-grid" count={3} />
            ) : lifeEvents.error ? (
              <p className="text-sm text-destructive">Failed to load events.</p>
            ) : lifeEvents.data?.events && lifeEvents.data.events.length > 0 ? (
              <LifeEventTimeline events={lifeEvents.data.events} />
            ) : (
              <p className="text-sm text-muted-foreground">No events for this day.</p>
            )}
          </GlassCardWithHeader>

          {/* Psyche Insights */}
          {psycheTips.isLoading ? (
            <LoadingSkeleton variant="card" count={1} />
          ) : psycheTips.data ? (
            <PsycheTips tips={psycheTips.data} />
          ) : (
            <PsycheTipsEmpty />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Mood Snapshot */}
          {emotionalState.isLoading ? (
            <LoadingSkeleton variant="card" count={1} />
          ) : emotionalState.data ? (
            <MoodOrb state={emotionalState.data} />
          ) : null}

          {/* Warmth Meter */}
          {emotionalState.isLoading ? (
            <LoadingSkeleton variant="card" count={1} />
          ) : emotionalState.data ? (
            <WarmthMeter value={emotionalState.data.intimacy} />
          ) : null}

          {/* Social Circle */}
          <GlassCardWithHeader
            title="Friends"
            description={
              socialCircle.data
                ? `${socialCircle.data.total_count} in circle`
                : undefined
            }
          >
            {socialCircle.isLoading ? (
              <LoadingSkeleton variant="card-grid" count={2} />
            ) : socialCircle.data?.friends ? (
              <SocialCircleGallery friends={socialCircle.data.friends} />
            ) : (
              <p className="text-sm text-muted-foreground">No friends yet.</p>
            )}
          </GlassCardWithHeader>
        </div>
      </div>
    </div>
  )
}
