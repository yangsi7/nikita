"use client"

import { useId } from "react"

/**
 * CombinedDualTextarea — Screen 10 (T O G E T H E R / O D D) per AC C1.18.
 *
 * Outer `<fieldset role="group" aria-labelledby="screen-10-heading">` wraps
 * both textareas so screen-reader users perceive them as co-required.
 * Continue button has `aria-describedby` linking the combined helper
 * "both fields ≥10 chars".
 *
 * Each textarea carries per-slot `aria-label`, `aria-describedby`, and
 * `aria-required`.
 *
 * Submit (handled by WizardShell): the wizard issues TWO POST /answer
 * calls back-to-back — one for `together_we_could`, one for `same_weird_if`.
 * Both slots remain individually validated by FinalForm; the combined
 * screen is purely a UX optimization (CRO free-text-fatigue mitigation).
 */
export interface CombinedDualTextareaProps {
  togetherValue: string
  oddValue: string
  onTogetherChange: (v: string) => void
  onOddChange: (v: string) => void
  helperId: string
}

const MIN_LEN = 10

export function CombinedDualTextarea({
  togetherValue,
  oddValue,
  onTogetherChange,
  onOddChange,
  helperId,
}: CombinedDualTextareaProps) {
  const togetherDesc = useId()
  const oddDesc = useId()
  const togetherInvalid = togetherValue.trim().length < MIN_LEN
  const oddInvalid = oddValue.trim().length < MIN_LEN

  return (
    <fieldset className="border-0 p-0 m-0 space-y-6">
      <legend className="sr-only">
        what we&apos;d do together / the specific weird thing
      </legend>

      <div>
        <label className="block text-sm text-foreground/80 mb-1">
          together, we could…
        </label>
        <textarea
          value={togetherValue}
          onChange={(e) => onTogetherChange(e.target.value)}
          rows={3}
          aria-label="what we'd do together"
          aria-describedby={togetherDesc}
          aria-required="true"
          aria-invalid={togetherInvalid ? "true" : undefined}
          placeholder="long lunch on tuesdays. saturday market and lazy."
          className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <p id={togetherDesc} className="text-xs text-foreground/60 mt-1">
          a few words. ≥10 chars.
        </p>
      </div>

      <div>
        <label className="block text-sm text-foreground/80 mb-1">
          we&apos;re the same weird if…
        </label>
        <textarea
          value={oddValue}
          onChange={(e) => onOddChange(e.target.value)}
          rows={3}
          aria-label="the specific weird thing"
          aria-describedby={oddDesc}
          aria-required="true"
          aria-invalid={oddInvalid ? "true" : undefined}
          placeholder="we both reorganize someone else's bookshelves."
          className="w-full px-4 py-3 rounded-md bg-white/5 border border-white/10 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <p id={oddDesc} className="text-xs text-foreground/60 mt-1">
          one specific thing. ≥10 chars.
        </p>
      </div>

      <p id={helperId} className="text-xs text-foreground/60">
        both fields must be at least 10 characters.
      </p>
    </fieldset>
  )
}

export const COMBINED_MIN_LEN = MIN_LEN

export function combinedDualValid(t: string, o: string): boolean {
  return t.trim().length >= MIN_LEN && o.trim().length >= MIN_LEN
}
