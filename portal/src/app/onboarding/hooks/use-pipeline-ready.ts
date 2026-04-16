/**
 * useOnboardingPipelineReady — polls GET /onboarding/pipeline-ready/{user_id}.
 *
 * Spec 214 FR-5 + AC-5.1..5.6. Caller passes the server-driven cadence
 * (`poll_interval_seconds` and `poll_max_wait_seconds` from the POST
 * /onboarding/profile response, each converted to milliseconds). Backend
 * defaults are `PIPELINE_GATE_POLL_INTERVAL_S=2.0` and
 * `PIPELINE_GATE_MAX_WAIT_S=20.0` per `nikita/onboarding/tuning.py`.
 *
 * State machine:
 *   - Enabled + pre-terminal: poll every `pollIntervalMs`; fire once on mount.
 *   - Response `state === "ready"` or `state === "failed"` → stop polling.
 *   - Elapsed ≥ `maxWaitMs` → set `timedOut = true`, stop polling.
 *   - Response throws with `status: 429` (rate limit) → surface via `error`, stop.
 *   - Exposes `wizardStep` (FR-10.2) for cross-device resume hints.
 */

"use client"

import { useEffect, useRef, useState } from "react"

import { api } from "@/lib/api/client"
import type {
  PipelineReadyResponse,
  PipelineReadyState,
} from "@/app/onboarding/types/contracts"

export interface UseOnboardingPipelineReadyParams {
  userId: string
  enabled: boolean
  /** Poll cadence — caller should pass `poll_interval_seconds * 1000`. */
  pollIntervalMs: number
  /** Hard cap — caller should pass `poll_max_wait_seconds * 1000`. */
  maxWaitMs: number
}

export interface PipelineReadyError {
  status: number
  detail: string
}

export interface UseOnboardingPipelineReadyResult {
  state: PipelineReadyState | null
  venueResearchStatus: PipelineReadyResponse["venue_research_status"]
  backstoryAvailable: boolean
  wizardStep: number | null
  timedOut: boolean
  error: PipelineReadyError | null
}

type ApiErrorShape = { status?: unknown; detail?: unknown }

function toPipelineReadyError(err: unknown): PipelineReadyError | null {
  if (typeof err !== "object" || err === null) return null
  const shape = err as ApiErrorShape
  if (typeof shape.status !== "number") return null
  const detail = typeof shape.detail === "string" ? shape.detail : ""
  return { status: shape.status, detail }
}

function isTerminal(state: PipelineReadyState | null): boolean {
  return state === "ready" || state === "failed"
}

/**
 * Hook implementing the FR-5 poll loop.
 *
 * AC-5.1: polls at `pollIntervalMs` cadence via setInterval.
 * AC-5.2: stops immediately when response is terminal.
 * AC-5.3: hard-caps at `maxWaitMs`; sets `timedOut` and stops.
 * AC-5.6: 429 response is surfaced via `error` and polling stops.
 */
export function useOnboardingPipelineReady(
  params: UseOnboardingPipelineReadyParams
): UseOnboardingPipelineReadyResult {
  const { userId, enabled, pollIntervalMs, maxWaitMs } = params

  const [state, setState] = useState<PipelineReadyState | null>(null)
  const [venueResearchStatus, setVenueResearchStatus] =
    useState<PipelineReadyResponse["venue_research_status"]>("pending")
  const [backstoryAvailable, setBackstoryAvailable] = useState<boolean>(false)
  const [wizardStep, setWizardStep] = useState<number | null>(null)
  const [timedOut, setTimedOut] = useState<boolean>(false)
  const [error, setError] = useState<PipelineReadyError | null>(null)

  // Stable refs to avoid stale closures inside the interval callback
  const stoppedRef = useRef<boolean>(false)

  useEffect(() => {
    if (!enabled) return

    stoppedRef.current = false
    let intervalId: ReturnType<typeof setInterval> | null = null
    let timeoutId: ReturnType<typeof setTimeout> | null = null

    const stop = () => {
      stoppedRef.current = true
      if (intervalId !== null) {
        clearInterval(intervalId)
        intervalId = null
      }
      if (timeoutId !== null) {
        clearTimeout(timeoutId)
        timeoutId = null
      }
    }

    const poll = async () => {
      if (stoppedRef.current) return
      try {
        const resp = await api.get<PipelineReadyResponse>(
          `/onboarding/pipeline-ready/${userId}`
        )
        if (stoppedRef.current) return
        setState(resp.state)
        setVenueResearchStatus(resp.venue_research_status)
        setBackstoryAvailable(resp.backstory_available)
        setWizardStep(resp.wizard_step ?? null)
        if (isTerminal(resp.state)) {
          stop()
        }
      } catch (err) {
        if (stoppedRef.current) return
        const pretty = toPipelineReadyError(err)
        setError(pretty)
        stop()
      }
    }

    // AC-5.1: first poll fires immediately on mount, then on cadence.
    // Install the interval BEFORE the first poll so a terminal-on-first-poll
    // response (fast network/mocks) doesn't race with `setInterval` and leave
    // a stray timer (cosmetic but noisy in tests).
    intervalId = setInterval(() => {
      if (stoppedRef.current) return
      void poll()
    }, pollIntervalMs)
    void poll()

    // AC-5.3: hard cap via an independent setTimeout. Triggers at maxWaitMs
    // regardless of poll state and flips timedOut → true.
    timeoutId = setTimeout(() => {
      if (stoppedRef.current) return
      setTimedOut(true)
      stop()
    }, maxWaitMs)

    return () => {
      stop()
    }
  }, [userId, enabled, pollIntervalMs, maxWaitMs])

  return {
    state,
    venueResearchStatus,
    backstoryAvailable,
    wizardStep,
    timedOut,
    error,
  }
}
