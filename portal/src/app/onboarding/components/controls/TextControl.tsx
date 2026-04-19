"use client"

/**
 * TextControl — Spec 214 T3.6.
 *
 * Free-text onboarding input. Enter submits; 44px min-height satisfies the
 * AC-plan-11d.M1 touch-target floor.
 */

import { useState, type FormEvent } from "react"
import type { ControlSelection } from "../../types/ControlSelection"

export interface TextControlProps {
  disabled?: boolean
  placeholder?: string
  onSubmit: (selection: ControlSelection) => void
}

export function TextControl({ disabled, placeholder, onSubmit }: TextControlProps) {
  const [value, setValue] = useState("")

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) return
    onSubmit({ kind: "text", value: trimmed })
    setValue("")
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2" data-testid="text-control">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder ?? "type here..."}
        className="flex-1 h-11 min-h-[44px] rounded-xl border border-input bg-background px-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        aria-label="chat input"
      />
      <button
        type="submit"
        disabled={disabled || value.trim().length === 0}
        className="h-11 min-w-[44px] min-h-[44px] rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        send
      </button>
    </form>
  )
}
