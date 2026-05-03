"use client"

/**
 * Chips — small-set chip select (e.g. voice_tone_pref tri-state). Single-pick.
 */
export interface ChipsProps {
  options: readonly { value: string; label: string }[]
  value: string | null
  onChange: (v: string) => void
  ariaLabel: string
}

export function Chips({ options, value, onChange, ariaLabel }: ChipsProps) {
  return (
    <div role="group" aria-label={ariaLabel} className="flex gap-2 flex-wrap">
      {options.map((opt) => {
        const selected = value === opt.value
        return (
          <button
            type="button"
            key={opt.value}
            aria-pressed={selected}
            onClick={() => onChange(opt.value)}
            className={`px-4 py-2 rounded-full text-sm border min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              selected
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-white/5 border-white/10 hover:bg-primary/20"
            }`}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
