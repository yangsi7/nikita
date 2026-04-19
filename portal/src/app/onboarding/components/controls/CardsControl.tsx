"use client"

/**
 * CardsControl — Spec 214 T3.6.
 *
 * Backstory card picker. `options` carry the 12-char hex option_id payload
 * expected by FR-4. Submitting commits `{kind: "cards", value: option_id}`.
 */

import type { ControlSelection } from "../../types/ControlSelection"

export interface CardOption {
  chosen_option_id: string
  cache_key?: string
  preview: string
}

export interface CardsControlProps {
  options: CardOption[]
  disabled?: boolean
  onSubmit: (selection: ControlSelection) => void
}

export function CardsControl({ options, disabled, onSubmit }: CardsControlProps) {
  return (
    <div data-testid="cards-control" className="flex flex-col gap-3">
      {options.map((opt) => (
        <button
          key={opt.chosen_option_id}
          type="button"
          disabled={disabled}
          onClick={() =>
            onSubmit({ kind: "cards", value: opt.chosen_option_id })
          }
          className="min-h-[44px] rounded-xl border border-input bg-background px-4 py-3 text-left text-sm disabled:opacity-50"
        >
          {opt.preview}
        </button>
      ))}
    </div>
  )
}
