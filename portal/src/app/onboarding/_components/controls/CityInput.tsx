"use client"

import { useId } from "react"
import { SuggestionChips } from "../SuggestionChips"

const DEFAULT_CITIES = [
  { value: "zurich", label: "Zürich" },
  { value: "berlin", label: "Berlin" },
  { value: "lisbon", label: "Lisbon" },
] as const

/**
 * CityInput — text input with optional suggestion chips below.
 *
 * The Aceternity placeholders-and-vanish-input + Magicui text-shimmer
 * embellishments named in C1.13 are aspirational; the production component
 * here ships a clean accessible text input + the SuggestionChips row that
 * fills + submits on click. Visual polish can iterate post-merge.
 */
export interface CityInputProps {
  value: string
  onChange: (v: string) => void
  describedBy?: string
  suggestions?: readonly { value: string; label: string }[]
}

export function CityInput({
  value,
  onChange,
  describedBy,
  suggestions = DEFAULT_CITIES,
}: CityInputProps) {
  const id = useId()
  return (
    <div className="space-y-3">
      <input
        id={id}
        type="text"
        autoComplete="address-level2"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="your city"
        aria-describedby={describedBy}
        aria-required="true"
        placeholder="city"
        className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      />
      <SuggestionChips
        chips={suggestions}
        ariaLabel="city suggestions"
        onPick={(v) => onChange(v)}
      />
    </div>
  )
}
