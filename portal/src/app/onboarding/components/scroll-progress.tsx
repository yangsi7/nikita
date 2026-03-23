"use client"

import { useEffect, useState, useCallback } from "react"
import { cn } from "@/lib/utils"

const SECTION_IDS = [
  "section-score",
  "section-chapters",
  "section-rules",
  "section-profile",
  "section-mission",
] as const

const SECTION_LABELS = [
  "The Score",
  "The Chapters",
  "The Rules",
  "Who Are You",
  "Your Mission",
] as const

export function ScrollProgress() {
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const elements = SECTION_IDS.map((id) =>
      document.querySelector(`[data-testid="${id}"]`)
    ).filter(Boolean) as Element[]

    if (elements.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const testId = entry.target.getAttribute("data-testid")
            const idx = SECTION_IDS.indexOf(testId as (typeof SECTION_IDS)[number])
            if (idx !== -1) {
              setActiveIndex(idx)
            }
          }
        }
      },
      { threshold: 0.5 }
    )

    for (const el of elements) {
      observer.observe(el)
    }

    return () => observer.disconnect()
  }, [])

  const scrollToSection = useCallback((index: number) => {
    const el = document.querySelector(`[data-testid="${SECTION_IDS[index]}"]`)
    el?.scrollIntoView({ behavior: "smooth" })
  }, [])

  return (
    <nav
      role="navigation"
      aria-label="Section progress"
      className="fixed right-6 top-1/2 z-10 hidden -translate-y-1/2 md:flex"
    >
      <div className="flex flex-col items-center gap-3 rounded-full bg-white/5 p-2 backdrop-blur-sm">
        {SECTION_IDS.map((id, i) => (
          <button
            key={id}
            type="button"
            onClick={() => scrollToSection(i)}
            aria-label={SECTION_LABELS[i]}
            aria-current={i === activeIndex ? "step" : undefined}
            className={cn(
              "size-2 rounded-full transition-all duration-200",
              i === activeIndex
                ? "scale-110 bg-rose-500 shadow-[0_0_8px_oklch(0.75_0.15_350/40%)]"
                : "bg-white/20 hover:bg-white/40"
            )}
          />
        ))}
      </div>
    </nav>
  )
}
