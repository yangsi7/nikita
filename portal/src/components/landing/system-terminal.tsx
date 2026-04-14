"use client"

import { useEffect, useRef, useState } from "react"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const SYSTEMS = [
  { name: "Emotional Memory Engine", detail: "4D affect model" },
  { name: "Vice Personalization Layer", detail: "8 categories" },
  { name: "Relationship Scoring Engine", detail: "4 metrics + decay" },
  { name: "Boss Encounter System", detail: "5 chapters + bosses" },
  { name: "Chapter Progression Engine", detail: "5 chapters" },
  { name: "Engagement Decay Engine", detail: "6-state machine" },
  { name: "Telegram Integration", detail: "11 async stages" },
  { name: "Voice Conversation Engine", detail: "ElevenLabs Conv AI" },
  { name: "Text Generation Pipeline", detail: "token-budgeted" },
  { name: "Temporal Memory System", detail: "pgVector semantic" },
  { name: "Score History Tracker", detail: "delay + typos + style" },
  { name: "Onboarding Orchestrator", detail: "she texts you first" },
  { name: "Pipeline Monitoring", detail: "Gottman-based" },
  { name: "Admin Control Panel", detail: "attachment theory" },
]

const STATS = [
  { value: "742", label: "Python files" },
  { value: "5,533", label: "Tests passing" },
  { value: "86", label: "Specifications" },
]

interface SystemTerminalProps {
  className?: string
}

export function SystemTerminal({ className }: SystemTerminalProps) {
  const [visibleCount, setVisibleCount] = useState(0)
  const reducedMotion = useRef(false)

  useEffect(() => {
    reducedMotion.current =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches

    if (reducedMotion.current) {
      // Show all immediately
      setVisibleCount(SYSTEMS.length)
      return
    }

    // Stagger lines: 50ms each
    let count = 0
    const interval = setInterval(() => {
      count++
      setVisibleCount(count)
      if (count >= SYSTEMS.length) clearInterval(interval)
    }, 50)

    return () => clearInterval(interval)
  }, [])

  return (
    <div
      className={cn(
        "font-mono text-sm bg-black/40 rounded-lg border border-white/10 overflow-hidden",
        className
      )}
    >
      {/* Terminal title bar */}
      <div className="flex items-center gap-2 px-4 py-2 bg-white/5 border-b border-white/10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/60" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
          <div className="w-3 h-3 rounded-full bg-green-500/60" />
        </div>
        <span className="text-muted-foreground text-xs ml-2">nikita — bash</span>
      </div>

      {/* Terminal content */}
      <div className="p-4 space-y-1">
        <p className="text-muted-foreground text-xs mb-3">
          <span className="text-primary">$</span> nikita --systems --status
        </p>

        {SYSTEMS.map((system, i) => (
          <div
            key={system.name}
            className={cn(
              "flex items-start gap-3 transition-opacity duration-200",
              i < visibleCount ? "opacity-100" : "opacity-0"
            )}
          >
            <Check className="h-3.5 w-3.5 text-green-400 shrink-0 mt-[2px]" aria-hidden="true" strokeWidth={2.5} />
            <span className="text-foreground">{system.name}</span>
            <span className="text-muted-foreground ml-auto text-xs">{system.detail}</span>
          </div>
        ))}

        {/* Cursor */}
        <div className="flex items-center gap-1 mt-2">
          <span className="text-primary text-xs">$</span>
          <span className="terminal-cursor" aria-hidden="true" />
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 border-t border-white/10">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            className="px-4 py-3 text-center border-r border-white/10 last:border-r-0"
          >
            <p className="text-foreground font-semibold tabular-nums text-sm">
              {`${stat.value} ${stat.label}`}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
