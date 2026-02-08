"use client"

import { ScoreRing } from "@/components/charts/score-ring"
import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { CHAPTER_ROMAN } from "@/lib/constants"
import type { UserStats } from "@/lib/api/types"

interface RelationshipHeroProps {
  stats: UserStats
}

export function RelationshipHero({ stats }: RelationshipHeroProps) {
  const statusColors: Record<string, string> = {
    active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    boss_fight: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    game_over: "bg-red-500/20 text-red-400 border-red-500/30",
    won: "bg-rose-500/20 text-rose-400 border-rose-500/30",
  }

  return (
    <GlassCard variant="elevated" className="p-6">
      <div className="flex flex-col items-center gap-4 md:flex-row md:gap-8">
        <ScoreRing score={stats.relationship_score} size={140} />
        <div className="flex flex-col items-center gap-3 md:items-start">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-rose-500/30 text-rose-400">
              Chapter {CHAPTER_ROMAN[stats.chapter]} — {stats.chapter_name}
            </Badge>
            <Badge variant="outline" className={statusColors[stats.game_status] ?? ""}>
              {stats.game_status.replace("_", " ")}
            </Badge>
          </div>
          {stats.game_status === "boss_fight" && (
            <div className="w-full max-w-[200px]">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Boss Progress</span>
                <span>{Math.round(stats.progress_to_boss)}%</span>
              </div>
              <Progress value={stats.progress_to_boss} className="h-2" />
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {stats.days_played} days played
            {stats.boss_attempts > 0 && ` · ${stats.boss_attempts} boss attempts`}
          </p>
        </div>
      </div>
    </GlassCard>
  )
}
