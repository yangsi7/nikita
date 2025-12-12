'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useSystemOverview, useJobStatus } from '@/hooks/use-admin-data'
import Link from 'next/link'

export default function AdminDashboardPage() {
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useSystemOverview()
  const { data: jobs, isLoading: jobsLoading } = useJobStatus()

  if (overviewError) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-lg font-medium text-destructive">
          {overviewError instanceof Error ? overviewError.message : 'Failed to load overview'}
        </p>
      </div>
    )
  }

  if (overviewLoading || !overview) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl animate-pulse mb-4">📊</div>
        <p className="text-muted-foreground">Loading system overview...</p>
      </div>
    )
  }

  // Calculate recent failures
  const failedJobs = jobs?.jobs.filter((j) => j.failures_24h > 0) || []

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">System Overview</h1>
        <p className="text-muted-foreground">Monitor Nikita game state and scheduled jobs</p>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{overview.total_users}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-500">
              {overview.active_users.last_24h}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">In Zone</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-500">
              {overview.engagement_states.in_zone}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Job Failures (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`text-3xl font-bold ${failedJobs.length > 0 ? 'text-red-500' : 'text-green-500'}`}
            >
              {failedJobs.reduce((sum, j) => sum + j.failures_24h, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Game Status Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Game Status Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-green-500">{overview.game_status.active}</div>
              <div className="text-sm text-muted-foreground">Active</div>
            </div>
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-orange-500">
                {overview.game_status.boss_fight}
              </div>
              <div className="text-sm text-muted-foreground">Boss Fight</div>
            </div>
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-red-500">
                {overview.game_status.game_over}
              </div>
              <div className="text-sm text-muted-foreground">Game Over</div>
            </div>
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-purple-500">{overview.game_status.won}</div>
              <div className="text-sm text-muted-foreground">Won</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Chapter Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Chapter Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-4">
            {[1, 2, 3, 4, 5].map((chapter) => {
              const count =
                overview.chapters[`chapter_${chapter}` as keyof typeof overview.chapters]
              const names = ['Stranger', 'Acquaintance', 'Honeymoon', 'Committed', 'Soulmate']
              return (
                <div key={chapter} className="text-center p-4 bg-muted/30 rounded-lg">
                  <div className="text-2xl font-bold">{count}</div>
                  <div className="text-xs text-muted-foreground">Ch {chapter}</div>
                  <div className="text-xs text-muted-foreground">{names[chapter - 1]}</div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Engagement States */}
      <Card>
        <CardHeader>
          <CardTitle>Engagement States</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Object.entries(overview.engagement_states).map(([state, count]) => {
              const stateColors: Record<string, string> = {
                calibrating: 'text-gray-500',
                in_zone: 'text-green-500',
                drifting: 'text-yellow-500',
                clingy: 'text-orange-500',
                distant: 'text-blue-500',
                out_of_zone: 'text-red-500',
              }
              return (
                <div key={state} className="text-center p-3 bg-muted/30 rounded-lg">
                  <div className={`text-xl font-bold ${stateColors[state] || ''}`}>{count}</div>
                  <div className="text-xs text-muted-foreground capitalize">
                    {state.replace('_', ' ')}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Active Users by Period */}
      <Card>
        <CardHeader>
          <CardTitle>Active Users</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold text-green-500">
                {overview.active_users.last_24h}
              </div>
              <div className="text-sm text-muted-foreground">Last 24h</div>
            </div>
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold">{overview.active_users.last_7d}</div>
              <div className="text-sm text-muted-foreground">Last 7d</div>
            </div>
            <div className="text-center p-4 bg-muted/30 rounded-lg">
              <div className="text-2xl font-bold">{overview.active_users.last_30d}</div>
              <div className="text-sm text-muted-foreground">Last 30d</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Job Status */}
      {!jobsLoading && jobs && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Scheduled Jobs</CardTitle>
            <Link href="/admin/jobs">
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">
                View All →
              </Badge>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {jobs.jobs.slice(0, 3).map((job) => (
                <div
                  key={job.job_name}
                  className="flex items-center justify-between p-3 bg-muted/30 rounded-lg"
                >
                  <div>
                    <div className="font-medium capitalize">{job.job_name.replace('_', ' ')}</div>
                    <div className="text-xs text-muted-foreground">
                      {job.last_run_at ? new Date(job.last_run_at).toLocaleString() : 'Never run'}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {job.failures_24h > 0 && (
                      <Badge variant="destructive">{job.failures_24h} failures</Badge>
                    )}
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
                    >
                      {job.last_status || 'pending'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Links */}
      <div className="flex justify-center space-x-4 pt-4">
        <Link href="/admin/users">
          <Badge variant="outline" className="px-4 py-2 text-base cursor-pointer hover:bg-muted">
            👥 Browse Users
          </Badge>
        </Link>
        <Link href="/admin/jobs">
          <Badge variant="outline" className="px-4 py-2 text-base cursor-pointer hover:bg-muted">
            ⚙️ Job Details
          </Badge>
        </Link>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-8">
        Data refreshes every 60 seconds
      </div>
    </div>
  )
}
