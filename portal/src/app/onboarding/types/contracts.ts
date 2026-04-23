/**
 * TypeScript mirror of nikita/onboarding/contracts.py
 *
 * Spec 214 Appendix B is the canonical mapping for these types — any drift
 * between this module and the Python source breaks the wizard contract.
 *
 * Interfaces only — runtime validation lives in `portal/src/app/onboarding/schemas.ts`
 * (zod) for form-level guards. The Python backend is the source of truth for
 * acceptance and the contracts are FROZEN per Spec 213; Spec 214 adds two
 * additive items only:
 *   - `BackstoryChoiceRequest` (FR-10.1) — body of PUT /profile/chosen-option
 *   - `PipelineReadyResponse.wizard_step` (FR-10.2) — optional resume hint
 *
 * No runtime imports from this file should pull in zod or other validators.
 */

// ---------------------------------------------------------------------------
// Pipeline state alias
// ---------------------------------------------------------------------------

export type PipelineReadyState = "pending" | "ready" | "degraded" | "failed"

// ---------------------------------------------------------------------------
// BackstoryOption
// ---------------------------------------------------------------------------

export type BackstoryTone = "romantic" | "intellectual" | "chaotic"

export interface BackstoryOption {
  id: string
  venue: string
  context: string
  the_moment: string
  unresolved_hook: string
  tone: BackstoryTone
}

// ---------------------------------------------------------------------------
// OnboardingV2ProfileRequest / Response
// ---------------------------------------------------------------------------

export type SocialScene = "techno" | "art" | "food" | "cocktails" | "nature"

export type LifeStage =
  | "tech"
  | "finance"
  | "creative"
  | "student"
  | "entrepreneur"
  | "other"

export interface OnboardingV2ProfileRequest {
  location_city: string
  social_scene: SocialScene
  drug_tolerance: number
  life_stage?: LifeStage | null
  interest?: string | null
  phone?: string | null
  name?: string | null
  age?: number | null
  occupation?: string | null
  /** Last completed wizard step (1-11) for server-side resume detection. */
  wizard_step?: number | null
}

export interface OnboardingV2ProfileResponse {
  user_id: string
  pipeline_state: PipelineReadyState
  backstory_options: BackstoryOption[]
  /** ALWAYS null from Spec 213 endpoints. Populated only by FR-10.1 PUT. */
  chosen_option?: BackstoryOption | null
  poll_endpoint: string
  poll_interval_seconds: number
  poll_max_wait_seconds: number
}

// ---------------------------------------------------------------------------
// BackstoryPreviewRequest / Response
// ---------------------------------------------------------------------------

/**
 * Note: SPEC-INTENTIONAL ASYMMETRY — `occupation` here has no min-length.
 * The preview endpoint accepts an empty string (buckets to "other" in
 * compute_backstory_cache_key); only the final POST /profile applies the
 * stricter min_length=1 constraint via OnboardingV2ProfileRequest.
 * See contracts.py:143-150 for the canonical comment.
 */
export interface BackstoryPreviewRequest {
  city: string
  social_scene: SocialScene
  /** Mirrors UserOnboardingProfile.darkness_level — backend maps drug_tolerance → darkness_level. */
  darkness_level: number
  life_stage?: LifeStage | null
  interest?: string | null
  age?: number | null
  occupation?: string | null
}

export interface BackstoryPreviewResponse {
  scenarios: BackstoryOption[]
  venues_used: string[]
  /**
   * Opaque cache key — MUST be persisted to wizard state between step 8 and
   * the subsequent PUT /profile/chosen-option call (it is the required
   * `cache_key` field of `BackstoryChoiceRequest`).
   */
  cache_key: string
  degraded: boolean
}

// ---------------------------------------------------------------------------
// PipelineReadyResponse (extended with wizard_step in Spec 214 FR-10.2)
// ---------------------------------------------------------------------------

export interface PipelineReadyResponse {
  state: PipelineReadyState
  message?: string | null
  /** ISO-8601 timestamp. */
  checked_at: string
  venue_research_status: "pending" | "complete" | "failed" | "cache_hit"
  backstory_available: boolean
  /**
   * NEW (Spec 214 FR-10.2). Reads `onboarding_profile.wizard_step` JSONB or
   * null when not yet set. Used for cross-device wizard resume.
   */
  wizard_step?: number | null
}

// ---------------------------------------------------------------------------
// BackstoryChoiceRequest (NEW in Spec 214 FR-10.1)
// ---------------------------------------------------------------------------

export interface BackstoryChoiceRequest {
  /** Opaque scenario id (sha256(cache_key:index)[:12]). 1-64 chars. */
  chosen_option_id: string
  /**
   * Echoed cache_key from BackstoryPreviewResponse. The backend recomputes
   * its own and rejects mismatches with HTTP 403 — required for the
   * idempotency guard + stale-selection rejection.
   */
  cache_key: string
}

// ---------------------------------------------------------------------------
// LinkCodeResponse (GH #321 REQ-2) — POST /portal/link-telegram
// ---------------------------------------------------------------------------

/**
 * Response from POST /portal/link-telegram. The portal mints a single-use,
 * 10-minute-TTL 6-character uppercase alphanumeric code that the bot
 * consumes via `/start <code>` to bind users.telegram_id.
 *
 * Mirror of `nikita.api.schemas.portal.LinkCodeResponse`.
 */
export interface LinkCodeResponse {
  /** 6-char uppercase alphanumeric (`^[A-Z0-9]{6}$`). */
  code: string
  /** ISO-8601 timestamp. Server enforces a 10-min TTL. */
  expires_at: string
  /** Human-readable string. UI composes its own CTA URL from `code`. */
  instructions: string
}

// ---------------------------------------------------------------------------
// ConversationProfileResponse (GH #385 — GET /onboarding/conversation)
// ---------------------------------------------------------------------------

/**
 * Response from GET /onboarding/conversation.
 * Returns prior conversation turns so the wizard can hydrate on page reload.
 * Mirror of `ConversationProfileResponse` in portal_onboarding.py.
 */
export interface ConversationProfileResponse {
  /** Prior conversation turns in chronological order. Empty array if none. */
  conversation: Array<{
    role: "nikita" | "user"
    content: string
    timestamp: string
    source?: "llm" | "fallback" | "idempotent" | "validation_reject" | null
    extracted?: Record<string, unknown>
  }>
  /** Progress percentage (0-100) derived from committed extracted fields. */
  progress_pct: number
  /** All extracted fields committed to the user's profile (across all sessions, not just the current one). */
  elided_extracted: Record<string, unknown>
  /** Active link code if one exists for the user (AC-11d.7). Null if not yet minted. */
  link_code?: string | null
  /** ISO-8601 expiry timestamp for the active link code. */
  link_expires_at?: string | null
  /** True if the link code exists but has expired — wizard should re-mint on next complete. */
  link_code_expired?: boolean | null
}

// ---------------------------------------------------------------------------
// ErrorResponse — flat shape used by handler-raised errors (403/404/409/429)
// ---------------------------------------------------------------------------

/**
 * Pydantic 422 (schema-shape violation) returns a list shape under `detail`.
 * Handler-raised errors return flat `{ detail: string }`. Consumers MUST
 * branch on `typeof detail === "string"` vs `Array.isArray(detail)`.
 */
export interface ErrorResponse {
  detail: string
}
