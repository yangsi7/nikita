/**
 * Tests for useEmotionalState hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { EmotionalStateResponse } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getEmotionalState: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useEmotionalState } from "@/hooks/use-emotional-state"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockEmotionalState: EmotionalStateResponse = {
  state_id: "es-001",
  arousal: 0.6,
  valence: 0.7,
  dominance: 0.5,
  intimacy: 0.8,
  conflict_state: "none",
  conflict_started_at: null,
  conflict_trigger: null,
  description: "Feeling warm and affectionate",
  last_updated: "2026-03-20T15:00:00Z",
}

describe("useEmotionalState", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("returns emotional state data on success", async () => {
    vi.mocked(portalApi.getEmotionalState).mockResolvedValue(mockEmotionalState)

    const { result } = renderHook(() => useEmotionalState(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(mockEmotionalState)
    expect(result.current.data?.arousal).toBe(0.6)
    expect(result.current.data?.conflict_state).toBe("none")
  })

  it("uses correct query key ['portal', 'emotional-state']", async () => {
    vi.mocked(portalApi.getEmotionalState).mockResolvedValue(mockEmotionalState)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useEmotionalState(), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "emotional-state"])
    expect(cached).toEqual(mockEmotionalState)
  })

  it("invokes queryFn on failure (retry:2 defers isError)", async () => {
    vi.mocked(portalApi.getEmotionalState).mockRejectedValue({ detail: "Not found", status: 404 })

    const { result } = renderHook(() => useEmotionalState(), { wrapper })

    // Verify the queryFn was called; isError only appears after all retries
    await waitFor(() => expect(portalApi.getEmotionalState).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getEmotionalState).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useEmotionalState(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })
})
