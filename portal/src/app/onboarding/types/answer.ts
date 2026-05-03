/**
 * AnswerRequest / AnswerResponse / StateResponse — TypeScript mirrors of
 * `nikita/agents/onboarding/answer_contracts.py` (Spec 216-B3).
 *
 * Wire shapes are validated by Pydantic on the backend; the FE reflects
 * those shapes at compile time. Keep this file in lockstep with
 * `answer_contracts.py` — any drift surfaces in the wizard's discriminated
 * union handling.
 */

/** 13 SlotKind enum members per `nikita/agents/onboarding/question_registry.py`. */
export type SlotKind =
  | "display_name"
  | "age"
  | "occupation"
  | "city"
  | "darkness_level"
  | "primary_hobbies"
  | "saturday_morning"
  | "geek_out_on"
  | "together_we_could"
  | "same_weird_if"
  | "voice_tone_pref"
  | "backstory_pick"
  | "phone"

/** ChipOption — mirrors `nikita/agents/onboarding/cohort_chips.py:ChipOption`. */
export interface ChipOption {
  value: string
  label: string
}

/** 12 archetype labels — locked taxonomy per `nikita/agents/onboarding/archetypes.py`. */
export type ArchetypeLabel =
  | "the runner"
  | "the maker"
  | "the watcher"
  | "the climber"
  | "the seeker"
  | "the architect"
  | "the survivor"
  | "the rebel"
  | "the romantic"
  | "the wanderer"
  | "the host"
  | "the fugitive"

export const ARCHETYPE_LABELS: readonly ArchetypeLabel[] = [
  "the runner",
  "the maker",
  "the watcher",
  "the climber",
  "the seeker",
  "the architect",
  "the survivor",
  "the rebel",
  "the romantic",
  "the wanderer",
  "the host",
  "the fugitive",
] as const

/** ArchetypeCard — mirrors `nikita/agents/onboarding/archetypes.py:ArchetypeCard`. */
export interface ArchetypeCard {
  label: ArchetypeLabel
  prose: string
  archetype_seed: string
}

/** SlotDelta — extracted slot payload; keys vary by slot kind. */
export interface SlotDelta {
  kind: SlotKind
  value: unknown
}

/** Happy-path turn output (envelope.kind === "success"). */
export interface TurnOutputEnvelope {
  kind: "success"
  delta: SlotDelta | null
  reply: string
  next_slot_kind: SlotKind | null
  cohort_chips?: ChipOption[] | null
  archetype_cards?: ArchetypeCard[] | null
}

/** Graceful re-ask (envelope.kind === "failure"). */
export interface TurnFailureEnvelope {
  kind: "failure"
  explanation: string
  last_slot_kind: SlotKind | null
}

/** POST /api/v1/onboarding/answer request body. */
export interface AnswerRequest {
  slot_kind: SlotKind
  value: string
  turn_id: string
  conversation_id?: string | null
}

/** POST /api/v1/onboarding/answer response body. */
export interface AnswerResponse {
  output: TurnOutputEnvelope | TurnFailureEnvelope
  progress_pct: number
  is_complete: boolean
  link_code?: string | null
  conversation_id: string
  meta?: Record<string, string> | null
}

/** GET /api/v1/onboarding/state response body — read-only state projection. */
export interface StateResponse {
  last_assistant_turn: Record<string, unknown> | null
  progress_pct: number
  is_complete: boolean
  link_code?: string | null
  elided_extracted: Record<string, unknown>
  conversation_id: string | null
}
