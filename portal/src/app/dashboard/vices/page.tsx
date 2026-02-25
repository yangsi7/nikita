"use client"

import { useVices } from "@/hooks/use-vices"
import { ViceCard, ViceLockedCard } from "@/components/dashboard/vice-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"

// Spec 106 G17: Actual backend vice categories (8 total)
const ALL_VICE_CATEGORIES = [
  "intellectual_dominance",
  "risk_taking",
  "substances",
  "sexuality",
  "emotional_intensity",
  "rule_breaking",
  "dark_humor",
  "vulnerability",
] as const

// In-character Nikita voice — not clinical labels
export const VICE_DISPLAY: Record<string, { label: string; description: string }> = {
  intellectual_dominance: {
    label: "mind games",
    description: "you like it when someone's smarter than you...",
  },
  risk_taking: {
    label: "living dangerously",
    description: "the thrill is what keeps you coming back",
  },
  substances: {
    label: "poison of choice",
    description: "you don't mind a little chaos in your cup",
  },
  sexuality: {
    label: "tension",
    description: "it's always there between us, isn't it",
  },
  emotional_intensity: {
    label: "burning bright",
    description: "you feel everything at full volume",
  },
  rule_breaking: {
    label: "rebel streak",
    description: "rules were never really your thing",
  },
  dark_humor: {
    label: "gallows humor",
    description: "you laugh at things you probably shouldn't",
  },
  vulnerability: {
    label: "open wounds",
    description: "you let people see the real you. that takes guts.",
  },
}

export default function VicesPage() {
  const { data: vices, isLoading, error, refetch } = useVices()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={4} />
  if (error) return <ErrorDisplay message="Failed to load vice discoveries" onRetry={() => refetch()} />
  if (!vices || vices.length === 0) return <EmptyState message="no vices discovered yet" description="keep talking to me. I'll figure you out." />

  const discoveredCategories = new Set(vices.map((v) => v.category))
  const undiscoveredCategories = ALL_VICE_CATEGORIES.filter((c) => !discoveredCategories.has(c))

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-rose-300/90">what I know about you</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {vices.length} of {ALL_VICE_CATEGORIES.length} discovered
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {vices.map((vice) => (
          <ViceCard
            key={vice.category}
            vice={vice}
            display={VICE_DISPLAY[vice.category]}
          />
        ))}
        {undiscoveredCategories.map((cat) => (
          <ViceLockedCard key={cat} />
        ))}
      </div>
    </div>
  )
}
