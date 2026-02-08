"use client"

import { useEngagement } from "@/hooks/use-engagement"
import { useDecay } from "@/hooks/use-decay"
import { EngagementPulse } from "@/components/dashboard/engagement-pulse"
import { DecayWarning } from "@/components/dashboard/decay-warning"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function EngagementPage() {
  const { data: engagement, isLoading: engLoading, error: engError, refetch } = useEngagement()
  const { data: decay, isLoading: decayLoading } = useDecay()

  if (engLoading) return <LoadingSkeleton variant="card-grid" count={2} />
  if (engError) return <ErrorDisplay message="Failed to load engagement data" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      {engagement && <EngagementPulse data={engagement} />}
      {decayLoading ? <LoadingSkeleton variant="card" /> : decay && <DecayWarning data={decay} />}
    </div>
  )
}
