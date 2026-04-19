"use client"
/** InlineControl — Spec 214 T3.6 dispatcher. Registry pattern; no switch tree. */
import type { ControlSelection, PromptType } from "../types/ControlSelection"
import type { ComponentType } from "react"
import { TextControl } from "./controls/TextControl"
import { ChipsControl } from "./controls/ChipsControl"
import { SliderControl } from "./controls/SliderControl"
import { ToggleControl } from "./controls/ToggleControl"
import { CardsControl, type CardOption } from "./controls/CardsControl"
export interface InlineControlProps {
  promptType: PromptType
  options?: string[]
  cardOptions?: CardOption[]
  disabled?: boolean
  onSubmit: (sel: ControlSelection) => void
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const REGISTRY: Record<Exclude<PromptType, "none">, ComponentType<any>> = {
  text: TextControl, chips: ChipsControl, slider: SliderControl,
  toggle: ToggleControl, cards: CardsControl,
}
export function InlineControl({ promptType, options, cardOptions, disabled, onSubmit }: InlineControlProps) {
  if (promptType === "none") return null
  const Cmp = REGISTRY[promptType]
  const props = promptType === "chips" ? { options: options ?? [] }
    : promptType === "cards" ? { options: cardOptions ?? [] } : {}
  return <Cmp disabled={disabled} onSubmit={onSubmit} {...props} />
}
