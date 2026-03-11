"use client"

import { useEngagement } from "@/hooks/use-engagement"
import { useDecay } from "@/hooks/use-decay"
import { EngagementPulse } from "@/components/dashboard/engagement-pulse"
import { DecayWarning } from "@/components/dashboard/decay-warning"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { RelativeTime } from "@/components/shared/relative-time"
import { Badge } from "@/components/ui/badge"

export default function EngagementPage() {
  const { data: engagement, isLoading: engLoading, error: engError, refetch } = useEngagement()
  const { data: decay, isLoading: decayLoading } = useDecay()

  if (engLoading) return <LoadingSkeleton variant="card-grid" count={2} />
  if (engError) return <ErrorDisplay message="Failed to load engagement data" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      {engagement && <EngagementPulse data={engagement} />}
      {decayLoading ? <LoadingSkeleton variant="card" /> : decay && <DecayWarning data={decay} />}

      {engagement && (
        <GlassCardWithHeader
          title="Engagement History"
          description="Recent state changes"
        >
          {engagement.recent_transitions.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No state changes recorded yet. Your engagement history will appear here.
            </p>
          ) : (
            <div className="space-y-3">
              {engagement.recent_transitions.map((t, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <div className="flex-shrink-0 mt-1">
                    <div className="h-2 w-2 rounded-full bg-white/20" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className="text-xs bg-white/5">
                        {(t.from_state ?? "start").replace(/_/g, " ")}
                      </Badge>
                      <span className="text-muted-foreground">&rarr;</span>
                      <Badge variant="outline" className="text-xs bg-white/5">
                        {t.to_state.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                      {t.reason && <span>{t.reason}</span>}
                      {t.reason && <span>&middot;</span>}
                      <RelativeTime date={t.created_at} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCardWithHeader>
      )}
    </div>
  )
}
