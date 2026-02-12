"use client"

import { useState } from "react"
import { useThoughts } from "@/hooks/use-thoughts"
import { ThoughtFeed } from "@/components/dashboard/thought-feed"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Button } from "@/components/ui/button"

export default function NikitaMindPage() {
  const [filter, setFilter] = useState<string | null>(null)
  const [limit] = useState(20)
  const { data, isLoading, error, refetch } = useThoughts({
    limit,
    type: filter ?? undefined,
  })

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
        {isLoading ? (
          <LoadingSkeleton variant="card-grid" count={4} />
        ) : data?.thoughts ? (
          <div className="space-y-4">
            <ThoughtFeed
              thoughts={data.thoughts}
              onFilterChange={setFilter}
            />
            {data.has_more && (
              <div className="flex justify-center">
                <Button variant="ghost" size="sm" className="text-muted-foreground">
                  Load more...
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
