"use client"

import { useId, useMemo, useState } from "react"
import { motion, useReducedMotion } from "framer-motion"
import {
  HOBBY_CATEGORIES,
  HOBBY_CHIPS,
  MAX_HOBBIES,
  MIN_HOBBIES,
  OTHER_MAX_LEN,
  OTHER_WARN_LEN,
  type HobbyChip,
} from "./hobby-taxonomy"

/**
 * HobbyChips — 100 chips × 10 categories with autocomplete + 3-5 enforcement
 * + "+ other" free-text (AC C1.6 + C1.12).
 *
 * - `role="group"` + `aria-label="primary hobbies"`
 * - Each chip is `<button aria-pressed>`
 * - Autocomplete input has `role="combobox"` + `aria-expanded` + `aria-autocomplete="list"`
 * - Live-region (`aria-live="polite"`) announces `${count}/5 picked`
 * - "+ other" free-text: `maxLength=40`, helper turns rose at len ≥35,
 *   trim before submit, reject empty-after-trim.
 */

export interface HobbyChipsProps {
  /** Currently picked values (slugs). */
  picks: readonly string[]
  /** Free-text "+ other" entry, if any. */
  other: string
  onPicksChange: (next: readonly string[]) => void
  onOtherChange: (next: string) => void
}

export function HobbyChips({
  picks,
  other,
  onPicksChange,
  onOtherChange,
}: HobbyChipsProps) {
  const [filter, setFilter] = useState("")
  const reduceMotion = useReducedMotion()
  const filterInputId = useId()
  const liveRegionId = useId()
  const listboxId = useId()

  const filteredByCategory = useMemo<Record<string, HobbyChip[]>>(() => {
    const norm = filter.trim().toLowerCase()
    const out: Record<string, HobbyChip[]> = {}
    for (const cat of HOBBY_CATEGORIES) out[cat] = []
    for (const chip of HOBBY_CHIPS) {
      if (norm && !chip.label.toLowerCase().includes(norm)) continue
      out[chip.category].push(chip)
    }
    return out
  }, [filter])

  const totalCount = picks.length + (other.trim().length > 0 ? 1 : 0)

  const togglePick = (value: string) => {
    if (picks.includes(value)) {
      onPicksChange(picks.filter((v) => v !== value))
      return
    }
    if (totalCount >= MAX_HOBBIES) return
    onPicksChange([...picks, value])
  }

  const otherWarn = other.length >= OTHER_WARN_LEN

  return (
    <div role="group" aria-label="primary hobbies" className="space-y-4">
      <div>
        <label htmlFor={filterInputId} className="sr-only">
          filter hobbies
        </label>
        <input
          id={filterInputId}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={filter.length > 0}
          aria-controls={listboxId}
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="filter hobbies…"
          className="w-full px-4 py-2 rounded-md bg-white/5 border border-white/10 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      <div id={listboxId} className="space-y-3 max-h-80 overflow-y-auto pr-1">
        {HOBBY_CATEGORIES.map((cat) => {
          const chips = filteredByCategory[cat]
          if (!chips || chips.length === 0) return null
          return (
            <div key={cat}>
              <h3 className="text-xs uppercase tracking-wider text-foreground/60 mb-2">
                {cat}
              </h3>
              <motion.div
                className="flex flex-wrap gap-2"
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: {},
                  visible: { transition: { staggerChildren: 0.02 } },
                }}
              >
                {chips.map((chip) => {
                  const selected = picks.includes(chip.value)
                  return (
                    <motion.button
                      type="button"
                      key={chip.value}
                      aria-pressed={selected}
                      onClick={() => togglePick(chip.value)}
                      variants={
                        reduceMotion
                          ? undefined
                          : {
                              hidden: { opacity: 0, scale: 0.95 },
                              visible: { opacity: 1, scale: 1 },
                            }
                      }
                      transition={{
                        duration: 0.18,
                        ease: [0.16, 1, 0.3, 1] as const,
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm border min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                        selected
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-white/5 border-white/10 hover:bg-primary/20"
                      }`}
                    >
                      {chip.label}
                    </motion.button>
                  )
                })}
              </motion.div>
            </div>
          )
        })}
      </div>

      <div className="space-y-1">
        <label htmlFor="hobby-other" className="text-xs uppercase tracking-wider text-foreground/60">
          + other
        </label>
        <input
          id="hobby-other"
          type="text"
          maxLength={OTHER_MAX_LEN}
          value={other}
          onChange={(e) => onOtherChange(e.target.value)}
          placeholder="something not above…"
          className="w-full px-4 py-2 rounded-md bg-white/5 border border-white/10 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <p
          className={`text-xs ${otherWarn ? "text-primary" : "text-foreground/60"}`}
        >
          {other.length}/{OTHER_MAX_LEN}
        </p>
      </div>

      <p
        id={liveRegionId}
        aria-live="polite"
        className="text-sm text-foreground/70"
      >
        {totalCount}/{MAX_HOBBIES} picked
      </p>
    </div>
  )
}

/** True iff the picks (+ trimmed other) form a valid 3-5 selection. */
export function hobbyPicksValid(
  picks: readonly string[],
  other: string
): boolean {
  const otherTrimmed = other.trim()
  const total = picks.length + (otherTrimmed.length > 0 ? 1 : 0)
  return total >= MIN_HOBBIES && total <= MAX_HOBBIES
}

/** Build the wire-shape value submitted to /answer for primary_hobbies. */
export function serializeHobbies(
  picks: readonly string[],
  other: string
): string {
  const otherTrimmed = other.trim()
  const all = otherTrimmed.length > 0 ? [...picks, otherTrimmed] : [...picks]
  return all.join(", ")
}
