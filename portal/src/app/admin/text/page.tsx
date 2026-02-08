"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { formatDateTime } from "@/lib/utils"
import { STALE_TIMES } from "@/lib/constants"
import { cn } from "@/lib/utils"

export default function TextMonitorPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "text", "conversations", page],
    queryFn: () => adminApi.getTextConversations({ page }),
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={6} />
  if (error) return <ErrorDisplay message="Failed to load text conversations" onRetry={() => refetch()} />
  if (!data?.conversations?.length) return <EmptyState message="No text conversations" />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Text Monitor</h1>
      <div className="glass-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-white/5">
              <TableHead>Date</TableHead>
              <TableHead>User</TableHead>
              <TableHead>Messages</TableHead>
              <TableHead>Tone</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.conversations.map((conv) => (
              <TableRow key={conv.id} className="border-white/5 hover:bg-white/5">
                <TableCell className="text-sm">{formatDateTime(conv.started_at)}</TableCell>
                <TableCell className="text-xs font-mono">{conv.user_identifier ?? conv.user_id.slice(0, 8)}</TableCell>
                <TableCell className="text-sm">{conv.message_count}</TableCell>
                <TableCell className="text-xs">{conv.emotional_tone ?? "—"}</TableCell>
                <TableCell>
                  {conv.score_delta !== null ? (
                    <Badge variant="outline" className={cn(
                      "text-xs",
                      conv.score_delta > 0 ? "text-emerald-400 border-emerald-400/30" :
                      conv.score_delta < 0 ? "text-red-400 border-red-400/30" :
                      "text-zinc-400 border-zinc-400/30"
                    )}>
                      {conv.score_delta > 0 ? "+" : ""}{conv.score_delta.toFixed(1)}
                    </Badge>
                  ) : "—"}
                </TableCell>
                <TableCell className="text-xs">{conv.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex justify-between items-center">
        <p className="text-xs text-muted-foreground">{data.total_count} total conversations</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
          <Button variant="outline" size="sm" disabled={data.conversations.length < data.page_size} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      </div>
    </div>
  )
}
