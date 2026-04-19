"use client"

/**
 * SliderControl — Spec 214 T3.6.
 *
 * 1-5 segmented button row (darkness slider replacement). Each segment is a
 * 44×44 min-touch-target per AC-plan-11d.M1.
 *
 * Maintains an internal `selected` state so radio `aria-checked` reflects the
 * most recent pick. Without this, screen readers report the whole radiogroup
 * as unchecked, even after the user selects a value (PR #363 QA iter-1 fix I1).
 */

import { useState } from "react"

import type { ControlSelection } from "../../types/ControlSelection"

export interface SliderControlProps {
  disabled?: boolean
  onSubmit: (selection: ControlSelection) => void
}

export function SliderControl({ disabled, onSubmit }: SliderControlProps) {
  const [selected, setSelected] = useState<number | null>(null)

  function handleClick(n: number) {
    setSelected(n)
    onSubmit({ kind: "slider", value: n })
  }

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
          aria-checked={n === selected}
          disabled={disabled}
          onClick={() => handleClick(n)}
          className="h-11 min-w-[44px] min-h-[44px] flex-1 rounded-xl border border-input bg-background text-sm disabled:opacity-50"
        >
          {n}
        </button>
      ))}
    </div>
  )
}
