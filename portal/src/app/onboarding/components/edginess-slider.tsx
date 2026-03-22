"use client"

import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

const LEVELS = [
  { emoji: "\uD83D\uDE07", label: "Keep it clean" },
  { emoji: "\uD83D\uDE09", label: "Light flirting" },
  { emoji: "\uD83C\uDF36\uFE0F", label: "Spicy is okay" },
  { emoji: "\uD83D\uDC80", label: "Dark humor welcome" },
  { emoji: "\uD83D\uDD25", label: "No limits" },
]

interface EdginessSliderProps {
  value: number
  onChange: (value: number) => void
}

export function EdginessSlider({ value, onChange }: EdginessSliderProps) {
  const currentLevel = LEVELS[value - 1]

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Emoji markers above track */}
      <div className="flex w-full justify-between px-1">
        {LEVELS.map((level, i) => (
          <span
            key={i}
            className={cn(
              "text-sm transition-opacity duration-150",
              i + 1 === value ? "opacity-100" : "opacity-40"
            )}
            aria-hidden="true"
          >
            {level.emoji}
          </span>
        ))}
      </div>

      {/* Slider */}
      <Slider
        min={1}
        max={5}
        step={1}
        value={[value]}
        onValueChange={(vals) => onChange(vals[0])}
        aria-label="Edginess level"
        aria-valuetext={currentLevel.label}
        className="w-full [&_[data-slot=slider-range]]:bg-rose-500 [&_[data-slot=slider-thumb]]:border-rose-500 [&_[data-slot=slider-thumb]]:shadow-[0_0_8px_oklch(0.75_0.15_350/40%)]"
      />

      {/* Current value display */}
      <div className="flex items-center gap-3 transition-opacity duration-150">
        <span className="text-4xl" aria-hidden="true">
          {currentLevel.emoji}
        </span>
        <span className="text-sm font-medium text-muted-foreground">
          {currentLevel.label}
        </span>
      </div>
    </div>
  )
}
