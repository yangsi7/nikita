/**
 * Tests for useDetailedScores hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { DetailedScoreHistory } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getDetailedScoreHistory: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useDetailedScores } from "@/hooks/use-detailed-scores"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockDetailedScores: DetailedScoreHistory = {
  points: [
    {
      id: "ds-1",
      score: 60,
      chapter: 2,
      event_type: "message",
      recorded_at: "2026-03-20T10:00:00Z",
      intimacy_delta: 0.5,
      passion_delta: 0.2,
      trust_delta: 0.3,
      secureness_delta: 0.1,
      score_delta: 1.5,
      conversation_id: "conv-1",
    },
    {
      id: "ds-2",
      score: 62,
      chapter: 2,
      event_type: "chapter_advance",
      recorded_at: "2026-03-21T10:00:00Z",
      intimacy_delta: null,
      passion_delta: null,
      trust_delta: null,
      secureness_delta: null,
      score_delta: null,
      conversation_id: null,
    },
  ],
  total_count: 2,
}

describe("useDetailedScores", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getDetailedScoreHistory).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useDetailedScores(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches detailed scores with default 30 days", async () => {
    vi.mocked(portalApi.getDetailedScoreHistory).mockResolvedValue(mockDetailedScores)

    const { result } = renderHook(() => useDetailedScores(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getDetailedScoreHistory).toHaveBeenCalledWith(30)
    expect(result.current.data?.points).toHaveLength(2)
    expect(result.current.data?.points[0].score_delta).toBe(1.5)
  })

  it("passes custom days parameter", async () => {
    vi.mocked(portalApi.getDetailedScoreHistory).mockResolvedValue(mockDetailedScores)

    const { result } = renderHook(() => useDetailedScores(7), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getDetailedScoreHistory).toHaveBeenCalledWith(7)
  })

  it("includes days in query key for cache isolation", async () => {
    vi.mocked(portalApi.getDetailedScoreHistory).mockResolvedValue(mockDetailedScores)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useDetailedScores(14), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "detailed-scores", 14])
    expect(cached).toEqual(mockDetailedScores)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getDetailedScoreHistory).mockRejectedValue({ detail: "Server error", status: 500 })

    const { result } = renderHook(() => useDetailedScores(), { wrapper })

    await waitFor(() => expect(portalApi.getDetailedScoreHistory).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
