"use client"

/**
 * ToggleControl — Spec 214 T3.6.
 *
 * Binary voice/text toggle for the handoff preference. Each option is a
 * 44×44 min-touch-target per AC-plan-11d.M1.
 *
 * Maintains an internal `selected` state so radio `aria-checked` reflects the
 * most recent pick. Without this, screen readers report the whole radiogroup
 * as unchecked, even after the user selects a value (PR #363 QA iter-1 fix I2).
 */

import { useState } from "react"

import type { ControlSelection } from "../../types/ControlSelection"

export interface ToggleControlProps {
  disabled?: boolean
  onSubmit: (selection: ControlSelection) => void
}

export function ToggleControl({ disabled, onSubmit }: ToggleControlProps) {
  const [selected, setSelected] = useState<"voice" | "text" | null>(null)

  function handleClick(v: "voice" | "text") {
    setSelected(v)
    onSubmit({ kind: "toggle", value: v })
  }

  return (
    <div
      data-testid="toggle-control"
      className="flex items-center gap-2"
      role="radiogroup"
      aria-label="handoff preference"
    >
      {(["voice", "text"] as const).map((v) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={v === selected}
          disabled={disabled}
          onClick={() => handleClick(v)}
          className="h-11 min-w-[44px] min-h-[44px] flex-1 rounded-xl border border-input bg-background text-sm disabled:opacity-50"
        >
          {v}
        </button>
      ))}
    </div>
  )
}
