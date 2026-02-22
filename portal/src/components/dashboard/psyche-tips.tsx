"use client"

import { GlassCardWithHeader } from "@/components/glass/glass-card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import type { PsycheTipsData } from "@/lib/api/types"

interface PsycheTipsProps {
  tips: PsycheTipsData
}

const toneColors: Record<string, string> = {
  playful: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  serious: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  warm: "bg-rose-500/20 text-rose-400 border-rose-500/30",
  distant: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  volatile: "bg-red-500/20 text-red-400 border-red-500/30",
}

const attachmentColors: Record<string, string> = {
  secure: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  anxious: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  avoidant: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  disorganized: "bg-red-500/20 text-red-400 border-red-500/30",
}

const defenseColors: Record<string, string> = {
  open: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  guarded: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  deflecting: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  withdrawing: "bg-red-500/20 text-red-400 border-red-500/30",
}

export function PsycheTips({ tips }: PsycheTipsProps) {
  const vulnerabilityPct = Math.round(tips.vulnerability_level * 100)

  return (
    <GlassCardWithHeader
      title="Psyche Insights"
      description={
        tips.generated_at
          ? `Updated ${new Date(tips.generated_at).toLocaleDateString()}`
          : "Default analysis"
      }
    >
      <div className="space-y-4">
        {/* Badges row */}
        <div className="flex flex-wrap gap-2">
          <Badge
            variant="outline"
            className={attachmentColors[tips.attachment_style] || ""}
          >
            {tips.attachment_style}
          </Badge>
          <Badge
            variant="outline"
            className={defenseColors[tips.defense_mode] || ""}
          >
            {tips.defense_mode}
          </Badge>
          <Badge
            variant="outline"
            className={toneColors[tips.emotional_tone] || ""}
          >
            {tips.emotional_tone}
          </Badge>
        </div>

        {/* Vulnerability bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between items-center">
            <span className="text-xs text-muted-foreground font-medium">
              Vulnerability
            </span>
            <span className="text-xs text-foreground font-mono">
              {vulnerabilityPct}%
            </span>
          </div>
          <Progress
            value={vulnerabilityPct}
            className="h-1.5"
            aria-label={`Vulnerability: ${vulnerabilityPct}%`}
          />
        </div>

        {/* Inner monologue */}
        <div className="rounded-md bg-white/5 p-3">
          <p className="text-xs text-muted-foreground italic leading-relaxed">
            &ldquo;{tips.internal_monologue}&rdquo;
          </p>
        </div>

        {/* Behavioral tips */}
        {tips.behavioral_tips.length > 0 && (
          <div className="space-y-1">
            <h5 className="text-xs font-medium text-muted-foreground">Tips</h5>
            <ul className="space-y-1">
              {tips.behavioral_tips.map((tip, i) => (
                <li
                  key={i}
                  className="text-xs text-foreground/80 pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[7px] before:h-1 before:w-1 before:rounded-full before:bg-foreground/40"
                >
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Topic chips */}
        <div className="flex flex-wrap gap-4">
          {tips.topics_to_encourage.length > 0 && (
            <div className="space-y-1">
              <h5 className="text-xs font-medium text-emerald-400/70">
                Encourage
              </h5>
              <div className="flex flex-wrap gap-1">
                {tips.topics_to_encourage.map((topic) => (
                  <span
                    key={topic}
                    className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-400 border border-emerald-500/20"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {tips.topics_to_avoid.length > 0 && (
            <div className="space-y-1">
              <h5 className="text-xs font-medium text-red-400/70">Avoid</h5>
              <div className="flex flex-wrap gap-1">
                {tips.topics_to_avoid.map((topic) => (
                  <span
                    key={topic}
                    className="inline-flex items-center rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] text-red-400 border border-red-500/20"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </GlassCardWithHeader>
  )
}

export function PsycheTipsEmpty() {
  return (
    <GlassCardWithHeader title="Psyche Insights">
      <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
        Psyche analysis pending...
      </div>
    </GlassCardWithHeader>
  )
}
