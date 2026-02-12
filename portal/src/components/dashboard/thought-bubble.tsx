"use client"

import { cn, formatRelativeTime } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import type { ThoughtItem } from "@/lib/api/types"

interface ThoughtBubbleProps {
  thought: ThoughtItem
}

const thoughtTypeColors: Record<
  string,
  { border: string; text: string; badge: string }
> = {
  curiosity: {
    border: "border-cyan-400/50",
    text: "text-cyan-300",
    badge: "bg-cyan-500/20 text-cyan-300 border-cyan-400/30",
  },
  memory: {
    border: "border-amber-400/50",
    text: "text-amber-300",
    badge: "bg-amber-500/20 text-amber-300 border-amber-400/30",
  },
  desire: {
    border: "border-rose-400/50",
    text: "text-rose-300",
    badge: "bg-rose-500/20 text-rose-300 border-rose-400/30",
  },
  worry: {
    border: "border-red-400/50",
    text: "text-red-300",
    badge: "bg-red-500/20 text-red-300 border-red-400/30",
  },
  fantasy: {
    border: "border-purple-400/50",
    text: "text-purple-300",
    badge: "bg-purple-500/20 text-purple-300 border-purple-400/30",
  },
  hope: {
    border: "border-emerald-400/50",
    text: "text-emerald-300",
    badge: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
  },
  regret: {
    border: "border-slate-400/50",
    text: "text-slate-300",
    badge: "bg-slate-500/20 text-slate-300 border-slate-400/30",
  },
  jealousy: {
    border: "border-orange-400/50",
    text: "text-orange-300",
    badge: "bg-orange-500/20 text-orange-300 border-orange-400/30",
  },
}

const defaultColors = {
  border: "border-slate-400/50",
  text: "text-slate-300",
  badge: "bg-slate-500/20 text-slate-300 border-slate-400/30",
}

export function ThoughtBubble({ thought }: ThoughtBubbleProps) {
  const colors = thoughtTypeColors[thought.thought_type] ?? defaultColors
  const isExpired = thought.is_expired
  const isUsed = thought.used_at !== null

  return (
    <div
      className={cn(
        "rounded-lg bg-white/5 border border-white/10 p-4",
        "border-l-2 transition-opacity",
        colors.border,
        isExpired && "opacity-60"
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <Badge variant="outline" className={cn("text-xs capitalize", colors.badge)}>
          {thought.thought_type.replace(/_/g, " ")}
        </Badge>
        <span className="text-xs text-muted-foreground/60 shrink-0">
          {formatRelativeTime(thought.created_at)}
        </span>
      </div>

      <p className={cn("text-sm italic leading-relaxed", colors.text)}>
        &ldquo;{thought.content}&rdquo;
      </p>

      <div className="flex items-center gap-2 mt-3">
        {isUsed && (
          <Badge variant="outline" className="text-xs bg-blue-500/20 text-blue-300 border-blue-400/30">
            Used
          </Badge>
        )}
        {isExpired && (
          <Badge variant="outline" className="text-xs bg-slate-500/10 text-muted-foreground border-slate-400/20">
            Expired
          </Badge>
        )}
      </div>
    </div>
  )
}
