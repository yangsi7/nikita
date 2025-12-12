'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useJobStatus } from '@/hooks/use-admin-data'

export default function AdminJobsPage() {
  const { data: jobs, isLoading, error } = useJobStatus()

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-lg font-medium text-destructive">
          {error instanceof Error ? error.message : 'Failed to load jobs'}
        </p>
      </div>
    )
  }

  if (isLoading || !jobs) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl animate-pulse mb-4">⚙️</div>
        <p className="text-muted-foreground">Loading job status...</p>
      </div>
    )
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatTime = (isoString: string | null) => {
    if (!isoString) return 'Never'
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return date.toLocaleDateString()
  }

  const jobDescriptions: Record<string, string> = {
    decay: 'Apply daily score decay to all active users based on chapter rates',
    deliver: 'Process pending scheduled message deliveries',
    summary: 'Generate daily summaries for all users (LLM-powered)',
    cleanup: 'Remove expired pending registrations (>10 minutes old)',
    'process-conversations': 'Detect stale conversations and trigger post-processing pipeline',
  }

  const jobSchedules: Record<string, string> = {
    decay: 'Daily at midnight UTC',
    deliver: 'Every minute',
    summary: 'Daily at 23:59 UTC',
    cleanup: 'Every hour',
    'process-conversations': 'Every minute',
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">Scheduled Jobs</h1>
        <p className="text-muted-foreground">Monitor pg_cron scheduled job executions</p>
      </div>

      {/* Jobs Grid */}
      <div className="space-y-4">
        {jobs.jobs.map((job) => (
          <Card key={job.job_name}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="capitalize">{job.job_name.replace(/_/g, ' ')}</CardTitle>
                <Badge
                  variant={
                    job.last_status === 'completed'
                      ? 'default'
                      : job.last_status === 'running'
                        ? 'secondary'
                        : job.last_status === 'failed'
                          ? 'destructive'
                          : 'outline'
                  }
                  className="ml-2"
                >
                  {job.last_status || 'never run'}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {jobDescriptions[job.job_name] || 'No description'}
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wide">
                    Last Run
                  </div>
                  <div className="font-medium">{formatTime(job.last_run_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wide">
                    Duration
                  </div>
                  <div className="font-medium">{formatDuration(job.last_duration_ms)}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wide">
                    Runs (24h)
                  </div>
                  <div className="font-medium">{job.runs_24h}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wide">
                    Failures (24h)
                  </div>
                  <div
                    className={`font-medium ${job.failures_24h > 0 ? 'text-red-500' : 'text-green-500'}`}
                  >
                    {job.failures_24h}
                  </div>
                </div>
              </div>

              {/* Schedule Info */}
              <div className="mt-4 pt-4 border-t border-border/40">
                <div className="text-xs text-muted-foreground">
                  <span className="font-medium">Schedule:</span>{' '}
                  {jobSchedules[job.job_name] || 'Unknown'}
                </div>
              </div>

              {/* Last Result */}
              {job.last_result && (
                <div className="mt-4 pt-4 border-t border-border/40">
                  <div className="text-xs text-muted-foreground uppercase tracking-wide mb-2">
                    Last Result
                  </div>
                  <pre className="text-xs bg-muted/30 p-2 rounded overflow-x-auto">
                    {JSON.stringify(job.last_result, null, 2)}
                  </pre>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Failures */}
      {jobs.recent_failures.length > 0 && (
        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="text-destructive">Recent Failures</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {jobs.recent_failures.map((failure, index) => (
                <div key={index} className="p-3 bg-destructive/10 rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">
                      {failure.job_name.replace(/_/g, ' ')}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {formatTime(failure.last_run_at)}
                    </span>
                  </div>
                  {failure.last_result && (
                    <pre className="mt-2 text-xs text-red-400 overflow-x-auto">
                      {JSON.stringify(failure.last_result, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-8">
        Data refreshes every 30 seconds
      </div>
    </div>
  )
}
