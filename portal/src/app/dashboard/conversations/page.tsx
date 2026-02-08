"use client"

import { useState } from "react"
import { useConversations } from "@/hooks/use-conversations"
import { ConversationCard } from "@/components/dashboard/conversation-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"

export default function ConversationsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading, error, refetch } = useConversations(page)

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={4} />
  if (error) return <ErrorDisplay message="Failed to load conversations" onRetry={() => refetch()} />
  if (!data?.conversations?.length) return <EmptyState message="No conversations yet" description="Start chatting with Nikita on Telegram or voice" />

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Conversation History</h2>
      <div className="space-y-3">
        {data.conversations.map((conv) => (
          <ConversationCard key={conv.id} conversation={conv} />
        ))}
      </div>
      <div className="flex justify-center gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={data.conversations.length < 10} onClick={() => setPage((p) => p + 1)}>
          Next
        </Button>
      </div>
    </div>
  )
}
