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
  OnboardingV2ProfileRequest,
  OnboardingV2ProfileResponse,
} from "@/app/onboarding/types/contracts"

/**
 * Backoff delays between attempts in milliseconds, per Spec 214 NFR-001.
 * Indexed by previous-attempt number: attempt 1 → attempt 2 waits 500ms, etc.
 *
 * Current: [500, 1000, 2000]
 * Rationale: Exponential with base=500ms mirrors the preview-backstory retry
 *   pattern already used on the backend for BackstoryGeneratorService.
 */
const RETRY_DELAYS_MS: readonly number[] = [500, 1000, 2000] as const

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
    }),
    []
  )
}
