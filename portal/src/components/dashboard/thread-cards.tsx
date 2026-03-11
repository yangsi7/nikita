"use client"

import { HelpCircle, Lightbulb, Handshake, RotateCcw, Bookmark, Flag, MessageCircle, Target } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { GlassCard } from "@/components/glass/glass-card"
import { RelativeTime } from "@/components/shared/relative-time"
import { cn } from "@/lib/utils"
import type { Thread } from "@/lib/api/types"

const TYPE_COLORS: Record<string, string> = {
  question: "text-cyan-300 border-cyan-500/30",
  promise: "text-rose-300 border-rose-500/30",
  topic: "text-purple-300 border-purple-500/30",
  complaint: "text-red-300 border-red-500/30",
  request: "text-amber-300 border-amber-500/30",
  revelation: "text-emerald-300 border-emerald-500/30",
  conflict: "text-orange-300 border-orange-500/30",
  goal: "text-blue-300 border-blue-500/30",
}

const THREAD_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  question: HelpCircle,
  promise: Handshake,
  curiosity: Lightbulb,
  topic: MessageCircle,
  complaint: Flag,
  request: Target,
  callback: RotateCcw,
}

interface ThreadCardsProps {
  threads: Thread[]
  openCount: number
}

export function ThreadCards({ threads, openCount }: ThreadCardsProps) {
  if (threads.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No conversation threads yet.
      </div>
    )
  }

  // Sort: open first, then by created_at desc
  const sortedThreads = [...threads].sort((a, b) => {
    if (a.status === "open" && b.status !== "open") return -1
    if (a.status !== "open" && b.status === "open") return 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          {openCount} open {openCount === 1 ? "thread" : "threads"}
        </h3>
      </div>
      <div className="grid gap-3">
        {sortedThreads.map((thread) => {
          const Icon = THREAD_ICONS[thread.thread_type] ?? Bookmark
          const typeColor = TYPE_COLORS[thread.thread_type] ?? "text-muted-foreground"
          return (
            <GlassCard key={thread.id} className="p-3">
              <div className="flex items-start gap-3">
                <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", typeColor)} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm line-clamp-2">{thread.content}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className={cn("text-xs", typeColor)}>
                      {thread.thread_type}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      <RelativeTime date={thread.created_at} />
                    </span>
                  </div>
                </div>
                <Badge
                  variant={thread.status === "open" ? "default" : "secondary"}
                  className="text-xs shrink-0"
                >
                  {thread.status}
                </Badge>
              </div>
            </GlassCard>
          )
        })}
      </div>
    </div>
  )
}
