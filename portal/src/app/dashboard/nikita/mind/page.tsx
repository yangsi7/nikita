"use client"

import { useState, useEffect, useCallback } from "react"
import { useThoughts } from "@/hooks/use-thoughts"
import { ThoughtFeed } from "@/components/dashboard/thought-feed"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"
import type { ThoughtItem } from "@/lib/api/types"

const PAGE_SIZE = 20

export default function NikitaMindPage() {
  const [filter, setFilter] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [allThoughts, setAllThoughts] = useState<ThoughtItem[]>([])

  const { data, isLoading, error, refetch } = useThoughts({
    limit: PAGE_SIZE,
    offset,
    type: filter ?? undefined,
  })

  // Accumulate thoughts when new data arrives
  /* eslint-disable react-hooks/set-state-in-effect -- pagination accumulation requires setState in effect */
  useEffect(() => {
    if (data?.thoughts) {
      if (offset === 0) {
        setAllThoughts(data.thoughts)
      } else {
        setAllThoughts(prev => [...prev, ...data.thoughts])
      }
    }
  }, [data, offset])
  /* eslint-enable react-hooks/set-state-in-effect */

  // Reset when filter changes
  const handleFilterChange = useCallback((type: string | null) => {
    setFilter(type)
    setOffset(0)
    setAllThoughts([])
  }, [])

  const handleLoadMore = useCallback(() => {
    setOffset(prev => prev + PAGE_SIZE)
  }, [])

  if (error) {
    return <ErrorDisplay message="Failed to load thoughts" onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Nikita&apos;s Mind</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total_count} thought{data.total_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <GlassCardWithHeader title="Thoughts" description="What Nikita is thinking about">
        {isLoading && offset === 0 ? (
          <LoadingSkeleton variant="card-grid" count={4} />
        ) : allThoughts.length > 0 ? (
          <div className="space-y-4">
            <ThoughtFeed
              thoughts={allThoughts}
              onFilterChange={handleFilterChange}
            />
            {data?.has_more && (
              <div className="flex justify-center">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground"
                  onClick={handleLoadMore}
                  disabled={isLoading}
                >
                  {isLoading ? "Loading..." : "Load more..."}
                </Button>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No thoughts yet.</p>
        )}
      </GlassCardWithHeader>
    </div>
  )
}
