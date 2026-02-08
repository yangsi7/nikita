"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { adminApi } from "@/lib/api/admin"
import { ConversationCard } from "@/components/dashboard/conversation-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { STALE_TIMES } from "@/lib/constants"

export default function TextMonitorPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "text", "conversations", page],
    queryFn: () => adminApi.getTextConversations({ page }),
    staleTime: STALE_TIMES.admin,
  })

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={6} />
  if (error) return <ErrorDisplay message="Failed to load text conversations" onRetry={() => refetch()} />
  if (!data?.items?.length) return <EmptyState message="No text conversations" />

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-cyan-400">Text Monitor</h1>
      <div className="space-y-3">
        {data.items.map((conv) => (
          <ConversationCard key={conv.id} conversation={conv} />
        ))}
      </div>
      <div className="flex justify-center gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
        <Button variant="outline" size="sm" disabled={data.items.length < 10} onClick={() => setPage(p => p + 1)}>Next</Button>
      </div>
    </div>
  )
}
