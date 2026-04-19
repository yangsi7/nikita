/**
 * ControlSelection — Spec 214 FR-11d (T3.2).
 *
 * Discriminated TypeScript union that mirrors the Pydantic ControlSelection
 * server model in `nikita/agents/onboarding/control_selection.py`. The portal
 * serializes chip/slider/toggle/cards selections in this shape before
 * POSTing to `/portal/onboarding/converse`. Free-text input is normalized to
 * a raw `string` before POST (see `normalizeUserInput` below).
 *
 * Design decision D4 (plan.md §3): TS union with `kind` discriminator +
 * per-kind payload; matches server model 1:1.
 *
 * Zod schema lives alongside so client-side validation catches malformed
 * payloads before the wire (AC-T3.2.1).
 */

import { z } from "zod"

export const textControlSchema = z.object({
  kind: z.literal("text"),
  value: z.string().min(1),
})

export const chipsControlSchema = z.object({
  kind: z.literal("chips"),
  value: z.string().min(1).max(64),
})

export const sliderControlSchema = z.object({
  kind: z.literal("slider"),
  value: z.number().int().min(1).max(5),
})

export const toggleControlSchema = z.object({
  kind: z.literal("toggle"),
  value: z.union([z.literal("voice"), z.literal("text")]),
})

export const cardsControlSchema = z.object({
  kind: z.literal("cards"),
  value: z.string().regex(/^[a-f0-9]{12}$/, "must be a 12-char hex option_id"),
})

export const controlSelectionSchema = z.discriminatedUnion("kind", [
  textControlSchema,
  chipsControlSchema,
  sliderControlSchema,
  toggleControlSchema,
  cardsControlSchema,
])

export type TextControl = z.infer<typeof textControlSchema>
export type ChipsControl = z.infer<typeof chipsControlSchema>
export type SliderControl = z.infer<typeof sliderControlSchema>
export type ToggleControl = z.infer<typeof toggleControlSchema>
export type CardsControl = z.infer<typeof cardsControlSchema>
export type ControlSelection = z.infer<typeof controlSelectionSchema>

export type PromptType = "text" | "chips" | "slider" | "toggle" | "cards" | "none"

/**
 * Collapse a TextControl to a raw string before the HTTP body leaves the
 * portal (AC-T3.2.2). Chip/slider/toggle/cards selections pass through so
 * the server sees the full discriminated union.
 */
export function normalizeUserInput(
  value: string | ControlSelection
): string | ControlSelection {
  if (typeof value === "string") return value
  if (value.kind === "text") return value.value
  return value
}
