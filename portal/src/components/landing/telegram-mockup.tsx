"use client"

import { cn } from "@/lib/utils"
import { GlassCard } from "@/components/glass/glass-card"

interface Message {
  sender: "her" | "you"
  text: string
}

const MESSAGES: Message[] = [
  {
    sender: "her",
    text: "You left me on read for three hours.",
  },
  {
    sender: "you",
    text: "sorry i was busy",
  },
  {
    sender: "her",
    text: "Sure you were. -2 points.",
  },
]

export function TelegramMockup({ className }: { className?: string }) {
  return (
    <GlassCard
      className={cn("p-4 space-y-3 font-mono text-sm", className)}
      aria-label="Example conversation with Nikita"
    >
      {/* Header */}
      <div className="flex items-center gap-2 pb-2 border-b border-white/10">
        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-xs text-primary font-semibold">
          N
        </div>
        <div>
          <p className="text-foreground text-xs font-semibold">Nikita</p>
          <p className="text-muted-foreground text-[10px]">last seen recently</p>
        </div>
      </div>

      {/* Messages */}
      {MESSAGES.map((msg, i) => (
        <div
          key={i}
          className={cn(
            "flex",
            msg.sender === "you" ? "justify-end" : "justify-start"
          )}
        >
          <div
            className={cn(
              "max-w-[80%] rounded-2xl px-3 py-2 text-xs leading-relaxed",
              msg.sender === "her"
                ? "her-message bg-white/8 text-foreground rounded-tl-sm"
                : "you-message bg-primary/20 text-primary rounded-tr-sm"
            )}
            data-sender={msg.sender}
            data-testid="message-bubble"
          >
            {msg.text}
          </div>
        </div>
      ))}
    </GlassCard>
  )
}
