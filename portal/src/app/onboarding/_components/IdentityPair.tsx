"use client"

/**
 * IdentityPair — Spec 217-3B FR-10a compound name+age control.
 *
 * Single Card with two inputs and one Continue button. POSTs the slot
 * `identity_pair` with a JSON-encoded `{name, age}` value string; the BE
 * (Spec 217-3A.3 SlotKind.IDENTITY_PAIR) parses + partial-validates and
 * returns either:
 *   - `deterministic_advance` (both valid → both slots persisted, advance)
 *   - `field_error` ({name?: msg, age?: msg}) — partial-failure: valid
 *     sub-fields persisted, FE preserves the entered values and renders
 *     inline errors next to the offending fields.
 *
 * AC-10b.1, 10b.2, 10b.3, 10b.4 — single-card, partial-validation, value
 * preservation across server round-trip.
 */

import { useState } from "react"

export interface IdentityPairProps {
  /** Initial name value (e.g. when re-rendering after partial field_error). */
  initialName?: string
  /** Initial age value (string, since the input is string-typed). */
  initialAge?: string
  /** Field-level error map from the most recent BE response. Keys are
   *  `name` / `age`. Empty / undefined when no errors are pending. */
  fieldErrors?: Record<string, string> | null
  /** Whether the control is disabled (e.g. while a POST is in flight, or
   *  while a followup is open). */
  disabled?: boolean
  /** Submit handler — called with the trimmed name + raw-string age.
   *  Caller is responsible for serializing to the wire shape and POSTing
   *  to /onboarding/answer with slot_kind=identity_pair. */
  onSubmit: (payload: { name: string; age: string }) => void
  /** Optional aria-describedby id for the why-we-ask helper text. */
  describedBy?: string
}

export function IdentityPair({
  initialName = "",
  initialAge = "",
  fieldErrors,
  disabled = false,
  onSubmit,
  describedBy,
}: IdentityPairProps) {
  const [name, setName] = useState(initialName)
  const [age, setAge] = useState(initialAge)

  const nameErr = fieldErrors?.name ?? null
  const ageErr = fieldErrors?.age ?? null

  const canSubmit =
    !disabled && name.trim().length > 0 && /^\d+$/.test(age.trim())

  return (
    <div data-testid="identity-pair" className="flex flex-col gap-4">
      <label className="flex flex-col gap-1">
        <span className="text-sm text-foreground/70">your name</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={disabled}
          autoComplete="given-name"
          placeholder="your name"
          aria-describedby={describedBy}
          aria-invalid={nameErr ? "true" : undefined}
          data-testid="identity-pair-name"
          className="w-full rounded-md bg-white/5 border border-white/10 px-4 py-3 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        {nameErr ? (
          <span
            data-testid="identity-pair-name-error"
            className="text-xs text-rose-400"
            role="alert"
          >
            {nameErr}
          </span>
        ) : null}
      </label>
      <label className="flex flex-col gap-1">
        <span className="text-sm text-foreground/70">how old are you?</span>
        <input
          type="text"
          inputMode="numeric"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          disabled={disabled}
          placeholder="age"
          aria-describedby={describedBy}
          aria-invalid={ageErr ? "true" : undefined}
          data-testid="identity-pair-age"
          className="w-full rounded-md bg-white/5 border border-white/10 px-4 py-3 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        {ageErr ? (
          <span
            data-testid="identity-pair-age-error"
            className="text-xs text-rose-400"
            role="alert"
          >
            {ageErr}
          </span>
        ) : null}
      </label>
      <div className="flex justify-end">
        <button
          type="button"
          data-testid="identity-pair-submit"
          disabled={!canSubmit}
          onClick={() =>
            onSubmit({ name: name.trim(), age: age.trim() })
          }
          className="inline-flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-base font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
        >
          continue
        </button>
      </div>
    </div>
  )
}
