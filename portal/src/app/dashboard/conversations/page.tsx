"use client"

import { useState, useMemo } from "react"
import { useConversations, type ConversationFilters } from "@/hooks/use-conversations"
import { ConversationCard } from "@/components/dashboard/conversation-card"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { EmptyState } from "@/components/shared/empty-state"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function ConversationsPage() {
  const [tab, setTab] = useState("all")
  const [page, setPage] = useState(1)

  const filters: ConversationFilters | undefined = useMemo(() => {
    switch (tab) {
      case "text": return { platform: "telegram" }
      case "voice": return { platform: "voice" }
      case "boss": return { boss_only: true }
      default: return undefined
    }
  }, [tab])

  const { data, isLoading, error, refetch } = useConversations(page, 10, filters)

  if (isLoading) return <LoadingSkeleton variant="card-grid" count={4} />
  if (error) return <ErrorDisplay message="Failed to load conversations" onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Conversation History</h2>
      </div>
      <Tabs value={tab} onValueChange={(v) => { setTab(v); setPage(1) }}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="text">Text</TabsTrigger>
          <TabsTrigger value="voice">Voice</TabsTrigger>
          <TabsTrigger value="boss">Boss Fights</TabsTrigger>
        </TabsList>
      </Tabs>
      {!data?.conversations?.length ? (
        <EmptyState
          message="No conversations found"
          description={tab !== "all" ? "Try a different filter" : "Start chatting with Nikita on Telegram or voice"}
        />
      ) : (
        <>
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
        </>
      )}
    </div>
  )
}
