import { GlassCard } from "@/components/glass/glass-card"
import { cn } from "@/lib/utils"
import { Lock } from "lucide-react"
import type { VicePreference } from "@/lib/api/types"

interface ViceDisplayInfo {
  label: string
  description: string
}

interface ViceCardProps {
  vice: VicePreference
  display?: ViceDisplayInfo
}

const intensityColors: Record<number, string> = {
  1: "text-blue-400 border-blue-400/30",
  2: "text-teal-400 border-teal-400/30",
  3: "text-amber-400 border-amber-400/30",
  4: "text-orange-400 border-orange-400/30",
  5: "text-rose-400 border-rose-400/30",
}

const intensityFills: Record<number, string> = {
  1: "bg-blue-400",
  2: "bg-teal-400",
  3: "bg-amber-400",
  4: "bg-orange-400",
  5: "bg-rose-400",
}

export function ViceCard({ vice, display }: ViceCardProps) {
  const color = intensityColors[vice.intensity_level] ?? intensityColors[1]
  const fill = intensityFills[vice.intensity_level] ?? intensityFills[1]
  const label = display?.label ?? vice.category.replace(/_/g, " ")
  const description = display?.description

  return (
    <GlassCard className={cn("p-4 min-w-[180px]", `border-l-2`, color.split(" ")[1])}>
      <h4 className={cn("text-sm font-medium", color.split(" ")[0])}>
        {label}
      </h4>
      {description && (
        <p className="text-xs text-muted-foreground/70 mt-1 italic">
          {description}
        </p>
      )}
      <div className="flex gap-0.5 mt-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i < vice.intensity_level ? fill : "bg-white/10"
            )}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        {Math.round(vice.engagement_score * 100)}% engagement
      </p>
    </GlassCard>
  )
}

export function ViceLockedCard() {
  return (
    <GlassCard className="p-4 min-w-[180px] opacity-40 blur-[1px]">
      <div className="flex items-center gap-2">
        <Lock className="h-3 w-3 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">undiscovered</span>
      </div>
      <div className="flex gap-0.5 mt-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-1.5 flex-1 rounded-full bg-white/5" />
        ))}
      </div>
      <p className="text-xs text-muted-foreground/50 mt-2">keep talking to find out</p>
    </GlassCard>
  )
}
