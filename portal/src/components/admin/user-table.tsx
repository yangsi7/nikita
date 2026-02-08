"use client"

import { useState, useCallback } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAdminUsers } from "@/hooks/use-admin-users"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { scoreColor, formatDate } from "@/lib/utils"
import { CHAPTER_ROMAN, ENGAGEMENT_STATES } from "@/lib/constants"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"

export function UserTable() {
  const [search, setSearch] = useState("")
  const [chapter, setChapter] = useState<number | undefined>()
  const [engagement, setEngagement] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const router = useRouter()

  const { data, isLoading, error, refetch } = useAdminUsers({
    search: search || undefined,
    chapter,
    engagement,
    page,
    page_size: 20,
  })

  const debounceSearch = useCallback(
    (() => {
      let timer: ReturnType<typeof setTimeout>
      return (value: string) => {
        clearTimeout(timer)
        timer = setTimeout(() => { setSearch(value); setPage(1) }, 300)
      }
    })(),
    []
  )

  if (isLoading) return <LoadingSkeleton variant="table" count={8} />
  if (error) return <ErrorDisplay message="Failed to load users" onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, email, telegram ID..."
            onChange={(e) => debounceSearch(e.target.value)}
            className="pl-9 bg-white/5 border-white/10"
          />
        </div>
        <Select value={chapter?.toString() ?? "all"} onValueChange={(v) => { setChapter(v === "all" ? undefined : Number(v)); setPage(1) }}>
          <SelectTrigger className="w-[130px] bg-white/5 border-white/10">
            <SelectValue placeholder="Chapter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Chapters</SelectItem>
            {[1,2,3,4,5].map(c => <SelectItem key={c} value={String(c)}>Ch {CHAPTER_ROMAN[c]}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={engagement ?? "all"} onValueChange={(v) => { setEngagement(v === "all" ? undefined : v); setPage(1) }}>
          <SelectTrigger className="w-[150px] bg-white/5 border-white/10">
            <SelectValue placeholder="Engagement" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All States</SelectItem>
            {ENGAGEMENT_STATES.map(s => <SelectItem key={s} value={s}>{s.replace("_", " ")}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {!data?.items?.length ? (
        <EmptyState message="No users found" description="Try adjusting your filters" />
      ) : (
        <>
          <div className="glass-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-white/5 hover:bg-transparent">
                  <TableHead>User</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Chapter</TableHead>
                  <TableHead>Engagement</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((user) => (
                  <TableRow
                    key={user.id}
                    className="border-white/5 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => router.push(`/admin/users/${user.id}`)}
                  >
                    <TableCell>
                      <div>
                        <p className="text-sm font-medium">{user.email ?? user.telegram_id ?? user.id.slice(0, 8)}</p>
                        {user.telegram_id && <p className="text-xs text-muted-foreground">TG: {user.telegram_id}</p>}
                      </div>
                    </TableCell>
                    <TableCell className={scoreColor(user.relationship_score)}>
                      {Math.round(user.relationship_score)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{CHAPTER_ROMAN[user.chapter]}</Badge>
                    </TableCell>
                    <TableCell className="text-xs">{user.engagement_state}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{user.game_status}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {user.last_interaction_at ? formatDate(user.last_interaction_at) : "Never"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex justify-between items-center">
            <p className="text-xs text-muted-foreground">{data.total} total users</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <Button variant="outline" size="sm" disabled={data.items.length < 20} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
