import { GlassCard } from "@/components/glass/glass-card"
import { cn } from "@/lib/utils"
import { Lock } from "lucide-react"
import type { VicePreference } from "@/lib/api/types"

interface ViceCardProps {
  vice: VicePreference
}

const intensityColors: Record<number, string> = {
  1: "text-blue-400 border-blue-400/30",
  2: "text-teal-400 border-teal-400/30",
  3: "text-amber-400 border-amber-400/30",
  4: "text-orange-400 border-orange-400/30",
  5: "text-rose-400 border-rose-400/30",
}

export function ViceCard({ vice }: ViceCardProps) {
  const color = intensityColors[vice.intensity_level] ?? intensityColors[1]

  return (
    <GlassCard className={cn("p-4 min-w-[180px]", `border-l-2`, color.split(" ")[1])}>
      <h4 className={cn("text-sm font-medium capitalize", color.split(" ")[0])}>
        {vice.category.replace(/_/g, " ")}
      </h4>
      <div className="flex gap-0.5 mt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-1.5 w-4 rounded-full",
              i < vice.intensity_level ? "bg-current" : "bg-white/10"
            )}
            style={{ color: color.includes("blue") ? "#60a5fa" : color.includes("teal") ? "#2dd4bf" : color.includes("amber") ? "#fbbf24" : color.includes("orange") ? "#fb923c" : "#fb7185" }}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Engagement: {Math.round(vice.engagement_score * 100)}%
      </p>
    </GlassCard>
  )
}

export function ViceLockedCard() {
  return (
    <GlassCard className="p-4 min-w-[180px] opacity-40 blur-[1px]">
      <div className="flex items-center gap-2">
        <Lock className="h-3 w-3 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Undiscovered</span>
      </div>
      <div className="flex gap-0.5 mt-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-1.5 w-4 rounded-full bg-white/5" />
        ))}
      </div>
      <p className="text-xs text-muted-foreground/50 mt-2">Talk more to discover</p>
    </GlassCard>
  )
}
