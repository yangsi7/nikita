"use client"

import { useSocialCircle } from "@/hooks/use-social-circle"
import { SocialCircleGallery } from "@/components/dashboard/social-circle-gallery"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function NikitaCirclePage() {
  const { data, isLoading, error, refetch } = useSocialCircle()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={6} />
  if (error) return <ErrorDisplay message="Failed to load social circle" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Social Circle</h1>
        {data && (
          <span className="text-sm text-muted-foreground">
            {data.total_count} friend{data.total_count !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {data?.friends ? (
        <SocialCircleGallery friends={data.friends} />
      ) : (
        <p className="text-sm text-muted-foreground">No friends in Nikita&apos;s circle yet.</p>
      )}
    </div>
  )
}
