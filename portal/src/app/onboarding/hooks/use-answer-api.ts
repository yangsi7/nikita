/**
 * useAnswerAPI — typed wrappers for the Spec 216-B3 onboarding endpoints.
 *
 * POST /api/v1/onboarding/answer  — single-turn stateful submit (idempotent
 *   per `(user_id, turn_id)` pair).
 * GET  /api/v1/onboarding/state   — read-only state projection used to
 *   resume a wizard mid-flow.
 *
 * NEVER retried (POST); the server provides idempotency via the body
 * `turn_id` UUID. Client just retransmits the same `turn_id` on retry.
 */

"use client"

import { useMemo } from "react"

import { api } from "@/lib/api/client"
import type {
  AnswerRequest,
  AnswerResponse,
  StateResponse,
} from "@/app/onboarding/types/answer"

export interface UseAnswerAPI {
  /** POST /api/v1/onboarding/answer — single-turn submit. */
  submitAnswer: (req: AnswerRequest, signal?: AbortSignal) => Promise<AnswerResponse>
  /** GET /api/v1/onboarding/state — read-only projection used on mount/resume. */
  getState: () => Promise<StateResponse>
}

export function useAnswerAPI(): UseAnswerAPI {
  return useMemo<UseAnswerAPI>(
    () => ({
      submitAnswer: (req, signal) =>
        api.post<AnswerResponse>(
          "/onboarding/answer",
          req,
          { "Idempotency-Key": req.turn_id },
          signal
        ),
      getState: () => api.get<StateResponse>("/onboarding/state"),
    }),
    []
  )
}
