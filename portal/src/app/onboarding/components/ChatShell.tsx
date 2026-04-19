"use client"

/**
 * ChatShell — Spec 214 T3.5.
 *
 * Virtualized message thread (react-virtuoso) driven by `useConversationState`
 * turns. Holds the single aria-live region for the entire wizard: bubbles do
 * NOT carry aria-live themselves (AC-T3.5.1). Includes the typing indicator
 * when `isLoading=true` and delegates the input surface to children via the
 * `footer` slot.
 *
 * Virtualization: we switch from plain stacking to the Virtuoso windowed
 * renderer at `VIRTUALIZATION_THRESHOLD` turns (AC-T3.5.2). Under the
 * threshold the entire list renders eagerly (better first-paint for typical
 * onboarding flows which are <20 turns).
 */

import { useEffect, useRef } from "react"
import { Virtuoso } from "react-virtuoso"

import type { Turn } from "../types/converse"
import { MessageBubble } from "./MessageBubble"
import { TypingIndicator } from "./TypingIndicator"

/** Above this turn count, switch to virtualized rendering (AC-T3.5.2). */
export const VIRTUALIZATION_THRESHOLD = 20

export interface ChatShellProps {
  turns: Turn[]
  isLoading: boolean
  /** Slot rendered below the thread (input + inline control). */
  footer?: React.ReactNode
  /** Slot rendered above the thread (progress header). */
  header?: React.ReactNode
}

export function ChatShell({ turns, isLoading, footer, header }: ChatShellProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const useVirtualization = turns.length > VIRTUALIZATION_THRESHOLD

  // Auto-scroll-to-bottom on new turns (for the non-virtualized path).
  useEffect(() => {
    if (useVirtualization) return
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [turns.length, isLoading, useVirtualization])

  return (
    <div className="flex h-[100dvh] flex-col bg-background">
      {header}
      <div
        ref={scrollRef}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-atomic="false"
        data-testid="chat-log"
        className="flex-1 overflow-y-auto px-4 pt-4 pb-2"
      >
        {useVirtualization ? (
          <Virtuoso
            data={turns}
            followOutput="smooth"
            itemContent={(index, turn) => (
              <MessageBubble
                key={index}
                turn={turn}
                instant={index < turns.length - 1}
              />
            )}
            className="virtuoso-full-height"
          />
        ) : (
          <div className="flex flex-col">
            {turns.map((turn, i) => (
              <MessageBubble
                key={i}
                turn={turn}
                instant={i < turns.length - 1}
              />
            ))}
          </div>
        )}
        {isLoading ? (
          <div className="flex w-full my-2 justify-start" data-testid="chat-loading">
            <TypingIndicator />
          </div>
        ) : null}
      </div>
      {footer ? (
        <div className="border-t bg-background px-4 py-3" data-testid="chat-footer">
          {footer}
        </div>
      ) : null}
    </div>
  )
}
