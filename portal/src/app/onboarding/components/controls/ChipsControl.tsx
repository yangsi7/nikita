"use client"

/**
 * ChipsControl — Spec 214 T3.6.
 *
 * Renders the current-prompt options as a wrap-capable chip grid. AC-plan-11d.M2:
 * wraps cleanly at viewport ≤360px (flex-wrap + gap). No horizontal scroll.
 */

import type { ControlSelection } from "../../types/ControlSelection"

export interface ChipsControlProps {
  options: string[]
  disabled?: boolean
  onSubmit: (selection: ControlSelection) => void
}

export function ChipsControl({ options, disabled, onSubmit }: ChipsControlProps) {
  return (
    <div
      data-testid="chips-control"
      className="flex flex-wrap gap-2"
    >
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          disabled={disabled}
          onClick={() => onSubmit({ kind: "chips", value: opt })}
          className="h-11 min-w-[44px] min-h-[44px] rounded-full border border-input bg-background px-4 text-sm disabled:opacity-50"
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
