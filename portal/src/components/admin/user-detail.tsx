"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { CHAPTER_ROMAN } from "@/lib/constants"
import { scoreColor, formatDate } from "@/lib/utils"
import type { AdminUserDetail } from "@/lib/api/types"

interface UserDetailProps {
  user: AdminUserDetail
}

export function UserDetail({ user }: UserDetailProps) {
  return (
    <div className="space-y-6">
      {/* Profile Card */}
      <GlassCard variant="elevated" className="p-6">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="flex-1 space-y-3">
            <h2 className="text-xl font-bold">
              {user.phone ?? (user.telegram_id ? `TG: ${user.telegram_id}` : user.id.slice(0, 12))}
            </h2>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="border-rose-500/30 text-rose-400">
                Chapter {CHAPTER_ROMAN[user.chapter]}
              </Badge>
              <Badge variant="outline">{user.game_status}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Score</span>
                <p className={scoreColor(user.relationship_score)}>{Math.round(user.relationship_score)}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Days Played</span>
                <p>{user.days_played}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Boss Attempts</span>
                <p>{user.boss_attempts}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Last Active</span>
                <p className="text-xs">{user.last_interaction_at ? formatDate(user.last_interaction_at) : "Never"}</p>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
