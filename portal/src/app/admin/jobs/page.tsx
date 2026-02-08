"use client"

import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { JobCard } from "@/components/admin/job-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { STALE_TIMES } from "@/lib/constants"

export default function JobsPage() {
  const { data: jobs, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "jobs"],
    queryFn: adminApi.getProcessingStats,
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={5} />
  if (error) return <ErrorDisplay message="Failed to load jobs" onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Background Jobs</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(jobs ?? []).map((job) => (
          <JobCard key={job.name} job={job} />
        ))}
      </div>
    </div>
  )
}
