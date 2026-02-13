"use client"

import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { GlassCard } from "@/components/glass/glass-card"
import { NarrativeArcItem } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { format } from "date-fns"

interface StoryArcViewerProps {
  arcs: NarrativeArcItem[]
}

const STAGES = ["setup", "rising", "climax", "falling", "resolved"] as const
const STAGE_LABELS = {
  setup: "Setup",
  rising: "Rising",
  climax: "Climax",
  falling: "Falling",
  resolved: "Resolved",
}

export function StoryArcViewer({ arcs }: StoryArcViewerProps) {
  if (arcs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No storylines active yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {arcs.map((arc) => {
        const rawStageIndex = STAGES.indexOf(arc.current_stage as typeof STAGES[number])
        const currentStageIndex = rawStageIndex >= 0 ? rawStageIndex : 0
        const isResolved = arc.current_stage === "resolved" && arc.resolved_at
        const progress = (arc.conversations_in_arc / arc.max_conversations) * 100

        return (
          <GlassCard
            key={arc.id}
            className={cn("p-4", isResolved && "opacity-60")}
          >
            <div className="space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-medium text-foreground">
                    {arc.template_name}
                  </h3>
                  <Badge variant="secondary" className="mt-1">
                    {arc.category}
                  </Badge>
                </div>
                {isResolved && arc.resolved_at && (
                  <div className="text-xs text-muted-foreground">
                    Resolved {format(new Date(arc.resolved_at), "MMM d, yyyy")}
                  </div>
                )}
              </div>

              {/* Stage Progress Dots */}
              <div className="flex items-center gap-1">
                {STAGES.map((stage, index) => {
                  const isPast = index < currentStageIndex
                  const isCurrent = index === currentStageIndex
                  const isFuture = index > currentStageIndex

                  return (
                    <div key={stage} className="flex items-center flex-1">
                      <div
                        className={cn(
                          "w-3 h-3 rounded-full transition-colors",
                          isCurrent && "bg-rose-400",
                          isPast && "bg-white/50",
                          isFuture && "bg-white/20"
                        )}
                        title={STAGE_LABELS[stage]}
                      />
                      {index < STAGES.length - 1 && (
                        <div
                          className={cn(
                            "h-0.5 flex-1 transition-colors",
                            isPast ? "bg-white/50" : "bg-white/20"
                          )}
                        />
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Stage Labels */}
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                {STAGES.map((stage) => (
                  <div
                    key={stage}
                    className={cn(
                      "flex-1 text-center",
                      stage === arc.current_stage && "text-rose-400 font-medium"
                    )}
                  >
                    {STAGE_LABELS[stage]}
                  </div>
                ))}
              </div>

              {/* Progress Bar */}
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {arc.conversations_in_arc} / {arc.max_conversations}{" "}
                    conversations
                  </span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="h-1" />
              </div>

              {/* Current Description */}
              {arc.current_description && (
                <p className="text-sm text-foreground/80 italic">
                  {arc.current_description}
                </p>
              )}

              {/* Involved Characters */}
              {arc.involved_characters.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {arc.involved_characters.map((character, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="text-xs bg-white/5"
                    >
                      {character}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </GlassCard>
        )
      })}
    </div>
  )
}
