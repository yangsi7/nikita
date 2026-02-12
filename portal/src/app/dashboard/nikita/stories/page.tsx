"use client"

import { useState } from "react"
import { useNarrativeArcs } from "@/hooks/use-narrative-arcs"
import { StoryArcViewer } from "@/components/dashboard/story-arc-viewer"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"

export default function NikitaStoriesPage() {
  const [showResolved, setShowResolved] = useState(false)
  const { data, isLoading, error, refetch } = useNarrativeArcs(!showResolved)

  if (error) {
    return <ErrorDisplay message="Failed to load storylines" onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Storylines</h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowResolved(!showResolved)}
          className="text-muted-foreground"
        >
          {showResolved ? "Hide resolved" : "Show resolved"}
        </Button>
      </div>

      <GlassCardWithHeader
        title="Active Arcs"
        description={data ? `${data.active_arcs.length} active` : undefined}
      >
        {isLoading ? (
          <LoadingSkeleton variant="card-grid" count={2} />
        ) : data?.active_arcs && data.active_arcs.length > 0 ? (
          <StoryArcViewer arcs={data.active_arcs} />
        ) : (
          <p className="text-sm text-muted-foreground">No active storylines yet.</p>
        )}
      </GlassCardWithHeader>

      {showResolved && data?.resolved_arcs && data.resolved_arcs.length > 0 && (
        <GlassCardWithHeader
          title="Resolved Arcs"
          description={`${data.resolved_arcs.length} completed`}
        >
          <StoryArcViewer arcs={data.resolved_arcs} />
        </GlassCardWithHeader>
      )}
    </div>
  )
}
