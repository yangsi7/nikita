import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { formatDate, cn } from "@/lib/utils"
import type { DailySummary } from "@/lib/api/types"

interface DiaryEntryProps {
  summary: DailySummary
}

const toneBorderColors: Record<string, string> = {
  positive: "border-l-rose-400",
  neutral: "border-l-zinc-400",
  negative: "border-l-blue-400",
}

export function DiaryEntry({ summary }: DiaryEntryProps) {
  const delta = (summary.score_end ?? 0) - (summary.score_start ?? 0)

  return (
    <GlassCard className={cn("p-5 border-l-2", summary.emotional_tone ? toneBorderColors[summary.emotional_tone] ?? "border-l-zinc-400" : "border-l-zinc-400")}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted-foreground">{formatDate(summary.date)}</p>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={cn(
            "text-xs",
            delta > 0 ? "text-emerald-400 border-emerald-400/30" :
            delta < 0 ? "text-red-400 border-red-400/30" :
            "text-zinc-400 border-zinc-400/30"
          )}>
            {delta > 0 ? "+" : ""}{delta.toFixed(1)}
          </Badge>
          <Badge variant="outline" className="text-xs text-muted-foreground border-white/10">
            {summary.conversations_count} chats
          </Badge>
        </div>
      </div>
      <p className="text-sm italic text-foreground/80 font-serif leading-relaxed">
        &ldquo;{summary.summary_text ?? "No summary available"}&rdquo;
      </p>
    </GlassCard>
  )
}
