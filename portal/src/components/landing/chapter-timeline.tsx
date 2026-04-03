"use client"

import { cn } from "@/lib/utils"

// Marketing names — game uses "Curiosity"/"Established" internally
const CHAPTERS = [
  { id: "Ch1", name: "Spark", threshold: "55%" },
  { id: "Ch2", name: "Intrigue", threshold: "60%" },
  { id: "Ch3", name: "Investment", threshold: "65%" },
  { id: "Ch4", name: "Intimacy", threshold: "70%" },
  { id: "Ch5", name: "Home", threshold: "75%" },
]

interface ChapterTimelineProps {
  className?: string
  activeChapter?: number
}

export function ChapterTimeline({ className, activeChapter }: ChapterTimelineProps) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <div className="min-w-[480px] px-4 py-6">
        {/* Track */}
        <div className="relative flex items-center justify-between">
          {/* Connecting line */}
          <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-px bg-white/20" />

          {CHAPTERS.map((ch, i) => {
            const isActive = activeChapter !== undefined && i < activeChapter
            return (
              <div key={ch.id} className="relative flex flex-col items-center gap-2 z-10">
                {/* Threshold above dot */}
                <span className="text-muted-foreground text-xs tabular-nums">
                  {ch.threshold}
                </span>

                {/* Chapter dot */}
                <div
                  data-testid="chapter-dot"
                  className={cn(
                    "w-4 h-4 rounded-full border-2 transition-colors",
                    isActive
                      ? "bg-primary border-primary"
                      : "bg-void border-white/30"
                  )}
                />

                {/* Chapter label */}
                <span className="text-muted-foreground text-xs font-mono">{ch.id}</span>

                {/* Chapter name */}
                <span className="text-foreground text-xs font-medium capitalize">
                  {ch.name}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
