'use client'

import { use } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useAdminUserDetail, useStateMachines } from '@/hooks/use-admin-data'

interface PageProps {
  params: Promise<{ id: string }>
}

export default function AdminUserDetailPage({ params }: PageProps) {
  const { id } = use(params)
  const { data: user, isLoading: userLoading, error: userError } = useAdminUserDetail(id)
  const { data: stateMachines, isLoading: smLoading } = useStateMachines(id)

  if (userError) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-lg font-medium text-destructive">
          {userError instanceof Error ? userError.message : 'Failed to load user'}
        </p>
        <Link href="/admin/users">
          <Button variant="outline" className="mt-4">
            ← Back to Users
          </Button>
        </Link>
      </div>
    )
  }

  if (userLoading || !user) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl animate-pulse mb-4">👤</div>
        <p className="text-muted-foreground">Loading user details...</p>
      </div>
    )
  }

  const gameStatusColors: Record<string, string> = {
    active: 'bg-green-500/20 text-green-500',
    boss_fight: 'bg-orange-500/20 text-orange-500',
    game_over: 'bg-red-500/20 text-red-500',
    won: 'bg-purple-500/20 text-purple-500',
  }

  const engagementColors: Record<string, string> = {
    calibrating: 'bg-gray-500/20 text-gray-500',
    in_zone: 'bg-green-500/20 text-green-500',
    drifting: 'bg-yellow-500/20 text-yellow-500',
    clingy: 'bg-orange-500/20 text-orange-500',
    distant: 'bg-blue-500/20 text-blue-500',
    out_of_zone: 'bg-red-500/20 text-red-500',
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link href="/admin/users">
        <Button variant="ghost" size="sm">
          ← Back to Users
        </Button>
      </Link>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Detail</h1>
          <p className="text-muted-foreground font-mono text-sm">{user.id}</p>
        </div>
        <Badge className={gameStatusColors[user.game_status] || ''} variant="outline">
          {user.game_status.replace('_', ' ')}
        </Badge>
      </div>

      {/* User Info Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Basic Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {user.telegram_id && (
              <div>
                <div className="text-xs text-muted-foreground uppercase">Telegram ID</div>
                <div className="font-medium">{user.telegram_id}</div>
              </div>
            )}
            {user.email && (
              <div>
                <div className="text-xs text-muted-foreground uppercase">Email</div>
                <div className="font-medium">{user.email}</div>
              </div>
            )}
            {user.phone && (
              <div>
                <div className="text-xs text-muted-foreground uppercase">Phone</div>
                <div className="font-medium">{user.phone}</div>
              </div>
            )}
            <div>
              <div className="text-xs text-muted-foreground uppercase">Days Played</div>
              <div className="font-medium">{user.days_played}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Created</div>
              <div className="font-medium">{new Date(user.created_at).toLocaleDateString()}</div>
            </div>
          </CardContent>
        </Card>

        {/* Game State */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Game State</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="text-xs text-muted-foreground uppercase">Relationship Score</div>
              <div className="text-2xl font-bold">{user.relationship_score.toFixed(1)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Chapter</div>
              <div className="font-medium">
                {user.chapter} - {user.chapter_name}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Boss Attempts</div>
              <div className="font-medium">{user.boss_attempts} / 3</div>
            </div>
          </CardContent>
        </Card>

        {/* Timing */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Timing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="text-xs text-muted-foreground uppercase">Last Interaction</div>
              <div className="font-medium">
                {user.last_interaction_at
                  ? `${user.timing.hours_since_last_interaction.toFixed(1)}h ago`
                  : 'Never'}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Grace Period</div>
              <Badge variant={user.timing.is_in_grace_period ? 'default' : 'destructive'}>
                {user.timing.is_in_grace_period
                  ? `${user.timing.grace_period_remaining_hours.toFixed(1)}h remaining`
                  : 'Expired - Decaying'}
              </Badge>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Decay Rate</div>
              <div className="font-medium">-{user.timing.decay_rate_per_hour}/hour</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Next Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Next Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-muted/30 rounded-lg">
              <div className="text-xs text-muted-foreground uppercase">Should Decay</div>
              <Badge variant={user.next_actions.should_decay ? 'destructive' : 'default'}>
                {user.next_actions.should_decay ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg">
              <div className="text-xs text-muted-foreground uppercase">Boss Ready</div>
              <Badge variant={user.timing.boss_ready ? 'default' : 'outline'}>
                {user.timing.boss_ready ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg">
              <div className="text-xs text-muted-foreground uppercase">Boss Threshold</div>
              <div className="font-medium">{user.next_actions.boss_threshold}</div>
            </div>
            <div className="p-4 bg-muted/30 rounded-lg">
              <div className="text-xs text-muted-foreground uppercase">Score to Boss</div>
              <div className="font-medium">{user.next_actions.score_to_boss.toFixed(1)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* State Machines */}
      {!smLoading && stateMachines && (
        <>
          {/* Engagement State */}
          <Card>
            <CardHeader>
              <CardTitle>Engagement State Machine</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Badge
                  className={engagementColors[stateMachines.engagement.current_state] || ''}
                  variant="outline"
                >
                  {stateMachines.engagement.current_state.replace('_', ' ')}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Multiplier: {stateMachines.engagement.multiplier}x
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-muted/30 rounded-lg text-center">
                  <div className="text-xl font-bold">
                    {stateMachines.engagement.consecutive_in_zone}
                  </div>
                  <div className="text-xs text-muted-foreground">Consecutive In Zone</div>
                </div>
                <div className="p-3 bg-muted/30 rounded-lg text-center">
                  <div className="text-xl font-bold">
                    {stateMachines.engagement.consecutive_clingy_days}
                  </div>
                  <div className="text-xs text-muted-foreground">Clingy Days</div>
                </div>
                <div className="p-3 bg-muted/30 rounded-lg text-center">
                  <div className="text-xl font-bold">
                    {stateMachines.engagement.consecutive_distant_days}
                  </div>
                  <div className="text-xs text-muted-foreground">Distant Days</div>
                </div>
              </div>

              {/* Recent Transitions */}
              {stateMachines.engagement.recent_transitions.length > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground uppercase mb-2">
                    Recent Transitions
                  </div>
                  <div className="space-y-2">
                    {stateMachines.engagement.recent_transitions.slice(0, 5).map((t, i) => (
                      <div key={i} className="flex items-center text-sm">
                        <Badge variant="outline" className="mr-2">
                          {t.from_state}
                        </Badge>
                        <span className="text-muted-foreground">→</span>
                        <Badge variant="outline" className="ml-2 mr-2">
                          {t.to_state}
                        </Badge>
                        <span className="text-xs text-muted-foreground ml-auto">{t.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Chapter Progress */}
          <Card>
            <CardHeader>
              <CardTitle>Chapter Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">
                    Chapter {stateMachines.chapter.current_chapter}:{' '}
                    {stateMachines.chapter.chapter_name}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {stateMachines.chapter.current_score.toFixed(1)} /{' '}
                    {stateMachines.chapter.boss_threshold} to boss
                  </div>
                </div>
                {stateMachines.chapter.can_trigger_boss && (
                  <Badge variant="default">Boss Ready!</Badge>
                )}
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Progress to Boss</span>
                  <span>{stateMachines.chapter.progress_to_boss.toFixed(1)}%</span>
                </div>
                <Progress value={stateMachines.chapter.progress_to_boss} />
              </div>
              <div className="text-sm text-muted-foreground">
                Boss Attempts: {stateMachines.chapter.boss_attempts} / 3
              </div>
            </CardContent>
          </Card>

          {/* Vice Profile */}
          <Card>
            <CardHeader>
              <CardTitle>Vice Profile</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-4">
                <span className="text-muted-foreground">
                  {stateMachines.vice_profile.total_vices_discovered} vices discovered
                </span>
                {stateMachines.vice_profile.expression_level && (
                  <Badge variant="outline">{stateMachines.vice_profile.expression_level}</Badge>
                )}
              </div>
              {stateMachines.vice_profile.top_vices.length > 0 ? (
                <div className="space-y-3">
                  {stateMachines.vice_profile.top_vices.map((vice) => (
                    <div key={vice.category} className="p-3 bg-muted/30 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="font-medium capitalize">
                          {vice.category.replace(/_/g, ' ')}
                        </span>
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline">Level {vice.intensity_level}</Badge>
                          <span className="text-sm">{vice.engagement_score.toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-4">
                  No vices discovered yet
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-4">
        Data does not auto-refresh - Refresh page to update
      </div>
    </div>
  )
}
