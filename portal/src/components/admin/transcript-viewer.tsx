"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { cn, formatDateTime } from "@/lib/utils"
import type { ConversationMessage } from "@/lib/api/types"

interface TranscriptViewerProps {
  messages: ConversationMessage[]
}

export function TranscriptViewer({ messages }: TranscriptViewerProps) {
  return (
    <ScrollArea className="h-[60vh]">
      <div className="space-y-4 p-4">
        {messages.map((msg) => (
          <div key={msg.id} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn(
              "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm",
              msg.role === "user"
                ? "bg-cyan-500/20 text-foreground rounded-br-md"
                : "bg-white/5 text-foreground rounded-bl-md"
            )}>
              <p className="text-[10px] font-medium text-muted-foreground mb-1">
                {msg.role === "user" ? "Player" : "Nikita"}
              </p>
              <p>{msg.content}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{formatDateTime(msg.created_at)}</p>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
