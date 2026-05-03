"use client"

import { useId } from "react"

export interface TextInputProps {
  value: string
  onChange: (v: string) => void
  ariaLabel: string
  describedBy?: string
  placeholder?: string
  inputMode?: "text" | "numeric"
  autoComplete?: string
}

export function TextInput({
  value,
  onChange,
  ariaLabel,
  describedBy,
  placeholder,
  inputMode = "text",
  autoComplete,
}: TextInputProps) {
  const id = useId()
  return (
    <input
      id={id}
      type="text"
      inputMode={inputMode}
      autoComplete={autoComplete}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={ariaLabel}
      aria-describedby={describedBy}
      aria-required="true"
      placeholder={placeholder}
      className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    />
  )
}
