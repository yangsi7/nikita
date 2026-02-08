"use client"

import { useParams } from "next/navigation"
import { useConversation } from "@/hooks/use-conversations"
import { GlassCard } from "@/components/glass/glass-card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { LoadingSkeleton } from "@/components/shared/loading-skeleton"
import { ErrorDisplay } from "@/components/shared/error-boundary"
import { formatDateTime, cn } from "@/lib/utils"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"

export default function ConversationDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { data: conversation, isLoading, error, refetch } = useConversation(id)

  if (isLoading) return <LoadingSkeleton variant="table" count={6} />
  if (error || !conversation) return <ErrorDisplay message="Failed to load conversation" onRetry={() => refetch()} />

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/conversations" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h2 className="text-lg font-semibold">Conversation</h2>
          <p className="text-xs text-muted-foreground">
            {formatDateTime(conversation.started_at)}
            {conversation.platform && <Badge variant="outline" className="ml-2 text-xs">{conversation.platform}</Badge>}
          </p>
        </div>
      </div>
      <GlassCard className="p-0">
        <ScrollArea className="h-[60vh] p-4">
          <div className="space-y-4">
            {conversation.messages.map((msg) => (
              <div key={msg.id} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
                <div className={cn(
                  "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm",
                  msg.role === "user"
                    ? "bg-rose-500/20 text-foreground rounded-br-md"
                    : "bg-white/5 text-foreground rounded-bl-md"
                )}>
                  <p>{msg.content}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">{formatDateTime(msg.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </GlassCard>
    </div>
  )
}
