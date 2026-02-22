/**
 * Tests for useDecay hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { DecayStatus } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getDecayStatus: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useDecay } from "@/hooks/use-decay"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockDecayActive: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 4,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 56,
  is_decaying: true,
}

const mockDecayGrace: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 20,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 62,
  is_decaying: false,
}

describe("useDecay", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns decay status data on success", async () => {
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayActive)

    const { result } = renderHook(() => useDecay(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockDecayActive)
    expect(result.current.data?.is_decaying).toBe(true)
  })

  it("returns grace period data when not decaying", async () => {
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayGrace)

    const { result } = renderHook(() => useDecay(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.is_decaying).toBe(false)
    expect(result.current.data?.hours_remaining).toBe(20)
  })

  it("uses correct query key ['portal', 'decay']", async () => {
    vi.mocked(portalApi.getDecayStatus).mockResolvedValue(mockDecayActive)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useDecay(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "decay"])
    expect(cached).toEqual(mockDecayActive)
  })

  it("invokes queryFn on failure (retry:2 defers isError)", async () => {
    const apiError = { detail: "Server error", status: 500 }
    vi.mocked(portalApi.getDecayStatus).mockRejectedValue(apiError)

    const { result } = renderHook(() => useDecay(), { wrapper })

    // Verify the queryFn was called; isError only appears after all retries
    await waitFor(() => expect(portalApi.getDecayStatus).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
