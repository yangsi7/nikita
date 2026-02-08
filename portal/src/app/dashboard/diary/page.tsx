"use client"

import { useSummaries } from "@/hooks/use-summaries"
import { DiaryEntry } from "@/components/dashboard/diary-entry"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"

export default function DiaryPage() {
  const { data: summaries, isLoading, error, refetch } = useSummaries()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={3} />
  if (error) return <ErrorDisplay message="Failed to load diary" onRetry={() => refetch()} />
  if (!summaries?.length) return <EmptyState message="No diary entries yet" description="Nikita writes about your relationship after each day" />

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Nikita&apos;s Diary</h2>
        <p className="text-xs text-muted-foreground">Dear Diary...</p>
      </div>
      <div className="space-y-4">
        {summaries.map((summary) => (
          <DiaryEntry key={summary.id} summary={summary} />
        ))}
      </div>
    </div>
  )
}
