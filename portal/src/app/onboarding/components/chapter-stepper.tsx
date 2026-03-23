"use client"

import { useRef } from "react"
import { motion, useInView, useReducedMotion } from "framer-motion"
import { Check, Lock } from "lucide-react"
import { cn } from "@/lib/utils"

interface Chapter {
  number: number
  name: string
  tagline: string
  locked: boolean
}

interface ChapterStepperProps {
  currentChapter: number
  chapters: Chapter[]
}

export function ChapterStepper({ currentChapter, chapters }: ChapterStepperProps) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.3 })
  const prefersReducedMotion = useReducedMotion()
  const show = prefersReducedMotion || isInView

  const romanNumerals: Record<number, string> = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
  }

  return (
    <div ref={ref} role="list" aria-label="Chapter progression" data-testid="onboarding-chapter-stepper">
      {/* Desktop: horizontal */}
      <div className="hidden md:flex md:items-center md:justify-center md:gap-0">
        {chapters.map((ch, i) => {
          const isCurrent = ch.number === currentChapter
          const isNext = ch.number === currentChapter + 1
          const isCompleted = ch.number < currentChapter

          return (
            <motion.div
              key={ch.number}
              role="listitem"
              aria-current={isCurrent ? "step" : undefined}
              className="flex items-center"
              initial={prefersReducedMotion ? false : { opacity: 0, scale: 0.8 }}
              animate={show ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.4, delay: i * 0.3, ease: "easeOut" }}
            >
              {/* Connector before (not on first) */}
              {i > 0 && (
                <div
                  className={cn(
                    "h-0.5 w-8 lg:w-12",
                    isCompleted || isCurrent
                      ? "bg-rose-500"
                      : isNext
                        ? "border-t-2 border-dashed border-rose-500/50 bg-transparent"
                        : "bg-muted-foreground/20"
                  )}
                />
              )}

              {/* Node */}
              <div className="flex flex-col items-center gap-1.5">
                {isCurrent ? (
                  <motion.div
                    className={cn(
                      "flex size-10 items-center justify-center rounded-full border-2 transition-all",
                      "border-rose-500 bg-rose-500 text-white"
                    )}
                    animate={show && !prefersReducedMotion ? {
                      scale: [1, 1.08, 1],
                      boxShadow: [
                        "0 0 15px oklch(0.75 0.15 350 / 40%)",
                        "0 0 25px oklch(0.75 0.15 350 / 60%)",
                        "0 0 15px oklch(0.75 0.15 350 / 40%)",
                      ],
                    } : {}}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <Check className="size-4" />
                  </motion.div>
                ) : ch.locked && !isNext ? (
                  <motion.div
                    className={cn(
                      "flex size-10 items-center justify-center rounded-full border-2 transition-all",
                      "border-muted-foreground/30 bg-muted text-muted-foreground"
                    )}
                    initial={prefersReducedMotion ? false : { opacity: 0, filter: "blur(4px)" }}
                    animate={show ? { opacity: 1, filter: "blur(0px)" } : { opacity: 0, filter: "blur(4px)" }}
                    transition={{ duration: 0.6, delay: i * 0.3 + 0.2, ease: "easeOut" }}
                  >
                    <Lock className="size-3.5" />
                  </motion.div>
                ) : (
                  <div
                    className={cn(
                      "flex size-10 items-center justify-center rounded-full border-2 transition-all",
                      isNext && "border-dashed border-rose-500/50 bg-transparent text-rose-500/50",
                      isCompleted && "border-rose-500 bg-rose-500/20 text-rose-500"
                    )}
                  >
                    {isCompleted ? (
                      <Check className="size-4" />
                    ) : (
                      <Lock className="size-3.5" />
                    )}
                  </div>
                )}
                <span className="text-[10px] font-medium text-muted-foreground">
                  {romanNumerals[ch.number]}
                </span>
                <span
                  className={cn(
                    "max-w-[80px] text-center text-[10px] leading-tight",
                    isCurrent ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  {ch.name}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Mobile: vertical */}
      <div className="flex flex-col gap-0 md:hidden">
        {chapters.map((ch, i) => {
          const isCurrent = ch.number === currentChapter
          const isNext = ch.number === currentChapter + 1
          const isCompleted = ch.number < currentChapter
          const isLast = i === chapters.length - 1

          return (
            <motion.div
              key={ch.number}
              role="listitem"
              aria-current={isCurrent ? "step" : undefined}
              className="flex gap-3"
              initial={prefersReducedMotion ? false : { opacity: 0, x: -20 }}
              animate={show ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
              transition={{ duration: 0.4, delay: i * 0.3, ease: "easeOut" }}
            >
              {/* Node + connector column */}
              <div className="flex flex-col items-center">
                {isCurrent ? (
                  <motion.div
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-full border-2",
                      "border-rose-500 bg-rose-500 text-white"
                    )}
                    animate={show && !prefersReducedMotion ? {
                      scale: [1, 1.08, 1],
                      boxShadow: [
                        "0 0 15px oklch(0.75 0.15 350 / 40%)",
                        "0 0 25px oklch(0.75 0.15 350 / 60%)",
                        "0 0 15px oklch(0.75 0.15 350 / 40%)",
                      ],
                    } : {}}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  >
                    <Check className="size-3.5" />
                  </motion.div>
                ) : ch.locked && !isNext ? (
                  <motion.div
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-full border-2",
                      "border-muted-foreground/30 bg-muted text-muted-foreground"
                    )}
                    initial={prefersReducedMotion ? false : { opacity: 0, filter: "blur(4px)" }}
                    animate={show ? { opacity: 1, filter: "blur(0px)" } : { opacity: 0, filter: "blur(4px)" }}
                    transition={{ duration: 0.6, delay: i * 0.3 + 0.2, ease: "easeOut" }}
                  >
                    <Lock className="size-3" />
                  </motion.div>
                ) : (
                  <div
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-full border-2",
                      isNext && "border-dashed border-rose-500/50 bg-transparent text-rose-500/50",
                      isCompleted && "border-rose-500 bg-rose-500/20 text-rose-500"
                    )}
                  >
                    {isCompleted ? (
                      <Check className="size-3.5" />
                    ) : (
                      <Lock className="size-3" />
                    )}
                  </div>
                )}
                {!isLast && (
                  <div
                    className={cn(
                      "w-0.5 grow min-h-6",
                      isCompleted || isCurrent
                        ? "bg-rose-500"
                        : "bg-muted-foreground/20"
                    )}
                  />
                )}
              </div>

              {/* Label */}
              <div className="pb-4">
                <span
                  className={cn(
                    "text-sm font-medium",
                    isCurrent ? "text-foreground" : "text-muted-foreground"
                  )}
                >
                  Chapter {romanNumerals[ch.number]} &mdash; {ch.name}
                </span>
                <p className="text-xs text-muted-foreground/60">
                  {isCurrent
                    ? "(you are here)"
                    : isNext
                      ? "(next)"
                      : ch.locked
                        ? "(locked)"
                        : ""}
                </p>
                {!ch.locked && (
                  <p className="mt-0.5 text-xs text-muted-foreground/80">
                    {ch.tagline}
                  </p>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
