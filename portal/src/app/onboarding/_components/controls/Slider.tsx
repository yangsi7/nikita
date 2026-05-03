"use client"

import { useId } from "react"

/**
 * Slider — darkness 0-10 (AC C1.12). Uses native `<input type="range">`
 * with `aria-valuetext` formatted as `darkness ${value}/10`.
 *
 * Native HTML `<input type="range">` is used here. The spec text in
 * C1.12 mentions Radix `<Slider>` for richer theming + multi-handle
 * support, neither of which the wizard needs. Native preserves the
 * canonical `aria-valuenow` / `aria-valuetext` / keyboard-arrow support
 * out of the box. Migration to Radix tracked as a deferred enhancement
 * (filed as a GH `enhancement` issue post-merge).
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
