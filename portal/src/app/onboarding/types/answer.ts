/**
 * AnswerRequest / AnswerResponse / StateResponse — TypeScript mirrors of
 * `nikita/agents/onboarding/answer_contracts.py` (Spec 216-B3).
 *
 * Wire shapes are validated by Pydantic on the backend; the FE reflects
 * those shapes at compile time. Keep this file in lockstep with
 * `answer_contracts.py` — any drift surfaces in the wizard's discriminated
 * union handling.
 */

/** SlotKind enum members per `nikita/agents/onboarding/question_registry.py`.
 *  217-3A.3 added `identity_pair` (compound name+age) for FR-10a. */
export type SlotKind =
  | "display_name"
  | "age"
  | "identity_pair"
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

/** POST /api/v1/onboarding/answer request body. The `value` field is
 *  string-typed for scalar slots; compound slots (e.g. identity_pair)
 *  send JSON-encoded payloads as strings — the BE parses by `slot_kind`. */
export interface AnswerRequest {
  slot_kind: SlotKind
  value: string
  turn_id: string
  conversation_id?: string | null
}

// ---------------------------------------------------------------------------
// AnswerResponse — 6-branch flat discriminated union.
// Mirrors `nikita/api/schemas/onboarding.py:AnswerResponse` (Spec 217-3A
// AC-9.1bis + GH #561 amendment adding the 6th `completion` branch).
// Each branch flattens its payload onto the envelope (no `payload:` nesting)
// per QA iter-1 ruling on PR #560.
// ---------------------------------------------------------------------------

/** Agent intercepted with a reaction; deterministic question STAYS pending. */
export interface ReactionResponse {
  kind: "reaction"
  reaction_text: string
}

/** Agent emitted a clarifying follow-up; FE locks deterministic chrome. */
export interface FollowUpResponse {
  kind: "followup"
  question_text: string
  target_slot: string | null
}

/** Partial-validation failure (e.g. IdentityPair age bad while name ok).
 *  Valid sub-fields are persisted server-side; FE re-renders preserving
 *  valid entries and surfaces inline errors next to offending fields. */
export interface FieldErrorResponse {
  kind: "field_error"
  /** Sub-field name → human-readable error reason. Always >=1 entry. */
  errors: Record<string, string>
}

/** Agent emitted TurnFailure or output_retries exhausted. */
export interface TurnFailureResponse {
  kind: "turn_failure"
  explanation: string
}

/** Deterministic happy path: slot advanced, next prompt queued. */
export interface DeterministicAdvanceResponse {
  kind: "deterministic_advance"
  next_slot_kind: string | null
  progress_pct: number
  /** ArchetypeCard list emitted on backstory_pick slot; null on other slots
   *  or while the backstory pipeline is still warming. */
  archetype_cards: ArchetypeCard[] | null
}

/** Terminal turn: wizard reached completion (FinalForm validated). */
export interface CompletionResponse {
  kind: "completion"
  is_complete: true
  link_code: string | null
  conversation_id: string
  progress_pct: 100
}

/** Discriminated union; narrow via `response.kind`. */
export type AnswerResponse =
  | ReactionResponse
  | FollowUpResponse
  | FieldErrorResponse
  | TurnFailureResponse
  | DeterministicAdvanceResponse
  | CompletionResponse

/** GET /api/v1/onboarding/state response body — read-only state projection. */
export interface StateResponse {
  last_assistant_turn: Record<string, unknown> | null
  progress_pct: number
  is_complete: boolean
  link_code?: string | null
  elided_extracted: Record<string, unknown>
  conversation_id: string | null
}
