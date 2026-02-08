"use client"

import { useVices } from "@/hooks/use-vices"
import { ViceCard, ViceLockedCard } from "@/components/dashboard/vice-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"

const ALL_VICE_CATEGORIES = [
  "adventure", "intellectual", "creative", "social",
  "romantic", "hedonistic", "competitive", "nurturing",
]

export default function VicesPage() {
  const { data: vices, isLoading, error, refetch } = useVices()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={4} />
  if (error) return <ErrorDisplay message="Failed to load vice discoveries" onRetry={() => refetch()} />
  if (!vices || vices.length === 0) return <EmptyState message="No vices discovered yet" description="Keep talking to Nikita to unlock your vices" />

  const discoveredCategories = new Set(vices.map((v) => v.category))
  const undiscoveredCount = ALL_VICE_CATEGORIES.filter((c) => !discoveredCategories.has(c)).length

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Vice Discoveries</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {vices.map((vice) => (
          <ViceCard key={vice.category} vice={vice} />
        ))}
        {Array.from({ length: undiscoveredCount }).map((_, i) => (
          <ViceLockedCard key={`locked-${i}`} />
        ))}
      </div>
    </div>
  )
}
