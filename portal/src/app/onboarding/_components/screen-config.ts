/**
 * Screen ordering and per-slot copy for the Spec 216-C cinematic wizard.
 *
 * Visual order (15 screens) per AC C1.1, locked:
 *   welcome → display_name → age → city → occupation → darkness_level
 *   → primary_hobbies → saturday_morning → geek_out_on
 *   → together/odd combined → phone → voice_tone_pref → backstory_pick
 *   → completion
 *
 * The combined together/odd screen collects two SlotKinds in sequence
 * (together_we_could then same_weird_if). C1.18 notes both slots remain
 * individually validated by FinalForm; the combined screen submits each
 * via successive POST /answer calls.
 */

import type { SlotKind } from "@/app/onboarding/types/answer"

export type ControlType =
  | "text"
  | "tel"
  | "city"
  | "slider"
  | "chips"
  | "radio"
  | "scenarios"
  | "hobbies"
  | "archetype"
  | "dual_textarea"
  | "textarea"

export interface ScreenConfig {
  /** Screen index 0..14 (welcome=0, completion=14). */
  index: number
  /** SlotKind being collected, or null for welcome / completion screens. */
  slot: SlotKind | null
  /** Optional second slot — only set for the combined together/odd screen. */
  secondSlot?: SlotKind
  /** Control dispatched per slot. */
  control: ControlType | null
  /** Headline rendered above the control (third-person narrator voice). */
  headline: string
  /**
   * Why-we-ask helper — third-person narrator voice (C1.20). Per-slot text
   * tailoring backstory + Nikita's persona/city/age/interests for compatibility.
   */
  whyWeAsk: string | null
  /** Show the "Halfway. Six down, six to go." sunk-cost nudge (C1.19). */
  midpointNudge?: boolean
}

export const WIZARD_SCREENS: readonly ScreenConfig[] = [
  {
    index: 0,
    slot: null,
    control: null,
    headline: "let's begin.",
    whyWeAsk: null,
  },
  {
    index: 1,
    slot: "display_name",
    control: "text",
    headline: "what should she call you?",
    whyWeAsk: "Your name shapes how Nikita addresses you in every reply.",
  },
  {
    index: 2,
    slot: "age",
    control: "text",
    headline: "how old are you?",
    whyWeAsk: "Age tunes Nikita's references, slang, and the shared cultural floor.",
  },
  {
    index: 3,
    slot: "city",
    control: "city",
    headline: "where do you live?",
    whyWeAsk: "Your city sets where Nikita lives and what nights look like.",
  },
  {
    index: 4,
    slot: "occupation",
    control: "text",
    headline: "what do you do?",
    whyWeAsk: "Your work shapes the rhythm Nikita slots into around you.",
  },
  {
    index: 5,
    slot: "darkness_level",
    control: "slider",
    headline: "how dark can she go?",
    whyWeAsk: "Calibrates Nikita's edge: from playful to bruising honest.",
  },
  {
    index: 6,
    slot: "primary_hobbies",
    control: "hobbies",
    headline: "what do you love?",
    whyWeAsk: "Three to five anchors Nikita can echo back as shared ground.",
  },
  {
    index: 7,
    slot: "saturday_morning",
    control: "scenarios",
    headline: "saturday morning. you're doing what?",
    whyWeAsk: "Reveals tempo: lazy + slow, or up + out, or somewhere between.",
    midpointNudge: true,
  },
  {
    index: 8,
    slot: "geek_out_on",
    control: "textarea",
    headline: "what do you geek out on?",
    whyWeAsk: "The thing you over-explain. Nikita will ask about it on day three.",
  },
  {
    index: 9,
    slot: "together_we_could",
    secondSlot: "same_weird_if",
    control: "dual_textarea",
    headline: "together / odd",
    whyWeAsk: "Two short answers: what we'd do, and the specific weird thing.",
  },
  {
    index: 10,
    slot: "phone",
    control: "tel",
    headline: "phone, in case she calls.",
    whyWeAsk: "E.164 only. Used for the voice line and nothing else.",
  },
  {
    index: 11,
    slot: "voice_tone_pref",
    control: "radio",
    headline: "how should she sound?",
    whyWeAsk: "Voice cadence: text only, voice only, or both depending on time of day.",
  },
  {
    index: 12,
    slot: "backstory_pick",
    control: "archetype",
    headline: "I wrote three versions of us.",
    whyWeAsk: null,
  },
  {
    index: 13,
    slot: null,
    control: null,
    headline: "you're cleared. portal opens.",
    whyWeAsk: null,
  },
  {
    index: 14,
    slot: null,
    control: null,
    headline: "you're cleared. portal opens.",
    whyWeAsk: null,
  },
] as const

export const TOTAL_VISUAL_SCREENS = WIZARD_SCREENS.length
