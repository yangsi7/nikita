import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// Mock the apiClient transport — only the GET is exercised by this hook
vi.mock("@/lib/api/client", () => {
  return {
    api: {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  }
})

import { act, renderHook } from "@testing-library/react"

import { useOnboardingPipelineReady } from "@/app/onboarding/hooks/use-pipeline-ready"
import { api } from "@/lib/api/client"

// Spec 214 PR 214-A — T103 (RED)
// Tests AC-5.1 (poll fires on interval), AC-5.2 (stops on terminal state),
// AC-5.3 (hard-cap at maxWaitMs), AC-5.6 (429 surfaces error).
//
// The hook signature (per spec FR-5):
//   useOnboardingPipelineReady({ userId, enabled, pollIntervalMs, maxWaitMs })
//     → { state, venueResearchStatus, backstoryAvailable, timedOut, error }

const mocked = api as unknown as {
  get: ReturnType<typeof vi.fn>
}

const USER = "u-1"

const okResponse = (overrides: Record<string, unknown> = {}) => ({
  state: "pending",
  message: null,
  checked_at: "2026-04-16T08:00:00.000Z",
  venue_research_status: "pending",
  backstory_available: false,
  wizard_step: null,
  ...overrides,
})

describe("useOnboardingPipelineReady — polling cadence (spec FR-5, AC-5.1)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocked.get.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("does NOT poll when disabled", async () => {
    const { result } = renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: false,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )
    // Initial state before any poll (spec line 853: initial venueResearchStatus is "pending"; state is null)
    expect(result.current.state).toBeNull()
    expect(result.current.venueResearchStatus).toBe("pending")
    expect(result.current.backstoryAvailable).toBe(false)
    expect(result.current.timedOut).toBe(false)
    expect(result.current.error).toBeNull()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(mocked.get).not.toHaveBeenCalled()
  })

  it("fires the first poll immediately on mount, then on every pollIntervalMs (AC-5.1)", async () => {
    mocked.get.mockResolvedValue(okResponse({ state: "pending" }))
    renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: true,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )
    // First poll fires synchronously after mount
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(mocked.get).toHaveBeenCalledTimes(1)
    expect(mocked.get).toHaveBeenCalledWith(`/onboarding/pipeline-ready/${USER}`)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(2)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(3)
  })
})

describe("useOnboardingPipelineReady — terminal states (spec FR-5, AC-5.2)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocked.get.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("stops polling once state === 'ready'", async () => {
    mocked.get
      .mockResolvedValueOnce(okResponse({ state: "pending" }))
      .mockResolvedValueOnce(okResponse({ state: "ready", venue_research_status: "complete", backstory_available: true }))

    const { result } = renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: true,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(2)
    expect(result.current.state).toBe("ready")
    expect(result.current.venueResearchStatus).toBe("complete")
    expect(result.current.backstoryAvailable).toBe(true)

    // Subsequent intervals must NOT trigger more requests
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(2)
  })

  it("stops polling once state === 'failed'", async () => {
    mocked.get.mockResolvedValueOnce(okResponse({ state: "failed" }))
    renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: true,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(mocked.get).toHaveBeenCalledTimes(1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(1)
  })
})

describe("useOnboardingPipelineReady — hard cap (spec FR-5, AC-5.3)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocked.get.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("flags timedOut and stops polling at maxWaitMs (default 20s per PIPELINE_GATE_MAX_WAIT_S)", async () => {
    mocked.get.mockResolvedValue(okResponse({ state: "pending" }))
    const { result } = renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: true,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )

    // Advance past maxWaitMs — the hard-cap setTimeout fires at exactly 20s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_500)
    })
    expect(result.current.timedOut).toBe(true)

    const callsAtTimeout = mocked.get.mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(mocked.get).toHaveBeenCalledTimes(callsAtTimeout)
  })
})

describe("useOnboardingPipelineReady — rate-limit surfacing (spec FR-5, AC-5.6)", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mocked.get.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("surfaces a 429 rate-limit error and stops polling", async () => {
    const rateLimitErr = { status: 429, detail: "Too many requests" }
    mocked.get.mockRejectedValue(rateLimitErr)
    const { result } = renderHook(() =>
      useOnboardingPipelineReady({
        userId: USER,
        enabled: true,
        pollIntervalMs: 2000,
        maxWaitMs: 20000,
      })
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(result.current.error).not.toBeNull()
    expect(result.current.error?.status).toBe(429)

    const callsAfter429 = mocked.get.mock.calls.length
    await vi.advanceTimersByTimeAsync(10_000)
    expect(mocked.get).toHaveBeenCalledTimes(callsAfter429)
  })
})
