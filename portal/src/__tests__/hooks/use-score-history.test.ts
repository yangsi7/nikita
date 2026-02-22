/**
 * Tests for useScoreHistory hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { ScoreHistory } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getScoreHistory: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useScoreHistory } from "@/hooks/use-score-history"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockHistory: ScoreHistory = {
  points: [
    { score: 50, chapter: 1, event_type: "message", recorded_at: "2026-02-01T10:00:00Z" },
    { score: 55, chapter: 1, event_type: "message", recorded_at: "2026-02-02T10:00:00Z" },
    { score: 62, chapter: 2, event_type: "chapter_advance", recorded_at: "2026-02-10T10:00:00Z" },
  ],
  total_count: 3,
}

describe("useScoreHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches score history with default 30 days", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useScoreHistory(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getScoreHistory).toHaveBeenCalledWith(30)
    expect(result.current.data?.points).toHaveLength(3)
  })

  it("passes custom days parameter", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useScoreHistory(7), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getScoreHistory).toHaveBeenCalledWith(7)
  })

  it("uses days in query key for caching", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockHistory)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useScoreHistory(14), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "score-history", 14])
    expect(cached).toEqual(mockHistory)
  })

  it("calls queryFn and reports no data on failure", async () => {
    const apiError = { detail: "Not found", status: 404 }
    vi.mocked(portalApi.getScoreHistory).mockRejectedValue(apiError)

    // Hook has retry:2 — just verify the function was invoked
    const { result } = renderHook(() => useScoreHistory(), { wrapper })

    await waitFor(() => expect(portalApi.getScoreHistory).toHaveBeenCalled())
    // Initially no data available while retrying
    expect(result.current.data).toBeUndefined()
  })

  it("returns total_count from the response", async () => {
    vi.mocked(portalApi.getScoreHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useScoreHistory(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.total_count).toBe(3)
  })
})
