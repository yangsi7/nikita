'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAdminUsers } from '@/hooks/use-admin-data'
import type { UserListFilters } from '@/lib/api/admin-types'

export default function AdminUsersPage() {
  const [filters, setFilters] = useState<UserListFilters>({
    page: 1,
    page_size: 50,
  })

  const { data: usersResponse, isLoading, error } = useAdminUsers(filters)

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-lg font-medium text-destructive">
          {error instanceof Error ? error.message : 'Failed to load users'}
        </p>
      </div>
    )
  }

  if (isLoading || !usersResponse) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl animate-pulse mb-4">👥</div>
        <p className="text-muted-foreground">Loading users...</p>
      </div>
    )
  }

  const { users, total_count, page, page_size } = usersResponse
  const totalPages = Math.ceil(total_count / page_size)

  const formatTime = (isoString: string | null) => {
    if (!isoString) return 'Never'
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    if (diffMins < 10080) return `${Math.floor(diffMins / 1440)}d ago`
    return date.toLocaleDateString()
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
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Users</h1>
          <p className="text-muted-foreground">{total_count} total users</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {/* Game Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Button
                variant={!filters.game_status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({ ...filters, game_status: undefined, page: 1 })}
              >
                All
              </Button>
              {['active', 'boss_fight', 'game_over', 'won'].map((status) => (
                <Button
                  key={status}
                  variant={filters.game_status === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilters({ ...filters, game_status: status, page: 1 })}
                >
                  {status.replace('_', ' ')}
                </Button>
              ))}
            </div>

            {/* Chapter Filter */}
            <div className="flex items-center gap-2 ml-4">
              <span className="text-sm text-muted-foreground">Chapter:</span>
              <Button
                variant={!filters.chapter ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilters({ ...filters, chapter: undefined, page: 1 })}
              >
                All
              </Button>
              {[1, 2, 3, 4, 5].map((ch) => (
                <Button
                  key={ch}
                  variant={filters.chapter === ch ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilters({ ...filters, chapter: ch, page: 1 })}
                >
                  {ch}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/30">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    User
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Chapter
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Engagement
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Last Active
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-mono text-xs text-muted-foreground">
                          {user.id.slice(0, 8)}...
                        </div>
                        {user.telegram_id && <div className="text-sm">TG: {user.telegram_id}</div>}
                        {user.email && (
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-bold">{user.relationship_score.toFixed(1)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">Ch {user.chapter}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={gameStatusColors[user.game_status] || ''}>
                        {user.game_status.replace('_', ' ')}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {user.engagement_state ? (
                        <Badge className={engagementColors[user.engagement_state] || ''}>
                          {user.engagement_state.replace('_', ' ')}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground text-sm">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatTime(user.last_interaction_at)}
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/admin/users/${user.id}`}>
                        <Button variant="ghost" size="sm">
                          View →
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {(page - 1) * page_size + 1} to {Math.min(page * page_size, total_count)} of{' '}
            {total_count}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setFilters({ ...filters, page: page - 1 })}
            >
              ← Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page === totalPages}
              onClick={() => setFilters({ ...filters, page: page + 1 })}
            >
              Next →
            </Button>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="text-center text-xs text-muted-foreground/50 pt-4">
        Data refreshes every 60 seconds
      </div>
    </div>
  )
}
