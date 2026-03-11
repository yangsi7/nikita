"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { GlassCard } from "@/components/glass/glass-card"
import type { PsycheTipsData } from "@/lib/api/types"

const attachmentColors: Record<string, string> = {
  secure: "border-emerald-400/30 text-emerald-400",
  anxious: "border-amber-400/30 text-amber-400",
  avoidant: "border-blue-400/30 text-blue-400",
  disorganized: "border-rose-400/30 text-rose-400",
}

const defenseColors: Record<string, string> = {
  open: "border-emerald-400/30 text-emerald-400",
  guarded: "border-amber-400/30 text-amber-400",
  deflecting: "border-orange-400/30 text-orange-400",
  withdrawing: "border-rose-400/30 text-rose-400",
}

interface PsycheSummaryProps {
  psyche: PsycheTipsData
}

export function PsycheSummary({ psyche }: PsycheSummaryProps) {
  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-muted-foreground">
          Nikita&apos;s State
        </h3>
        <Link
          href="/dashboard/nikita/day"
          className="text-xs text-rose-400 hover:underline"
        >
          Full analysis &rarr;
        </Link>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <Badge
          variant="outline"
          className={attachmentColors[psyche.attachment_style] ?? ""}
        >
          {psyche.attachment_style}
        </Badge>
        <Badge
          variant="outline"
          className={defenseColors[psyche.defense_mode] ?? ""}
        >
          {psyche.defense_mode}
        </Badge>
        <Badge variant="outline">{psyche.emotional_tone}</Badge>
      </div>
      {psyche.internal_monologue && (
        <p className="text-xs italic text-muted-foreground mt-2 line-clamp-2">
          &ldquo;{psyche.internal_monologue}&rdquo;
        </p>
      )}
    </GlassCard>
  )
}
