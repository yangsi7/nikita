/**
 * Screen ordering and per-slot copy for the Spec 216-C cinematic wizard.
 *
 * Visual order (15 screens) per AC C1.1, locked:
 *   welcome → display_name → age → city → occupation → darkness_level
 *   → primary_hobbies → saturday_morning → geek_out_on
 *   → together/odd combined → phone → voice_tone_pref → backstory_pick
 *   → personalizing → completion
 *
 * Index 13 ("personalizing") is a transient handoff screen rendered after
 * `is_complete` flips true while the BE persists the link_code and the FE
 * waits for the redirect. Index 14 ("you're cleared. portal opens.") is the
 * terminal cleared screen. The "cleared / portal" copy is the carve-out
 * exception to the no-`FILE`/`dossier`/`clearance` ban — see
 * `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/feedback_no_file_metaphor_in_wizard.md`
 * (interstitial-level "cleared/portal" copy is the documented carve-out).
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
  | "personalizing"

export interface ScreenConfig {
  /** Screen index 0..14 (welcome=0, completion=14). */
  index: number
  /** SlotKind being collected, or null for welcome / personalizing / completion screens. */
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
    // Personalizing transition card (per AC C1.14): NikitaThinkingDots while
    // BE persists link_code and FE awaits the redirect to /dashboard.
    index: 13,
    slot: null,
    control: "personalizing",
    headline: "personalizing.",
    whyWeAsk: null,
  },
  {
    // Completion screen — narrator voice. "cleared/portal" carve-out
    // documented in feedback_no_file_metaphor_in_wizard.md (interstitial-
    // level "cleared/portal" copy is the documented exception to the
    // FILE/dossier/clearance ban).
    index: 14,
    slot: null,
    control: null,
    headline: "you're cleared. portal opens.",
    whyWeAsk: null,
  },
] as const

export const TOTAL_VISUAL_SCREENS = WIZARD_SCREENS.length

/** Index of the personalizing-transition screen (post-completion handoff). */
export const PERSONALIZING_SCREEN_INDEX = 13

/** Index of the terminal completion screen. */
export const COMPLETION_SCREEN_INDEX = 14

/**
 * Total Pydantic SlotKind values mirrored from `nikita/agents/onboarding/state.py`
 * (`TOTAL_SLOTS: Final[int] = 13`). Used to convert `progress_pct` →
 * count-of-slots-filled when resuming the wizard mid-flow.
 *
 * The wizard fills slots in WIZARD_SCREENS order. Screen 9 covers TWO slots
 * (`together_we_could` then `same_weird_if`); every other slot-collecting
 * screen covers exactly one. Hence 12 visible slot-collecting screens for 13
 * slots. See `screenIndexForSlotsFilled` for the mapping.
 */
export const TOTAL_SLOTS = 13

/**
 * Linear order of slots as the wizard fills them (matches the WIZARD_SCREENS
 * dispatch in `WizardShell.tsx::handleSubmit`). Screen 9 fills two slots
 * sequentially; every other screen fills exactly one.
 */
const SLOT_FILL_ORDER: readonly (
  | "display_name"
  | "age"
  | "city"
  | "occupation"
  | "darkness_level"
  | "primary_hobbies"
  | "saturday_morning"
  | "geek_out_on"
  | "together_we_could"
  | "same_weird_if"
  | "phone"
  | "voice_tone_pref"
  | "backstory_pick"
)[] = [
  "display_name",
  "age",
  "city",
  "occupation",
  "darkness_level",
  "primary_hobbies",
  "saturday_morning",
  "geek_out_on",
  "together_we_could",
  "same_weird_if",
  "phone",
  "voice_tone_pref",
  "backstory_pick",
] as const

/**
 * Map a SlotKind to the WIZARD_SCREENS index that collects it.
 *
 * Note: `same_weird_if` resolves to screen 9 (the combined together/odd
 * screen), since `WizardShell::handleSubmit` submits both slots from one
 * screen. Returns `null` for unknown slot kinds.
 */
export function slotKindToScreenIndex(slot: SlotKind): number | null {
  for (const sc of WIZARD_SCREENS) {
    if (sc.slot === slot) return sc.index
    if (sc.secondSlot === slot) return sc.index
  }
  return null
}

/**
 * Resolve the screen index where the next missing slot is collected, given
 * how many slots the BE has already accepted (derived from
 * `StateResponse.progress_pct`). On `slotsFilled === 0` returns the welcome
 * screen (index 0). On `slotsFilled >= TOTAL_SLOTS` returns the personalizing
 * transition (post-completion). The fill order matches the wizard's actual
 * dispatch order in `WizardShell::handleSubmit`.
 */
export function screenIndexForSlotsFilled(slotsFilled: number): number {
  if (slotsFilled <= 0) return 0
  if (slotsFilled >= TOTAL_SLOTS) return PERSONALIZING_SCREEN_INDEX
  // Look up the (slotsFilled)-th slot in fill order — that's the next slot
  // the wizard should collect — then map it to its screen.
  const nextSlot = SLOT_FILL_ORDER[slotsFilled]
  if (!nextSlot) return 0
  return slotKindToScreenIndex(nextSlot) ?? 0
}

/**
 * Convert `StateResponse.progress_pct` (0..100, BE-computed cumulative) to
 * the number of slots the BE has accepted. Rounds to the nearest integer
 * since FE↔BE may drift by sub-percent due to int truncation in the BE.
 */
export function slotsFilledFromProgressPct(progressPct: number): number {
  if (progressPct <= 0) return 0
  if (progressPct >= 100) return TOTAL_SLOTS
  return Math.round((progressPct / 100) * TOTAL_SLOTS)
}
