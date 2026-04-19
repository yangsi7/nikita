/**
 * useOnboardingAPI — typed wrappers for the onboarding HTTP surface.
 *
 * Spec 214 PR 214-A: provides the four endpoint helpers the wizard consumes
 * (previewBackstory, submitProfile, patchProfile, selectBackstory) plus a
 * shared `withRetry` helper with the exponential-backoff policy mandated by
 * NFR-001.
 *
 * Retry policy:
 *   - GET / PUT / PATCH (idempotent): up to 3 attempts with delays
 *     500ms / 1000ms / 2000ms (cumulative 3.5s tail latency under failure).
 *   - POST (non-idempotent, e.g. submitProfile): NEVER retried — server may
 *     have already processed the request. Caller must surface errors.
 */

"use client"

import { useMemo } from "react"

import { api } from "@/lib/api/client"
import type {
  BackstoryChoiceRequest,
  BackstoryPreviewRequest,
  BackstoryPreviewResponse,
  LinkCodeResponse,
  OnboardingV2ProfileRequest,
  OnboardingV2ProfileResponse,
} from "@/app/onboarding/types/contracts"
import { normalizeUserInput } from "@/app/onboarding/types/ControlSelection"
import type {
  ConverseRequest,
  ConverseResponse,
} from "@/app/onboarding/types/converse"

/**
 * Backoff delays between attempts in milliseconds, per Spec 214 NFR-001.
 * Indexed by previous-attempt number: attempt 1 → attempt 2 waits 500ms,
 * attempt 2 → attempt 3 waits 1000ms.
 *
 * Current: [500, 1000]   (cumulative tail latency ≤ 1.5s)
 * Prior: [500, 1000, 2000] (PR-A iter-1; QA nitpick — third entry was dead
 *   code because MAX_ATTEMPTS=3 only consumes 2 delays. Removed for
 *   spec-vs-code coherence.)
 * Rationale: Exponential with base=500ms mirrors the preview-backstory retry
 *   pattern already used on the backend for BackstoryGeneratorService.
 */
const RETRY_DELAYS_MS: readonly number[] = [500, 1000] as const

/** Max total attempts (initial + retries). */
const MAX_ATTEMPTS = 3

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"

/** HTTP methods safe to retry (idempotent per RFC 9110). */
const RETRYABLE_METHODS: ReadonlySet<HttpMethod> = new Set<HttpMethod>([
  "GET",
  "PUT",
  "PATCH",
  "DELETE",
])

/**
 * Invokes `op` with exponential backoff on failure. Only retries for
 * idempotent methods. On exhaustion, re-throws the last error.
 */
export async function withRetry<T>(
  op: () => Promise<T>,
  opts: { method: HttpMethod }
): Promise<T> {
  const retryable = RETRYABLE_METHODS.has(opts.method)
  let lastError: unknown

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    try {
      return await op()
    } catch (err) {
      lastError = err
      if (!retryable) {
        throw err
      }
      const delay = RETRY_DELAYS_MS[attempt]
      if (delay === undefined || attempt === MAX_ATTEMPTS - 1) {
        throw err
      }
      await sleep(delay)
    }
  }

  throw lastError
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export interface UseOnboardingAPI {
  /** POST /onboarding/preview-backstory — Step 8. Retryable. */
  previewBackstory: (body: BackstoryPreviewRequest) => Promise<BackstoryPreviewResponse>
  /** POST /onboarding/profile — Step 10 commit. NEVER retried (non-idempotent). */
  submitProfile: (body: OnboardingV2ProfileRequest) => Promise<OnboardingV2ProfileResponse>
  /** PATCH /onboarding/profile — fire-and-forget per-step update. Retryable. */
  patchProfile: (body: Partial<OnboardingV2ProfileRequest>) => Promise<OnboardingV2ProfileResponse>
  /**
   * PUT /onboarding/profile/chosen-option — commits backstory selection (FR-10.1).
   * Idempotent; safe to retry on network failure.
   */
  selectBackstory: (
    chosenOptionId: string,
    cacheKey: string
  ) => Promise<OnboardingV2ProfileResponse>
  /**
   * POST /portal/link-telegram — mint a 6-char deep-link token (GH #321 REQ-2).
   *
   * NOT idempotent: each call mints a NEW code and consumes any pre-existing
   * code for this user (the repository's `create_link_code` replaces). Caller
   * MUST NOT wrap in withRetry — a silent retry after a transient server
   * error would mint a second code and the first would leak unused in the
   * 10-min TTL window.
   */
  linkTelegram: () => Promise<LinkCodeResponse>
  /**
   * POST /onboarding/converse — Spec 214 FR-11d conversational turn (T3.4).
   *
   * NEVER retried. The server provides idempotency via the `Idempotency-Key`
   * HTTP header (same value as body `turn_id`). Client generates the turn_id
   * via `crypto.randomUUID()` on each user input. On 429, the caller renders
   * `nikita_reply` as an in-character bubble (no red banner) and honors the
   * `Retry-After` response header. See AC-T3.4.1 / AC-T3.4.2.
   *
   * Optional `signal`: lets the caller abort the request (used to wire the
   * reducer's `timeout` action via `AbortSignal.timeout(CONVERSATION_AGENT_TIMEOUT_MS)`).
   */
  converse: (req: ConverseRequest, signal?: AbortSignal) => Promise<ConverseResponse>
}

/**
 * Hook factory that returns the typed onboarding API wrappers. Memoized so
 * callers passing `useOnboardingAPI()` result into effect deps don't thrash.
 */
export function useOnboardingAPI(): UseOnboardingAPI {
  return useMemo<UseOnboardingAPI>(
    () => ({
      previewBackstory: (body) =>
        withRetry(
          () => api.post<BackstoryPreviewResponse>("/onboarding/preview-backstory", body),
          { method: "POST" }
        ),
      submitProfile: (body) =>
        withRetry(
          () => api.post<OnboardingV2ProfileResponse>("/onboarding/profile", body),
          { method: "POST" }
        ),
      patchProfile: (body) =>
        withRetry(
          () => api.patch<OnboardingV2ProfileResponse>("/onboarding/profile", body),
          { method: "PATCH" }
        ),
      selectBackstory: (chosenOptionId, cacheKey) => {
        const requestBody: BackstoryChoiceRequest = {
          chosen_option_id: chosenOptionId,
          cache_key: cacheKey,
        }
        return withRetry(
          () =>
            api.put<OnboardingV2ProfileResponse>(
              "/onboarding/profile/chosen-option",
              requestBody
            ),
          { method: "PUT" }
        )
      },
      // GH #321 REQ-2: direct api.post, no withRetry. See interface docstring.
      linkTelegram: () => api.post<LinkCodeResponse>("/portal/link-telegram"),
      // Spec 214 T3.4: direct api.post, no withRetry (server is idempotent
      // via Idempotency-Key header; client retry would race the cache TTL).
      converse: (req, signal) => {
        const turnId = req.turn_id ?? crypto.randomUUID()
        const body: ConverseRequest = {
          conversation_history: req.conversation_history,
          user_input: normalizeUserInput(req.user_input),
          locale: req.locale ?? "en",
          turn_id: turnId,
        }
        return api.post<ConverseResponse>(
          "/portal/onboarding/converse",
          body,
          { "Idempotency-Key": turnId },
          signal
        )
      },
    }),
    []
  )
}
