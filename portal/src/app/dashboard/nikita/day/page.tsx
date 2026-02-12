"use client"

import { useState } from "react"
import { useLifeEvents } from "@/hooks/use-life-events"
import { LifeEventTimeline } from "@/components/dashboard/life-event-timeline"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
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
  const { data, isLoading, error, refetch } = useLifeEvents(dateStr)

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

  if (error) {
    return <ErrorDisplay message="Failed to load life events" onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
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

      <GlassCardWithHeader
        title={isToday ? "Today's Events" : `Events for ${dateStr}`}
        description={data ? `${data.total_count} event${data.total_count !== 1 ? "s" : ""}` : undefined}
      >
        {isLoading ? (
          <LoadingSkeleton variant="card-grid" count={3} />
        ) : data?.events ? (
          <LifeEventTimeline events={data.events} />
        ) : (
          <p className="text-sm text-muted-foreground">No events for this day.</p>
        )}
      </GlassCardWithHeader>
    </div>
  )
}
