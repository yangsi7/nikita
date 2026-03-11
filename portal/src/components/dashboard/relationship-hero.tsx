"use client"

import { ScoreRing } from "@/components/charts/score-ring"
import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Heart } from "lucide-react"
import { CHAPTER_ROMAN } from "@/lib/constants"
import { cn } from "@/lib/utils"
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
    <GlassCard variant="elevated" className="p-6" data-testid="card-score-ring">
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
          <p className="text-xs text-muted-foreground">
            {stats.days_played} days played
            {stats.boss_attempts > 0 && ` · ${stats.boss_attempts} boss attempts`}
          </p>
          {stats.game_status !== "won" && stats.game_status !== "game_over" && (
            <div className="w-full max-w-[200px] space-y-1.5 mt-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Next Boss: {stats.boss_threshold}%
                </span>
                <div className="flex items-center gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <Heart
                      key={i}
                      className={cn("h-3 w-3",
                        i < (3 - (stats.boss_attempts ?? 0))
                          ? "fill-rose-400 text-rose-400"
                          : "text-muted-foreground/30"
                      )}
                    />
                  ))}
                </div>
              </div>
              <Progress
                value={stats.progress_to_boss ?? 0}
                className={cn("h-1.5",
                  stats.game_status === "boss_fight" && "animate-pulse"
                )}
              />
            </div>
          )}
        </div>
      </div>
    </GlassCard>
  )
}
