"use client"

/**
 * SliderControl — Spec 214 T3.6.
 *
 * 1-5 segmented button row (darkness slider replacement). Each segment is a
 * 44×44 min-touch-target per AC-plan-11d.M1.
 */

import type { ControlSelection } from "../../types/ControlSelection"

export interface SliderControlProps {
  disabled?: boolean
  onSubmit: (selection: ControlSelection) => void
}

export function SliderControl({ disabled, onSubmit }: SliderControlProps) {
  return (
    <div
      data-testid="slider-control"
      className="flex items-center gap-2"
      role="radiogroup"
      aria-label="darkness level"
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={false}
          disabled={disabled}
          onClick={() => onSubmit({ kind: "slider", value: n })}
          className="h-11 min-w-[44px] min-h-[44px] flex-1 rounded-xl border border-input bg-background text-sm disabled:opacity-50"
        >
          {n}
        </button>
      ))}
    </div>
  )
}
