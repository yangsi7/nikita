"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { EmotionalStateResponse } from "@/lib/api/types"

interface MoodOrbMiniProps {
  state: EmotionalStateResponse
}

const conflictVariants: Record<string, { variant: "default" | "secondary" | "destructive" | "outline", className: string }> = {
  cold: { variant: "outline", className: "border-blue-400 text-blue-400" },
  passive_aggressive: { variant: "outline", className: "border-amber-400 text-amber-400" },
  vulnerable: { variant: "outline", className: "border-purple-400 text-purple-400" },
  explosive: { variant: "destructive", className: "" },
}

export function MoodOrbMini({ state }: MoodOrbMiniProps) {
  // Compute orb color from emotional state
  const hue = 240 + state.valence * 100 // Blue (240) to Rose/Pink (340)

  // Conflict state color overrides
  const conflictColors: Record<string, number> = {
    cold: 200,
    passive_aggressive: 45,
    vulnerable: 280,
    explosive: 0,
  }

  const activeHue =
    state.conflict_state !== "none" && state.conflict_state in conflictColors
      ? conflictColors[state.conflict_state]
      : hue

  const orbStyle = {
    width: "36px",
    height: "36px",
    background: `radial-gradient(circle at 30% 30%, hsl(${activeHue}, 70%, 60%), hsl(${activeHue}, 80%, 40%))`,
    boxShadow: `0 0 ${state.intimacy * 10}px hsl(${activeHue}, 70%, 50%)`,
  }

  return (
    <Link
      href="/dashboard/nikita"
      className="flex items-center gap-3 hover:opacity-80 transition-opacity group"
    >
      {/* Mini Orb */}
      <div className="shrink-0 rounded-full" style={orbStyle} />

      {/* Description */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground/90 truncate group-hover:text-foreground transition-colors">
          {state.description}
        </p>
      </div>

      {/* Conflict Badge */}
      {state.conflict_state !== "none" && (
        <Badge
          variant={conflictVariants[state.conflict_state]?.variant || "outline"}
          className={cn(
            "shrink-0",
            conflictVariants[state.conflict_state]?.className
          )}
        >
          {state.conflict_state.replace("_", " ")}
        </Badge>
      )}
    </Link>
  )
}
