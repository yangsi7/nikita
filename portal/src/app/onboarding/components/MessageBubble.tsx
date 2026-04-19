"use client"

/**
 * MessageBubble — Spec 214 T3.5.
 *
 * Left-aligned Nikita turn / right-aligned user turn. Nikita turns animate
 * a typewriter reveal (AC-T3.5.3); user turns render their content directly.
 *
 * Accessibility: the typewriter visual is `aria-hidden="true"`; the final
 * text lives in a sibling `sr-only` span so screen readers announce the
 * full content once (AC-T3.5.1).
 */

import { cn } from "@/lib/utils"
import type { Turn } from "../types/converse"
import { useOptimisticTypewriter } from "../hooks/useOptimisticTypewriter"

export interface MessageBubbleProps {
  turn: Turn
  /** Disable typewriter animation, e.g. when hydrating historical turns. */
  instant?: boolean
}

export function MessageBubble({ turn, instant = false }: MessageBubbleProps) {
  const isUser = turn.role === "user"
  const typewriter = useOptimisticTypewriter(turn.role === "nikita" && !instant ? turn.content : "")
  const shouldAnimate = turn.role === "nikita" && !instant
  const visible = shouldAnimate ? typewriter.visible : turn.content

  return (
    <div
      data-testid={`message-bubble-${turn.role}`}
      data-superseded={turn.superseded ? "true" : undefined}
      data-source={turn.source ?? undefined}
      className={cn(
        "flex w-full my-2",
        isUser ? "justify-end" : "justify-start",
        turn.superseded ? "opacity-50" : ""
      )}
    >
      <div
        className={cn(
          "max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed min-h-[44px]",
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        )}
      >
        {/* Visual typewriter span (aria-hidden during reveal). */}
        <span aria-hidden="true" data-testid="message-bubble-visible">
          {visible}
        </span>
        {/* Screen-reader sibling carries the final full text once. */}
        {shouldAnimate && !typewriter.done ? null : (
          <span className="sr-only" data-testid="message-bubble-sr">
            {turn.content}
          </span>
        )}
      </div>
    </div>
  )
}
