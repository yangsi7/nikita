"use client"

import { GlassCard } from "@/components/glass/glass-card"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import type { EmotionalStateResponse } from "@/lib/api/types"

interface MoodOrbProps {
  state: EmotionalStateResponse
}

export function MoodOrb({ state }: MoodOrbProps) {
  // Compute orb visual parameters from emotional state
  const pulseSpeed = 3 - state.arousal * 2 // 3s (low arousal) -> 1s (high arousal)
  const hue = 240 + state.valence * 100 // Blue (240) to Rose/Pink (340)
  const size = 80 + state.dominance * 80 // 80px (low) -> 160px (high dominance)
  const glow = state.intimacy * 30 // 0-30px shadow spread

  // Conflict state color overrides
  const conflictColors: Record<string, number> = {
    cold: 200, // Cool blue
    passive_aggressive: 45, // Amber
    vulnerable: 280, // Purple
    explosive: 0, // Red
  }

  const activeHue =
    state.conflict_state !== "none" && state.conflict_state in conflictColors
      ? conflictColors[state.conflict_state]
      : hue

  // Orb gradient style
  const orbStyle = {
    width: `${size}px`,
    height: `${size}px`,
    background: `radial-gradient(circle at 30% 30%, hsl(${activeHue}, 70%, 60%), hsl(${activeHue}, 80%, 40%))`,
    boxShadow: `0 0 ${glow}px hsl(${activeHue}, 70%, 50%), 0 0 ${glow * 2}px hsl(${activeHue}, 70%, 30%)`,
    animation: `mood-orb-pulse ${pulseSpeed}s ease-in-out infinite`,
  }

  const stats = [
    { label: "Arousal", value: state.arousal },
    { label: "Valence", value: state.valence },
    { label: "Dominance", value: state.dominance },
    { label: "Intimacy", value: state.intimacy },
  ]

  return (
    <GlassCard variant="elevated" className="p-8">
      <div className="flex flex-col items-center gap-6">
        {/* Orb */}
        <div className="relative flex items-center justify-center">
          <div className="rounded-full" style={orbStyle} role="img" aria-label={`Mood orb: ${state.description}`} />
        </div>

        {/* Description */}
        <p className="text-center text-sm text-foreground/90 max-w-md">
          {state.description}
        </p>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
          {stats.map((stat) => (
            <div key={stat.label} className="space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground font-medium">
                  {stat.label}
                </span>
                <span className="text-xs text-foreground font-mono">
                  {(stat.value * 100).toFixed(0)}%
                </span>
              </div>
              <Progress value={stat.value * 100} className="h-1.5" aria-label={`${stat.label}: ${(stat.value * 100).toFixed(0)}%`} />
            </div>
          ))}
        </div>
      </div>
    </GlassCard>
  )
}
