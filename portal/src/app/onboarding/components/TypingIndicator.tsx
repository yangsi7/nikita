"use client"

/**
 * TypingIndicator — Spec 214 T3.5.
 *
 * Three pulsing dots rendered while awaiting Nikita's turn. `aria-hidden`
 * (scroll container carries the aria-live announcement, not the dots).
 */

import { cn } from "@/lib/utils"

export interface TypingIndicatorProps {
  className?: string
}

export function TypingIndicator({ className }: TypingIndicatorProps) {
  return (
    <div
      data-testid="typing-indicator"
      aria-hidden="true"
      className={cn(
        "inline-flex items-center gap-1 px-4 py-3 rounded-2xl bg-muted",
        className
      )}
    >
      <span className="h-2 w-2 rounded-full bg-foreground/40 animate-pulse [animation-delay:0ms]" />
      <span className="h-2 w-2 rounded-full bg-foreground/40 animate-pulse [animation-delay:150ms]" />
      <span className="h-2 w-2 rounded-full bg-foreground/40 animate-pulse [animation-delay:300ms]" />
    </div>
  )
}
