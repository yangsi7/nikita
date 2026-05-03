"use client"

import { useId } from "react"

/**
 * Tel — E.164-only phone control (AC C1.12).
 *
 * `inputMode="tel"`, `autocomplete="tel"`, `aria-describedby` for the E.164
 * hint, `aria-invalid` on validation fail. Validation is server-side; FE
 * renders the input + helper.
 */
export interface TelProps {
  value: string
  onChange: (v: string) => void
  invalid?: boolean
  describedBy: string
}

export function Tel({ value, onChange, invalid, describedBy }: TelProps) {
  const id = useId()
  return (
    <input
      id={id}
      type="tel"
      inputMode="tel"
      autoComplete="tel"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="phone number in E.164 format"
      aria-describedby={describedBy}
      aria-invalid={invalid ? "true" : undefined}
      aria-required="true"
      placeholder="+41 79 …"
      className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    />
  )
}
