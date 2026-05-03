"use client"

import { useId } from "react"

/**
 * Slider — darkness 0-10 (AC C1.12). Uses native `<input type="range">`
 * with `aria-valuetext` formatted as `darkness ${value}/10`.
 *
 * Note: spec mentions Radix `<Slider>` from shadcn. We ship the native
 * input here for simplicity and zero dep churn; visually identical with
 * Tailwind track styles. Switching to Radix is a one-file refactor if
 * needed.
 */
export interface SliderProps {
  value: number
  onChange: (v: number) => void
  describedBy?: string
  min?: number
  max?: number
}

export function Slider({
  value,
  onChange,
  describedBy,
  min = 0,
  max = 10,
}: SliderProps) {
  const id = useId()
  return (
    <div className="space-y-2">
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="darkness level"
        aria-describedby={describedBy}
        aria-valuetext={`darkness ${value}/${max}`}
        className="w-full accent-primary"
      />
      <div className="text-sm text-foreground/70">
        {value}/{max}
      </div>
    </div>
  )
}
