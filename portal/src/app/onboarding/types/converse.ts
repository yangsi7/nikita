/**
 * Converse request/response TypeScript models — mirrors the Pydantic shapes
 * in `nikita/agents/onboarding/converse_contracts.py` (Spec 214 FR-11d).
 */

import type { ControlSelection, PromptType } from "./ControlSelection"

/** Per-turn entry in the conversation_history array. */
export interface Turn {
  role: "nikita" | "user"
  content: string
  extracted?: Record<string, unknown> | null
  timestamp: string
  source?: "llm" | "fallback" | "idempotent" | "validation_reject" | null
  /**
   * Client-only flag set when the user rejects a confirmation (Fix-that).
   * Rendered with `opacity: 0.5`. Server never sees this field — the
   * api.converse() serializer strips it before POSTing (GH #376).
   */
  superseded?: boolean
}

export interface ConverseRequest {
  conversation_history: Turn[]
  user_input: string | ControlSelection
  locale?: "en"
  turn_id?: string
}

export interface ConverseResponse {
  nikita_reply: string
  extracted_fields: Record<string, unknown>
  confirmation_required: boolean
  next_prompt_type: PromptType
  next_prompt_options?: string[] | null
  progress_pct: number
  conversation_complete: boolean
  source: "llm" | "fallback" | "idempotent" | "validation_reject"
  latency_ms: number
  /** Present only on terminal turn (conversation_complete=true). Spec 214 AC-11d.7. */
  link_code?: string | null
  /** ISO-8601 expiry for the link code. Present only on terminal turn. */
  link_expires_at?: string | null
}
