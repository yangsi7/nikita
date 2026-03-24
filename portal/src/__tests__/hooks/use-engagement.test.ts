/**
 * Tests for useEngagement hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { EngagementData } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getEngagement: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useEngagement } from "@/hooks/use-engagement"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockEngagement: EngagementData = {
  state: "in_zone",
  multiplier: 1.2,
  calibration_score: 62,
  consecutive_in_zone: 3,
  consecutive_clingy_days: 0,
  consecutive_distant_days: 0,
  recent_transitions: [
    {
      from_state: "calibrating",
      to_state: "in_zone",
      reason: "score improved",
      created_at: "2026-03-19T12:00:00Z",
    },
  ],
}

describe("useEngagement", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns engagement data on success", async () => {
    vi.mocked(portalApi.getEngagement).mockResolvedValue(mockEngagement)

    const { result } = renderHook(() => useEngagement(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockEngagement)
    expect(result.current.data?.state).toBe("in_zone")
    expect(result.current.data?.multiplier).toBe(1.2)
  })

  it("uses correct query key ['portal', 'engagement']", async () => {
    vi.mocked(portalApi.getEngagement).mockResolvedValue(mockEngagement)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useEngagement(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "engagement"])
    expect(cached).toEqual(mockEngagement)
  })

  it("invokes queryFn on failure (retry:2 defers isError)", async () => {
    vi.mocked(portalApi.getEngagement).mockRejectedValue({ detail: "Unauthorized", status: 401 })

    const { result } = renderHook(() => useEngagement(), { wrapper })

    // Verify the queryFn was called; isError only appears after all retries
    await waitFor(() => expect(portalApi.getEngagement).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
