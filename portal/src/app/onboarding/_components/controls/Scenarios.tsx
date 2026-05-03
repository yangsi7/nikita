"use client"

/**
 * Scenarios — 3-card option picker (e.g. saturday_morning).
 *
 * Renders a radiogroup of glass cards. Single-pick.
 */
export interface ScenariosProps {
  options: readonly { value: string; label: string; description?: string }[]
  value: string | null
  onChange: (v: string) => void
  ariaLabel: string
}

export function Scenarios({ options, value, onChange, ariaLabel }: ScenariosProps) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className="grid gap-3 sm:grid-cols-3">
      {options.map((opt) => {
        const selected = value === opt.value
        return (
          <button
            type="button"
            key={opt.value}
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(opt.value)}
            className={`p-4 rounded-lg text-left border min-h-[80px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors ${
              selected
                ? "bg-primary/20 border-primary"
                : "bg-white/5 border-white/10 hover:bg-primary/10"
            }`}
          >
            <div className="font-medium">{opt.label}</div>
            {opt.description && (
              <div className="mt-1 text-sm text-foreground/70">{opt.description}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}

export const SATURDAY_MORNING_OPTIONS = [
  {
    value: "lazy",
    label: "still in bed",
    description: "coffee, slow, nothing scheduled",
  },
  {
    value: "active",
    label: "out the door",
    description: "run, gym, market, hike",
  },
  {
    value: "creative",
    label: "in flow",
    description: "music on, deep work or making",
  },
] as const

export const VOICE_TONE_OPTIONS = [
  { value: "text", label: "text only" },
  { value: "voice", label: "voice only" },
  { value: "both", label: "both" },
] as const
