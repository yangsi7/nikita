import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { MessageSquare, Mic } from "lucide-react"
import { formatDateTime, cn } from "@/lib/utils"
import type { Conversation } from "@/lib/api/types"
import Link from "next/link"

interface ConversationCardProps {
  conversation: Conversation
}

const toneColors: Record<string, string> = {
  positive: "bg-emerald-400",
  neutral: "bg-zinc-400",
  negative: "bg-blue-400",
  flirty: "bg-rose-400",
  angry: "bg-red-400",
}

export function ConversationCard({ conversation: conv }: ConversationCardProps) {
  return (
    <Link href={`/dashboard/conversations/${conv.id}`}>
      <GlassCard className="p-4 hover:bg-white/8 transition-colors cursor-pointer">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {conv.platform === "voice" ? (
              <Mic className="h-4 w-4 text-cyan-400" />
            ) : (
              <MessageSquare className="h-4 w-4 text-rose-400" />
            )}
            <div>
              <p className="text-sm font-medium">{formatDateTime(conv.started_at)}</p>
              <p className="text-xs text-muted-foreground">{conv.message_count} messages</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {conv.emotional_tone && (
              <div className={cn("h-2 w-2 rounded-full", toneColors[conv.emotional_tone] ?? "bg-zinc-400")}
                title={conv.emotional_tone}
              />
            )}
            {conv.score_delta !== null && (
              <Badge variant="outline" className={cn(
                "text-xs",
                conv.score_delta > 0 ? "text-emerald-400 border-emerald-400/30" :
                conv.score_delta < 0 ? "text-red-400 border-red-400/30" :
                "text-zinc-400 border-zinc-400/30"
              )}>
                {conv.score_delta > 0 ? "+" : ""}{conv.score_delta.toFixed(1)}
              </Badge>
            )}
          </div>
        </div>
      </GlassCard>
    </Link>
  )
}
