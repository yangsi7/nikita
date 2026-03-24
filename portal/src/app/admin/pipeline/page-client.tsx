"use client"

import { useAdminPipeline } from "@/hooks/use-admin-pipeline"
import { PipelineBoard } from "@/components/admin/pipeline-board"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"

export default function PipelinePage() {
  const { data: health, isLoading, error, refetch } = useAdminPipeline()

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={9} />
  if (error || !health) return <ErrorDisplay message="Failed to load pipeline health" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Pipeline Health</h1>
      <PipelineBoard health={health} />
    </div>
  )
}
