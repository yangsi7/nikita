"use client"

import { useId } from "react"

export interface RadioProps {
  options: readonly { value: string; label: string }[]
  value: string | null
  onChange: (v: string) => void
  ariaLabel: string
}

export function Radio({ options, value, onChange, ariaLabel }: RadioProps) {
  const groupName = useId()
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="space-y-2">
      {options.map((opt) => {
        const selected = value === opt.value
        return (
          <label
            key={opt.value}
            className={`flex items-center gap-3 px-4 py-3 rounded-md border min-h-[44px] cursor-pointer ${
              selected
                ? "bg-primary/20 border-primary"
                : "bg-white/5 border-white/10 hover:bg-primary/10"
            }`}
          >
            <input
              type="radio"
              name={groupName}
              value={opt.value}
              checked={selected}
              onChange={() => onChange(opt.value)}
              className="accent-primary"
            />
            <span>{opt.label}</span>
          </label>
        )
      })}
    </div>
  )
}
